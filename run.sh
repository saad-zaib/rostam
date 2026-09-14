#!/usr/bin/env bash
# ──────────────────────────────────────────────────────────────
#  Rostam — ATT&CK Kill-Chain Telemetry Generator
#  Linux bootstrap: ensures Python 3 + PyYAML, then launches the tool.
# ──────────────────────────────────────────────────────────────
set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$SCRIPT_DIR"

# ── helpers ──────────────────────────────────────────────────

info()  { echo "[*] $*"; }
ok()    { echo "[+] $*"; }
fail()  { echo "[!] $*" >&2; exit 1; }

command_exists() { command -v "$1" >/dev/null 2>&1; }

detect_pkg_manager() {
    if command_exists apt-get;  then echo "apt";  return; fi
    if command_exists dnf;      then echo "dnf";  return; fi
    if command_exists yum;      then echo "yum";  return; fi
    if command_exists pacman;   then echo "pacman"; return; fi
    if command_exists zypper;   then echo "zypper"; return; fi
    echo "unknown"
}

# ── install Python 3 if missing ─────────────────────────────

install_python() {
    local mgr="$1"
    info "Installing Python 3 via $mgr..."
    case "$mgr" in
        apt)
            apt-get update -qq
            apt-get install -y -qq python3 python3-pip python3-venv
            ;;
        dnf)
            dnf install -y -q python3 python3-pip
            ;;
        yum)
            yum install -y -q python3 python3-pip
            ;;
        pacman)
            pacman -Sy --noconfirm python python-pip
            ;;
        zypper)
            zypper --non-interactive install python3 python3-pip
            ;;
        *)
            fail "No supported package manager found. Install Python 3 manually."
            ;;
    esac
}

# ── install PyYAML if missing ────────────────────────────────

install_pyyaml() {
    local py="$1"
    info "Installing PyYAML..."
    if "$py" -m pip install pyyaml -q 2>/dev/null; then
        return 0
    fi
    if command_exists pip3; then
        pip3 install pyyaml -q 2>/dev/null && return 0
    fi
    # Try OS package as last resort
    local mgr
    mgr="$(detect_pkg_manager)"
    case "$mgr" in
        apt)    apt-get install -y -qq python3-yaml ;;
        dnf)    dnf install -y -q python3-pyyaml ;;
        yum)    yum install -y -q python3-pyyaml ;;
        pacman) pacman -Sy --noconfirm python-yaml ;;
        zypper) zypper --non-interactive install python3-PyYAML ;;
        *)      fail "Cannot install PyYAML. Run: pip3 install pyyaml" ;;
    esac
}

# ── main ─────────────────────────────────────────────────────

PY=""
for candidate in python3 python; do
    if command_exists "$candidate"; then
        ver=$("$candidate" -c "import sys; print(sys.version_info[0])" 2>/dev/null || echo "0")
        if [ "$ver" = "3" ]; then
            PY="$candidate"
            break
        fi
    fi
done

if [ -z "$PY" ]; then
    info "Python 3 not found."
    read -rp "  Install Python 3 now? [y/N] > " ans
    case "$ans" in
        y|Y|yes|YES)
            mgr="$(detect_pkg_manager)"
            install_python "$mgr"
            ;;
        *)
            fail "Python 3 is required. Install it and re-run."
            ;;
    esac

    for candidate in python3 python; do
        if command_exists "$candidate"; then
            PY="$candidate"
            break
        fi
    done
    [ -z "$PY" ] && fail "Python 3 installation failed."
fi

ok "Python 3 found: $($PY --version)"

# Check PyYAML
if ! "$PY" -c "import yaml" 2>/dev/null; then
    install_pyyaml "$PY"
    "$PY" -c "import yaml" 2>/dev/null || fail "PyYAML installation failed."
fi

ok "PyYAML available."

# Create logs dir if needed
mkdir -p "$SCRIPT_DIR/logs"

# Launch
exec "$PY" "$SCRIPT_DIR/attack_sim.py"
