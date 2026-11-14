#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$SCRIPT_DIR"

echo "[soundpad][arch] Рабочая директория: $SCRIPT_DIR"

# libmpv требует LC_NUMERIC=C (иначе возможны предупреждения и segfault)
export LC_NUMERIC=C

# Wayland: предпочитаем нативный Qt-платформенный плагин, с фолбэком на XWayland/X11
if [ -n "${WAYLAND_DISPLAY:-}" ]; then
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-wayland;xcb}"
  # Подавляем известный спам Qt Wayland text-input в консоли (не влияет на работу приложения)
  export QT_LOGGING_RULES="${QT_LOGGING_RULES:+$QT_LOGGING_RULES;}qt.qpa.wayland.textinput=false"
else
  export QT_QPA_PLATFORM="${QT_QPA_PLATFORM:-xcb}"
fi

# Предпочитаем локальное виртуальное окружение, если оно есть
PY=""
if [ -x "$SCRIPT_DIR/.venv/bin/python" ]; then
  PY="$SCRIPT_DIR/.venv/bin/python"
elif command -v python3 >/dev/null 2>&1; then
  PY=python3
elif command -v python >/dev/null 2>&1; then
  PY=python
fi

MISSING_CMDS=()
MISSING_PKGS=()
MISSING_PY_PKGS=()
CRITICAL=0

command -v pactl >/dev/null 2>&1 || { MISSING_CMDS+=("pactl"); MISSING_PKGS+=("pipewire-pulse (или libpulse)"); CRITICAL=1; }
command -v mpv >/dev/null 2>&1 || { MISSING_CMDS+=("mpv"); MISSING_PKGS+=("mpv"); CRITICAL=1; }

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
if [ "$HAS_LIBMPV" -eq 0 ] && command -v pacman >/dev/null 2>&1; then
  if pacman -Qi mpv >/dev/null 2>&1 || pacman -Qi libmpv >/dev/null 2>&1; then
    HAS_LIBMPV=1
  fi
fi
if [ "$HAS_LIBMPV" -eq 0 ]; then
  MISSING_PKGS+=("mpv/libmpv (пакет mpv)")
  CRITICAL=1
fi

if [ -z "$PY" ]; then
  echo "[soundpad][arch] Ошибка: python3/python не найден." >&2
  MISSING_PKGS+=("python")
  CRITICAL=1
else
  # Проверка Python-модулей (на Arch предпочтительны системные пакеты)
  "$PY" - <<'PY' >/dev/null 2>&1 || MISSING_PY_PKGS+=("python-pyqt6 (PyQt6)")
import PyQt6  # noqa
PY
  "$PY" - <<'PY' >/dev/null 2>&1 || MISSING_PY_PKGS+=("python-requests (requests)")
import requests  # noqa
PY
  "$PY" - <<'PY' >/dev/null 2>&1 || MISSING_PY_PKGS+=("python-beautifulsoup4 (bs4)")
import bs4  # noqa
PY
  "$PY" - <<'PY' >/dev/null 2>&1 || MISSING_PY_PKGS+=("python-mpv (mpv)")
import mpv  # noqa
PY
fi

if [ ${#MISSING_PY_PKGS[@]} -ne 0 ]; then
  CRITICAL=1
fi

# Проверка PipeWire/PulseAudio-сеанса (предупреждение, не критично для импорта)
if command -v pactl >/dev/null 2>&1; then
  if ! pactl info >/dev/null 2>&1; then
    echo "[soundpad][arch] ВНИМАНИЕ: pactl найден, но аудиосервер недоступен. Для маршрутизации нужен запущенный pipewire-pulse/PulseAudio в пользовательской сессии."
  fi
fi

if [ $CRITICAL -ne 0 ]; then
  echo "[soundpad][arch] Ошибка: отсутствуют зависимости, необходимые для запуска." >&2
  for c in "${MISSING_CMDS[@]:-}"; do [ -n "$c" ] && echo "  - команда: $c" >&2; done
  for p in "${MISSING_PKGS[@]:-}"; do [ -n "$p" ] && echo "  - пакет/компонент: $p" >&2; done
  for p in "${MISSING_PY_PKGS[@]:-}"; do [ -n "$p" ] && echo "  - python-модуль: $p" >&2; done

  echo "" >&2
  echo "[soundpad][arch] Рекомендуемая установка (Arch Linux, системные пакеты):" >&2
  echo "  sudo pacman -S --needed mpv pipewire-pulse python python-pyqt6 python-requests python-beautifulsoup4 python-mpv qt6-wayland" >&2

  if [ ${#MISSING_PY_PKGS[@]} -ne 0 ] && [ -n "$PY" ]; then
    # На Arch системный Python обычно externally-managed (PEP 668), pip --user может быть запрещён.
    EXTERNALLY_MANAGED=0
    STDLIB_PATH="$($PY - <<'PY' 2>/dev/null || true
import sysconfig
print(sysconfig.get_path('stdlib') or '')
PY
)"
    if [ -n "$STDLIB_PATH" ] && [ -f "$STDLIB_PATH/EXTERNALLY-MANAGED" ]; then
      EXTERNALLY_MANAGED=1
    fi

    echo "" >&2
    echo "[soundpad][arch] Альтернатива для Python-зависимостей (без изменения системного Python):" >&2
    echo "  $PY -m venv .venv" >&2
    echo "  source .venv/bin/activate" >&2
    echo "  pip install -r requirements.txt" >&2
    echo "  ./.venv/bin/python main.py" >&2
    echo "  (после создания .venv этот скрипт автоматически будет использовать ./.venv/bin/python)" >&2

    if [ "$EXTERNALLY_MANAGED" -eq 0 ]; then
      echo "" >&2
      echo "[soundpad][arch] Если окружение не управляется пакетным менеджером, можно попробовать:" >&2
      echo "  $PY -m pip install --user -r requirements.txt" >&2
    fi
  fi

  echo "" >&2
  echo "[soundpad][arch] Запуск отменён: установите недостающие зависимости и повторите попытку." >&2
  exit 1
fi

echo "[soundpad][arch] Запуск приложения (QT_QPA_PLATFORM=${QT_QPA_PLATFORM}, python=$PY)..."
exec "$PY" main.py
