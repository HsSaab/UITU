#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
RUN="$ROOT/.runtime"
TOOLS=${UITU_TOOLS:-/workspace/.uitu-tools}/root
if [ -f "$RUN/apache.pid" ]; then env LD_LIBRARY_PATH="$TOOLS/usr/lib/x86_64-linux-gnu" "$TOOLS/usr/sbin/apache2" -f "$RUN/httpd.conf" -k stop; fi
if [ -f "$RUN/fcgi.pid" ] && kill -0 "$(cat "$RUN/fcgi.pid")" 2>/dev/null; then kill "$(cat "$RUN/fcgi.pid")"; fi
rm -f "$RUN/fcgi.pid"
if [ -S "$RUN/mysql.sock" ]; then env LD_LIBRARY_PATH="$TOOLS/usr/lib/x86_64-linux-gnu" "$TOOLS/usr/bin/mariadb-admin" --no-defaults --socket="$RUN/mysql.sock" -u root shutdown; fi
