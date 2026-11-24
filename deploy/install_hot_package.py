"""Install and verify a generated hot package against the AEM demo Author."""
import argparse
import base64
import json
import os
import time
from pathlib import Path
from urllib.error import HTTPError
from urllib.parse import quote
from urllib.request import HTTPRedirectHandler, Request, build_opener

AUTHOR = "https://aem-demo-author.onrender.com"
BASE = "/content/wknd/us/en/aem-demo"
COMPONENT_ENDPOINT = BASE + "/weather/jcr:content/root/container/weather_panel/weather.current.json"


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def request(path, body=None, headers=None):
    authorization = base64.b64encode(
        f"{os.environ['AEM_DEPLOY_USER']}:{os.environ['AEM_DEPLOY_PASSWORD']}".encode()
    ).decode()
    req = Request(AUTHOR + path, data=body, headers={
        "Authorization": "Basic " + authorization, **(headers or {}),
    })
    with build_opener(NoRedirect()).open(req, timeout=180) as response:
        return response.read(), response.headers


def expected_value(value):
    if value is None:
        return None
    for kind, convert in (("Boolean", lambda x: x == "true"), ("Long", int), ("Double", float)):
        prefix = "{" + kind + "}"
        if value.startswith(prefix):
            return convert(value.removeprefix(prefix))
    if value.startswith("[") and value.endswith("]"):
        if "\\" in value:
            raise ValueError("Escaped multi-value property requires manual review")
        return value[1:-1].split(",") if value != "[]" else []
    if value.startswith("{"):
        raise ValueError("Unsupported typed property requires manual review")
    return value


def check_author_changes(guards):
    for guard in guards:
        path = guard["path"]
        try:
            payload, _ = request(quote(path, safe="/:") + ".0.json")
        except HTTPError as exc:
            if exc.code == 404 and guard.get("absent"):
                continue
            raise
        if guard.get("absent"):
            raise ValueError(f"Author already has a node at {path}; refusing to overwrite it.")
        live = json.loads(payload)
        for name, previous in guard["properties"].items():
            if live.get(name) != expected_value(previous):
                raise ValueError(f"Author conflict at {path}/{name}; review the authored value first.")


def form_request(path, fields, token):
    from uuid import uuid4
    boundary = uuid4().hex
    body = bytearray()
    for key, value in fields.items():
        body.extend(f"--{boundary}\r\nContent-Disposition: form-data; name=\"{key}\"".encode())
        if isinstance(value, Path):
            body.extend(f"; filename=\"{value.name}\"\r\nContent-Type: application/zip\r\n\r\n".encode())
            body.extend(value.read_bytes())
        else:
            body.extend(b"\r\n\r\n")
            body.extend(value.encode())
        body.extend(b"\r\n")
    body.extend(f"--{boundary}--\r\n".encode())
    payload, _ = request(path, bytes(body), {
        "Content-Type": f"multipart/form-data; boundary={boundary}",
        "CSRF-Token": token,
    })
    result = json.loads(payload)
    if result.get("success") is not True:
        raise RuntimeError("AEM Package Manager reported failure; inspect the package in Author.")
    return result


def smoke(bundle_version):
    for attempt in range(24):
        try:
            _, headers = request(COMPONENT_ENDPOINT)
            if headers.get("X-WKND-Weather-Bundle") == bundle_version:
                html, _ = request(BASE + "/weather.html?wcmmode=disabled")
                logs, _ = request(BASE + "/system-logs.html?wcmmode=disabled")
                if (b'data-weather-component="wknd-demo"' in html
                        and b"Recent entries from AEM error.log" in logs):
                    return
        except HTTPError as exc:
            if exc.code in (401, 403):
                raise
        if attempt < 23:
            time.sleep(5)
    raise RuntimeError("Smoke test did not observe the new bundle and the expected Weather and System Logs markup.")


def install(args):
    start = time.monotonic()
    if not all(os.environ.get(key) for key in ("AEM_DEPLOY_USER", "AEM_DEPLOY_PASSWORD")):
        raise ValueError("Configure the AEM deployment credentials in the GitHub environment.")
    token = json.loads(request("/libs/granite/csrf/token.json")[0])["token"]
    check_author_changes(json.loads(args.guards.read_text(encoding="utf-8")))
    upload = form_request("/crx/packmgr/service/.json", {
        "cmd": "upload", "package": args.package, "force": "false",
    }, token)
    package_path = upload.get("path", "")
    if package_path != f"/etc/packages/wknd-demo/{args.package.name}":
        raise ValueError("Unexpected package path returned by AEM.")
    form_request("/crx/packmgr/service/.json" + quote(package_path, safe="/"), {"cmd": "install"}, token)
    print(f"Package Manager accepted the installation in {time.monotonic() - start:.1f}s.", flush=True)
    smoke(args.bundle_version)
    print(f"Weather, System Logs and exact OSGi bundle version verified in {time.monotonic() - start:.1f}s.")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--package", type=Path, required=True)
    parser.add_argument("--guards", type=Path, required=True)
    parser.add_argument("--bundle-version", required=True)
    try:
        install(parser.parse_args())
    except (ValueError, OSError, RuntimeError) as exc:
        parser.exit(1, f"Fast Deploy failed: {exc}\n")
