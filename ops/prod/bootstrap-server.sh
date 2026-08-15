#!/usr/bin/env bash
# Preparación de un Ubuntu limpio para producción. Se corre UNA VEZ, como root
# (o con sudo), directamente en el servidor:
#
#   curl -fsSL https://raw.githubusercontent.com/moroyoqui/ProveedoresREPSECC/main/ops/prod/bootstrap-server.sh | sudo bash
#
# Deja listo: Docker, usuario `deploy`, /opt/repse, firewall y el timer de
# backups. NO configura secretos: eso es el paso manual que sigue (ver
# docs/deploy-produccion.md).

set -euo pipefail

DEPLOY_USER=deploy
DEPLOY_DIR=/opt/repse
REPO_RAW="https://raw.githubusercontent.com/moroyoqui/ProveedoresREPSECC/main"

log() { printf '\n== %s\n' "$*"; }

[ "$(id -u)" = "0" ] || { echo "Correr como root (sudo)."; exit 1; }

# --- 1. Paquetes base y Docker ----------------------------------------------
log "instalando paquetes base"
apt-get update
apt-get install -y --no-install-recommends \
    ca-certificates curl gnupg ufw unattended-upgrades

if ! command -v docker >/dev/null; then
    log "instalando Docker Engine + compose plugin"
    install -m 0755 -d /etc/apt/keyrings
    curl -fsSL https://download.docker.com/linux/ubuntu/gpg \
        | gpg --dearmor -o /etc/apt/keyrings/docker.gpg
    chmod a+r /etc/apt/keyrings/docker.gpg
    echo "deb [arch=$(dpkg --print-architecture) signed-by=/etc/apt/keyrings/docker.gpg] \
https://download.docker.com/linux/ubuntu $(. /etc/os-release && echo "$VERSION_CODENAME") stable" \
        > /etc/apt/sources.list.d/docker.list
    apt-get update
    apt-get install -y docker-ce docker-ce-cli containerd.io \
        docker-buildx-plugin docker-compose-plugin
fi
systemctl enable --now docker

# --- 2. Usuario de despliegue ------------------------------------------------
if ! id "$DEPLOY_USER" >/dev/null 2>&1; then
    log "creando usuario $DEPLOY_USER"
    useradd --create-home --shell /bin/bash "$DEPLOY_USER"
fi
usermod -aG docker "$DEPLOY_USER"
install -d -m 0700 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh"
touch "/home/$DEPLOY_USER/.ssh/authorized_keys"
chown "$DEPLOY_USER:$DEPLOY_USER" "/home/$DEPLOY_USER/.ssh/authorized_keys"
chmod 600 "/home/$DEPLOY_USER/.ssh/authorized_keys"

# --- 3. Directorio de despliegue --------------------------------------------
log "preparando $DEPLOY_DIR"
install -d -m 0750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$DEPLOY_DIR"
install -d -m 0750 -o "$DEPLOY_USER" -g "$DEPLOY_USER" "$DEPLOY_DIR/backups"

for f in docker-compose.prod.yml deploy.sh backup.sh; do
    curl -fsSL "$REPO_RAW/ops/prod/$f" -o "$DEPLOY_DIR/$f"
done
curl -fsSL "$REPO_RAW/ops/prod/.env.prod.example" -o "$DEPLOY_DIR/.env.example"
chmod +x "$DEPLOY_DIR/deploy.sh" "$DEPLOY_DIR/backup.sh"
chown -R "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR"

if [ ! -f "$DEPLOY_DIR/.env" ]; then
    cp "$DEPLOY_DIR/.env.example" "$DEPLOY_DIR/.env"
    chown "$DEPLOY_USER:$DEPLOY_USER" "$DEPLOY_DIR/.env"
    chmod 600 "$DEPLOY_DIR/.env"
    log "creado $DEPLOY_DIR/.env desde la plantilla — HAY QUE RELLENARLO"
fi

# --- 4. Firewall -------------------------------------------------------------
log "configurando ufw"
ufw allow OpenSSH
ufw allow 80/tcp
ufw allow 443/tcp
ufw --force enable

# --- 5. Backups automáticos --------------------------------------------------
log "instalando timer de backups"
curl -fsSL "$REPO_RAW/ops/prod/systemd/repse-backup.service" \
    -o /etc/systemd/system/repse-backup.service
curl -fsSL "$REPO_RAW/ops/prod/systemd/repse-backup.timer" \
    -o /etc/systemd/system/repse-backup.timer
systemctl daemon-reload
systemctl enable --now repse-backup.timer

# --- 6. Actualizaciones de seguridad automáticas -----------------------------
dpkg-reconfigure -f noninteractive unattended-upgrades

cat <<EOF

== Listo. Pasos manuales que faltan:
  1. Pegar la clave pública de CI en /home/$DEPLOY_USER/.ssh/authorized_keys
  2. Rellenar $DEPLOY_DIR/.env (secretos, dominio, SMTP, OIDC)
  3. docker login ghcr.io  (como usuario $DEPLOY_USER, con un PAT read:packages)
  4. Apuntar el DNS del dominio a este servidor antes del primer deploy
EOF
