from typing import Any, Dict

# Base structure for each theme:
# name, bg, panel, text, muted, border, accent, accent2, hover, sel_bg, sel_fg, danger, tab_inactive
# Optional (with defaults): font_family, font_size, radius, border_w, border_style, padding, tab_padding,
# qss_extra, labels{...} for UI text/symbols.

DEFAULT_LABELS: Dict[str, str] = {
    "window_title": "Soundpad — проэкт_soud",
    "settings": "[Настройки]",
    "stop": "[STOP]",
    "search_placeholder": "Поиск на MyInstants...",
    "search_btn": "[Поиск]",
    "trending_btn": "[Тренды]",
    "add_group": "[ + Группа ]",
    "load_more": "[ Загрузить ещё ]",
    "loading_more": "[ Загрузка... ]",
    "favorites_tab": "[ Избранное ]",
    "myinstants_tab": "[ MyInstants ]",
    "tab_l": "[ ",
    "tab_r": " ]",
    "fav_on": "[*]",
    "fav_off": "[ ]",
    "status_prefix": "STATUS: ",
    "no_sounds": "Нет звуков",
    "no_devices": "(нет устройств)",
    "mode_both": "Virtual Mic + Наушники (SoundpadAppSink)",
    "mode_headphones": "Только в наушники",
}

