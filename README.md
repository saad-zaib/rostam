# Rostam

Local attack simulation tool for MITRE ATT&CK kill-chain telemetry generation. Execute technique chains on Linux and Windows with an interactive menu, prerequisite handling, and JSONL logging for detection scoring.

## Quick Start

```bash
# Linux
bash run.sh

# Windows
run.bat
```

The bootstrap script installs Python 3 and PyYAML if missing, downloads test definitions on first run (~50 MB), then launches the interactive menu.

## Features

- **Prebuilt Attack Chains** — 5 Linux + 5 Windows kill-chain scenarios covering recon, credential access, persistence, privilege escalation, lateral movement, collection, and exfiltration
- **Custom Chains** — browse all available techniques with arrow-key navigation, select multiple, and execute as an ordered chain
- **Single Technique Execution** — pick and run individual techniques with input argument overrides
- **Prerequisite Handling** — checks dependencies before each test and prompts to install if missing
- **Accurate Status Reporting** — distinct statuses for success, error, timeout, warning, skipped, and manual tests with stderr pattern analysis
- **JSONL Logging** — every execution is logged with technique ID, timestamps, status, and output preview for detection scoring ground truth
- **Cross-Platform** — auto-detects OS and filters techniques to those supported on the current platform
- **Zero CLI Arguments** — fully interactive, menu-driven with arrow-key navigation

## Navigation

| Key | Action |
|-----|--------|
| `↑` `↓` | Move cursor |
| `Enter` | Expand sub-techniques / Run |
| `Space` | Toggle selection |
| `r` | Run selected techniques |
| `q` | Back |

## Project Structure

```
rostam/
├── run.sh                  # Linux entry point
├── run.bat                 # Windows entry point
├── attack_sim.py           # Main application
├── lib/
│   ├── menu.py             # Interactive menu and arrow-key picker
│   ├── executor.py         # Test execution with error classification
│   ├── atomics.py          # Test definition download and indexing
│   ├── chains.py           # Chain loader
│   └── log_writer.py       # JSONL logger
├── chains/
│   ├── linux/              # 5 prebuilt Linux chains
│   └── windows/            # 5 prebuilt Windows chains
├── logs/                   # Execution logs (JSONL)
└── atomics/                # Test definitions (downloaded on first run)
```

## Custom Chains

Drop YAML files in `chains/linux/` or `chains/windows/` to add your own chains:

```yaml
name: My Chain
description: Custom recon chain
steps:
  - technique: T1082
    name: System Information Discovery
    delay: 5
  - technique: T1033
    name: System Owner/User Discovery
    delay: 3
```

## Logging

Execution logs are written to `logs/` as JSONL files. Each line contains:

```json
{
  "technique_id": "T1082",
  "technique_name": "System Information Discovery",
  "test_name": "System Information Discovery",
  "status": "success",
  "start_time": "2025-01-15T10:30:00",
  "end_time": "2025-01-15T10:30:01",
  "duration_seconds": 0.85,
  "output_preview": "Linux hostname 6.1.0..."
}
```

## Requirements

- Python 3.6+
- PyYAML
- git (optional, for faster definition download; falls back to zip)

## References

Test definitions sourced from the [Atomic Red Team](https://github.com/redcanaryco/atomic-red-team) project. Technique IDs follow the [MITRE ATT&CK](https://attack.mitre.org/) framework.

## Disclaimer

This tool is intended for authorized security testing and detection engineering only. Run it on systems you own or have explicit permission to test. The authors are not responsible for misuse.
