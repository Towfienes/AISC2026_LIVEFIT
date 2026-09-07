#!/bin/sh
# LiveLift daily database backup loop (POSIX sh, BusyBox-compatible).
#
# Runs inside the `backup` service (see docker-compose.yml), which provides
# PGHOST/PGUSER/PGPASSWORD/PGDATABASE. Once per day at ${BACKUP_HOUR}:00
# (default 02:00, container clock) it writes a compressed custom-format dump to
# ${BACKUP_DIR}/livelift-YYYY-MM-DD.dump.gz, prunes dumps older than
# ${RETENTION_DAYS} days, and logs exactly one line per run.
#
# A dump is only logged OK after it has been VERIFIED readable
# (gzip -t + pg_restore --list). On any failure the temp file is removed,
# a FAILED line (with the real exit code) is logged, and the script exits
# with that code — `restart: unless-stopped` restarts the container, so the
# failure is visible in `docker ps` (restart count) instead of a silent
# corrupt dump. The next attempt runs at the next ${BACKUP_HOUR}:00.
#
# Restore example:
#   gunzip -c /backups/livelift-2026-08-24.dump.gz | pg_restore -d livelift --clean

# pipefail: without it `pg_dump ... | gzip` reports gzip's status, so a dead
# pg_dump with a happy gzip used to log OK over a corrupt dump.
set -euo pipefail

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
    if pg_dump -Fc | gzip > "$out.tmp"; then
        # A finished write is not yet a usable backup: verify BEFORE declaring OK.
        #   1) gzip -t          — whole-file integrity (catches truncated writes);
        #   2) pg_restore --list — the custom-format header/TOC reads back.
        # pg_restore --list stops after the TOC, so gunzip can get SIGPIPE (141)
        # on a GOOD dump — that gunzip status is ignored on purpose (gzip -t
        # already scanned the whole file); only pg_restore decides the pipe.
        if gzip -t "$out.tmp" \
            && { gunzip -c "$out.tmp" 2>/dev/null || true; } | pg_restore --list >/dev/null; then
            mv "$out.tmp" "$out"
            size=$(wc -c < "$out" | tr -d ' ')
            pruned=$(find "$BACKUP_DIR" -name 'livelift-*.dump.gz' -mtime +"$RETENTION_DAYS" -print -delete | wc -l | tr -d ' ')
            log "OK $out size=${size}B pruned=${pruned}"
        else
            rc=$?
            rm -f "$out.tmp"
            log "FAILED xác minh dump (gzip -t / pg_restore --list, exit=$rc) cho $day — dump hỏng, không giữ lại, không ghi đè bản cũ"
            exit "$rc"
        fi
    else
        rc=$?
        rm -f "$out.tmp"
        log "FAILED pg_dump|gzip (exit=$rc) cho $day (db=${PGDATABASE:-?}@${PGHOST:-?})"
        exit "$rc"
    fi
done