THEMES: Dict[str, Dict[str, Any]] = {
    # --- Existing themes ---
    "dark": {
        "name": "Тёмная",
        "bg": "#0d0d0d",
        "panel": "#141414",
        "text": "#d0d0d0",
        "muted": "#666666",
        "border": "#333333",
        "accent": "#00ff66",
        "accent2": "#ffb000",
        "hover": "#1e1e1e",
        "sel_bg": "#1f1f1f",
        "sel_fg": "#00ff66",
        "danger": "#ff5555",
        "tab_inactive": "#888888",
    },
    "light": {
        "name": "Светлая",
        "bg": "#f2f2f2",
        "panel": "#ffffff",
        "text": "#1a1a1a",
        "muted": "#777777",
        "border": "#bdbdbd",
        "accent": "#007a3d",
        "accent2": "#b36b00",
        "hover": "#e6e6e6",
        "sel_bg": "#d9f2e4",
        "sel_fg": "#005f2f",
        "danger": "#c62828",
        "tab_inactive": "#666666",
    },
    "purple": {
        "name": "Пурпурно-тёмная",
        "bg": "#120b18",
        "panel": "#1b1024",
        "text": "#e9ddf5",
        "muted": "#8a7699",
        "border": "#3a2948",
        "accent": "#d16bff",
        "accent2": "#ff79c6",
        "hover": "#261733",
        "sel_bg": "#352045",
        "sel_fg": "#f0b3ff",
        "danger": "#ff5c8a",
        "tab_inactive": "#9b86aa",
    },
    "pink": {
        "name": "Пикми",
        "bg": "#fff0f6",
        "panel": "#ffe3ef",
        "text": "#4a2040",
        "muted": "#9b6b86",
        "border": "#f3a6c8",
        "accent": "#ff4fa3",
        "accent2": "#ff85c2",
        "hover": "#ffd6e8",
        "sel_bg": "#ffc2de",
        "sel_fg": "#a6005c",
        "danger": "#e5397a",
        "tab_inactive": "#a05a7a",
    },
    "obs": {
        "name": "OBS",
        "bg": "#1e1f22",
        "panel": "#2b2e38",
        "text": "#dcdcdc",
        "muted": "#8b8f98",
        "border": "#3a3f4b",
        "accent": "#4da3ff",
        "accent2": "#6cb6ff",
        "hover": "#353945",
        "sel_bg": "#3a4252",
        "sel_fg": "#ffffff",
        "danger": "#e06c75",
        "tab_inactive": "#9aa0aa",
    },
    # --- Классика терминалов и гик-культуры ---
    "matrix": {
        "name": "Матрица",
        "bg": "#050805",
        "panel": "#0c140c",
        "text": "#00ff41",
        "muted": "#0f7a26",
        "border": "#143d14",
        "accent": "#00ff41",
        "accent2": "#66ff8c",
        "hover": "#142914",
        "sel_bg": "#143d14",
        "sel_fg": "#b6ffd0",
        "danger": "#39ff14",
        "tab_inactive": "#2fbf55",
    },
    "amber": {
        "name": "Янтарный монитор",
        "bg": "#0f0a00",
        "panel": "#1c1400",
        "text": "#ffb000",
        "muted": "#b37b00",
        "border": "#4d3600",
        "accent": "#ffd000",
        "accent2": "#ffb000",
        "hover": "#2e2100",
        "sel_bg": "#4d3600",
        "sel_fg": "#fff0a6",
        "danger": "#ff6a00",
        "tab_inactive": "#cc8c00",
    },
    "gruvbox": {
        "name": "Ламповый ретро",
        "bg": "#1d2021",
        "panel": "#282828",
        "text": "#ebdbb2",
        "muted": "#a89984",
        "border": "#504945",
        "accent": "#fe8019",
        "accent2": "#fabd2f",
        "hover": "#3c3836",
        "sel_bg": "#504945",
        "sel_fg": "#fbf1c7",
        "danger": "#fb4934",
        "tab_inactive": "#bdae93",
    },
    "nord": {
        "name": "Скандинавский лёд",
        "bg": "#242933",
        "panel": "#2e3440",
        "text": "#eceff4",
        "muted": "#a3abb8",
        "border": "#434c5e",
        "accent": "#88c0d0",
        "accent2": "#8fbcbb",
        "hover": "#3b4252",
        "sel_bg": "#434c5e",
        "sel_fg": "#eceff4",
        "danger": "#bf616a",
        "tab_inactive": "#d8dee9",
    },
    "cyberpunk": {
        "name": "Киберпанк",
        "bg": "#090a14",
        "panel": "#121426",
        "text": "#d1f7ff",
        "muted": "#7aa7b0",
        "border": "#ff2a6d",
        "accent": "#05d9e8",
        "accent2": "#ff2a6d",
        "hover": "#1d203d",
        "sel_bg": "#ff2a6d",
        "sel_fg": "#090a14",
        "danger": "#ff2a6d",
        "tab_inactive": "#8be9fd",
    },
    "pipboy": {
        "name": "Пустошь / Fallout",
        "bg": "#081208",
        "panel": "#0f240f",
        "text": "#1aff80",
        "muted": "#12a653",
        "border": "#1f4d1f",
        "accent": "#66ffaa",
        "accent2": "#1aff80",
        "hover": "#173817",
        "sel_bg": "#1f4d1f",
        "sel_fg": "#d6ffe9",
        "danger": "#66ffaa",
        "tab_inactive": "#2edb7a",
    },
    "mint": {
        "name": "Родной Mint",
        "bg": "#1a1a1a",
        "panel": "#252525",
        "text": "#eeeeee",
        "muted": "#9e9e9e",
        "border": "#3c3c3c",
        "accent": "#87cf3e",
        "accent2": "#a8e063",
        "hover": "#333333",
        "sel_bg": "#3c3c3c",
        "sel_fg": "#ffffff",
        "danger": "#e06c75",
        "tab_inactive": "#bdbdbd",
    },
    # --- Мемные и игровые ---
    "bsod": {
        "name": "Синий экран смерти",
        "bg": "#0000aa",
        "panel": "#000088",
        "text": "#ffffff",
        "muted": "#d0d0ff",
        "border": "#ffffff",
        "accent": "#ffff55",
        "accent2": "#ffffff",
        "hover": "#0000cc",
        "sel_bg": "#ffffff",
        "sel_fg": "#0000aa",
        "danger": "#ffff55",
        "tab_inactive": "#e0e0ff",
        "font_family": '"Lucida Console", "Consolas", "Courier New", monospace',
        "labels": {
            "window_title": ":(  Soundpad — произошла ошибка настроения",
            "settings": "[F8=ПАРАМЕТРЫ]",
            "stop": "[СТОП 0x00000000]",
            "status_prefix": "STOP_CODE: ",
            "myinstants_tab": "[ ДАМП_ЗВУКОВ ]",
            "favorites_tab": "[ ИЗБРАННЫЙ_ДАМП ]",
            "no_sounds": "Сбор информации о звуках... 0%",
        },
    },
    "brainrot": {
        "name": "СДВГ-режим",
        "bg": "#000000",
        "panel": "#141414",
        "text": "#ffffff",
        "muted": "#bdbdbd",
        "border": "#ffe600",
        "accent": "#ff003c",
        "accent2": "#ffe600",
        "hover": "#262600",
        "sel_bg": "#ffe600",
        "sel_fg": "#000000",
        "danger": "#ff003c",
        "tab_inactive": "#ffe600",
        "radius": "0px",
        "border_w": "3px",
        "labels": {
            "window_title": "SOUNDPAD ULTRA MEGA SIGMA 🔥",
            "settings": "[ НАСТРОЙКИ!! ]",
            "stop": "[ СТОП БЫСТРО ]",
            "search_placeholder": "ИЩИ ЗВУК СЕЙЧАС!!!",
            "search_btn": "[ ЖМИ ]",
            "trending_btn": "[ ВИРУСНОЕ ]",
            "add_group": "[ + ЕЩЁ ПАПКА ]",
            "load_more": "[ ЕЩЁ ЕЩЁ ЕЩЁ ]",
            "loading_more": "[ ГРУЗИМ... ]",
            "status_prefix": "МОЗГ: ",
            "fav_on": "[!!!]",
            "fav_off": "[  ]",
        },
    },
    # --- Новые абсурдные («бредовые») темы ---
    "1c": {
        "name": "1С: Бухгалтерия 7.7",
        "bg": "#ffffcc",
        "panel": "#f2e8a0",
        "text": "#000000",
        "muted": "#4d4d00",
        "border": "#808000",
        "accent": "#cc0000",
        "accent2": "#000080",
        "hover": "#e6d673",
        "sel_bg": "#808000",
        "sel_fg": "#ffffff",
        "danger": "#cc0000",
        "tab_inactive": "#333300",
        "font_family": '"MS Sans Serif", "Tahoma", "Arial", sans-serif',
        "font_size": "12px",
        "radius": "0px",
        "labels": {
            "window_title": "1С:Предприятие — Саундпад (Конфигурация)",
            "settings": "Сервис",
            "stop": "Остановить",
            "search_placeholder": "Введите наименование звука...",
            "search_btn": "Найти",
            "trending_btn": "Журнал",
            "add_group": "Добавить группу",
            "load_more": "Показать ещё",
            "loading_more": "Обработка...",
            "myinstants_tab": "Справочник",
            "favorites_tab": "Избранное",
            "tab_l": "",
            "tab_r": "",
            "fav_on": "[V]",
            "fav_off": "[ ]",
            "status_prefix": "Состояние: ",
            "no_sounds": "Элементы не найдены",
        },
    },
    "watermelon": {
        "name": "Радиоактивный Арбуз",
        "bg": "#112b15",
        "panel": "#ff2e63",
        "text": "#050505",
        "muted": "#2b0a14",
        "border": "#39ff14",
        "accent": "#39ff14",
        "accent2": "#112b15",
        "hover": "#ff527e",
        "sel_bg": "#112b15",
        "sel_fg": "#39ff14",
        "danger": "#050505",
        "tab_inactive": "#1f3d24",
        "radius": "14px",
        "border_w": "3px",
        "labels": {
            "window_title": "АРБУЗНЫЙ ПУЛЬТ ЯДЕРНОГО САУНДА",
            "settings": "[ СЕМЕЧКИ ]",
            "stop": "[ ЗАТКНУТЬ ]",
            "search_placeholder": "какой арбуз ищем...",
            "search_btn": "[ РЕЗАТЬ ]",
            "trending_btn": "[ СОЧНОЕ ]",
            "add_group": "[ + ДОЛЬКА ]",
            "fav_on": "[●]",
            "fav_off": "[○]",
            "status_prefix": "СОК: ",
            "no_sounds": "Арбузы не завезли",
        },
    },
    "gpu": {
        "name": "Сломанная видеокарта",
        "bg": "#120012",
        "panel": "#ff00ff",
        "text": "#000000",
        "muted": "#2b002b",
        "border": "#ffff00",
        "accent": "#00ffff",
        "accent2": "#ffff00",
        "hover": "#00ffff",
        "sel_bg": "#ffff00",
        "sel_fg": "#000000",
        "danger": "#ffff00",
        "tab_inactive": "#00ffff",
        "font_family": '"Impact", "Arial Black", sans-serif',
        "border_w": "4px",
        "labels": {
            "window_title": "S̷O̷U̷N̷D̷P̷A̷D̷ (АРТЕФАКТЫ)",
            "settings": "[ ГЛЮКИ ]",
            "stop": "[ АВАРИЙНЫЙ СТОП ]",
            "status_prefix": "VRAM: ",
            "search_placeholder": "поиск в битых секторах...",
            "fav_on": "[#]",
            "fav_off": "[.]",
            "no_sounds": "ТЕКСТУРЫ ЗВУКОВ НЕ ЗАГРУЗИЛИСЬ",
        },
    },
    # --- Новые «шизовые» темы (меняют всё) ---
    "vaporwave": {
        "name": "V A P O R W A V E  9 5",
        "bg": "#1a0033",
        "panel": "#2b0057",
        "text": "#ffe6ff",
        "muted": "#d19ad1",
        "border": "#00fff7",
        "accent": "#ff71ce",
        "accent2": "#01cdfe",
        "hover": "#3d007a",
        "sel_bg": "#ff71ce",
        "sel_fg": "#1a0033",
        "danger": "#fffb96",
        "tab_inactive": "#b967ff",
        "font_family": '"Comic Sans MS", "Trebuchet MS", "Verdana", sans-serif',
        "font_size": "13px",
        "radius": "12px",
        "border_w": "2px",
        "labels": {
            "window_title": "【﻿ＳＯＵＮＤＰＡＤ　ＡＥＳＴＨＥＴＩＣ】",
            "settings": "【設定】",
            "stop": "【ＳＴＯＰ】",
            "search_placeholder": "ｓｅａｒｃｈ　ｔｈｅ　ｖｏｉｄ．．．",
            "search_btn": "【探す】",
            "trending_btn": "【流行】",
            "add_group": "【＋フォルダ】",
            "load_more": "【もっと】",
            "loading_more": "【ｌｏａｄｉｎｇ．．．】",
            "myinstants_tab": "【ウェーブ】",
            "favorites_tab": "【好き】",
            "tab_l": "【",
            "tab_r": "】",
            "fav_on": "♡",
            "fav_off": "·",
            "status_prefix": "ＡＥＳＴＨ：",
            "no_sounds": "ｎｏ　ｓｉｇｎａｌ",
        },
        "qss_extra": """
        QMainWindow, QWidget, QDialog {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #1a0033, stop:0.5 #2b0057, stop:1 #00334d);
        }
        QPushButton { font-weight: bold; }
        QLabel#statusLabel {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #ff71ce, stop:1 #01cdfe);
            color: #1a0033;
        }
        """,
    },
    "uwu": {
        "name": "UwU SOFT MODE",
        "bg": "#fff5fb",
        "panel": "#ffe9f6",
        "text": "#5c2a4a",
        "muted": "#b07aa0",
        "border": "#ff9ecb",
        "accent": "#ff5fa2",
        "accent2": "#7aa2ff",
        "hover": "#ffd6ec",
        "sel_bg": "#ffb3d9",
        "sel_fg": "#4a1033",
        "danger": "#ff6b81",
        "tab_inactive": "#c989b0",
        "font_family": '"Comic Sans MS", "Segoe UI", "Verdana", sans-serif',
        "font_size": "13px",
        "radius": "16px",
        "border_w": "2px",
        "labels": {
            "window_title": "sounyadpad uwu~ ✨",
            "settings": "(✿◠‿◠) настройки",
            "stop": "(ﾉ｀□´)ﾉ стоп!!",
            "search_placeholder": "ищи звукички~",
            "search_btn": "(˘▽˘) поиск",
            "trending_btn": "(★ω★) топ",
            "add_group": "(＋ω＋) папочка",
            "load_more": "(｡•̀ᴗ-)✧ ещё~",
            "loading_more": "(。-ω-) грузим...",
            "myinstants_tab": "✨ звуки",
            "favorites_tab": "💖 любимое",
            "tab_l": "~ ",
            "tab_r": " ~",
            "fav_on": "♥",
            "fav_off": "♡",
            "status_prefix": "uwu: ",
            "no_sounds": "ничего нет qwq",
            "mode_both": "в ушки и в микрофончик~",
            "mode_headphones": "только в ушки~",
        },
        "qss_extra": """
        QPushButton { border-radius: 14px; }
        QLineEdit, QComboBox { border-radius: 12px; }
        QLabel#statusLabel { border-radius: 12px; font-weight: bold; }
        """,
    },
    "newspaper": {
        "name": "ГАЗЕТА «ЗВУКОВОЙ ВЕСТНИК»",
        "bg": "#f4ecd8",
        "panel": "#efe2c4",
        "text": "#1a1a1a",
        "muted": "#4a4a4a",
        "border": "#1a1a1a",
        "accent": "#000000",
        "accent2": "#6b0000",
        "hover": "#e6d6b3",
        "sel_bg": "#1a1a1a",
        "sel_fg": "#f4ecd8",
        "danger": "#8b0000",
        "tab_inactive": "#333333",
        "font_family": '"Times New Roman", "Georgia", "DejaVu Serif", serif',
        "font_size": "13px",
        "radius": "0px",
        "border_w": "2px",
        "labels": {
            "window_title": "ЗВУКОВОЙ ВЕСТНИК — ЭКСТРЕННЫЙ ВЫПУСК",
            "settings": "РЕДАКЦИЯ",
            "stop": "СТОП-ПЕЧАТЬ",
            "search_placeholder": "РАЗЫСКИВАЕТСЯ ЗВУК...",
            "search_btn": "НАЙТИ",
            "trending_btn": "СЕНСАЦИИ",
            "add_group": "+ РУБРИКА",
            "load_more": "ЕЩЁ МАТЕРИАЛЫ",
            "loading_more": "ПЕЧАТАЕМ...",
            "myinstants_tab": "ЛЕНТА",
            "favorites_tab": "ИЗБРАННОЕ",
            "tab_l": "« ",
            "tab_r": " »",
            "fav_on": "[★]",
            "fav_off": "[☆]",
            "status_prefix": "СРОЧНО: ",
            "no_sounds": "ТИРАЖ ПУСТ",
            "mode_both": "В ЭФИР И В НАУШНИКИ",
            "mode_headphones": "ТОЛЬКО В НАУШНИКИ",
        },
        "qss_extra": """
        QLabel#statusLabel { font-weight: bold; text-transform: uppercase; border: 3px double #1a1a1a; }
        QPushButton { font-weight: bold; text-transform: uppercase; }
        QGroupBox::title { font-weight: bold; text-transform: uppercase; }
        """,
    },
    "toxic_gamer": {
        "name": "ТОКСИК ГЕЙМЕР RGB",
        "bg": "#05060a",
        "panel": "#0f111a",
        "text": "#e6f7ff",
        "muted": "#7f8aa3",
        "border": "#00ff88",
        "accent": "#00ff88",
        "accent2": "#ff0066",
        "hover": "#151826",
        "sel_bg": "#00ff88",
        "sel_fg": "#05060a",
        "danger": "#ff0033",
        "tab_inactive": "#00bcd4",
        "font_family": '"Orbitron", "Russo One", "Arial Black", sans-serif',
        "font_size": "12px",
        "radius": "6px",
        "border_w": "2px",
        "labels": {
            "window_title": "SOUNDPAD // EZ MODE ACTIVATED",
            "settings": "[ CONFIG ]",
            "stop": "[ ALT+F4 SOUND ]",
            "search_placeholder": "найти звук для камбэка...",
            "search_btn": "[ SEARCH ]",
            "trending_btn": "[ META ]",
            "add_group": "[ + SQUAD ]",
            "load_more": "[ NEXT DROP ]",
            "loading_more": "[ LOADING... ]",
            "myinstants_tab": "[ LOBBY ]",
            "favorites_tab": "[ LOADOUT ]",
            "tab_l": "< ",
            "tab_r": " >",
            "fav_on": "[+]",
            "fav_off": "[-]",
            "status_prefix": "PING: ",
            "no_sounds": "NO LOOT FOUND",
            "mode_both": "STREAM + HEADSET",
            "mode_headphones": "HEADSET ONLY",
        },
        "qss_extra": """
        QMainWindow, QWidget, QDialog {
            background: qlineargradient(x1:0, y1:0, x2:1, y2:1, stop:0 #05060a, stop:0.5 #0b1020, stop:1 #120016);
        }
        QPushButton:hover { border: 2px solid #ff0066; }
        QLabel#statusLabel {
            border: 2px solid #ff0066;
            background: qlineargradient(x1:0, y1:0, x2:1, y2:0, stop:0 #001a12, stop:1 #1a0010);
        }
        """,
    },
    "overload": {
        "name": "ПЕРЕГРУЗКА 3000",
        "bg": "#fff700",
        "panel": "#ff8a00",
        "text": "#001aff",
        "muted": "#3d00b8",
        "border": "#ff0055",
        "accent": "#001aff",
        "accent2": "#ff0055",
        "hover": "#ffd000",
        "sel_bg": "#001aff",
        "sel_fg": "#fff700",
        "danger": "#ff0055",
        "tab_inactive": "#5a00ff",
        "font_family": '"Comic Sans MS", "Impact", "Arial Black", sans-serif',
        "font_size": "14px",
        "radius": "18px",
        "border_w": "4px",
        "labels": {
            "window_title": "!!! САУНДПАД ПЕРЕГРЕЛСЯ !!!",
            "settings": "!!! КНОПКИ !!!",
            "stop": "!!! ХВАТИТ !!!",
            "search_placeholder": "ВВЕДИ ЧТО-НИБУДЬ СРОЧНО",
            "search_btn": "!!! ПОИСК !!!",
            "trending_btn": "!!! ОГОНЬ !!!",
            "add_group": "!!! НОВАЯ КУЧА !!!",
            "load_more": "!!! ДАВАЙ ЕЩЁ !!!",
            "loading_more": "!!! КРУТИТСЯ !!!",
            "myinstants_tab": "!!! ВСЁ !!!",
            "favorites_tab": "!!! ТОП !!!",
            "tab_l": "!!! ",
            "tab_r": " !!!",
            "fav_on": "★",
            "fav_off": "☆",
            "status_prefix": "ПАНИКА: ",
            "no_sounds": "ПУСТО КРИЧИМ",
        },
        "qss_extra": """
        QPushButton { font-weight: 900; }
        QLabel#statusLabel { font-weight: 900; border-style: dashed; }
        QLineEdit { font-weight: bold; }
        """,
    },
}

