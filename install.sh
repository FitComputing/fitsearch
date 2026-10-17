#!/usr/bin/env bash
set -euo pipefail

SOURCE_DIR="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")" && pwd)"
MODE="${1:-}"

usage() {
  echo "Usage : ./install.sh [user|system|server]"
  echo "  user    Installation personnelle, sans droits administrateur"
  echo "  system  Installation commune à la machine, avec sudo/root"
  echo "  server  Installation multi-utilisateur derrière un reverse proxy HTTPS"
}

if [[ "$MODE" == "--help" || "$MODE" == "-h" ]]; then usage; exit 0; fi
if [[ -z "$MODE" ]]; then
  if [[ -t 0 ]]; then
    echo "Installation de FitSearch V2.17.7"
    echo "  1) Utilisateur local — réglages personnels, sans sudo"
    echo "  2) Système local — service commun à tous les comptes"
    echo "  3) Serveur — invités et comptes FitSearch séparés"
    read -r -p "Votre choix [1] : " answer
    case "${answer:-1}" in 2) MODE="system" ;; 3) MODE="server" ;; *) MODE="user" ;; esac
  else
    MODE="user"
  fi
fi
[[ "$MODE" == "--user" ]] && MODE="user"
[[ "$MODE" == "--system" ]] && MODE="system"
if [[ "$MODE" != "user" && "$MODE" != "system" && "$MODE" != "server" ]]; then usage; exit 2; fi

command -v python3 >/dev/null || { echo "Python 3 est requis."; exit 1; }
python3 -c 'import sys; raise SystemExit(sys.version_info < (3,10))' || {
  echo "FitSearch nécessite Python 3.10 ou plus récent."; exit 1;
}

install_application() {
  local app_dir="$1"
  mkdir -p "$app_dir"
  cp -R "$SOURCE_DIR/fitsearch" "$SOURCE_DIR/pyproject.toml" "$SOURCE_DIR/requirements.txt" "$app_dir/"
  if ! python3 -m venv "$app_dir/.venv"; then
    echo "Impossible de créer l’environnement Python. Installez python3-venv (Debian/Deepin) ou python (Arch)."
    exit 1
  fi
  "$app_dir/.venv/bin/pip" install --disable-pip-version-check --upgrade pip
  "$app_dir/.venv/bin/pip" install --disable-pip-version-check --upgrade "$app_dir"
}

if [[ "$MODE" == "user" ]]; then
  APP_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fitsearch/app"
  DATA_DIR="${XDG_DATA_HOME:-$HOME/.local/share}/fitsearch"
  BIN_DIR="$HOME/.local/bin"
  CONFIG_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/fitsearch"
  UNIT_DIR="${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user"
  mkdir -p "$DATA_DIR" "$BIN_DIR" "$CONFIG_DIR" "$UNIT_DIR"
  install_application "$APP_DIR"
  ln -sfn "$APP_DIR/.venv/bin/fitsearch" "$BIN_DIR/fitsearch"
  umask 077
  {
    echo "FITSEARCH_MODE=user"
    echo "FITSEARCH_HOST=127.0.0.1"
    echo "FITSEARCH_PORT=8765"
    echo "FITSEARCH_DATA=$DATA_DIR"
    echo "FITSEARCH_AUTH_MODE=local"
  } > "$CONFIG_DIR/fitsearch.env"
  umask 022
  sed -e "s|@EXEC@|$APP_DIR/.venv/bin/fitsearch|g" \
      -e "s|@ENVFILE@|$CONFIG_DIR/fitsearch.env|g" \
      "$SOURCE_DIR/services/fitsearch-user.service" > "$UNIT_DIR/fitsearch.service"
  if command -v systemctl >/dev/null && systemctl --user daemon-reload 2>/dev/null; then
    systemctl --user enable fitsearch
    systemctl --user restart fitsearch
    SERVICE_MESSAGE="Le service utilisateur est activé et démarré."
  else
    SERVICE_MESSAGE="Le service systemd utilisateur n’est pas disponible ; lancez $BIN_DIR/fitsearch."
  fi
  echo "FitSearch V2.17.7 est installé pour l’utilisateur $USER."
  echo "$SERVICE_MESSAGE"
  echo "Adresse : http://127.0.0.1:8765"
  echo "Diagnostic : $SOURCE_DIR/fitsearch-doctor.sh user"
  exit 0
fi

if [[ "$EUID" -ne 0 ]]; then
  echo "L’installation système nécessite les droits administrateur."
  echo "Relancez : sudo ./install.sh system"
  exit 1
fi

BASE_DIR="/opt/fitsearch"
RELEASES_DIR="$BASE_DIR/releases"
CURRENT_LINK="$BASE_DIR/current"
LEGACY_DIR="$BASE_DIR/app"
VERSION="2.17.7"
RELEASE_DIR="$RELEASES_DIR/$VERSION"
BUILD_DIR="$RELEASES_DIR/.$VERSION.build.$$"
NEXT_LINK="$BASE_DIR/.current.next.$$"
DATA_DIR="/var/lib/fitsearch"
CONFIG_DIR="/etc/fitsearch"
UNIT_FILE="/etc/systemd/system/fitsearch.service"
SERVICE_USER="fitsearch"

previous_target=""
switched=0
release_created=0

cleanup_system_install() {
  local rc=$?
  trap - EXIT INT TERM
  rm -rf -- "$BUILD_DIR"
  rm -f -- "$NEXT_LINK"

  if (( rc != 0 && switched == 1 )) && [[ -n "$previous_target" ]]; then
    echo "Échec de la mise à niveau : retour vers $previous_target." >&2
    systemctl stop fitsearch.service 2>/dev/null || true
    ln -s "$previous_target" "$NEXT_LINK"
    mv -Tf "$NEXT_LINK" "$CURRENT_LINK"
    systemctl daemon-reload
    systemctl start fitsearch.service || true
  fi

  if (( rc != 0 && release_created == 1 )); then
    rm -rf -- "$RELEASE_DIR"
  fi
  exit "$rc"
}

