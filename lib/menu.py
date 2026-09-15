"""Interactive terminal menu utilities."""

import os
import sys
import platform

RED = "\033[91m"
BOLD = "\033[1m"
DIM = "\033[2m"
BLUE = "\033[94m"
GREEN = "\033[92m"
WHITE = "\033[97m"
RESET = "\033[0m"

_LOGO = rf"""{RED}{BOLD}
  ██████╗  ██████╗ ███████╗████████╗ █████╗ ███╗   ███╗
  ██╔══██╗██╔═══██╗██╔════╝╚══██╔══╝██╔══██╗████╗ ████║
  ██████╔╝██║   ██║███████╗   ██║   ███████║██╔████╔██║
  ██╔══██╗██║   ██║╚════██║   ██║   ██╔══██╗██║╚██╔╝██║
  ██║  ██║╚██████╔╝███████║   ██║   ██║  ██║██║ ╚═╝ ██║
  ╚═╝  ╚═╝ ╚═════╝ ╚══════╝   ╚═╝   ╚═╝  ╚═╝╚═╝     ╚═╝
{RESET}{DIM}  attack simulation & telemetry{RESET}
"""


def clear_screen():
    os.system("cls" if platform.system() == "Windows" else "clear")


def print_logo(os_platform=None):
    print(_LOGO)
    if os_platform:
        print(f"  {DIM}Platform:{RESET} {WHITE}{os_platform.upper()}{RESET}")
    print()


def print_banner(title):
    print(f"\n  {RED}{'━' * 56}{RESET}")
    print(f"  {BOLD}{WHITE}  {title}{RESET}")
    print(f"  {RED}{'━' * 56}{RESET}\n")


def print_menu(title, options):
    cursor = 0
    while True:
        clear_screen()
        print_banner(title)
        for i, (key, label) in enumerate(options):
            if i == cursor:
                sys.stdout.write(f"\033[7m  {RED}▸{RESET}\033[7m {label} \033[0m\n")
            else:
                print(f"    {DIM}{label}{RESET}")
        sys.stdout.flush()

        k = read_key()
        if k == "up" and cursor > 0:
            cursor -= 1
        elif k == "down" and cursor < len(options) - 1:
            cursor += 1
        elif k == "enter":
            return options[cursor][0]
        elif k in ("q", "esc"):
            return options[-1][0]


def confirm(prompt):
    resp = input(f"  {prompt} {DIM}[y/N]{RESET} {RED}▸{RESET} ").strip().lower()
    return resp in ("y", "yes")


def get_number(prompt, default=None):
    suffix = f" {DIM}[{default}]{RESET}" if default is not None else ""
    raw = input(f"  {prompt}{suffix} {RED}▸{RESET} ").strip()
    if not raw and default is not None:
        return default
    try:
        return int(raw)
    except ValueError:
        return default


def pause():
    input(f"\n  {DIM}Press Enter to continue...{RESET}")


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
        print(f"\n  {BOLD}{WHITE}{title}{RESET}")
        print(f"  {DIM}{help_text}{RESET}")
        print(f"  {RED}{'━' * 68}{RESET}\n")

        for i in range(offset, end):
            item = items[i]
            is_cur = i == cursor
            is_sel = item["key"] in selected
            ind = "    " * item.get("indent", 0)

            arrow = f"{RED}▸{RESET}" if is_cur else " "
            if is_sel:
                check = f"{RED}✓{RESET}"
            else:
                check = f"{DIM}·{RESET}"

            tid_part = item["key"]
            rest = item["label"][len(tid_part):]

            if item.get("expandable"):
                marker = f" {RED}▼{RESET}" if item.get("expanded") else f" {DIM}▶{RESET}"
            else:
                marker = ""

            line = f"  {arrow} [{check}] {ind}{RED}{tid_part}{RESET}{DIM}{rest}{RESET}{marker}"

            if is_cur:
                sys.stdout.write(f"\033[7m  ▸ [{check}] {ind}{tid_part}{rest}{marker}\033[0m\n")
            else:
                sys.stdout.write(line + "\n")

        print(f"\n  {RED}{'━' * 68}{RESET}")
        sel_count = f"{WHITE}{len(selected)}{RESET}" if selected else f"{DIM}0{RESET}"
        print(f"  {DIM}Selected:{RESET} {sel_count}  {DIM}│{RESET}  {DIM}{offset + 1}-{end} of {n}{RESET}")
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
