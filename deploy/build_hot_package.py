"""Build a narrow FileVault package from the full-build inputs."""
import argparse
import io
import json
import re
from pathlib import Path
from xml.dom import minidom
from xml.etree import ElementTree as ET
from zipfile import ZIP_DEFLATED, ZipFile

JCR = "http://www.jcp.org/jcr/1.0"
APP_ROOTS = (
    "/apps/wknd-demo/config/org.apache.sling.commons.log.LogManager.factory.config~wknd-weather.cfg.json",
    "/apps/wknd-demo/components/weather",
    "/apps/wknd-demo/components/system-logs",
    "/apps/wknd/clientlibs/clientlib-demo-components",
)
BUNDLE_ROOT = "/apps/wknd-demo/install"
CONTENT_PREFIXES = (
    "/content/wknd/us/en/aem-demo",
    "/content/wknd/us/en/adventures/bali-surf-camp-demo",
    "/conf/wknd/settings/wcm/templates/adventure-page-template-demo",
    "/conf/wknd/settings/wcm/policies/wknd/components/container/adventure-demo",
    "/content/dam/wknd-demo-catalog",
    "/content/dam/wknd-demo-components.jpg",
)


def inside(path, root):
    return path == root or path.startswith(root + "/")


def repository_path(entry):
    return "/" + "/".join(re.sub(r"^_([^_]+)_", r"\1:", p)
                          for p in entry.removeprefix("jcr_root/").split("/"))


def element_children(node):
    return {c.tagName: c for c in node.childNodes if c.nodeType == c.ELEMENT_NODE}


def properties(node):
    return {a.name: a.value for a in node.attributes.values()
            if not a.name.startswith("xmlns:")}


def xml_node(node, attrs, include_children=False):
    with minidom.Document() as doc:
        root = doc.createElementNS(JCR, "jcr:root")
        doc.appendChild(root)
        for attr in node.ownerDocument.documentElement.attributes.values():
            if attr.name.startswith("xmlns:"):
                root.setAttribute(attr.name, attr.value)
        for name, value in attrs.items():
            root.setAttribute(name, value)
        if include_children:
            for child in element_children(node).values():
                root.appendChild(doc.importNode(child, deep=True))
        return doc.toxml(encoding="UTF-8")


def content_delta(previous, current, root, out, guards):
    before, after = properties(previous), properties(current)
    removed = before.keys() - after.keys()
    if removed:
        raise ValueError(f"Property removal requires a reviewed migration: {root} {sorted(removed)}")
    changes = {name: value for name, value in after.items() if before.get(name) != value}
    if changes:
        if "jcr:primaryType" in changes:
            raise ValueError(f"Node type change requires a reviewed migration: {root}")
        guards.append({"path": root, "properties": {name: before.get(name) for name in changes}})
        # AEM's DocView importer requires the existing node type even for updates.
        out[root] = ("update_properties", xml_node(current, {
            "jcr:primaryType": after["jcr:primaryType"], **changes,
        }))
    old, new = element_children(previous), element_children(current)
    if old.keys() - new.keys():
        raise ValueError(f"Node removal requires a reviewed migration: {root}")
    for name, child in new.items():
        path = f"{root}/{name}"
        if name in old:
            content_delta(old[name], child, path, out, guards)
        elif properties(child):
            guards.append({"path": path, "absent": True})
            out[path] = ("merge_properties", xml_node(child, properties(child), True))


def write_package(args):
    filters = ET.Element("workspaceFilter", version="1.0")
    for root in (*APP_ROOTS, BUNDLE_ROOT):
        ET.SubElement(filters, "filter", root=root, mode="replace")
    changes, guards = {}, []
    with ZipFile(args.current) as current, ZipFile(args.baseline) as baseline:
        new_roots = set()
        entries = {n for n in current.namelist() if n.startswith("jcr_root/") and not n.endswith("/")}
        old_entries = set(baseline.namelist())
        for name in sorted(entries | old_entries):
            if not name.startswith("jcr_root/") or name.endswith("/"):
                continue
            path = repository_path(name)
            if not any(inside(path, root) for root in CONTENT_PREFIXES):
                continue
            if name not in entries:
                raise ValueError(f"File removal requires a reviewed migration: {path}")
            if any(inside(path, root) for root in new_roots):
                continue
            after = current.read(name)
            if name in old_entries and after == baseline.read(name):
                continue
            if not name.endswith("/.content.xml"):
                if name in old_entries:
                    raise ValueError(f"Binary replacement requires an explicit asset migration: {path}")
                continue
            root = path.removesuffix("/.content.xml")
            with minidom.parseString(after) as new:
                if name not in old_entries:
                    guards.append({"path": root, "absent": True})
                    changes[root] = ("merge_properties", after)
                    new_roots.add(root)
                    continue
                with minidom.parseString(baseline.read(name)) as old:
                    content_delta(old.documentElement, new.documentElement, root, changes, guards)
        for root, (mode, _) in changes.items():
            ET.SubElement(filters, "filter", root=root, mode=mode)
        with ZipFile(args.output, "w", ZIP_DEFLATED) as out:
            out.writestr("META-INF/vault/filter.xml", ET.tostring(filters, encoding="utf-8"))
            out.writestr("META-INF/vault/properties.xml", (
                '<?xml version="1.0" encoding="UTF-8"?>\n'
                '<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">\n'
                '<properties><entry key="group">wknd-demo</entry>'
                '<entry key="name">wknd-demo-hot</entry>'
                f'<entry key="version">{args.version}</entry>'
                '<entry key="packageType">mixed</entry></properties>'))
            for name in sorted(entries):
                path = repository_path(name)
                if any(inside(path, root) for root in APP_ROOTS):
                    out.writestr(name, current.read(name))
                elif name not in old_entries and any(
                    inside(path, root) and path != f"{root}/.content.xml" for root in new_roots
                ):
                    out.writestr(name, current.read(name))
            for root, (_, xml) in changes.items():
                encoded = "/".join(p.replace(":", "_", 1) if ":" not in p else
                                   "_" + p.replace(":", "_", 1) for p in root.split("/"))
                out.writestr(f"jcr_root{encoded}/.content.xml", xml)
            out.write(args.bundle, f"jcr_root{BUNDLE_ROOT}/weather.jar")
    args.guards.write_text(json.dumps(guards, indent=2), encoding="utf-8")
    print(f"Hot package contains {len(changes)} scoped content nodes; WKND is excluded.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    for name in ("baseline", "current", "bundle", "output", "guards"):
        parser.add_argument(f"--{name}", type=Path, required=True)
    parser.add_argument("--version", required=True)
    args = parser.parse_args()
    if not re.fullmatch(r"[0-9][0-9A-Za-z._-]*", args.version):
        parser.error("Invalid package version")
    write_package(args)