THEME_ORDER = [
    "dark", "light", "purple", "pink", "obs",
    "matrix", "amber", "gruvbox", "nord", "cyberpunk", "pipboy", "mint",
    "bsod", "brainrot", "1c", "watermelon", "gpu",
    "vaporwave", "uwu", "newspaper", "toxic_gamer", "overload",
]


def get_theme(key: str) -> Dict[str, Any]:
    return THEMES.get(key, THEMES["dark"])


def get_theme_labels(key: str) -> Dict[str, str]:
    t = get_theme(key)
    labels = dict(DEFAULT_LABELS)
    labels.update(t.get("labels", {}) or {})
    return labels


def theme_label(key: str, name: str, default: str = "") -> str:
    labels = get_theme_labels(key)
    if name in labels:
        return labels[name]
    if default:
        return default
    return DEFAULT_LABELS.get(name, "")


def format_tab_label(theme_key: str, name: str) -> str:
    labels = get_theme_labels(theme_key)
    return f"{labels.get('tab_l', '[ ')}{name}{labels.get('tab_r', ' ]')}"


def format_status(theme_key: str, message: str) -> str:
    labels = get_theme_labels(theme_key)
    prefix = labels.get("status_prefix", DEFAULT_LABELS["status_prefix"])
    if not message:
        return prefix.rstrip()
    if message.startswith(prefix):
        return message
    return f"{prefix}{message}"


