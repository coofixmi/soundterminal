#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
RUN_SH="$SCRIPT_DIR/run.sh"
BIN_DIR="${XDG_BIN_HOME:-$HOME/.local/bin}"

if [ ! -f "$RUN_SH" ]; then
  echo "[install] Ошибка: не найден $RUN_SH" >&2
  exit 1
fi

mkdir -p "$BIN_DIR"

install_launcher() {
  local name="$1"
  local target="$BIN_DIR/$name"
  cat > "$target" <<BASH
#!/usr/bin/env bash
set -euo pipefail
exec "$RUN_SH" "\$@"
BASH
  chmod +x "$target"
  echo "[install] Установлена команда: $name -> $RUN_SH"
}

install_launcher "soundterminal"
install_launcher "soundterminal-mint"

echo "[install] Готово. Теперь можно запускать из терминала: soundterminal (или soundterminal-mint)"

case ":$PATH:" in
  *":$BIN_DIR:"*) ;;
  *)
    echo "[install] ВНИМАНИЕ: $BIN_DIR не найден в PATH. Добавь в конфиг оболочки, например:"
    echo "  export PATH=\"$BIN_DIR:\$PATH\""
    ;;
esac
