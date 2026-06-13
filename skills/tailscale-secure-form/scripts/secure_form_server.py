#!/usr/bin/env python3
import argparse
import json
import os
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from urllib.parse import parse_qs


def load_schema(path: str):
    with open(path, 'r', encoding='utf-8') as f:
        data = json.load(f)
    fields = data.get('fields', [])
    if not isinstance(fields, list) or not fields:
        raise ValueError('Schema must contain non-empty "fields" list')
    return fields


def html_escape(s: str) -> str:
    return (s.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
            .replace('"', '&quot;').replace("'", '&#39;'))


def build_form_html(title: str, fields):
    controls = []
    for f in fields:
        name = f['name']
        label = f.get('label', name)
        typ = f.get('type', 'text')
        required = 'required' if f.get('required', False) else ''
        placeholder = html_escape(f.get('placeholder', ''))
        if typ == 'textarea':
            control = f"<textarea name=\"{html_escape(name)}\" {required} placeholder=\"{placeholder}\"></textarea>"
        else:
            control = f"<input type=\"{html_escape(typ)}\" name=\"{html_escape(name)}\" {required} placeholder=\"{placeholder}\"/>"
        controls.append(f"<label>{html_escape(label)}</label>{control}")

    return f"""<!doctype html>
<html><head><meta charset='utf-8'><meta name='viewport' content='width=device-width, initial-scale=1'>
<title>{html_escape(title)}</title>
<style>
body{{font-family:system-ui,-apple-system,Segoe UI,Roboto,sans-serif;max-width:700px;margin:24px auto;padding:0 14px}}
form{{display:grid;gap:10px}}
label{{font-weight:600;margin-top:8px}}
input,textarea{{padding:10px;border:1px solid #bbb;border-radius:8px;font-size:14px}}
button{{margin-top:12px;padding:12px;border:0;border-radius:10px;background:#005fb5;color:white;font-weight:700;cursor:pointer}}
.small{{color:#666;font-size:12px}}
</style></head>
<body>
<h2>{html_escape(title)}</h2>
<p class='small'>Private form over Tailscale. Data is stored locally on submit.</p>
<form method='post' action='/submit'>
{''.join(controls)}
<button type='submit'>Send securely</button>
</form>
</body></html>"""


class Handler(BaseHTTPRequestHandler):
    fields = []
    out_path = ''
    title = 'Secure Intake'

    def _send(self, code, body, ctype='text/html; charset=utf-8'):
        b = body.encode('utf-8')
        self.send_response(code)
        self.send_header('Content-Type', ctype)
        self.send_header('Content-Length', str(len(b)))
        self.end_headers()
        self.wfile.write(b)

    def do_GET(self):
        if self.path in ['/', '/index.html']:
            self._send(200, build_form_html(self.title, self.fields))
            return
        if self.path == '/health':
            self._send(200, json.dumps({'ok': True, 'ts': datetime.now(timezone.utc).isoformat()}), 'application/json')
            return
        self._send(404, 'Not found', 'text/plain; charset=utf-8')

    def do_POST(self):
        if self.path != '/submit':
            self._send(404, 'Not found', 'text/plain; charset=utf-8')
            return
        length = int(self.headers.get('Content-Length', '0'))
        raw = self.rfile.read(length).decode('utf-8', errors='ignore')
        data = parse_qs(raw, keep_blank_values=True)

        record = {'submittedAt': datetime.now(timezone.utc).isoformat(), 'data': {}}
        for f in self.fields:
            name = f['name']
            val = data.get(name, [''])[0]
            record['data'][name] = val

        os.makedirs(os.path.dirname(self.out_path), exist_ok=True)
        with open(self.out_path, 'a', encoding='utf-8') as out:
            out.write(json.dumps(record, ensure_ascii=False) + '\n')

        self._send(200, "<html><body><h3>✅ Received</h3><p>You can close this page.</p></body></html>")


def main():
    ap = argparse.ArgumentParser(description='Run a local secure intake form server')
    ap.add_argument('--host', default='127.0.0.1')
    ap.add_argument('--port', type=int, default=18991)
    ap.add_argument('--schema', required=True)
    ap.add_argument('--out', required=True)
    ap.add_argument('--title', default='Secure Intake')
    args = ap.parse_args()

    fields = load_schema(args.schema)
    Handler.fields = fields
    Handler.out_path = args.out
    Handler.title = args.title

    server = HTTPServer((args.host, args.port), Handler)
    print(f"Secure form running on http://{args.host}:{args.port}")
    print(f"Writing submissions to: {args.out}")
    server.serve_forever()


if __name__ == '__main__':
    main()
