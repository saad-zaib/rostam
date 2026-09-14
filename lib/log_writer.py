"""JSONL execution logger — one line per test execution."""

import os
import json
from datetime import datetime


class LogWriter:
    def __init__(self, base_dir):
        self.log_dir = os.path.join(base_dir, "logs")
        os.makedirs(self.log_dir, exist_ok=True)
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.session_file = os.path.join(self.log_dir, f"run_{ts}.jsonl")

    def log(self, entry):
        with open(self.session_file, "a") as f:
            f.write(json.dumps(entry, default=str) + "\n")

    def list_logs(self):
        if not os.path.isdir(self.log_dir):
            return []
        return sorted(
            [f for f in os.listdir(self.log_dir) if f.endswith(".jsonl")],
            reverse=True,
        )

    def read_log(self, filename):
        path = os.path.join(self.log_dir, filename)
        entries = []
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line:
                    entries.append(json.loads(line))
        return entries
