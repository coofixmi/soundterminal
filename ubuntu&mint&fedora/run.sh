#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[soundpad] Рабочая директория: $SCRIPT_DIR"

# libmpv требует LC_NUMERIC=C (иначе возможны предупреждения и segfault)
export LC_NUMERIC=C

# Проверка системных зависимостей
MISSING_PKGS=()
command -v pactl >/dev/null 2>&1 || MISSING_PKGS+=("pulseaudio-utils (или pipewire-pulse)")
command -v mpv >/dev/null 2>&1 || MISSING_PKGS+=("mpv")

# Проверка нативной библиотеки libmpv
HAS_LIBMPV=0
if ldconfig -p 2>/dev/null | grep -qE 'libmpv\.so(\.|$)'; then
  HAS_LIBMPV=1
fi
if [ "$HAS_LIBMPV" -eq 0 ] && compgen -G "/usr/lib*/libmpv.so*" >/dev/null 2>&1; then
  HAS_LIBMPV=1
fi
if [ "$HAS_LIBMPV" -eq 0 ] && compgen -G "/usr/local/lib*/libmpv.so*" >/dev/null 2>&1; then
  HAS_LIBMPV=1
fi
if [ "$HAS_LIBMPV" -eq 0 ] && command -v dpkg >/dev/null 2>&1; then
  if dpkg -s libmpv1 >/dev/null 2>&1 || dpkg -s libmpv2 >/dev/null 2>&1; then
    HAS_LIBMPV=1
  fi
fi
if [ "$HAS_LIBMPV" -eq 0 ]; then
  MISSING_PKGS+=("libmpv (libmpv1/libmpv2 или libmpv-dev)")
fi

if [ ${#MISSING_PKGS[@]} -ne 0 ]; then
  echo "[soundpad] ВНИМАНИЕ: не найдены некоторые системные зависимости:"
  for p in "${MISSING_PKGS[@]}"; do echo "  - $p"; done
  echo "[soundpad] Пример установки (Linux Mint/Ubuntu):"
  echo "  sudo apt update && sudo apt install -y mpv libmpv-dev pulseaudio-utils python3-pip"
  echo "[soundpad] Продолжаю попытку запуска..."
fi

# Python-зависимости
if command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
else
  echo "[soundpad] Ошибка: python3 не найден." >&2
  exit 1
fi

if [ -f "requirements.txt" ]; then
  echo "[soundpad] Установка/проверка Python-зависимостей..."
  "$PY" -m pip install --user -r requirements.txt || {
    echo "[soundpad] Не удалось установить зависимости через pip. Проверьте python3-pip." >&2
  }
fi

echo "[soundpad] Запуск приложения..."
exec "$PY" main.py
