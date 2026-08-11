"""
Local dev server for the JEEV TECH site.

`python -m http.server` is not good enough to test this site: every link in the
nav points at a clean URL (/principles, /about), because vercel.json sets
"cleanUrls": true. Plain http.server 404s on all of them, so nothing but the
home page is reachable.

This mirrors the two routing rules Vercel actually applies, so local behaviour
matches production:

  cleanUrls: true      /principles      -> principles.html
                       /principles.html -> 308 to /principles
  trailingSlash: false /about/          -> 308 to /about

It also sends Cache-Control: no-store. That is wrong for production and right
here — a stale stylesheet after an edit is the single most common way local
testing lies to you.

    python _tools/serve.py [port]
"""
import os
import sys
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))


class Handler(SimpleHTTPRequestHandler):
    def __init__(self, *a, **kw):
        super().__init__(*a, directory=ROOT, **kw)

    def send_head(self):
        path, _, query = self.path.partition("?")
        suffix = ("?" + query) if query else ""

        # trailingSlash: false — /about/ is not a URL on this site.
        if len(path) > 1 and path.endswith("/"):
            return self.redirect(path.rstrip("/") + suffix)

        # cleanUrls — the extension is never part of the canonical URL.
        if path.endswith(".html") and path != "/index.html":
            return self.redirect(path[:-5] + suffix)
        if path == "/index.html":
            return self.redirect("/" + suffix)

        # …and the extensionless URL is what the file is served under.
        if path != "/" and "." not in os.path.basename(path):
            if os.path.isfile(os.path.join(ROOT, path.lstrip("/") + ".html")):
                self.path = path + ".html" + suffix

        return super().send_head()

    def redirect(self, location):
        self.send_response(308)
        self.send_header("Location", location)
        self.send_header("Content-Length", "0")
        self.end_headers()
        return None

    def send_error(self, code, message=None, explain=None):
        """404.html is a real page here, so serve it rather than the stock
           http.server error body."""
        page = os.path.join(ROOT, "404.html")
        if code == 404 and os.path.isfile(page):
            body = open(page, "rb").read()
            self.send_response(404)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store")
            self.end_headers()
            if self.command != "HEAD":
                self.wfile.write(body)
            return
        return super().send_error(code, message, explain)

    def end_headers(self):
        self.send_header("Cache-Control", "no-store")
        super().end_headers()

    def log_message(self, fmt, *args):
        sys.stderr.write("%s %s\n" % (self.address_string(), fmt % args))


if __name__ == "__main__":
    port = int(sys.argv[1]) if len(sys.argv) > 1 else 8737
    print("JEEV TECH dev server — http://localhost:%d  (clean URLs, no cache)" % port)
    ThreadingHTTPServer(("127.0.0.1", port), Handler).serve_forever()
