#!/usr/bin/env python3
"""Render CLAUDE.md from machine.json + Jinja2-style template (no jinja2 dep)."""
import json
import re
import sys


def render(template: str, vars: dict) -> str:
    """Minimalist Jinja2-like renderer: {{var}} and {%- if x %}...{%- endif %}.

    `{%-` and `-%}` strip surrounding whitespace (incl. one trailing newline)
    just like Jinja2's whitespace-control markers.
    """
    def expand_if(text):
        pattern = re.compile(
            r'(\n?)(\{%-?\s*if\s+(\w+)\s*-?%\})(.*?)(\{%-?\s*endif\s*-?%\})(\n?)',
            re.DOTALL,
        )
        while True:
            m = pattern.search(text)
            if not m:
                return text
            pre_nl, open_tag, var, block, close_tag, post_nl = m.groups()
            strip_pre = open_tag.startswith('{%-')
            strip_post = close_tag.endswith('-%}')
            if vars.get(var):
                replacement = block
            else:
                replacement = ''
            # Restore surrounding newlines unless stripped
            replacement = ('' if strip_pre else pre_nl) + replacement + ('' if strip_post else post_nl)
            text = text[:m.start()] + replacement + text[m.end():]

    text = expand_if(template)
    for k, v in vars.items():
        text = text.replace('{{' + k + '}}', str(v))
    return text


def main():
    if len(sys.argv) != 3:
        print('Usage: render-claude-md.py <machine.json> <template.j2>', file=sys.stderr)
        sys.exit(1)

    with open(sys.argv[1]) as f:
        machine = json.load(f)
    with open(sys.argv[2]) as f:
        template = f.read()

    print(render(template, machine))


if __name__ == '__main__':
    main()