def build_qss(theme_key: str) -> str:
    t = get_theme(theme_key)
    labels = get_theme_labels(theme_key)
    _ = labels  # reserved for future QSS-text hooks

    font_family = t.get("font_family", '"JetBrains Mono", "Fira Code", "DejaVu Sans Mono", monospace')
    font_size = t.get("font_size", "12px")
    radius = t.get("radius", "0px")
    border_w = t.get("border_w", "1px")
    border_style = t.get("border_style", "solid")
    padding = t.get("padding", "4px")
    tab_padding = t.get("tab_padding", "6px 10px")
    extra = t.get("qss_extra", "") or ""

    border = f"{border_w} {border_style} {t['border']}"

    return f"""
        * {{
            border-radius: {radius};
        }}
        QMainWindow, QWidget, QDialog {{
            background-color: {t['bg']};
            color: {t['text']};
            font-family: {font_family};
            font-size: {font_size};
        }}
        QLineEdit, QComboBox, QTabWidget::pane, QScrollArea, QGroupBox, QProgressBar {{
            background-color: {t['panel']};
            color: {t['text']};
            border: {border};
            border-radius: {radius};
            padding: {padding};
            selection-background-color: {t['sel_bg']};
            selection-color: {t['sel_fg']};
        }}
        QLineEdit:hover, QComboBox:hover {{
            background-color: {t['hover']};
            color: {t['text']};
        }}
        QGroupBox {{ margin-top: 8px; padding-top: 10px; }}
        QGroupBox::title {{ subcontrol-origin: margin; left: 8px; padding: 0 4px; color: {t['accent']}; }}
        QComboBox::drop-down {{ border: 0px; width: 18px; background: {t['panel']}; }}
        QComboBox::drop-down:hover {{ background: {t['hover']}; }}
        QComboBox QAbstractItemView {{
            background-color: {t['panel']};
            color: {t['text']};
            border: {border};
            outline: none;
            selection-background-color: {t['sel_bg']};
            selection-color: {t['sel_fg']};
        }}
        QComboBox QAbstractItemView::item {{
            padding: {padding};
            color: {t['text']};
            background-color: {t['panel']};
        }}
        QComboBox QAbstractItemView::item:hover {{
            background-color: {t['hover']};
            color: {t['text']};
        }}
        QComboBox QAbstractItemView::item:selected {{
            background-color: {t['sel_bg']};
            color: {t['sel_fg']};
        }}
        QPushButton {{
            background-color: {t['panel']};
            color: {t['accent']};
            border: {border};
            border-radius: {radius};
            padding: {padding} 8px;
        }}
        QPushButton:hover {{ background-color: {t['hover']}; color: {t['accent']}; }}
        QPushButton:pressed {{ background-color: {t['bg']}; color: {t['accent']}; }}
        QPushButton#soundButton {{ color: {t['text']}; text-align: left; }}
        QPushButton#soundButton:hover {{ background-color: {t['hover']}; color: {t['text']}; }}
        QPushButton#favButton {{ color: {t['accent2']}; }}
        QPushButton#favButton:hover {{ background-color: {t['hover']}; color: {t['accent2']}; }}
        QPushButton#stopButton {{ color: {t['danger']}; font-weight: bold; }}
        QPushButton#stopButton:hover {{ background-color: {t['hover']}; color: {t['danger']}; }}
        QLabel#statusLabel {{ color: {t['accent']}; border: {border}; padding: {padding}; background: {t['panel']}; }}
        QLabel#muted {{ color: {t['muted']}; }}
        QLabel#sectionTitle {{ color: {t['accent']}; font-weight: bold; }}
        QTabBar::tab {{
            background: {t['panel']};
            color: {t['tab_inactive']};
            border: {border};
            border-bottom: none;
            border-radius: {radius};
            padding: {tab_padding};
            margin-right: 2px;
        }}
        QTabBar::tab:selected {{ color: {t['accent']}; background: {t['bg']}; }}
        QTabBar::tab:hover {{ color: {t['text']}; background: {t['hover']}; }}
        QScrollBar:vertical, QScrollBar:horizontal {{
            background: {t['bg']}; border: {border}; border-radius: {radius};
        }}
        QScrollBar::handle {{ background: {t['border']}; border-radius: {radius}; min-height: 20px; min-width: 20px; }}
        QScrollBar::handle:hover {{ background: {t['muted']}; }}
        QMenu {{
            background-color: {t['panel']}; color: {t['text']}; border: {border};
        }}
        QMenu::item {{ padding: 4px 16px; }}
        QMenu::item:selected {{ background-color: {t['sel_bg']}; color: {t['sel_fg']}; }}
        QStatusBar {{ border-top: {border}; }}
        QProgressBar {{ text-align: center; color: {t['text']}; }}
        QProgressBar::chunk {{ background-color: {t['accent']}; border-radius: {radius}; }}
        QToolTip {{
            background-color: {t['panel']}; color: {t['text']}; border: {border};
        }}
        {extra}
        """
