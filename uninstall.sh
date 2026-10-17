#!/usr/bin/env bash
set -euo pipefail
MODE="${1:-user}"
if [[ "$MODE" == "system" ]]; then
  [[ "$EUID" -eq 0 ]] || { echo "Utilisez : sudo ./uninstall.sh system"; exit 1; }
  systemctl disable --now fitsearch 2>/dev/null || true
  rm -f /etc/systemd/system/fitsearch.service
  systemctl daemon-reload
  rm -rf /opt/fitsearch/app /opt/fitsearch/current /opt/fitsearch/releases
  echo "Application système supprimée. Les données sont conservées dans /var/lib/fitsearch."
else
  systemctl --user disable --now fitsearch 2>/dev/null || true
  rm -f "${XDG_CONFIG_HOME:-$HOME/.config}/systemd/user/fitsearch.service"
  systemctl --user daemon-reload 2>/dev/null || true
  rm -f "$HOME/.local/bin/fitsearch"
  rm -rf "${XDG_DATA_HOME:-$HOME/.local/share}/fitsearch/app"
  echo "Application utilisateur supprimée. Les données sont conservées dans ${XDG_DATA_HOME:-$HOME/.local/share}/fitsearch."
fi
