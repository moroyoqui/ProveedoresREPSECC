#!/usr/bin/env bash
# Backup periódico (BD + uploads) invocado por repse-backup.timer.
# Los dumps pre-despliegue los genera deploy.sh; éste es el respaldo diario.

set -euo pipefail

DEPLOY_DIR="${DEPLOY_DIR:-/opt/repse}"
ENV_FILE="$DEPLOY_DIR/.env"
COMPOSE_FILE="$DEPLOY_DIR/docker-compose.prod.yml"

# Lectura directa en vez de `source`: el .env admite valores con espacios que
# bash intentaría ejecutar (ver deploy.sh).
env_get() {
    grep -E "^$1=" "$ENV_FILE" | tail -1 | cut -d= -f2-
}

MYSQL_ROOT_PASSWORD="$(env_get MYSQL_ROOT_PASSWORD)"
DB_NAME="$(env_get DB_NAME)"
BACKUP_DIR="$(env_get BACKUP_DIR)"
BACKUP_DIR="${BACKUP_DIR:-$DEPLOY_DIR/backups}"
RETENTION="$(env_get BACKUP_RETENTION_DAYS)"
RETENTION="${RETENTION:-14}"
STAMP="$(date +%Y%m%d-%H%M%S)"

mkdir -p "$BACKUP_DIR"

compose() {
    docker compose --env-file "$ENV_FILE" -f "$COMPOSE_FILE" "$@"
}

# --- Base de datos ----------------------------------------------------------
DUMP="$BACKUP_DIR/db-$STAMP.sql.gz"
compose exec -T mysql \
    mysqldump -u root -p"$MYSQL_ROOT_PASSWORD" \
    --single-transaction --routines --triggers --databases "$DB_NAME" \
    | gzip > "$DUMP"

if [ ! -s "$DUMP" ]; then
    echo "ERROR: dump vacío" >&2
    rm -f "$DUMP"
    exit 1
fi

# --- Uploads ----------------------------------------------------------------
# El volumen no es accesible directamente desde el host, así que se empaqueta
# desde un contenedor efímero que lo monta en modo lectura. El nombre viene del
# `name: repse-prod` del compose más el nombre del volumen.
docker run --rm \
    -v repse-prod_uploads_data:/data:ro \
    -v "$BACKUP_DIR":/backup \
    alpine:3 tar czf "/backup/uploads-$STAMP.tar.gz" -C /data .

# --- Retención --------------------------------------------------------------
find "$BACKUP_DIR" -name 'db-*.sql.gz' -mtime "+$RETENTION" -delete
find "$BACKUP_DIR" -name 'uploads-*.tar.gz' -mtime "+$RETENTION" -delete
find "$BACKUP_DIR" -name 'pre-deploy-*.sql.gz' -mtime "+$RETENTION" -delete

echo "backup OK: $DUMP y uploads-$STAMP.tar.gz"
