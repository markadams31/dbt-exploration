#!/bin/bash
# SQL Server's official image has no /docker-entrypoint-initdb.d hook, so this
# wrapper starts the server, waits until it accepts connections, then runs the
# init scripts once. Standard pattern for MSSQL in compose.
set -euo pipefail

/opt/mssql/bin/sqlservr &
SQLSERVR_PID=$!

SQLCMD="/opt/mssql-tools18/bin/sqlcmd -C -S localhost -U sa -P ${MSSQL_SA_PASSWORD}"

for i in $(seq 1 60); do
  if $SQLCMD -Q "SELECT 1" >/dev/null 2>&1; then
    break
  fi
  sleep 2
done

$SQLCMD -i /lab-init/init.sql
$SQLCMD -d warehouse -i /lab-init/raw-seed.sql
echo "lab-init: warehouse ready, raw schema seeded"

wait "$SQLSERVR_PID"
