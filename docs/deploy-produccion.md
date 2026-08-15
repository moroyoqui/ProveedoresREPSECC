# Despliegue en producción (CI/CD)

Flujo: **push a `main` → tests → build de imágenes en GHCR → deploy por SSH al
servidor Ubuntu → backup → migraciones → arranque → health check.**

El servidor nunca compila nada ni tiene el código fuente: sólo descarga
imágenes ya construidas.

---

## Piezas

| Archivo | Qué hace |
|---|---|
| `.github/workflows/ci.yml` | ruff + pytest del backend (MySQL vía testcontainers). Corre en PR y como gate del deploy. |
| `.github/workflows/deploy.yml` | Build y push de `app` y `web` a GHCR, luego deploy por SSH. |
| `ops/Dockerfile.app` | Imagen del backend (compartida con desarrollo). |
| `ops/Dockerfile.web` | Build de Vite + Caddy sirviendo el estático y proxy a la API. |
| `ops/Caddyfile.prod` | Sitio de producción con TLS automático (ACME). |
| `ops/prod/docker-compose.prod.yml` | Stack de producción (mysql, app, web). |
| `ops/prod/deploy.sh` | Despliegue en el servidor: pull → backup → migrar → up → health. |
| `ops/prod/backup.sh` + `systemd/` | Backup diario de BD y uploads con retención. |
| `ops/prod/bootstrap-server.sh` | Preparación inicial del Ubuntu limpio. |

Diferencias con `ops/docker-compose.yml` (desarrollo): sin bind mounts ni
`--reload`, sin Mailpit, sin puerto de MySQL publicado, Caddy en 80/443 con
certificado real y frontend compilado en vez de `vite dev`.

---

## 1. Preparar el repositorio

```bash
# Crear main a partir de la rama actual de integración y volverla la default
git checkout -b main 001-repse-compliance-tracker
git push -u origin main
# En GitHub: Settings → General → Default branch → main
# (recomendado) Settings → Branches → proteger main exigiendo el check "CI"
```

## 2. Preparar el servidor Ubuntu

Como root en el servidor limpio:

```bash
curl -fsSL https://raw.githubusercontent.com/moroyoqui/ProveedoresREPSECC/main/ops/prod/bootstrap-server.sh | sudo bash
```

Instala Docker, crea el usuario `deploy`, prepara `/opt/repse`, abre 22/80/443
en ufw y activa el timer de backups.

## 3. Clave SSH para CI

En tu máquina:

```bash
ssh-keygen -t ed25519 -C "github-actions-repse" -f ./deploy_key -N ""
```

En el servidor, pegar `deploy_key.pub` en
`/home/deploy/.ssh/authorized_keys`.

Obtener el fingerprint del host para `known_hosts`:

```bash
ssh-keyscan -H <IP_DEL_SERVIDOR>
```

## 4. Secretos en GitHub

`Settings → Secrets and variables → Actions`:

| Secreto | Valor |
|---|---|
| `DEPLOY_HOST` | IP o hostname del servidor |
| `DEPLOY_USER` | `deploy` |
| `DEPLOY_SSH_KEY` | contenido completo de `deploy_key` (la privada) |
| `DEPLOY_KNOWN_HOSTS` | salida de `ssh-keyscan -H <IP>` |
| `DEPLOY_SSH_PORT` | sólo si SSH no está en el 22 |

Borra la copia local de `deploy_key` cuando termines.

## 5. Acceso del servidor a GHCR

Las imágenes son privadas por defecto. Como usuario `deploy`:

```bash
echo "<PAT_con_read:packages>" | docker login ghcr.io -u <tu_usuario_github> --password-stdin
```

Alternativa: hacer públicos los paquetes `app` y `web` en GitHub y saltarse el
login.

## 6. Configurar `/opt/repse/.env`

```bash
sudo -u deploy nano /opt/repse/.env    # partiendo de .env.example
```

Imprescindibles:

- `APP_SECRET` → `openssl rand -hex 32`
- `DB_PASS` y `MYSQL_PASSWORD` con **el mismo valor**; `MYSQL_ROOT_PASSWORD` aparte
- `CADDY_DOMAIN` y `APP_BASE_URL` con el dominio real
- Credenciales OIDC de Google/Microsoft con los redirect URIs del dominio de producción
- SMTP real (`ALERTS_SCHEDULER_ENABLED=true` envía correos de verdad)

El DNS del dominio debe apuntar al servidor **antes** del primer despliegue: si
no, Caddy no consigue el certificado ACME.

## 7. Primer despliegue

Push a `main` (o `Actions → Deploy a producción → Run workflow`). El primer
arranque crea la base vacía y `deploy.sh` aplica todas las migraciones. El
backup previo se omite porque no hay nada que respaldar todavía.

---

## Operación

**Ver estado y logs** (como `deploy`):

```bash
cd /opt/repse
docker compose --env-file .env -f docker-compose.prod.yml ps
docker compose --env-file .env -f docker-compose.prod.yml logs -f app
```

**Rollback** a una versión anterior — el SHA corto es el tag de la imagen:

```bash
/opt/repse/deploy.sh ghcr.io/moroyoqui/proveedoresrepsecc/app:<sha> \
                     ghcr.io/moroyoqui/proveedoresrepsecc/web:<sha>
```

Ojo: el rollback revierte el **código**, no la base de datos. Si la versión
nueva aplicó una migración destructiva hay que restaurar el dump
`pre-deploy-*.sql.gz` que `deploy.sh` dejó en `/opt/repse/backups/`.

**Backups**: diarios a las 03:30 en `/opt/repse/backups` (BD + uploads),
retención `BACKUP_RETENTION_DAYS` días. Forzar uno:

```bash
sudo systemctl start repse-backup.service
```

Los backups viven en el mismo disco que la aplicación: conviene sincronizarlos
a otro destino (`rsync`/`rclone` a almacenamiento externo) — no está incluido.

**Restaurar la BD**:

```bash
cd /opt/repse
gunzip -c backups/db-<stamp>.sql.gz | \
  docker compose --env-file .env -f docker-compose.prod.yml exec -T mysql \
  mysql -u root -p"$MYSQL_ROOT_PASSWORD"
```

---

## Notas y límites conocidos

- **Un solo worker de uvicorn** a propósito: el scheduler de alertas corre
  dentro del proceso de la app y con varios workers se dispararía N veces. Para
  escalar hay que extraer el scheduler a un servicio propio.
- **Ventana de indisponibilidad** de unos segundos en cada deploy (`compose up`
  recrea los contenedores). Para cero downtime haría falta un despliegue
  azul/verde detrás de Caddy.
- **`/metrics` no se expone públicamente** (Caddy responde 404); se consulta
  desde la red interna de Docker.
- Los tests del frontend no bloquean el despliegue: sólo corren los del
  backend, según lo decidido.
