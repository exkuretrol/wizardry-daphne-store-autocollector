#!/usr/bin/env bash
#
# setup_vm.sh — provision an Oracle Cloud (or any Linux) VM to run the JP webstore
# autocollector (main_jp.py) headless on a weekly cron.
#
# Designed for a small Always-Free instance (1 vCPU / 1 GB RAM). Tuned accordingly:
# adds swap (Chromium can spike past 1 GB), installs the headless-shell Chromium, and
# uses the lean launch flags already baked into main_jp.py.
#
# Idempotent: safe to re-run. Works on Ubuntu/Debian (apt) and Oracle Linux/RHEL (dnf).
#
# Usage:
#   git clone <your-fork-url> wvd && cd wvd
#   bash setup_vm.sh
#   # then edit ~/.wvd_jp.env with your JP credentials (the script creates a template)
#   # test:  ./run_jp.sh
#
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
VENV_DIR="$REPO_DIR/.venv"
ENV_FILE="$HOME/.wvd_jp.env"          # credentials live OUTSIDE the repo — never committed
RUNNER="$REPO_DIR/run_jp.sh"
LOG_FILE="$HOME/wvd-jp.log"
SWAP_FILE="/swapfile"
SWAP_SIZE="2G"
CRON_SCHEDULE="0 11 * * 1"            # Monday 11:00 UTC — matches the international store
CRON_MARKER="# wvd-jp-autocollector"

say() { printf '\n\033[1;36m==> %s\033[0m\n' "$*"; }
warn() { printf '\033[1;33m[warn]\033[0m %s\n' "$*"; }

# ---------------------------------------------------------------------------
# 0. Detect package manager
# ---------------------------------------------------------------------------
if command -v apt-get >/dev/null 2>&1; then
    PKG=apt
elif command -v dnf >/dev/null 2>&1; then
    PKG=dnf
else
    echo "Unsupported distro: need apt-get or dnf." >&2
    exit 1
fi
say "Package manager: $PKG"

# ---------------------------------------------------------------------------
# 1. Swap (critical on 1 GB RAM)
# ---------------------------------------------------------------------------
if swapon --show 2>/dev/null | grep -q "$SWAP_FILE" || [ -f "$SWAP_FILE" ]; then
    say "Swap already present — skipping."
else
    say "Creating ${SWAP_SIZE} swap at ${SWAP_FILE}..."
    sudo fallocate -l "$SWAP_SIZE" "$SWAP_FILE" || sudo dd if=/dev/zero of="$SWAP_FILE" bs=1M count=2048
    sudo chmod 600 "$SWAP_FILE"
    sudo mkswap "$SWAP_FILE"
    sudo swapon "$SWAP_FILE"
    if ! grep -q "$SWAP_FILE" /etc/fstab; then
        echo "$SWAP_FILE none swap sw 0 0" | sudo tee -a /etc/fstab >/dev/null
    fi
fi
free -h | sed -n '1,3p'

# ---------------------------------------------------------------------------
# 2. Base system packages
# ---------------------------------------------------------------------------
say "Installing base packages (python3, venv, pip, git)..."
if [ "$PKG" = apt ]; then
    sudo apt-get update -y
    sudo apt-get install -y python3 python3-venv python3-pip git ca-certificates
else
    sudo dnf install -y python3 python3-pip git ca-certificates
fi

# ---------------------------------------------------------------------------
# 3. Python venv + dependencies
# ---------------------------------------------------------------------------
say "Setting up Python virtualenv..."
[ -d "$VENV_DIR" ] || python3 -m venv "$VENV_DIR"
"$VENV_DIR/bin/pip" install --upgrade pip
"$VENV_DIR/bin/pip" install -r "$REPO_DIR/requirements.txt"

# ---------------------------------------------------------------------------
# 4. Playwright browser + system libraries
# ---------------------------------------------------------------------------
say "Installing Chromium for Playwright..."
"$VENV_DIR/bin/playwright" install chromium

say "Installing Chromium system dependencies..."
if [ "$PKG" = apt ]; then
    # Officially supported path.
    sudo "$VENV_DIR/bin/playwright" install-deps chromium
else
    # Oracle Linux / RHEL: playwright install-deps is not supported. Install the known libs.
    if ! sudo dnf install -y \
        nss nspr atk at-spi2-atk cups-libs libdrm libxkbcommon \
        libXcomposite libXdamage libXrandr libXfixes libXext libX11 libxcb \
        mesa-libgbm pango cairo alsa-lib 2>/dev/null; then
        warn "Some Chromium libs may be missing on this distro. If the browser fails to"
        warn "launch, run: ldd \"\$(${VENV_DIR}/bin/playwright install chromium --dry-run | tail -1)\""
        warn "to find the missing .so and install it via dnf."
    fi
fi

# ---------------------------------------------------------------------------
# 5. Credentials template (outside the repo, locked down)
# ---------------------------------------------------------------------------
if [ ! -f "$ENV_FILE" ]; then
    say "Creating credentials template at ${ENV_FILE} (fill it in!)..."
    cat > "$ENV_FILE" <<'EOF'
# Wizardry Variants Daphne — JP webstore credentials. Keep this file private.
WIZARDRY_JP_EMAIL=
WIZARDRY_JP_PASSWORD=
# Leave WIZARDRY_JP_PROXY unset on the VM — it already has a native Japan IP.
EOF
    chmod 600 "$ENV_FILE"
else
    say "Credentials file already exists at ${ENV_FILE} — leaving it untouched."
fi

# ---------------------------------------------------------------------------
# 6. Runner wrapper (sources creds, runs the script, used by cron)
# ---------------------------------------------------------------------------
say "Writing runner ${RUNNER}..."
cat > "$RUNNER" <<EOF
#!/usr/bin/env bash
set -euo pipefail
cd "$REPO_DIR"
set -a; . "$ENV_FILE"; set +a
exec "$VENV_DIR/bin/python" main_jp.py
EOF
chmod +x "$RUNNER"

# ---------------------------------------------------------------------------
# 7. Cron entry (weekly, idempotent)
# ---------------------------------------------------------------------------
say "Installing weekly cron job..."
CRON_LINE="$CRON_SCHEDULE $RUNNER >> $LOG_FILE 2>&1 $CRON_MARKER"
# Replace any existing entry with our marker, then append the current one.
( crontab -l 2>/dev/null | grep -v "$CRON_MARKER" ; echo "$CRON_LINE" ) | crontab -
say "Current crontab:"
crontab -l | grep "$CRON_MARKER" || true

# ---------------------------------------------------------------------------
# 8. Timezone sanity + next steps
# ---------------------------------------------------------------------------
TZ_NOW="$(timedatectl 2>/dev/null | awk -F': ' '/Time zone/{print $2}' || cat /etc/timezone 2>/dev/null || echo unknown)"
say "Done."
cat <<EOF

Next steps:
  1. Fill in your JP credentials:
       nano ${ENV_FILE}
  2. Test it now (will report "already claimed" if this week's reward is taken):
       ${RUNNER}
       tail -n 40 ${LOG_FILE}
  3. The cron runs '${CRON_SCHEDULE}'. Cron uses this VM's timezone, currently: ${TZ_NOW}
     The schedule assumes UTC (to match the international store at 11:00 UTC).
     If the VM is NOT on UTC, either set it (sudo timedatectl set-timezone UTC)
     or adjust the hour in the crontab accordingly.

Logs: ${LOG_FILE}
EOF