trap cleanup_system_install EXIT INT TERM

if [[ -e "$RELEASE_DIR" || -L "$RELEASE_DIR" ]]; then
  echo "La version $VERSION existe déjà : $RELEASE_DIR" >&2
  exit 1
fi

if ! getent group "$SERVICE_USER" >/dev/null; then groupadd --system "$SERVICE_USER"; fi
if ! id "$SERVICE_USER" >/dev/null 2>&1; then
  NOLOGIN="$(command -v nologin || echo /usr/sbin/nologin)"
  useradd --system --gid "$SERVICE_USER" --home-dir "$DATA_DIR" --shell "$NOLOGIN" "$SERVICE_USER"
fi

install -d -o root -g root -m 0755 "$BASE_DIR" "$RELEASES_DIR"
install -d -o "$SERVICE_USER" -g "$SERVICE_USER" -m 0750 "$DATA_DIR"
install -d -o root -g "$SERVICE_USER" -m 0750 "$CONFIG_DIR"

if [[ ! -L "$CURRENT_LINK" ]]; then
  if [[ -d "$LEGACY_DIR" ]]; then
    ln -s "app" "$CURRENT_LINK"
  elif [[ -e "$CURRENT_LINK" ]]; then
    echo "$CURRENT_LINK existe mais n’est pas un lien symbolique." >&2
    exit 1
  fi
fi
if [[ -L "$CURRENT_LINK" ]]; then
  previous_target="$(readlink "$CURRENT_LINK")"
fi

echo "Préparation isolée de FitSearch $VERSION..."
install -d -o root -g root -m 0755 "$BUILD_DIR"
cp -R "$SOURCE_DIR/fitsearch" "$SOURCE_DIR/pyproject.toml" "$SOURCE_DIR/requirements.txt" "$BUILD_DIR/"
find "$BUILD_DIR" -type d -exec chmod 0755 {} +
find "$BUILD_DIR" -type f -exec chmod 0644 {} +
chown -R root:root "$BUILD_DIR"
mv -T "$BUILD_DIR" "$RELEASE_DIR"
release_created=1

# Les lanceurs du venv mémorisent leur chemin absolu : il doit donc être créé
# directement dans la release définitive, avant la bascule de « current ».
if ! python3 -m venv "$RELEASE_DIR/.venv"; then
  echo "Impossible de créer l’environnement Python. Installez python3-venv." >&2
  exit 1
fi
"$RELEASE_DIR/.venv/bin/pip" install --disable-pip-version-check --upgrade pip
"$RELEASE_DIR/.venv/bin/pip" install --disable-pip-version-check --upgrade "$RELEASE_DIR"

installed_version="$("$RELEASE_DIR/.venv/bin/python3" -c 'import fitsearch; print(fitsearch.__version__)')"
if [[ "$installed_version" != "$VERSION" ]]; then
  echo "Version préparée inattendue : $installed_version" >&2
  exit 1
fi

chown -R root:root "$RELEASE_DIR"
chown -R "$SERVICE_USER:$SERVICE_USER" "$DATA_DIR"
chmod 750 "$DATA_DIR"
{
  echo "FITSEARCH_MODE=system"
  echo "FITSEARCH_HOST=127.0.0.1"
  echo "FITSEARCH_PORT=8765"
  echo "FITSEARCH_DATA=$DATA_DIR"
  if [[ "$MODE" == "server" ]]; then
    echo "FITSEARCH_AUTH_MODE=multiuser"
  else
    echo "FITSEARCH_AUTH_MODE=local"
  fi
} > "$CONFIG_DIR/fitsearch.env"
chmod 640 "$CONFIG_DIR/fitsearch.env"
chown root:"$SERVICE_USER" "$CONFIG_DIR/fitsearch.env"
echo "Bascule atomique vers $VERSION..."
ln -s "releases/$VERSION" "$NEXT_LINK"
mv -Tf "$NEXT_LINK" "$CURRENT_LINK"
switched=1

sed -e "s|@EXEC@|$CURRENT_LINK/.venv/bin/fitsearch|g" \
    -e "s|@ENVFILE@|$CONFIG_DIR/fitsearch.env|g" \
    "$SOURCE_DIR/services/fitsearch-system.service" > "$UNIT_FILE"
systemctl daemon-reload
systemctl enable fitsearch
systemctl restart fitsearch

echo "Contrôle de santé de la nouvelle version..."
healthy=0
for _attempt in {1..30}; do
  if systemctl is-active --quiet fitsearch.service && \
     curl -fsS http://127.0.0.1:8765/health | grep -q "\"version\":\"$VERSION\""; then
    healthy=1
    break
  fi
  sleep 1
done
if (( healthy == 0 )); then
  echo "Le contrôle de santé de FitSearch $VERSION a échoué." >&2
  exit 1
fi

switched=0
release_created=0
trap - EXIT INT TERM

echo "FitSearch V2.17.7 est installé en mode $MODE."
echo "Version active : $(readlink -f "$CURRENT_LINK")"
if [[ -n "$previous_target" ]]; then
  echo "Version précédente conservée : $previous_target"
fi
echo "Adresse interne : http://127.0.0.1:8765"
if [[ "$MODE" == "server" ]]; then
  echo "Créez le premier administrateur avec fitsearch-accounts avant d'ouvrir le service aux utilisateurs."
else
  echo "Les réglages et données sont communs et stockés dans $DATA_DIR."
fi
echo "Diagnostic : $SOURCE_DIR/fitsearch-doctor.sh system"
