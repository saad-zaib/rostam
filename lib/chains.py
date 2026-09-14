"""Load and manage kill-chain definition files."""

import os
import yaml


class ChainLoader:
    def __init__(self, base_dir, os_platform):
        self.chains_dir = os.path.join(base_dir, "chains", os_platform)
        self.chains = []
        self._load()

    def _load(self):
        if not os.path.isdir(self.chains_dir):
            return
        for fname in sorted(os.listdir(self.chains_dir)):
            if not fname.endswith((".yaml", ".yml")):
                continue
            path = os.path.join(self.chains_dir, fname)
            try:
                with open(path) as f:
                    chain = yaml.safe_load(f)
                if chain and "steps" in chain:
                    chain["_file"] = fname
                    self.chains.append(chain)
            except Exception:
                continue

    def list_chains(self):
        return [
            (i, c["name"], c.get("description", ""))
            for i, c in enumerate(self.chains)
        ]

    def get_chain(self, index):
        if 0 <= index < len(self.chains):
            return self.chains[index]
        return None
