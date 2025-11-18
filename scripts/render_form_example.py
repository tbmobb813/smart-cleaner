"""Tiny example that renders a simple HTML form from a plugin's JSON Schema.

Usage:
  PYTHONPATH=src python scripts/render_form_example.py smartcleaner.plugins.kernels > /tmp/kernels_form.html

Open the generated HTML file in a browser. This is intentionally minimal and
designed as a starting point for GUI integration experiments.
"""
import sys
import html
from smartcleaner.utils.json_schema import plugin_info_to_json_schema


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
        # naive: join items with commas
        val = '' if default is None else ','.join(map(str, default))
        return f'<label>{label}: <input type="text" name="{label}" value="{html.escape(val)}"></label> <small>comma-separated</small>'
    # default to text
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

    parts.append('<form method="post">')
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


def main():
    if len(sys.argv) < 2:
        print('Usage: render_form_example.py <plugin_module>')
        sys.exit(2)
    module_name = sys.argv[1]
    html_out = render_schema_to_html(module_name)
    print(html_out)


if __name__ == '__main__':
    main()
