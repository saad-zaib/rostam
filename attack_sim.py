#!/usr/bin/env python3
"""MITRE ATT&CK Kill-Chain Telemetry Generator."""

import sys
import os
import platform

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

import yaml  # noqa: E402 — guaranteed by run.sh / run.bat

from lib import menu          # noqa: E402
from lib.atomics import AtomicsManager   # noqa: E402
from lib.chains import ChainLoader       # noqa: E402
from lib.executor import Executor        # noqa: E402
from lib.log_writer import LogWriter     # noqa: E402

R = "\033[91m"
B = "\033[94m"
G = "\033[92m"
W = "\033[1;97m"
D = "\033[2m"
X = "\033[0m"


def detect_platform():
    s = platform.system().lower()
    if s == "linux":
        return "linux"
    if s == "windows":
        return "windows"
    print(f"[!] Unsupported platform: {s}")
    sys.exit(1)


# ── technique tree builder ──────────────────────────────────


def _build_technique_tree(atomics):
    """Group techniques into parent -> sub-technique hierarchy."""
    all_tids = atomics.list_techniques()
    parents = {}

    for tid in all_tids:
        t = atomics.get_technique(tid)
        tc = len(t["tests"])
        entry = {"tid": tid, "name": t["display_name"], "tests": tc}

        if "." in tid:
            base = tid.split(".")[0]
            parents.setdefault(base, {"tid": base, "name": None, "tests": 0, "subs": []})
            parents[base]["subs"].append(entry)
        else:
            if tid in parents:
                parents[tid]["name"] = t["display_name"]
                parents[tid]["tests"] = tc
            else:
                parents[tid] = {"tid": tid, "name": t["display_name"], "tests": tc, "subs": []}

    ordered = []
    for tid in sorted(parents.keys()):
        p = parents[tid]
        if p["name"] is None:
            base_name = p["subs"][0]["name"].split(":")[0].strip() if p["subs"] else tid
            p["name"] = base_name
        sub_count = len(p["subs"])
        total_tests = p["tests"] + sum(s["tests"] for s in p["subs"])
        ordered.append({
            "tid": p["tid"], "name": p["name"],
            "tests": p["tests"], "sub_count": sub_count,
            "total_tests": total_tests, "subs": sorted(p["subs"], key=lambda s: s["tid"]),
        })

    return ordered


# ── arrow-key picker for techniques ────────────────────────


def _build_picker_items(tree):
    """Build flat item list from tree (parents only, collapsed)."""
    items = []
    for t in tree:
        has_subs = t["sub_count"] > 0
        tests_str = f"({t['total_tests']} tests)"
        sub_str = f"  [{t['sub_count']} sub]" if has_subs else ""
        items.append({
            "key": t["tid"],
            "label": f"{t['tid']:12s} {t['name']}  {tests_str}{sub_str}",
            "indent": 0,
            "expandable": has_subs,
            "expanded": False,
            "has_tests": t["tests"] > 0,
            "_subs": t["subs"],
            "_name": t["name"],
        })
    return items


def _expand_item(items, idx):
    """Insert sub-technique items after the parent at idx."""
    parent = items[idx]
    parent["expanded"] = True
    subs = parent.get("_subs", [])
    for j, sub in enumerate(subs):
        child = {
            "key": sub["tid"],
            "label": f"{sub['tid']:15s} {sub['name']}  ({sub['tests']} tests)",
            "indent": 1,
            "expandable": False,
            "expanded": False,
            "has_tests": True,
            "_name": sub["name"],
        }
        items.insert(idx + 1 + j, child)


def _collapse_item(items, idx):
    """Remove children of the item at idx."""
    items[idx]["expanded"] = False
    parent_indent = items[idx]["indent"]
    while idx + 1 < len(items) and items[idx + 1]["indent"] > parent_indent:
        items.pop(idx + 1)


def technique_picker(atomics, os_platform, multi=True):
    """
    Interactive arrow-key technique picker.
    multi=True  → space to select multiple, r to run chain
    multi=False → enter on a leaf runs it immediately
    Returns list of technique IDs, or empty list if cancelled.
    """
    tree = _build_technique_tree(atomics)
    items = _build_picker_items(tree)
    selected = set()
    cursor = 0

    if multi:
        help_text = "↑↓ Move  Enter: Expand  Space: Select  r: Run selected  q: Back"
    else:
        help_text = "↑↓ Move  Enter: Expand/Run  q: Back"
    title = f"Techniques — {os_platform.upper()}"

    while True:
        (action, data), cursor, selected = menu.picker(
            items, title=title, help_text=help_text,
            selected=selected, cursor=cursor,
            on_expand=_expand_item, on_collapse=_collapse_item,
        )

        if action == "select":
            if multi:
                selected.add(data)
            else:
                return [data]
        elif action == "run":
            if selected:
                return sorted(selected)
            return []
        elif action == "quit":
            return []


# ── menu actions ────────────────────────────────────────────


def run_prebuilt_chain(chains, executor):
    chain_list = chains.list_chains()
    if not chain_list:
        print(f"\n  {R}[!]{X} No prebuilt chains found for this platform.")
        menu.pause()
        return

    options = [(str(i), f"{name}  —  {desc}") for i, name, desc in chain_list]
    options.append(("b", "Back"))

    choice = menu.print_menu("Prebuilt Attack Chains", options)
    if choice == "b":
        return

    try:
        chain = chains.get_chain(int(choice))
    except (ValueError, IndexError):
        chain = None

    if not chain:
        print(f"  {R}[!]{X} Invalid selection.")
        menu.pause()
        return

    print(f"\n  {W}Chain :{X} {chain['name']}")
    print(f"  {D}Desc  :{X} {chain.get('description', '')}")
    print(f"  {D}Steps :{X}")
    for i, step in enumerate(chain["steps"]):
        print(f"    {R}{i + 1}. [{step['technique']}]{X} {step.get('name', '')}")

    if menu.confirm(f"\n  {W}Execute this chain?{X}"):
        executor.run_chain(chain)
    menu.pause()


