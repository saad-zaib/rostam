"""Execute ATT&CK technique tests with prerequisite handling and cleanup tracking."""

import subprocess
import time
import traceback
from datetime import datetime

from lib import menu

_HARD_ERROR_PATTERNS = [
    "command not found", "no such file", "cannot find",
    "not recognized", "fatal error", "segmentation fault",
    "core dumped",
]

_WARN_PATTERNS = [
    "access denied", "permission denied", "operation not permitted",
]


class Executor:
    def __init__(self, atomics, log_writer, os_platform):
        self.atomics = atomics
        self.log = log_writer
        self.os_platform = os_platform
        self.delay = 5
        self.atomics_dir = atomics.atomics_dir

    def set_delay(self, seconds):
        self.delay = seconds

    # ── chain execution ─────────────────────────────────────

    def run_chain(self, chain):
        chain_name = chain["name"]
        steps = chain["steps"]
        total = len(steps)
        cleanups = []
        counts = {"success": 0, "error": 0, "skipped": 0, "timeout": 0, "manual": 0}

        print(f"\n[*] Executing chain: {chain_name}")
        print(f"[*] Steps: {total}\n")

        for i, step in enumerate(steps):
            tid = step["technique"]
            step_name = step.get("name", tid)
            step_delay = step.get("delay", self.delay)

            print(f"  [{i + 1}/{total}] {tid} — {step_name}")

            technique = self.atomics.get_technique(tid)
            if not technique:
                print(f"    [!] Technique not found in index. Skipping.")
                self.log.log({
                    "chain": chain_name, "technique_id": tid,
                    "step_name": step_name, "status": "skipped",
                    "reason": "not in index", "timestamp": datetime.now().isoformat(),
                })
                counts["skipped"] += 1
                continue

            test_idx = step.get("test_index", 0)
            tests = technique["tests"]
            if test_idx >= len(tests):
                test_idx = 0
            test = tests[test_idx]

            try:
                result = self._execute_test(technique, test, chain_name=chain_name)
            except Exception as exc:
                print(f"    [!] Unexpected error: {exc}")
                self.log.log({
                    "chain": chain_name, "technique_id": tid,
                    "test_name": test.get("name", "Unnamed"),
                    "status": "error", "reason": f"unhandled exception: {exc}",
                    "timestamp": datetime.now().isoformat(),
                })
                counts["error"] += 1
                continue

            if result:
                counts[result["status"]] = counts.get(result["status"], 0) + 1
                if result.get("cleanup"):
                    cleanups.append(result["cleanup"])
            else:
                counts["skipped"] += 1

            if i < total - 1:
                print(f"    [~] Waiting {step_delay}s...")
                time.sleep(step_delay)

        # Chain summary
        print(f"\n{'—' * 50}")
        print(f"[*] Chain '{chain_name}' complete.")
        parts = []
        for key in ("success", "error", "timeout", "skipped", "manual"):
            if counts.get(key, 0) > 0:
                parts.append(f"{counts[key]} {key}")
        print(f"[*] Results: {', '.join(parts)}")
        print(f"{'—' * 50}")

        if cleanups:
            print(f"\n[?] {len(cleanups)} cleanup commands available.")
            if menu.confirm("Run cleanup now?"):
                self._run_cleanups(cleanups, chain_name)

    # ── single-technique execution ──────────────────────────

    def run_single(self, technique_id, test_index=0, input_overrides=None):
        technique = self.atomics.get_technique(technique_id)
        if not technique:
            print(f"[!] Technique {technique_id} not found.")
            return

        tests = technique["tests"]
        if test_index >= len(tests):
            test_index = 0

        try:
            result = self._execute_test(
                technique, tests[test_index], input_overrides=input_overrides
            )
        except Exception as exc:
            print(f"    [!] Unexpected error: {exc}")
            self.log.log({
                "technique_id": technique_id,
                "test_name": tests[test_index].get("name", "Unnamed"),
                "status": "error", "reason": f"unhandled exception: {exc}",
                "timestamp": datetime.now().isoformat(),
            })
            return

        if result and result.get("cleanup"):
            if menu.confirm("  Run cleanup for this test?"):
                info = result["cleanup"]
                r = self._run_command(info["command"], info["executor"])
                if r["returncode"] == 0:
                    print("    [+] Cleanup done.")
                else:
                    print(f"    [!] Cleanup failed (exit code {r['returncode']}).")

    # ── internal helpers ────────────────────────────────────

    def _execute_test(self, technique, test, chain_name=None, input_overrides=None):
        tid = technique["technique_id"]
        test_name = test.get("name", "Unnamed")
        executor_info = test.get("executor", {})
        executor_name = executor_info.get(
            "name", "bash" if self.os_platform == "linux" else "command_prompt"
        )
        command = executor_info.get("command", "")
        cleanup_cmd = executor_info.get("cleanup_command", "")

        # Manual tests — nothing to execute
        if executor_name == "manual":
            print(f"    [i] Manual test — {test.get('description', 'see definition')}")
            self.log.log({
                "chain": chain_name, "technique_id": tid,
                "test_name": test_name, "status": "manual",
                "timestamp": datetime.now().isoformat(),
            })
            return {"status": "manual", "cleanup": None}

        # Guard: empty command
        if not command or not command.strip():
            print(f"    [!] Empty command for {tid}. Skipping.")
            self.log.log({
                "chain": chain_name, "technique_id": tid,
                "test_name": test_name, "status": "error",
                "reason": "empty command in test definition",
                "timestamp": datetime.now().isoformat(),
            })
            return {"status": "error", "cleanup": None}

        command = self._interpolate(command, test, input_overrides)
        if cleanup_cmd:
            cleanup_cmd = self._interpolate(cleanup_cmd, test, input_overrides)

        # Prerequisites
        if not self._check_prereqs(test):
            self.log.log({
                "chain": chain_name, "technique_id": tid,
                "test_name": test_name, "status": "skipped",
                "reason": "prerequisites not met",
                "timestamp": datetime.now().isoformat(),
            })
            return None

        # Execute
        start = datetime.now()
        print(f"    [>] Running: {test_name}")

        result = self._run_command(command, executor_name)

        end = datetime.now()
        elapsed = (end - start).total_seconds()

        # Determine status
        status = self._classify_result(result)

        # Display output
        if result["output"]:
            lines = result["output"].strip().splitlines()
            for line in lines[:8]:
                print(f"    | {line}")
            if len(lines) > 8:
                print(f"    | ... ({len(lines) - 8} more lines)")

        # Status display
        if status == "success":
            print(f"    [+] SUCCESS ({elapsed:.1f}s)")
        elif status == "timeout":
            print(f"    [!] TIMEOUT ({elapsed:.1f}s)")
        elif status == "error":
            rc = result["returncode"]
            print(f"    [!] ERROR — exit code {rc} ({elapsed:.1f}s)")
        elif status == "warning":
            print(f"    [~] WARNING — completed but stderr indicates issues ({elapsed:.1f}s)")

        # Log
        self.log.log({
            "chain": chain_name,
            "technique_id": tid,
            "technique_name": technique["display_name"],
            "test_name": test_name,
            "executor": executor_name,
            "status": status,
            "return_code": result["returncode"],
            "start_time": start.isoformat(),
            "end_time": end.isoformat(),
            "duration_seconds": round(elapsed, 2),
            "output_preview": (result["output"] or "")[:500],
            "stderr_preview": (result.get("stderr") or "")[:500],
        })

        cleanup_info = None
        if cleanup_cmd:
            cleanup_info = {
                "technique_id": tid,
                "test_name": test_name,
                "command": cleanup_cmd,
                "executor": executor_name,
            }

        return {"status": status, "cleanup": cleanup_info}

    def _classify_result(self, result):
        """Determine true status from return code + output content."""
        rc = result["returncode"]
        stderr = (result.get("stderr") or "").lower()
        combined = (result.get("output") or "").lower()

        if rc == -1 and result.get("output") == "TIMEOUT":
            return "timeout"

        if rc != 0:
            return "error"

        for pattern in _HARD_ERROR_PATTERNS:
            if pattern in stderr or pattern in combined:
                return "error"

        for pattern in _WARN_PATTERNS:
            if pattern in stderr:
                return "warning"

        return "success"

    def _interpolate(self, command, test, overrides=None):
        inputs = test.get("input_arguments", {})
        overrides = overrides or {}

        for arg_name, arg_def in inputs.items():
            value = str(overrides.get(arg_name, arg_def.get("default", "")))
            value = value.replace("PathToAtomicsFolder", self.atomics_dir)
            command = command.replace(f"#{{{arg_name}}}", value)

        command = command.replace("$PathToAtomicsFolder", self.atomics_dir)
        command = command.replace("#{PathToAtomicsFolder}", self.atomics_dir)
        command = command.replace("PathToAtomicsFolder", self.atomics_dir)
        return command

    def _check_prereqs(self, test):
        deps = test.get("dependencies", [])
        if not deps:
            return True

        dep_executor = test.get(
            "dependency_executor_name",
            "bash" if self.os_platform == "linux" else "powershell",
        )

        for dep in deps:
            check_cmd = dep.get("prereq_command", "")
            install_cmd = dep.get("get_prereq_command", "")
            description = dep.get("description", "Unknown prerequisite")

            if not check_cmd:
                continue

            check_cmd = self._interpolate(check_cmd, test)
            result = self._run_command(check_cmd, dep_executor, quiet=True)

            if result["returncode"] != 0:
                print(f"    [!] Prerequisite not met: {description}")
                if install_cmd:
                    install_cmd = self._interpolate(install_cmd, test)
                    if menu.confirm("    Install this prerequisite?"):
                        print("    [*] Installing...")
                        inst = self._run_command(install_cmd, dep_executor)
                        if inst["returncode"] != 0:
                            print("    [!] Installation failed. Skipping test.")
                            return False
                        recheck = self._run_command(check_cmd, dep_executor, quiet=True)
                        if recheck["returncode"] != 0:
                            print("    [!] Prerequisite still not met after install. Skipping.")
                            return False
                        print("    [+] Installed and verified.")
                    else:
                        print("    [*] Skipping test.")
                        return False
                else:
                    print("    [!] No installer available. Skipping test.")
                    return False
        return True

    def _run_command(self, command, executor_name, quiet=False, timeout=120):
        try:
            if self.os_platform == "linux":
                shell_cmd = ["bash", "-c", command]
            else:
                if executor_name == "powershell":
                    shell_cmd = ["powershell", "-NoProfile", "-Command", command]
                else:
                    shell_cmd = ["cmd", "/c", command]

            proc = subprocess.run(
                shell_cmd, capture_output=True, text=True, timeout=timeout,
            )
            return {
                "returncode": proc.returncode,
                "output": proc.stdout + proc.stderr,
                "stderr": proc.stderr,
            }
        except subprocess.TimeoutExpired:
            if not quiet:
                print(f"    [!] Timed out after {timeout}s")
            return {"returncode": -1, "output": "TIMEOUT", "stderr": "TIMEOUT"}
        except FileNotFoundError as e:
            msg = f"Shell not found: {e}"
            if not quiet:
                print(f"    [!] {msg}")
            return {"returncode": -1, "output": msg, "stderr": msg}
        except PermissionError as e:
            msg = f"Permission denied: {e}"
            if not quiet:
                print(f"    [!] {msg}")
            return {"returncode": -1, "output": msg, "stderr": msg}
        except Exception as e:
            msg = f"{type(e).__name__}: {e}"
            if not quiet:
                print(f"    [!] {msg}")
            return {"returncode": -1, "output": msg, "stderr": msg}

    def _run_cleanups(self, cleanups, chain_name=None):
        print("\n[*] Running cleanup (reverse order)...")
        for info in reversed(cleanups):
            tid = info["technique_id"]
            test_name = info["test_name"]
            print(f"  [<] {tid} — {test_name}")
            result = self._run_command(info["command"], info["executor"])
            if result["returncode"] == 0:
                print(f"    [+] done")
                status = "success"
            else:
                print(f"    [!] failed (exit code {result['returncode']})")
                status = "error"
            self.log.log({
                "chain": chain_name,
                "technique_id": tid,
                "test_name": test_name,
                "phase": "cleanup",
                "status": status,
                "return_code": result["returncode"],
                "timestamp": datetime.now().isoformat(),
                "output_preview": (result["output"] or "")[:300],
            })
        print("[+] Cleanup complete.")
