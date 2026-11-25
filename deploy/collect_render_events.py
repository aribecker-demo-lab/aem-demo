"""Import a full Render deployment's events without placing a Render key in AEM."""
import argparse
import json
import os
import time
from datetime import datetime, timedelta
from pathlib import Path
from tempfile import TemporaryDirectory
from urllib.error import HTTPError
from urllib.parse import urlencode
from urllib.request import Request, urlopen

import build_render_events_package as events
import install_hot_package as aem


def render(path, parameters=()):
    url = "https://api.render.com/v1" + path
    if parameters:
        url += "?" + urlencode(parameters)
    request = Request(url, headers={"Authorization": "Bearer " + os.environ["RENDER_API_KEY"]})
    with urlopen(request, timeout=30) as response:
        return json.load(response)


def wait_for_deploy(service, commit, requested):
    deadline = time.monotonic() + 18 * 60
    while time.monotonic() < deadline:
        results = render(f"/services/{service}/deploys", [("limit", 10)])
        for item in results:
            deploy = item["deploy"]
            created = datetime.fromisoformat(deploy["createdAt"])
            if deploy.get("commit", {}).get("id") != commit or created < requested - timedelta(seconds=5):
                continue
            status = deploy["status"]
            if status == "live":
                return deploy
            if status in {"build_failed", "update_failed", "pre_deploy_failed", "canceled", "deactivated"}:
                raise RuntimeError(f"Render deployment {deploy['id']} finished with {status}")
            break
        time.sleep(12)
    raise TimeoutError("Render did not report the requested deployment live within 18 minutes")


def deploy_logs(service, owner, deploy):
    query = [("resource", service), ("ownerId", owner), ("limit", 100),
             ("type", "app"), ("type", "build")]
    start = deploy["startedAt"]
    end = datetime.fromisoformat(deploy["finishedAt"])
    end = min(end + timedelta(minutes=12), datetime.now(end.tzinfo)).isoformat()
    for _ in range(25):
        data = render("/logs", query + [("startTime", start), ("endTime", end)])
        yield from data["logs"]
        if not data.get("hasMore"):
            return
        start, end = data["nextStartTime"], data["nextEndTime"]
    raise RuntimeError("Render deployment log pagination exceeded 25 pages")


def install(deploy, logs):
    route = aem.BASE + "/system-logs/jcr:content/root/container/system_logs.diagnostics.json"
    for _ in range(48):
        try:
            snapshot = json.loads(aem.request(route)[0])
            if snapshot.get("commit") == deploy["commit"]["id"] and "lifecycleHistory" in snapshot:
                break
        except HTTPError as failure:
            if failure.code not in (404, 502, 503, 504):
                raise
        time.sleep(5)
    else:
        raise RuntimeError("AEM is not serving the verified Render commit")
    token = json.loads(aem.request("/libs/granite/csrf/token.json")[0])["token"]
    with TemporaryDirectory() as temp:
        folder = Path(temp)
        source = folder / "render-events.json"
        package = folder / "wknd-render-events-1.0.0.zip"
        source.write_text(json.dumps({"deploy": deploy, "logs": list(logs)}), encoding="utf-8")
        events.build(source, package)
        uploaded = aem.form_request(aem.PACKAGE_SERVICE,
            {"cmd": "upload", "package": package, "force": "true"}, token)
        path = f"/etc/packages/wknd-demo/{package.name}"
        if uploaded.get("path") != path:
            raise RuntimeError("Unexpected Render events package path")
        aem.package_command(path, "install", token)
    history = json.loads(aem.request(route)[0])["lifecycleHistory"]
    if not any(row["kind"] == "Render" and row["bundleId"] == deploy["id"]
               and row["to"] == "Live" for row in history):
        raise RuntimeError("AEM did not display the imported Render deployment")
    print(f"Render deployment {deploy['id']} is visible in AEM.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--service", required=True)
    parser.add_argument("--owner", required=True)
    parser.add_argument("--commit", required=True)
    parser.add_argument("--requested", required=True, type=datetime.fromisoformat)
    args = parser.parse_args()
    deploy = wait_for_deploy(args.service, args.commit, args.requested)
    install(deploy, deploy_logs(args.service, args.owner, deploy))
