"""Package a verified Render deployment's timeline for AEM diagnostics."""
import argparse
import json
import re
from datetime import datetime
from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


MESSAGES = (
    (re.compile(r"cloning from"), "Source", "Pending", "Cloning", "Render cloned the repository"),
    (re.compile(r"checking out commit"), "Source", "Cloning", "Checked out", "Render checked out the deploy commit"),
    (re.compile(r"exporting to docker image format|exporting to image"), "Image", "Building", "Exporting", "Docker image export"),
    (re.compile(r"pushing image"), "Image", "Exported", "Pushing", "Render pushed the image"),
    (re.compile(r"successfully pushed|image push.*complete"), "Image", "Pushing", "Published", "Image published"),
    (re.compile(r"\bdeploying\b"), "Service", "Building", "Deploying", "Render started the rollout"),
    (re.compile(r"service is live|service is now live"), "Service", "Deploying", "Live", "Render announced that the service was live"),
    (re.compile(r"startup completed|startup complete"), "AEM", "Starting", "Started", "AEM reported startup complete"),
    (re.compile(r"launching .*aem|starting .*quickstart"), "AEM", "Pending", "Starting", "AEM launcher started"),
)


def timeline(deploy, logs):
    deploy_id = deploy["id"]
    commit = deploy["commit"]["id"]
    if not re.fullmatch(r"dep-[a-z0-9]+", deploy_id) or not re.fullmatch(r"[a-f0-9]{40}", commit):
        raise ValueError("Expected a Render deployment ID and full commit SHA.")
    if deploy["status"] != "live":
        raise ValueError("The Render deployment must be live.")
    rows = set()

    def add(timestamp, kind, entity, before, after, detail):
        datetime.fromisoformat(timestamp.replace("Z", "+00:00"))
        rows.add((timestamp, kind, entity, deploy_id, commit, before, after, detail))

    add(deploy["createdAt"], "Render", "Deployment", "—", "Requested", "Render deployment created")
    if deploy.get("startedAt"):
        add(deploy["startedAt"], "Render", "Deployment", "Requested", "In progress", "Render deployment started")
    add(deploy["finishedAt"], "Render", "Deployment", "In progress", "Live", "Render marked the deployment live")
    for log in logs:
        for pattern, entity, before, after, detail in MESSAGES:
            if pattern.search(log["message"].lower()):
                kind = "Runtime" if entity == "AEM" else "Docker" if entity == "Image" else "Render"
                add(log["timestamp"], kind, entity, before, after, detail)
                break
    return "\n".join("\t".join(row) for row in sorted(rows)) + "\n"


def build(source, output):
    root = "/apps/wknd-demo/diagnostics/render-events.tsv"
    data = json.loads(source.read_text(encoding="utf-8"))
    with ZipFile(output, "w", ZIP_DEFLATED) as package:
        package.writestr("META-INF/vault/filter.xml",
            f'<workspaceFilter version="1.0"><filter root="{root}"/></workspaceFilter>')
        package.writestr("META-INF/vault/properties.xml", """<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE properties SYSTEM "http://java.sun.com/dtd/properties.dtd">
<properties>
    <entry key="group">wknd-demo</entry>
    <entry key="name">wknd-render-events</entry>
    <entry key="version">1.0.0</entry>
    <entry key="packageType">application</entry>
</properties>
""")
        package.writestr(f"jcr_root{root}", timeline(data["deploy"], data.get("logs", [])))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("source", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    build(args.source, args.output)
