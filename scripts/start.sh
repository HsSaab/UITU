#!/bin/bash
set -euo pipefail
ROOT=$(cd "$(dirname "$0")/.." && pwd)
TOOLS=${UITU_TOOLS:-/workspace/.uitu-tools}/root
RUN="$ROOT/.runtime"
mkdir -p "$RUN/db" "$RUN/sessions"
export LD_LIBRARY_PATH="$TOOLS/usr/lib/x86_64-linux-gnu"
if [ ! -d "$RUN/db/mysql" ]; then
 "$TOOLS/usr/bin/mariadb-install-db" --no-defaults --basedir="$TOOLS/usr" --datadir="$RUN/db" --auth-root-authentication-method=normal --skip-test-db > "$RUN/init.log" 2>&1
fi
if ! "$TOOLS/usr/bin/mariadb-admin" --no-defaults --socket="$RUN/mysql.sock" -u root ping >/dev/null 2>&1; then
 nohup "$TOOLS/usr/sbin/mariadbd" --no-defaults --basedir="$TOOLS/usr" --datadir="$RUN/db" --socket="$RUN/mysql.sock" --pid-file="$RUN/mysql.pid" --skip-networking --innodb-buffer-pool-size=64M --log-error="$RUN/mysql.log" > "$RUN/mysql-console.log" 2>&1 &
 for n in $(seq 1 40); do
  if "$TOOLS/usr/bin/mariadb-admin" --no-defaults --socket="$RUN/mysql.sock" -u root ping >/dev/null 2>&1; then break; fi
  sleep .25
 done
fi
"$TOOLS/usr/bin/mariadb" --no-defaults --socket="$RUN/mysql.sock" -u root -e "CREATE DATABASE IF NOT EXISTS uitu CHARACTER SET utf8mb4; CREATE USER IF NOT EXISTS 'uitu'@'localhost' IDENTIFIED BY ''; GRANT ALL ON uitu.* TO 'uitu'@'localhost';"
bash "$ROOT/scripts/php.sh" "$ROOT/app/seed.php"
cat > "$RUN/httpd.conf" <<EOF
ServerRoot "$TOOLS/etc/apache2"
DefaultRuntimeDir "$RUN"
PidFile "$RUN/apache.pid"
Listen 127.0.0.1:8080
ServerName localhost
LoadModule mpm_event_module "$TOOLS/usr/lib/apache2/modules/mod_mpm_event.so"
LoadModule authz_core_module "$TOOLS/usr/lib/apache2/modules/mod_authz_core.so"
LoadModule dir_module "$TOOLS/usr/lib/apache2/modules/mod_dir.so"
LoadModule mime_module "$TOOLS/usr/lib/apache2/modules/mod_mime.so"
LoadModule proxy_module "$TOOLS/usr/lib/apache2/modules/mod_proxy.so"
LoadModule proxy_fcgi_module "$TOOLS/usr/lib/apache2/modules/mod_proxy_fcgi.so"
ProxyFCGIBackendType GENERIC
TypesConfig /etc/mime.types
DocumentRoot "$ROOT/app/public"
DirectoryIndex index.php
ErrorLog "$RUN/apache-error.log"
LogLevel warn
<Directory "$ROOT/app/public">
 Require all granted
 AllowOverride None
 Options -Indexes
 <FilesMatch "\\.php$">
  SetHandler "proxy:fcgi://127.0.0.1:9000"
 </FilesMatch>
</Directory>
EOF
if [ ! -f "$RUN/fcgi.pid" ] || ! ps -p "$(cat "$RUN/fcgi.pid")" -o stat= 2>/dev/null | grep -q '^[^Z]'; then
 nohup "$TOOLS/usr/bin/php-cgi8.4" -n -d date.timezone=UTC -d extension="$TOOLS/usr/lib/php/20240924/pdo.so" -d extension="$TOOLS/usr/lib/php/20240924/mysqlnd.so" -d extension="$TOOLS/usr/lib/php/20240924/pdo_mysql.so" -b 127.0.0.1:9000 > "$RUN/fcgi.log" 2>&1 &
 echo $! > "$RUN/fcgi.pid"
fi
if [ ! -f "$RUN/apache.pid" ] || ! kill -0 "$(cat "$RUN/apache.pid")" 2>/dev/null; then
 "$TOOLS/usr/sbin/apache2" -f "$RUN/httpd.conf" -k start
fi
for n in $(seq 1 30); do
 if curl -fsS 'http://127.0.0.1:8080/index.php?api=session' > "$RUN/readiness.json" 2>/dev/null; then cat "$RUN/readiness.json"; exit 0; fi
 sleep .25
done
echo 'Не удалось запустить сайт; проверьте .runtime/*.log' >&2
exit 1
