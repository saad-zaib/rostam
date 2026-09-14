"""Interactive terminal menu utilities."""

import os
import sys
import platform


def clear_screen():
    os.system("cls" if platform.system() == "Windows" else "clear")


def print_banner(title):
    width = 60
    print(f"\n{'=' * width}")
    print(f"  {title}")
    print(f"{'=' * width}\n")


def print_menu(title, options):
    print_banner(title)
    for key, label in options:
        print(f"  [{key}] {label}")
    print()
    return input("  Select > ").strip()


def confirm(prompt):
    resp = input(f"  {prompt} [y/N] > ").strip().lower()
    return resp in ("y", "yes")


def get_number(prompt, default=None):
    suffix = f" [{default}]" if default is not None else ""
    raw = input(f"  {prompt}{suffix} > ").strip()
    if not raw and default is not None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def pause():
    input("\n  Press Enter to continue...")


# ── arrow-key input ─────────────────────────────────────────


def read_key():
    """Read a single keypress. Returns: 'up','down','enter','space','esc', or a char."""
    if platform.system() == "Windows":
        import msvcrt
        ch = msvcrt.getwch()
        if ch in ("\xe0", "\x00"):
            ch2 = msvcrt.getwch()
            return {"H": "up", "P": "down"}.get(ch2, "")
        if ch == "\r":
            return "enter"
        if ch == " ":
            return "space"
        if ch == "\x1b":
            return "esc"
        if ch == "\x03":
            raise KeyboardInterrupt
        return ch.lower()
    else:
        import tty
        import termios
        fd = sys.stdin.fileno()
        old = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                ch2 = sys.stdin.read(1)
                if ch2 == "[":
                    ch3 = sys.stdin.read(1)
                    return {"A": "up", "B": "down"}.get(ch3, "")
                return "esc"
            if ch in ("\r", "\n"):
                return "enter"
            if ch == " ":
                return "space"
            if ch == "\x03":
                raise KeyboardInterrupt
            return ch.lower()
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old)


# ── generic arrow-key list picker ────────────────────────────


def picker(items, title="", help_text="", selected=None, cursor=0, viewport=20,
           on_expand=None, on_collapse=None):
    """
    Arrow-key driven list picker with inline expand/collapse.

    items: list of dicts with:
        - label, key, indent, expandable, expanded, has_tests

    on_expand(items, idx)  — called when Enter on collapsed expandable
    on_collapse(items, idx) — called when Enter on expanded expandable
    If callbacks are provided, expand/collapse happens inside the loop.

    Returns (action, data), cursor, selected:
        ('toggle', key)  / ('select', key) / ('run', None) / ('quit', None)
    """
    if selected is None:
        selected = set()

    offset = 0
    vp = viewport

    while True:
        n = len(items)
        if cursor >= n:
            cursor = max(0, n - 1)
        if cursor < offset:
            offset = cursor
        if cursor >= offset + vp:
            offset = cursor - vp + 1

        end = min(offset + vp, n)

        clear_screen()
        print(f"\n  {title}")
        print(f"  {help_text}")
        print(f"  {'═' * 68}\n")

        for i in range(offset, end):
            item = items[i]
            is_cur = i == cursor
            is_sel = item["key"] in selected
            indent = "    " * item.get("indent", 0)

            arrow = "▸" if is_cur else " "
            check = "✓" if is_sel else " "
            if item.get("expandable"):
                marker = " ▼" if item.get("expanded") else " ▶"
            else:
                marker = ""

            line = f"  {arrow} [{check}] {indent}{item['label']}{marker}"

            if is_cur:
                sys.stdout.write(f"\033[7m{line}\033[0m\n")
            else:
                sys.stdout.write(line + "\n")

        print(f"\n  {'═' * 68}")
        print(f"  Selected: {len(selected)}  |  {offset + 1}-{end} of {n}")
        sys.stdout.flush()

        key = read_key()

        if key == "up" and cursor > 0:
            cursor -= 1
        elif key == "down" and cursor < n - 1:
            cursor += 1
        elif key == "space":
            item = items[cursor]
            if item.get("has_tests"):
                k = item["key"]
                if k in selected:
                    selected.discard(k)
                else:
                    selected.add(k)
        elif key == "enter":
            item = items[cursor]
            if item.get("expandable"):
                if item.get("expanded"):
                    if on_collapse:
                        on_collapse(items, cursor)
                    else:
                        return ("collapse", cursor), cursor, selected
                else:
                    if on_expand:
                        on_expand(items, cursor)
                        cursor = cursor + 1
                    else:
                        return ("expand", cursor), cursor, selected
            elif item.get("has_tests"):
                return ("select", item["key"]), cursor, selected
        elif key == "r":
            return ("run", None), cursor, selected
        elif key in ("q", "esc"):
            return ("quit", None), cursor, selected
