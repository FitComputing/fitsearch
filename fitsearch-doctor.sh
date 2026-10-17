#!/usr/bin/env bash
set -u
MODE="${1:-user}"
URL="http://127.0.0.1:8765"
echo "Diagnostic FitSearch — mode $MODE"
python3 --version 2>/dev/null || echo "ERREUR : Python 3 est introuvable"
if [[ "$MODE" == "system" || "$MODE" == "server" ]]; then
  systemctl is-enabled fitsearch 2>/dev/null || true
  systemctl --no-pager --full status fitsearch 2>/dev/null | sed -n '1,12p'
else
  systemctl --user is-enabled fitsearch 2>/dev/null || true
  systemctl --user --no-pager --full status fitsearch 2>/dev/null | sed -n '1,12p'
fi
if [[ "$MODE" == "server" ]]; then
  DATA_DIR="${FITSEARCH_DATA:-/var/lib/fitsearch}"
  if [[ -f "$DATA_DIR/auth.db" ]]; then
    echo "OK : base des comptes présente dans $DATA_DIR"
  else
    echo "ATTENTION : aucun compte serveur créé dans $DATA_DIR"
  fi
fi
if command -v curl >/dev/null && curl --silent --fail --max-time 3 "$URL/health" >/dev/null; then
  echo "OK : FitSearch répond sur $URL"
else
  echo "ERREUR : FitSearch ne répond pas sur $URL"
fi
