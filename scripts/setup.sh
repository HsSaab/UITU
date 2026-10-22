#!/bin/bash
# Rootless installation from signed Debian repositories; no system files changed.
set -euo pipefail
TOOLS=${UITU_TOOLS:-/workspace/.uitu-tools}
mkdir -p "$TOOLS/apt/lists/partial" "$TOOLS/apt/cache/archives/partial" "$TOOLS/root"
cat > "$TOOLS/apt/sources.list" <<'EOF'
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian trixie main contrib
deb [signed-by=/usr/share/keyrings/debian-archive-keyring.gpg] https://deb.debian.org/debian-security trixie-security main contrib
EOF
OPTIONS=(-o "Dir::State::lists=$TOOLS/apt/lists" -o "Dir::Cache=$TOOLS/apt/cache" -o "Dir::Etc::sourcelist=$TOOLS/apt/sources.list" -o Dir::Etc::sourceparts=- -o Debug::NoLocking=true)
/usr/bin/apt-get "${OPTIONS[@]}" update
/usr/bin/apt-get "${OPTIONS[@]}" --download-only --no-install-recommends -y install php8.4-cli php8.4-cgi php8.4-mysql mariadb-server-core mariadb-client-core mariadb-client apache2-bin
for package in "$TOOLS/apt/cache/archives/"*.deb; do dpkg-deb -x "$package" "$TOOLS/root"; done
env LD_LIBRARY_PATH="$TOOLS/root/usr/lib/x86_64-linux-gnu" "$TOOLS/root/usr/bin/php8.4" -n -v