def build_custom_chain(atomics, executor, os_platform):
    selected_ids = technique_picker(atomics, os_platform, multi=True)
    if not selected_ids:
        return

    steps = []
    for tid in selected_ids:
        t = atomics.get_technique(tid)
        if t:
            steps.append({"technique": tid, "name": t["display_name"], "delay": 5})

    if not steps:
        return

    menu.clear_screen()
    print(f"\n  {W}Custom chain{X} {D}({len(steps)} steps){X}")
    print(f"  {R}{'━' * 50}{X}")
    for i, s in enumerate(steps):
        print(f"    {R}{i + 1}. [{s['technique']}]{X} {s['name']}")
    print(f"  {R}{'━' * 50}{X}")

    if menu.confirm(f"\n  {W}Execute?{X}"):
        executor.run_chain({"name": "Custom Chain", "description": "User-built", "steps": steps})
    menu.pause()


def run_single_technique(atomics, executor, os_platform):
    selected_ids = technique_picker(atomics, os_platform, multi=False)
    if not selected_ids:
        return

    tid = selected_ids[0]
    technique = atomics.get_technique(tid)
    if not technique:
        return

    tests = technique["tests"]

    if len(tests) == 1:
        test_idx = 0
    else:
        menu.clear_screen()
        print(f"\n  {R}{tid}{X} {D}—{X} {W}{technique['display_name']}{X}")
        print(f"  {D}Tests ({len(tests)}):{X}\n")
        for i, t in enumerate(tests):
            exe = t.get("executor", {}).get("name", "?")
            print(f"    {R}[{W}{i}{R}]{X} {t.get('name', 'Unnamed')}  {D}({exe}){X}")
        test_idx = menu.get_number(f"\n  {W}Select test{X}", 0)
        if test_idx is None or not (0 <= test_idx < len(tests)):
            test_idx = 0

    test = tests[test_idx]

    overrides = {}
    inputs = test.get("input_arguments", {})
    if inputs:
        print(f"\n  {D}Input arguments (Enter to keep default):{X}")
        for arg, defn in inputs.items():
            default = defn.get("default", "")
            print(f"    {R}{arg}{X}: {D}{defn.get('description', '')}{X}")
            val = input(f"      {D}[{default}]{X} {R}▸{X} ").strip()
            if val:
                overrides[arg] = val

    executor.run_single(tid, test_idx, overrides or None)
    menu.pause()


def view_logs(log_writer):
    logs = log_writer.list_logs()
    if not logs:
        print(f"\n  {R}[!]{X} No logs yet.")
        menu.pause()
        return

    options = [(str(i), f) for i, f in enumerate(logs[:10])]
    options.append(("b", "Back"))

    choice = menu.print_menu("Execution Logs", options)
    if choice == "b":
        return

    try:
        entries = log_writer.read_log(logs[int(choice)])
    except (ValueError, IndexError):
        return

    _STATUS_CLR = {"SUCCESS": G, "ERROR": R, "WARNING": "\033[93m", "TIMEOUT": D, "SKIPPED": D, "MANUAL": B}
    print(f"\n  {R}{'━' * 60}{X}")
    for e in entries:
        status = e.get("status", "?").upper()
        tid = e.get("technique_id", "?")
        name = e.get("test_name", e.get("step_name", e.get("technique_name", "?")))
        ts = e.get("start_time", e.get("timestamp", ""))
        dur = e.get("duration_seconds")
        dur_s = f" {D}({dur:.1f}s){X}" if isinstance(dur, (int, float)) else ""
        sc = _STATUS_CLR.get(status, D)
        print(f"  {sc}[{status:7s}]{X} {R}{tid:12s}{X} {name}{dur_s}")
        if ts:
            print(f"  {D}           {ts}{X}")
    print(f"  {R}{'━' * 60}{X}")
    menu.pause()


# ── main ────────────────────────────────────────────────────


def main():
    os_platform = detect_platform()

    menu.clear_screen()
    menu.print_logo(os_platform)

    atomics = AtomicsManager(BASE_DIR, os_platform)
    log_writer = LogWriter(BASE_DIR)

    if not atomics.is_downloaded():
        print("\n[*] Test definitions not found.")
        if menu.confirm("Download now?"):
            atomics.download()
        else:
            print("[!] Cannot continue without test definitions.")
            sys.exit(1)

    atomics.load_index()
    chains = ChainLoader(BASE_DIR, os_platform)
    executor = Executor(atomics, log_writer, os_platform, base_dir=BASE_DIR)

    while True:
        choice = menu.print_menu("Main Menu", [
            ("1", "Run Prebuilt Attack Chain"),
            ("2", "Build & Run Custom Chain"),
            ("3", "Run Single Technique"),
            ("4", "View Execution Logs"),
            ("5", f"Set Step Delay  (current: {executor.delay}s)"),
            ("0", "Exit"),
        ])

        if choice == "1":
            run_prebuilt_chain(chains, executor)
        elif choice == "2":
            build_custom_chain(atomics, executor, os_platform)
        elif choice == "3":
            run_single_technique(atomics, executor, os_platform)
        elif choice == "4":
            view_logs(log_writer)
        elif choice == "5":
            d = menu.get_number("Delay between steps (seconds)", executor.delay)
            if d is not None:
                executor.set_delay(d)
                print(f"  [+] Delay set to {d}s")
        elif choice == "0":
            print(f"\n  {R}[*]{X} Done. Stay safe.\n")
            break


if __name__ == "__main__":
    main()
