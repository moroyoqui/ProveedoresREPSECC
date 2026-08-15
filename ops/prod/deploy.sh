#!/usr/bin/env bash
# Despliegue de producción. Corre EN EL SERVIDOR, invocado por SSH desde el
# workflow de GitHub Actions (o a mano para un rollback).
#
#   Uso: deploy.sh <app_image> <web_image>
#   Ej.: deploy.sh ghcr.io/moroyoqui/proveedoresrepsecc/app:a1b2c3d \
#                  ghcr.io/moroyoqui/proveedoresrepsecc/web:a1b2c3d
#
# Secuencia: pull -> backup de BD -> migraciones -> arranque -> health.
# Si el backup o las migraciones fallan, aborta y la versión anterior sigue
# corriendo intacta.

set -euo pipefail

APP_IMAGE_NEW="${1:?falta app_image}"
WEB_IMAGE_NEW="${2:?falta web_image}"

DEPLOY_DIR="${DEPLOY_DIR:-/opt/repse}"
ENV_FILE="$DEPLOY_DIR/.env"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.prod.yml"

cd "$DEPLOY_DIR"

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

# shellcheck disable=SC1090
set -a; source "$ENV_FILE"; set +a

BACKUP_DIR="${BACKUP_DIR:-$DEPLOY_DIR/backups}"

log() { printf '\n[deploy] %s\n' "$*"; }

# --- 1. Guardar la versión actual para poder revertir a mano ----------------
PREV_APP_IMAGE="${APP_IMAGE:-}"
PREV_WEB_IMAGE="${WEB_IMAGE:-}"
log "versión actual: app=$PREV_APP_IMAGE web=$PREV_WEB_IMAGE"

# --- 2. Descargar las imágenes nuevas antes de tocar nada -------------------
log "descargando imágenes"
docker pull "$APP_IMAGE_NEW"
docker pull "$WEB_IMAGE_NEW"

# --- 3. Backup de la base de datos ------------------------------------------
# Sólo si el stack ya está levantado: en el primer despliegue no hay nada que
# respaldar.
if compose ps --status running --services 2>/dev/null | grep -qx mysql; then
    mkdir -p "$BACKUP_DIR"
    STAMP="$(date +%Y%m%d-%H%M%S)"
    DUMP="$BACKUP_DIR/pre-deploy-$STAMP.sql.gz"
    log "backup de BD -> $DUMP"
    compose exec -T mysql \
        mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" \
        --single-transaction --routines --triggers --databases "$DB_NAME" \
        | gzip > "$DUMP"
    # Un dump vacío significa que mysqldump falló aunque el pipe devolviera 0.
    if [ ! -s "$DUMP" ]; then
        log "ERROR: el backup quedó vacío, se aborta el despliegue"
        rm -f "$DUMP"
        exit 1
    fi
else
    log "stack no levantado: se omite el backup (primer despliegue)"
fi

# --- 4. Fijar las imágenes nuevas en el .env --------------------------------
log "actualizando .env"
sed -i "s|^APP_IMAGE=.*|APP_IMAGE=$APP_IMAGE_NEW|" "$ENV_FILE"
sed -i "s|^WEB_IMAGE=.*|WEB_IMAGE=$WEB_IMAGE_NEW|" "$ENV_FILE"

# --- 5. Migraciones ---------------------------------------------------------
# Se ejecutan con la imagen nueva contra la BD viva, antes de reemplazar la app.
log "asegurando mysql arriba"
compose up -d --wait mysql

log "aplicando migraciones (alembic upgrade head)"
if ! compose run --rm --no-deps -w /app app alembic upgrade head; then
    log "ERROR: fallaron las migraciones. La versión anterior sigue corriendo."
    log "Restaurar el .env manualmente si hace falta: APP_IMAGE=$PREV_APP_IMAGE"
    exit 1
fi

# --- 6. Arranque ------------------------------------------------------------
log "levantando servicios"
compose up -d --remove-orphans

# --- 7. Health check --------------------------------------------------------
log "esperando health de app"
for i in $(seq 1 30); do
    if compose exec -T app curl -fsS http://localhost:8000/health >/dev/null 2>&1; then
        log "app saludable tras ${i} intento(s)"
        compose ps
        log "despliegue OK: $APP_IMAGE_NEW"
        # --- 8. Limpieza de imágenes viejas (conserva las en uso) -----------
        docker image prune -f --filter "until=168h" >/dev/null 2>&1 || true
        exit 0
    fi
    sleep 5
done

log "ERROR: la app no respondió /health en 150s. Últimos logs:"
compose logs --tail 80 app
log "Rollback manual: ./deploy.sh $PREV_APP_IMAGE $PREV_WEB_IMAGE"
exit 1
