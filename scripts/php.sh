#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TOOLS=${UITU_TOOLS:-/workspace/.uitu-tools}/root
exec env LD_LIBRARY_PATH="$TOOLS/usr/lib/x86_64-linux-gnu" "$TOOLS/usr/bin/php8.4" -n -d date.timezone=UTC -d extension="$TOOLS/usr/lib/php/20240924/pdo.so" -d extension="$TOOLS/usr/lib/php/20240924/mysqlnd.so" -d extension="$TOOLS/usr/lib/php/20240924/pdo_mysql.so" "$@"
