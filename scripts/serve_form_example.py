"""Serve a generated HTML form for a plugin and persist submitted values.

Usage:
  PYTHONPATH=src python scripts/serve_form_example.py smartcleaner.plugins.kernels --port 8000

The server renders a simple form (derived from the plugin's JSON schema) at
`/` and accepts POSTs to `/submit`. Submitted values are validated using
`smartcleaner.config.set_plugin_config` and persisted to the XDG config.
"""
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import parse_qs
import sys
import argparse
import html
from typing import Dict

from smartcleaner.utils.json_schema import plugin_info_to_json_schema
from smartcleaner.config import set_plugin_config


def input_for_prop(name: str, spec: dict) -> str:
    t = spec.get('type', 'string')
    label = html.escape(name)
    default = spec.get('default')
    if t == 'integer':
        val = '' if default is None else str(default)
        return f'<label>{label}: <input type="number" name="{label}" value="{html.escape(val)}"></label>'
    if t == 'boolean':
        checked = 'checked' if default else ''
        return f'<label>{label}: <input type="checkbox" name="{label}" {checked}></label>'
    if t == 'array':
        val = '' if default is None else ','.join(map(str, default))
        return f'<label>{label}: <input type="text" name="{label}" value="{html.escape(val)}"></label> <small>comma-separated</small>'
    val = '' if default is None else str(default)
    return f'<label>{label}: <input type="text" name="{label}" value="{html.escape(val)}"></label>'


def render_schema_to_html(module_name: str) -> str:
    schema = plugin_info_to_json_schema(module_name)
    title = html.escape(schema.get('title', module_name))
    description = html.escape(schema.get('description', ''))
    props = schema.get('properties', {})

    parts = [f'<html><head><meta charset="utf-8"><title>{title} - Form</title></head><body>']
    parts.append(f'<h1>{title}</h1>')
    if description:
        parts.append(f'<p>{description}</p>')

    parts.append('<form method="post" action="/submit">')
    for k, spec in props.items():
        parts.append('<div style="margin:0.5em 0;">')
        parts.append(input_for_prop(k, spec))
        if 'description' in spec:
            parts.append(f'<div><small>{html.escape(spec.get("description"))}</small></div>')
        parts.append('</div>')
    parts.append('<div><button type="submit">Save</button></div>')
    parts.append('</form>')
    parts.append('</body></html>')
    return '\n'.join(parts)


class FormHandler(BaseHTTPRequestHandler):
    def __init__(self, *args, module_name=None, **kwargs):
        self.module_name = module_name
        super().__init__(*args, **kwargs)

    def do_GET(self):
        if self.path != '/':
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')
            return
        html_out = render_schema_to_html(self.module_name)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(html_out.encode('utf-8'))

    def do_POST(self):
        if self.path != '/submit':
            self.send_response(404)
            self.end_headers()
            self.wfile.write(b'Not found')
            return

        length = int(self.headers.get('Content-Length', 0))
        body = self.rfile.read(length).decode('utf-8')
        data = parse_qs(body)

        results = []
        # data maps names to list of values
        for key, vals in data.items():
            # join multi-values with comma
            raw = vals[0] if vals else ''
            try:
                ok = set_plugin_config(self.module_name, key, raw)
                if ok:
                    results.append((key, True, None))
                else:
                    results.append((key, False, 'validation or IO error'))
            except Exception as e:
                results.append((key, False, str(e)))

        # respond with a simple status page
        parts = ['<html><body>']
        parts.append('<h2>Submission results</h2>')
        parts.append('<ul>')
        for k, ok, err in results:
            if ok:
                parts.append(f'<li>{html.escape(k)}: <strong>saved</strong></li>')
            else:
                parts.append(f'<li>{html.escape(k)}: <strong>failed</strong> - {html.escape(str(err))}</li>')
        parts.append('</ul>')
        parts.append('<p><a href="/">Back</a></p>')
        parts.append('</body></html>')

        out = '\n'.join(parts)
        self.send_response(200)
        self.send_header('Content-Type', 'text/html; charset=utf-8')
        self.end_headers()
        self.wfile.write(out.encode('utf-8'))


def run_server(module_name: str, port: int = 8000):
    def handler(*args, **kwargs):
        return FormHandler(*args, module_name=module_name, **kwargs)

    server = HTTPServer(('127.0.0.1', port), handler)
    print(f"Serving form for {module_name} at http://127.0.0.1:{port}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        print('Shutting down')
        server.server_close()


def main():
    p = argparse.ArgumentParser(description='Serve a plugin config form and persist values')
    p.add_argument('module', help='Plugin module name (e.g. smartcleaner.plugins.kernels)')
    p.add_argument('--port', type=int, default=8000, help='Port to serve on')
    args = p.parse_args()
    run_server(args.module, port=args.port)


if __name__ == '__main__':
    main()
