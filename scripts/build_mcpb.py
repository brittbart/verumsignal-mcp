#!/usr/bin/env python3
"""Build the MCP bundle (.mcpb) for this server, byte for byte the same every time.

    python3 scripts/build_mcpb.py           build dist/verumsignal-mcp-<version>.mcpb, print its SHA-256
    python3 scripts/build_mcpb.py --update  also write that SHA-256 into server.json (after changing
                                            any bundled file, before a release)
    python3 scripts/build_mcpb.py --check   also require server.json to match, run the bundled server
                                            once over stdio, and write dist/release-notes.md

The archive is stored uncompressed with fixed timestamps and permissions, so the same
source gives the same file and the same hash on any machine with LF line endings
(the Publish workflow builds on Linux).
"""
import hashlib
import json
import os
import re
import subprocess
import sys
import tempfile
import zipfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NAME = "verumsignal-mcp"
REPO = "https://github.com/brittbart/verumsignal-mcp"
FILES = [  # (path in the repository, path in the bundle)
    ("mcpb/manifest.json", "manifest.json"),
    ("mcpb/main.py", "server/main.py"),
    ("verumsignal_mcp/__init__.py", "server/verumsignal_mcp/__init__.py"),
    ("verumsignal_mcp/server.py", "server/verumsignal_mcp/server.py"),
    ("LICENSE", "LICENSE"),
]
STAMP = (2026, 1, 1, 0, 0, 0)


def read(rel):
    with open(os.path.join(ROOT, rel), "rb") as f:
        return f.read()


def fail(msg):
    sys.exit(f"FAILED: {msg}")


def version():
    found = {
        "mcpb/manifest.json": json.loads(read("mcpb/manifest.json"))["version"],
        "server.json": json.loads(read("server.json"))["version"],
        "verumsignal_mcp/__init__.py": re.search(r'__version__ = "([^"]+)"', read("verumsignal_mcp/__init__.py").decode()).group(1),
        "pyproject.toml": re.search(r'^version = "([^"]+)"', read("pyproject.toml").decode(), re.M).group(1),
    }
    if len(set(found.values())) != 1:
        fail(f"versions disagree: {found}")
    return found["server.json"]


def build(v):
    out = os.path.join(ROOT, "dist", f"{NAME}-{v}.mcpb")
    os.makedirs(os.path.dirname(out), exist_ok=True)
    with zipfile.ZipFile(out, "w", zipfile.ZIP_STORED) as z:
        for src, dst in sorted(FILES, key=lambda f: f[1]):
            info = zipfile.ZipInfo(dst, STAMP)
            info.create_system = 3
            info.external_attr = 0o644 << 16
            z.writestr(info, read(src))
    with open(out, "rb") as f:
        return out, hashlib.sha256(f.read()).hexdigest()


def mcpb_package(server):
    pk = [p for p in server.get("packages", []) if p.get("registryType") == "mcpb"]
    if len(pk) != 1:
        fail("server.json needs exactly one mcpb package")
    return pk[0]


def check(v, out, digest):
    server = json.loads(read("server.json"))
    pk = mcpb_package(server)
    want_url = f"{REPO}/releases/download/v{v}/{NAME}-{v}.mcpb"
    if pk.get("identifier") != want_url:
        fail(f"server.json identifier {pk.get('identifier')!r} should be {want_url!r}")
    if pk.get("version") != v:
        fail(f"server.json mcpb version {pk.get('version')!r} should be {v!r}")
    if pk.get("fileSha256") != digest:
        fail(f"server.json fileSha256 {pk.get('fileSha256')} does not match the bundle {digest}; "
             f"run python3 scripts/build_mcpb.py --update")

    manifest = json.loads(read("mcpb/manifest.json"))
    with tempfile.TemporaryDirectory() as tmp:
        with zipfile.ZipFile(out) as z:
            if z.testzip() is not None:
                fail("corrupt entry in the bundle")
            z.extractall(tmp)
        msgs = [
            {"jsonrpc": "2.0", "id": 1, "method": "initialize",
             "params": {"protocolVersion": "2024-11-05", "capabilities": {}, "clientInfo": {"name": "build", "version": "0"}}},
            {"jsonrpc": "2.0", "method": "notifications/initialized"},
            {"jsonrpc": "2.0", "id": 2, "method": "tools/list"},
        ]
        env = {k: val for k, val in os.environ.items() if k not in ("VS_API_KEY", "PYTHONPATH")}
        p = subprocess.run([sys.executable, os.path.join(tmp, "server", "main.py")], cwd=tmp, env=env,
                           input="".join(json.dumps(m) + "\n" for m in msgs),
                           capture_output=True, text=True, timeout=30)
        if p.returncode != 0 or p.stderr:
            fail(f"bundled server exited {p.returncode}: {p.stderr[:500]}")
        replies = {r["id"]: r for r in map(json.loads, p.stdout.splitlines())}
        got_v = replies[1]["result"]["serverInfo"]["version"]
        if got_v != v:
            fail(f"bundled server reports version {got_v}, expected {v}")
        served = [t["name"] for t in replies[2]["result"]["tools"]]
        listed = [t["name"] for t in manifest["tools"]]
        if served != listed:
            fail(f"manifest tools {listed} differ from the server's {served}")

    log = read("CHANGELOG.md").decode()
    m = re.search(rf"^## \[{re.escape(v)}\][^\n]*\n(.*?)(?=^## \[|\Z)", log, re.M | re.S)
    if not m:
        fail(f"CHANGELOG.md has no section for {v}")
    notes = os.path.join(ROOT, "dist", "release-notes.md")
    with open(notes, "w") as f:
        f.write(m.group(1).strip() + "\n")
    print(f"bundle runs: version {got_v}, {len(served)} tools; server.json matches; release notes written")


def main():
    v = version()
    out, digest = build(v)
    print(f"{os.path.relpath(out, ROOT)}  sha256 {digest}  {os.path.getsize(out)} bytes")
    if "--update" in sys.argv:
        path = os.path.join(ROOT, "server.json")
        server = json.loads(read("server.json"))
        mcpb_package(server)["fileSha256"] = digest
        with open(path, "w") as f:
            f.write(json.dumps(server, indent=2) + "\n")
        print("server.json fileSha256 updated")
    if "--check" in sys.argv:
        check(v, out, digest)


if __name__ == "__main__":
    main()
