#!/usr/bin/env python3
"""secure_display_server.py — display a secret to a human via a capability URL.

Agent-to-user direction: the agent generates an unguessable URL and prints it;
the human opens it in their browser to read the secret. The secret never appears
in the chat transcript.

Usage:
  python3 secure_display_server.py --secret "my-secret-value" --label "raguser password"
  python3 secure_display_server.py --secret-file /root/.secure/raguser.pw --label "API key" --view-once
  python3 secure_display_server.py --secret-file /tmp/mytoken.txt --host 100.x.x.x --port 18993

Options:
  --secret TEXT        Secret value to display (use --secret-file for files)
  --secret-file PATH   Path to file containing the secret
  --label TEXT         Human-readable label shown in the browser
  --host HOST          Bind address (default: Tailscale IP)
  --port PORT          Port (default: 18993)
  --view-once          Exit after first successful read (404 after that)
"""
import argparse
import os
import secrets
import subprocess
import sys
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path


def get_tailscale_ip() -> str:
    try:
        return subprocess.check_output(["tailscale", "ip", "-4"], timeout=5, text=True).strip()
    except Exception:
        return "127.0.0.1"


def make_handler(token: str, secret: str, label: str, view_once: bool, state: dict):
    class Handler(BaseHTTPRequestHandler):
        def log_message(self, fmt, *args):
            pass  # suppress default access logs (they'd contain the token path)

        def do_GET(self):
            if self.path != f"/{token}":
                self.send_response(404)
                self.end_headers()
                self.wfile.write(b"Not found")
                return

            if state.get("served") and view_once:
                self.send_response(410)
                self.end_headers()
                self.wfile.write(b"Gone (view-once: already read)")
                return

            state["served"] = True
            html = f"""<!DOCTYPE html>
<html lang="fr">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width,initial-scale=1">
<meta name="robots" content="noindex,nofollow">
<title>{label}</title>
<style>
  body{{font-family:monospace;background:#1a1a1a;color:#e0e0e0;display:flex;
       align-items:center;justify-content:center;min-height:100vh;margin:0}}
  .box{{background:#2a2a2a;border:1px solid #444;border-radius:8px;padding:2rem;
        max-width:600px;width:90%}}
  h2{{color:#aaa;font-size:0.9rem;margin:0 0 1rem;text-transform:uppercase;letter-spacing:.1em}}
  .secret{{background:#111;border:1px solid #555;border-radius:4px;padding:1rem;
           font-size:1.1rem;word-break:break-all;user-select:all;cursor:pointer;
           color:#7fff7f}}
  .hint{{color:#666;font-size:0.75rem;margin-top:0.75rem}}
  {"<p style='color:#ff6b6b;font-size:0.8rem'>⚠ View-once — cette page ne s'affichera plus après rechargement</p>" if view_once else ""}
</style>
</head>
<body>
<div class="box">
  <h2>{label}</h2>
  <div class="secret" onclick="navigator.clipboard.writeText(this.innerText).then(()=>this.style.outline='2px solid #7fff7f')"
       title="Clic pour copier">{secret}</div>
  <p class="hint">Clic pour copier · Ferme cette fenêtre après avoir noté le secret</p>
</div>
</body>
</html>"""
            body = html.encode()
            self.send_response(200)
            self.send_header("Content-Type", "text/html; charset=utf-8")
            self.send_header("Content-Length", str(len(body)))
            self.send_header("Cache-Control", "no-store, no-cache, must-revalidate")
            self.send_header("X-Robots-Tag", "noindex, nofollow")
            self.end_headers()
            self.wfile.write(body)

            if view_once:
                print("[secure-display] Secret read — shutting down (view-once)", flush=True)
                # Schedule shutdown after response is sent
                import threading
                threading.Timer(0.5, lambda: os._exit(0)).start()

    return Handler


def main():
    ap = argparse.ArgumentParser(description="Display a secret via a capability URL")
    ap.add_argument("--secret", help="Secret value to display")
    ap.add_argument("--secret-file", help="Path to file containing the secret")
    ap.add_argument("--label", default="Secret", help="Label shown in browser")
    ap.add_argument("--host", default="", help="Bind host (default: Tailscale IP)")
    ap.add_argument("--port", type=int, default=18993)
    ap.add_argument("--view-once", action="store_true", help="Exit after first read")
    args = ap.parse_args()

    if args.secret:
        secret = args.secret
    elif args.secret_file:
        secret = Path(args.secret_file).read_text().strip()
    else:
        ap.error("Either --secret or --secret-file is required")

    host = args.host or get_tailscale_ip()
    token = secrets.token_urlsafe(18)  # ~24 chars, URL-safe
    state = {"served": False}

    handler = make_handler(token, secret, args.label, args.view_once, state)
    server = HTTPServer((host, args.port), handler)

    url = f"http://{host}:{args.port}/{token}"
    print(f"\n[secure-display] Ready — open this URL in your browser:", flush=True)
    print(f"\n  {url}\n", flush=True)
    if args.view_once:
        print("[secure-display] view-once mode: server exits after first read", flush=True)
    print("[secure-display] Ctrl+C to stop\n", flush=True)

    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print("\n[secure-display] Stopped", flush=True)


if __name__ == "__main__":
    main()
