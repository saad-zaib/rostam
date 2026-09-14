"""Download and index ATT&CK technique test definitions."""

import os
import shutil
import subprocess
import yaml


class AtomicsManager:
    REPO_URL = "https://github.com/redcanaryco/atomic-red-team.git"
    ZIP_URL = (
        "https://github.com/redcanaryco/atomic-red-team/archive/refs/heads/master.zip"
    )

    def __init__(self, base_dir, os_platform):
        self.base_dir = base_dir
        self.os_platform = os_platform
        self.atomics_dir = os.path.join(base_dir, "atomics")
        self.index = {}

    def is_downloaded(self):
        if not os.path.isdir(self.atomics_dir):
            return False
        return any(
            e.startswith("T") and os.path.isdir(os.path.join(self.atomics_dir, e))
            for e in os.listdir(self.atomics_dir)
        )

    def download(self):
        print("[*] Downloading test definitions...")
        if shutil.which("git"):
            self._download_git()
        else:
            self._download_zip()

    def _download_git(self):
        tmp = os.path.join(self.base_dir, ".art_tmp")
        if os.path.exists(tmp):
            shutil.rmtree(tmp)
        try:
            subprocess.run(
                [
                    "git", "clone", "--depth", "1",
                    "--filter=blob:none", "--sparse",
                    self.REPO_URL, tmp,
                ],
                check=True,
            )
            subprocess.run(
                ["git", "sparse-checkout", "set", "atomics"],
                cwd=tmp, check=True,
            )
            src = os.path.join(tmp, "atomics")
            if os.path.exists(self.atomics_dir):
                shutil.rmtree(self.atomics_dir)
            shutil.copytree(src, self.atomics_dir)
            print("[+] Downloaded via git sparse-checkout.")
        finally:
            if os.path.exists(tmp):
                shutil.rmtree(tmp)

    def _download_zip(self):
        import urllib.request
        import zipfile

        print("[*] git not available — downloading zip archive (may take a minute)...")
        zip_path = os.path.join(self.base_dir, "art.zip")
        urllib.request.urlretrieve(self.ZIP_URL, zip_path)

        print("[*] Extracting atomics/...")
        with zipfile.ZipFile(zip_path) as zf:
            prefix = None
            for name in zf.namelist():
                if "/atomics/T" in name:
                    prefix = name.split("/atomics/")[0] + "/atomics/"
                    break

            if not prefix:
                print("[!] Could not locate atomics/ in the archive.")
                os.remove(zip_path)
                return

            if os.path.exists(self.atomics_dir):
                shutil.rmtree(self.atomics_dir)
            os.makedirs(self.atomics_dir)

            for member in zf.namelist():
                if member.startswith(prefix) and not member.endswith("/"):
                    rel = member[len(prefix):]
                    target = os.path.join(self.atomics_dir, rel)
                    os.makedirs(os.path.dirname(target), exist_ok=True)
                    with zf.open(member) as src, open(target, "wb") as dst:
                        dst.write(src.read())

        os.remove(zip_path)
        print("[+] Extracted.")

    def load_index(self):
        print("[*] Indexing techniques...")
        count = 0
        for entry in sorted(os.listdir(self.atomics_dir)):
            tech_dir = os.path.join(self.atomics_dir, entry)
            if not entry.startswith("T") or not os.path.isdir(tech_dir):
                continue

            yaml_file = os.path.join(tech_dir, f"{entry}.yaml")
            if not os.path.exists(yaml_file):
                continue

            try:
                with open(yaml_file, encoding="utf-8", errors="replace") as f:
                    data = yaml.safe_load(f)
            except Exception:
                continue

            if not data or "atomic_tests" not in data:
                continue

            tests = [
                t for t in data["atomic_tests"]
                if self.os_platform in t.get("supported_platforms", [])
            ]
            if not tests:
                continue

            self.index[data["attack_technique"]] = {
                "technique_id": data["attack_technique"],
                "display_name": data.get("display_name", entry),
                "tests": tests,
                "dir": tech_dir,
            }
            count += 1

        print(f"[+] {count} techniques available for {self.os_platform}.")

    def get_technique(self, technique_id):
        return self.index.get(technique_id)

    def list_techniques(self):
        return sorted(self.index.keys())

    def search(self, query):
        q = query.lower()
        results = []
        for tid, data in self.index.items():
            if q in tid.lower() or q in data["display_name"].lower():
                results.append((tid, data["display_name"]))
        return sorted(results)
