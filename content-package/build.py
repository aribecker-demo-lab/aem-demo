"""Build the FileVault content package from the pinned WKND release."""
import argparse
import io
import re
from pathlib import Path
from xml.dom import minidom
from zipfile import ZIP_DEFLATED, ZipFile

SAMPLE_PACKAGE = (
    "jcr_root/apps/wknd-packages/content/install/"
    "aem-guides-wknd.ui.content.sample-4.0.4.zip"
)
ADVENTURES = "/content/wknd/us/en/adventures"
SOURCE = f"{ADVENTURES}/bali-surf-camp"
TARGET = f"{ADVENTURES}/bali-surf-camp-demo"
TEMPLATE_SOURCE = "/conf/wknd/settings/wcm/templates/adventure-page-template"
TEMPLATE_TARGET = f"{TEMPLATE_SOURCE}-demo"

FILTER = f"""<?xml version="1.0" encoding="UTF-8"?>
<workspaceFilter version="1.0">
    <filter root="{TARGET}" mode="replace"/>
    <filter root="{TEMPLATE_TARGET}" mode="replace"/>
</workspaceFilter>
"""

PROPERTIES = """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
<properties>
    <entry key="group">wknd-demo</entry>
    <entry key="name">wknd-demo-adventure</entry>
    <entry key="version">1.0.0</entry>
    <entry key="packageType">content</entry>
    <entry key="dependencies">com.adobe.aem.guides:aem-guides-wknd.ui.content.sample:4.0.4</entry>
</properties>
"""


def build_package(wknd_release: Path, output: Path) -> None:
    with ZipFile(wknd_release) as release:
        sample_bytes = release.read(SAMPLE_PACKAGE)
    with ZipFile(io.BytesIO(sample_bytes)) as sample:
        page = sample.read(f"jcr_root{SOURCE}/.content.xml").decode("utf-8")
        template_prefix = f"jcr_root{TEMPLATE_SOURCE}/"
        template_files = {
            name.removeprefix(template_prefix): sample.read(name)
            for name in sample.namelist()
            if name.startswith(template_prefix) and not name.endswith("/")
        }

    template_files[".content.xml"] = template_files[".content.xml"].replace(
        b'jcr:title="Adventure Page Template"',
        b'jcr:title="Adventure Page Template - Demo"',
        1,
    )
    for name in ("structure/.content.xml", "initial/.content.xml"):
        template_files[name] = template_files[name].replace(
            f'cq:template="{TEMPLATE_SOURCE}"'.encode(),
            f'cq:template="{TEMPLATE_TARGET}"'.encode(),
        )

    page, title_count = re.subn(
        'jcr:title="Bali Surf Camp"',
        'jcr:title="Bali Surf Camp — Demo"',
        page,
        count=1,
    )
    if title_count != 1:
        raise ValueError("Expected the Bali Surf Camp page title in WKND 4.0.4")
    page = page.replace(
        'jcr:description="Surfing in Bali',
        'jcr:description="Demo adventure. Surfing in Bali',
        1,
    )
    # Give the copy its own page identity outside the original MSM live copy.
    page = re.sub(
        r'^ *\s*(?:jcr:mixinTypes="\[cq:LiveRelationship\]"|cq:lastRolledout(?:By)?="[^"]*")\n',
        "",
        page,
        flags=re.MULTILINE,
    )
    with minidom.parseString(page) as document:
        tabs = document.getElementsByTagName("tabs")[0]
        bring_tab = next(
            child
            for child in tabs.childNodes
            if child.nodeType == child.ELEMENT_NODE
            and child.getAttribute("cq:panelTitle") == "What to Bring"
        )
        demo_tab = bring_tab.cloneNode(deep=True)
        document.renameNode(demo_tab, None, "demo")
        demo_tab.setAttribute("cq:panelTitle", "Demo")
        tabs.insertBefore(demo_tab, bring_tab.nextSibling)
        page = document.toxml(encoding="UTF-8")

    output.parent.mkdir(parents=True, exist_ok=True)
    with ZipFile(output, "w", compression=ZIP_DEFLATED) as package:
        package.writestr("META-INF/vault/filter.xml", FILTER)
        package.writestr("META-INF/vault/properties.xml", PROPERTIES)
        package.writestr(f"jcr_root{TARGET}/.content.xml", page)
        for name, data in template_files.items():
            package.writestr(f"jcr_root{TEMPLATE_TARGET}/{name}", data)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("wknd_release", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build_package(args.wknd_release, args.output)
