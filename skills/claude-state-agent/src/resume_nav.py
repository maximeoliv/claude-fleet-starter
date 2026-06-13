"""Verified navigation of claude code's interactive menus (resume picker + resume mode).

The key safety property: we never press Enter blind. We parse the menu, locate the
target option by its TEXT, navigate the cursor onto it, re-capture, and only confirm
if the cursor is verifiably on the right line. If anything is off, we abort.
"""
from __future__ import annotations

import re

# A menu option line: optional cursor marker, a number, a dot, then the label.
# Examples:  "❯ 1. Resume from summary"   "  2. Resume full session as-is"
#            "_ 1. Resume from summary (recommended)"
_OPTION_RE = re.compile(r"^(\s*)([❯>_]?)\s*(\d+)\.\s+(.+?)\s*$")

# Cursor markers claude code may use to show the selected line
_CURSOR_CHARS = {"❯", ">", "_"}


def parse_menu(pane: str) -> list[dict]:
    """Parse a numbered menu from the pane. Returns a list of options in display order:
    [{index, number, label, selected}]  — index is 0-based display order.
    """
    options = []
    for line in pane.splitlines():
        m = _OPTION_RE.match(line)
        if not m:
            continue
        _indent, marker, number, label = m.groups()
        options.append({
            "index": len(options),
            "number": number,
            "label": label.strip(),
            "selected": marker in _CURSOR_CHARS,
        })
    return options


def find_option(options: list[dict], *needles: str) -> int | None:
    """Return the display index of the first option whose label contains ALL needles
    (case-insensitive). None if not found.
    """
    for opt in options:
        low = opt["label"].lower()
        if all(n.lower() in low for n in needles):
            return opt["index"]
    return None


def selected_index(options: list[dict]) -> int | None:
    for opt in options:
        if opt["selected"]:
            return opt["index"]
    return None


def plan_navigation(pane: str, *target_needles: str) -> dict:
    """Compute how to navigate to the target option.

    Returns a dict:
      {ok: bool, reason: str, key: 'Down'|'Up'|None, presses: int,
       target_index: int|None, current_index: int|None, options: [...]}
    """
    options = parse_menu(pane)
    if not options:
        return {"ok": False, "reason": "no menu options parsed", "key": None,
                "presses": 0, "target_index": None, "current_index": None, "options": []}

    target = find_option(options, *target_needles)
    if target is None:
        return {"ok": False, "reason": f"target option not found: {target_needles}",
                "key": None, "presses": 0, "target_index": None,
                "current_index": None, "options": options}

    current = selected_index(options)
    if current is None:
        # No cursor detected — unsafe to navigate blind
        return {"ok": False, "reason": "cursor position not detectable",
                "key": None, "presses": 0, "target_index": target,
                "current_index": None, "options": options}

    delta = target - current
    if delta == 0:
        return {"ok": True, "reason": "already on target", "key": None, "presses": 0,
                "target_index": target, "current_index": current, "options": options}
    return {
        "ok": True, "reason": "navigation planned",
        "key": "Down" if delta > 0 else "Up", "presses": abs(delta),
        "target_index": target, "current_index": current, "options": options,
    }


def verify_on_target(pane: str, *target_needles: str) -> bool:
    """After navigation, confirm the cursor is on the target option."""
    options = parse_menu(pane)
    sel = selected_index(options)
    tgt = find_option(options, *target_needles)
    return sel is not None and tgt is not None and sel == tgt
