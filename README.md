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

## MITRE ATT&CK Navigator Integration

After every chain or single technique execution, Rostam generates a **Navigator layer JSON file** compatible with the [ATT&CK Navigator](https://mitre-attack.github.io/attack-navigator/). Each executed technique is color-coded by result:

| Color | Status |
|-------|--------|
| Green | Success |
| Red | Error |
| Orange | Warning |
| Grey | Timeout / Skipped |
| Blue | Manual |

**To visualize:**
1. Run a chain or technique in Rostam
2. Open [mitre-attack.github.io/attack-navigator](https://mitre-attack.github.io/attack-navigator/)
3. Click **Open Existing Layer** → **Upload from local**
4. Select the generated `.json` file from `layers/`

Layer files are saved as `layers/rostam_<timestamp>.json`.

## HTML Reports

Every execution also generates a standalone HTML report in `reports/`. Open it in any browser — no external dependencies needed.

Reports include:
- Chain summary with color-coded status badges
- Per-technique cards with technique ID, name, description, status, and duration
- Expandable output preview for each test
- Reference to the corresponding Navigator layer file

Report filenames use kill-chain phase names for easy identification:
```
reports/discovery_credaccess_collection_exfil_20260915_073035.html
```

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
│   ├── log_writer.py       # JSONL logger
│   ├── navigator.py        # ATT&CK Navigator layer generator
│   └── report.py           # HTML report generator
├── chains/
│   ├── linux/              # 5 prebuilt Linux chains
│   └── windows/            # 5 prebuilt Windows chains
├── layers/                 # Navigator layer JSON files
├── reports/                # HTML execution reports
├── logs/                   # Execution logs (JSONL)
└── atomics/                # Test definitions (downloaded on first run)
```

## Requirements

- Python 3.6+
- PyYAML
- git (optional, for faster definition download; falls back to zip)

## References

Test definitions sourced from the [Atomic Red Team](https://github.com/redcanaryco/atomic-red-team) project. Technique IDs follow the [MITRE ATT&CK](https://attack.mitre.org/) framework.

## Disclaimer

This tool is intended for authorized security testing and detection engineering only. Run it on systems you own or have explicit permission to test. The author is not responsible for misuse.
