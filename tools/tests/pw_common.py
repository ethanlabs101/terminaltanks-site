"""Shared Playwright helpers: a local server for the site and a route that serves the Pyodide runtime from disk."""
import os, pathlib, mimetypes
PYODIDE_DIR = pathlib.Path(os.environ.get("TT_PYODIDE_DIR", "/home/claude/ext/pyodide/pyodide"))
BASE = os.environ.get("TT_BASE", "http://127.0.0.1:8766/")
CDN = ("https://cdn.jsdelivr.net/pyodide/v0.26.4/full/", "https://pyodide-cdn2.iodide.io/v0.26.4/full/")


def route_pyodide(ctx):
    """Requests for the Pyodide CDN are answered from a local copy (the test machine has no CDN access)."""
    def handle(route):
        url = route.request.url
        for c in CDN:
            if url.startswith(c):
                f = PYODIDE_DIR / url[len(c):].split("?")[0]
                if f.exists():
                    ct = mimetypes.guess_type(str(f))[0] or ("application/wasm" if f.suffix == ".wasm" else "application/octet-stream")
                    return route.fulfill(status=200, body=f.read_bytes(), headers={"content-type": ct, "access-control-allow-origin": "*"})
                return route.fulfill(status=404, body="")
        return route.continue_()
    ctx.route("**/*", handle)
