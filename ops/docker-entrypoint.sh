#!/bin/sh
# Normaliza el volumen de uploads y dropea a 'app' antes de exec.
# Razón: `docker compose run` u otros flujos pueden dejar archivos con dueño
# root en /var/repse/uploads y luego el proceso normal (uid 1000) no puede
# escribir. Este entrypoint se autocorrige al arranque.

set -e

if [ "$(id -u)" = "0" ]; then
    chown -R app:app /var/repse/uploads 2>/dev/null || true
    chmod 700 /var/repse/uploads 2>/dev/null || true
    exec setpriv --reuid=1000 --regid=1000 --init-groups --inh-caps=-all "$@"
fi

exec "$@"
