#!/bin/sh
# LiveLift daily database backup loop (POSIX sh, BusyBox-compatible).
#
# Runs inside the `backup` service (see docker-compose.yml), which provides
# PGHOST/PGUSER/PGPASSWORD/PGDATABASE. Once per day at ${BACKUP_HOUR}:00
# (default 02:00, container clock) it writes a compressed custom-format dump to
# ${BACKUP_DIR}/livelift-YYYY-MM-DD.dump.gz, prunes dumps older than
# ${RETENTION_DAYS} days, and logs exactly one line per run.
#
# Restore example:
#   gunzip -c /backups/livelift-2026-08-24.dump.gz | pg_restore -d livelift --clean

set -u

BACKUP_DIR="${BACKUP_DIR:-/backups}"
BACKUP_HOUR="${BACKUP_HOUR:-02}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"

log() {
    echo "$(date -u +%Y-%m-%dT%H:%M:%SZ) backup: $*"
}

mkdir -p "$BACKUP_DIR"
log "started (dir=$BACKUP_DIR hour=${BACKUP_HOUR}:00 retention=${RETENTION_DAYS}d db=${PGDATABASE:-?}@${PGHOST:-?})"

while true; do
    # Seconds until the next ${BACKUP_HOUR}:00 (avoids `date -d`, absent in BusyBox).
    # Strip one leading zero so "08"/"09" are not parsed as bad octal in $((...)).
    now_h=$(date +%H); now_m=$(date +%M); now_s=$(date +%S)
    now_h=${now_h#0}; now_m=${now_m#0}; now_s=${now_s#0}
    secs_today=$(( now_h * 3600 + now_m * 60 + now_s ))
    target=$(( ${BACKUP_HOUR#0} * 3600 ))
    wait=$(( target - secs_today ))
    [ "$wait" -le 0 ] && wait=$(( wait + 86400 ))
    sleep "$wait"

    day=$(date +%F)
    out="$BACKUP_DIR/livelift-$day.dump.gz"
    if pg_dump -Fc | gzip > "$out.tmp" && mv "$out.tmp" "$out"; then
        size=$(wc -c < "$out" | tr -d ' ')
        pruned=$(find "$BACKUP_DIR" -name 'livelift-*.dump.gz' -mtime +"$RETENTION_DAYS" -print -delete | wc -l | tr -d ' ')
        log "OK $out size=${size}B pruned=${pruned}"
    else
        rm -f "$out.tmp"
        log "FAILED pg_dump for $day (db=${PGDATABASE:-?}@${PGHOST:-?})"
    fi
done
