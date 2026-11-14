import array
import hashlib
import json
import locale
import math
import os
import re
import shutil
import struct
import subprocess
import sys
import tempfile
import threading
import time
import traceback
import wave
from pathlib import Path
from typing import Any, Dict, List, Optional

# libmpv requires LC_NUMERIC=C to avoid locale-related issues/crashes
os.environ.setdefault("LC_NUMERIC", "C")
try:
    locale.setlocale(locale.LC_NUMERIC, "C")
except Exception:
    try:
        locale.setlocale(locale.LC_NUMERIC, "C.UTF-8")
    except Exception:
        pass

from PyQt6.QtCore import QObject, QRunnable, Qt, QThread, QThreadPool, QTimer, pyqtSignal, pyqtSlot
from PyQt6.QtGui import QKeySequence, QShortcut, QPainter, QColor, QIcon, QPixmap, QAction
from PyQt6.QtWidgets import (
    QApplication,
    QComboBox,
    QDialog,
    QDialogButtonBox,
    QFileDialog,
    QGridLayout,
    QGroupBox,
    QHBoxLayout,
    QInputDialog,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMenu,
    QMessageBox,
    QPushButton,
    QProgressBar,
    QScrollArea,
    QSizePolicy,
    QSlider,
    QStatusBar,
    QSystemTrayIcon,
    QTabWidget,
    QVBoxLayout,
    QWidget,
)

try:
    import mpv
except Exception:  # pragma: no cover
    mpv = None  # type: ignore

from audio_router import APP_SINK_NAME, VIRT_MIC_NAME, AudioRouter, AudioRouterError
from scraper import MyInstantsScraper
from themes import THEMES, THEME_ORDER, build_qss, format_status, format_tab_label, get_theme_labels

APP_DIR = Path(__file__).resolve().parent
CACHE_DIR = APP_DIR / "cache"
CONFIG_PATH = APP_DIR / "config.json"
DATA_PATH = APP_DIR / "data.json"
DOWNLOADS_DIR = APP_DIR / "sounds" / "downloads"
DOWNLOADS_GROUP_NAME = "Загрузки"
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".opus", ".wma", ".aiff", ".aif"}


# ---------------------- persistence ----------------------
def load_json(path: Path, default: Any) -> Any:
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print(f"[storage] load error {path}: {e}")
    return default


def save_json(path: Path, data: Any):
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        tmp = path.with_suffix(path.suffix + ".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        tmp.replace(path)
    except Exception as e:
        print(f"[storage] save error {path}: {e}")


# ---------------------- themes ----------------------
# Theme palettes and QSS generator are defined in themes.py



# ---------------------- audio test utils ----------------------
def generate_test_tone(path: str, duration: float = 1.2, freq: float = 440.0, rate: int = 44100):
    n_samples = int(duration * rate)
    amplitude = 0.35
    with wave.open(path, "w") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        frames = bytearray()
        for i in range(n_samples):
            # simple fade in/out to avoid clicks
            env = 1.0
            if i < 400:
                env = i / 400.0
            elif i > n_samples - 400:
                env = max(0.0, (n_samples - i) / 400.0)
            val = int(amplitude * env * 32767 * math.sin(2 * math.pi * freq * (i / rate)))
            frames += struct.pack('<h', val)
        wf.writeframes(frames)


class LevelMonitorThread(QThread):
    level = pyqtSignal(float)  # 0..1

    def __init__(self, source_name: Optional[str], parent=None):
        super().__init__(parent)
        self.source_name = source_name
        self._stop = threading.Event()

    def stop(self):
        self._stop.set()

    def run(self):
        if not self.source_name:
            return
        parec = shutil.which("parec")
        if not parec:
            return
        cmd = [
            parec,
            "--device", self.source_name,
            "--format=s16le",
            "--rate=44100",
            "--channels=1",
            "--latency-msec=50",
        ]
        proc = None
        try:
            proc = subprocess.Popen(cmd, stdout=subprocess.PIPE, stderr=subprocess.DEVNULL)
            chunk_size = 2048  # bytes
            while not self._stop.is_set():
                if not proc.stdout:
                    break
                data = proc.stdout.read(chunk_size)
                if not data:
                    break
                if len(data) < 2:
                    continue
                samples = array.array('h')
                try:
                    samples.frombytes(data[: (len(data) // 2) * 2])
                except Exception:
                    continue
                if not samples:
                    continue
                # RMS -> 0..1
                ssum = 0.0
                for s in samples:
                    ssum += float(s) * float(s)
                rms = math.sqrt(ssum / max(1, len(samples))) / 32768.0
                level = max(0.0, min(1.0, rms * 3.0))
                self.level.emit(level)
        except Exception:
            pass
        finally:
            try:
                if proc:
                    proc.terminate()
                    proc.wait(timeout=1)
            except Exception:
                try:
                    if proc:
                        proc.kill()
                except Exception:
                    pass


# ---------------------- worker helpers ----------------------
class WorkerSignals(QObject):
    finished = pyqtSignal(object)
    error = pyqtSignal(str)


class Task(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = WorkerSignals()

    @pyqtSlot()
    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
            self.signals.finished.emit(res)
        except Exception as e:
            tb = traceback.format_exc()
            self.signals.error.emit(f"{e}\n{tb}")


# ---------------------- sound grid ----------------------
class SoundButtonWidget(QWidget):
    def __init__(self, sound: Dict[str, Any], is_favorite: bool, on_play, on_toggle_fav, on_context,
                 fav_on: str = "[*]", fav_off: str = "[ ]", marker_text: Optional[str] = None, parent=None):
        super().__init__(parent)
        self.sound = sound
        self.on_play = on_play
        self.on_toggle_fav = on_toggle_fav
        self.on_context = on_context

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(2)

        self.play_btn = QPushButton(sound.get("name", "sound"))
        self.play_btn.setObjectName("soundButton")
        self.play_btn.setCursor(Qt.CursorShape.PointingHandCursor)
        self.play_btn.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)
        self.play_btn.clicked.connect(lambda: self.on_play(self.sound))
        self.play_btn.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.play_btn.customContextMenuRequested.connect(self._ctx)

        marker = marker_text if marker_text is not None else (fav_on if is_favorite else fav_off)
        self.fav_btn = QPushButton(marker)
        self.fav_btn.setObjectName("favButton")
        self.fav_btn.setFixedWidth(36)
        self.fav_btn.setToolTip("Избранное / статус")
        self.fav_btn.clicked.connect(lambda: self.on_toggle_fav(self.sound))

        layout.addWidget(self.play_btn, 1)
        layout.addWidget(self.fav_btn, 0)

    def _ctx(self, pos):
        self.on_context(self.sound, self.play_btn.mapToGlobal(pos))

    def set_marker(self, marker_text: str):
        if self.fav_btn.text() != marker_text:
            self.fav_btn.setText(marker_text)

    def set_sound_name(self, name: str):
        if self.play_btn.text() != name:
            self.play_btn.setText(name)

    def set_sound(self, sound: Dict[str, Any]):
        self.sound = sound
        self.set_sound_name(sound.get("name", "sound"))


class SoundGrid(QWidget):
    def __init__(self, on_play, on_toggle_fav, on_context, fav_on: str = "[*]", fav_off: str = "[ ]", empty_text: str = "Нет звуков", parent=None):
        super().__init__(parent)
        self.on_play = on_play
        self.on_toggle_fav = on_toggle_fav
        self.on_context = on_context
        self.fav_on = fav_on
        self.fav_off = fav_off
        self.empty_text = empty_text
        self.playing_id: Optional[str] = None
        self.last_played_id: Optional[str] = None
        self._sounds: List[Dict[str, Any]] = []
        self._favorites: set = set()
        self._widgets_by_sid: Dict[str, SoundButtonWidget] = {}

        self.grid = QGridLayout(self)
        self.grid.setContentsMargins(6, 6, 6, 6)
        self.grid.setSpacing(6)
        self.grid.setAlignment(Qt.AlignmentFlag.AlignTop)

    def set_theme_labels(self, fav_on: str, fav_off: str, empty_text: str):
        changed = (fav_on != self.fav_on) or (fav_off != self.fav_off) or (empty_text != self.empty_text)
        self.fav_on = fav_on
        self.fav_off = fav_off
        self.empty_text = empty_text
        # if only marker labels changed and widgets exist, update in-place
        if changed and self._widgets_by_sid:
            self.refresh_markers()

    def set_playback_state(self, playing_id: Optional[str], last_played_id: Optional[str]):
        self.playing_id = playing_id
        self.last_played_id = last_played_id

    def _marker_for(self, sid: Optional[str], is_favorite: bool) -> str:
        # If favorite, favorite marker replaces status marker (as requested)
        if is_favorite:
            return self.fav_on
        if sid and self.playing_id and sid == self.playing_id:
            return "[▶]"
        if sid and self.last_played_id and sid == self.last_played_id:
            return "[■]"
        return self.fav_off

    def refresh_markers(self):
        if not self._widgets_by_sid:
            return
        for sid, w in list(self._widgets_by_sid.items()):
            try:
                is_fav = sid in self._favorites
                w.set_marker(self._marker_for(sid, is_fav))
            except Exception:
                pass

    def refresh_markers_for_ids(self, ids):
        if not self._widgets_by_sid or not ids:
            return
        for sid in ids:
            if not sid:
                continue
            w = self._widgets_by_sid.get(sid)
            if not w:
                continue
            try:
                is_fav = sid in self._favorites
                w.set_marker(self._marker_for(sid, is_fav))
            except Exception:
                pass

    def set_sounds(self, sounds: List[Dict[str, Any]], favorites: set, columns: int = 3):
        self._sounds = sounds or []
        self._favorites = favorites or set()
        while self.grid.count():
            item = self.grid.takeAt(0)
            w = item.widget()
            if w:
                w.deleteLater()
        self._widgets_by_sid = {}
        if not self._sounds:
            lbl = QLabel(self.empty_text)
            lbl.setObjectName("muted")
            self.grid.addWidget(lbl, 0, 0)
            return
        for idx, sound in enumerate(self._sounds):
            sid = sound.get("id")
            is_fav = sid in self._favorites
            w = SoundButtonWidget(
                sound,
                is_fav,
                self.on_play,
                self.on_toggle_fav,
                self.on_context,
                fav_on=self.fav_on,
                fav_off=self.fav_off,
                marker_text=self._marker_for(sid, is_fav),
            )
            if sid:
                self._widgets_by_sid[sid] = w
            r = idx // columns
            c = idx % columns
            self.grid.addWidget(w, r, c)


# ---------------------- settings dialog ----------------------
class SettingsDialog(QDialog):
    def __init__(self, main_window: "MainWindow", parent=None):
        super().__init__(parent)
        self.mw = main_window
        self.setWindowTitle("Настройки")
        self.resize(760, 520)
        self.setMinimumSize(300, 250)

        self.mic_monitor: Optional[LevelMonitorThread] = None
        self.mix_monitor: Optional[LevelMonitorThread] = None
        self.output_test_monitor: Optional[LevelMonitorThread] = None

        layout = QVBoxLayout(self)
        self.tabs = QTabWidget()
        layout.addWidget(self.tabs, 1)

        self._build_devices_tab()
        self._build_theme_tab()
        self._build_test_tab()

        btns = QDialogButtonBox(QDialogButtonBox.StandardButton.Close)
        btns.rejected.connect(self.reject)
        btns.accepted.connect(self.accept)
        layout.addWidget(btns)

        self._sync_from_main()

    def _build_devices_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)

        g = QGroupBox("Аудиоустройства")
        grid = QGridLayout(g)
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(8)

        grid.addWidget(QLabel("Наушники (куда слышать звуки):"), 0, 0)
        self.headphones_combo = QComboBox()
        self.headphones_combo.currentIndexChanged.connect(self.on_headphones_changed)
        grid.addWidget(self.headphones_combo, 0, 1)

        grid.addWidget(QLabel("Микрофон (ваш голос):"), 1, 0)
        self.mic_combo = QComboBox()
        self.mic_combo.currentIndexChanged.connect(self.on_mic_changed)
        grid.addWidget(self.mic_combo, 1, 1)

        grid.addWidget(QLabel("Режим вывода приложения:"), 2, 0)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem("Virtual Mic + Наушники (SoundpadAppSink)", "both")
        self.mode_combo.addItem("Только в наушники", "headphones_only")
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        grid.addWidget(self.mode_combo, 2, 1)

        self.mic_boost_label = QLabel("Усиление звуков в микрофон: 100%")
        self.mic_boost_slider = QSlider(Qt.Orientation.Horizontal)
        self.mic_boost_slider.setRange(100, 300)
        self.mic_boost_slider.setSingleStep(5)
        self.mic_boost_slider.setPageStep(10)
        self.mic_boost_slider.setToolTip("Усиливает только звуки саундпада в виртуальном микрофоне (наушники и ваш голос не меняются)")
        self.mic_boost_slider.valueChanged.connect(self.on_mic_boost_changed)
        grid.addWidget(self.mic_boost_label, 3, 0)
        grid.addWidget(self.mic_boost_slider, 3, 1)

        refresh_btn = QPushButton("[Обновить устройства]")
        refresh_btn.clicked.connect(self.refresh_devices)
        grid.addWidget(refresh_btn, 4, 1, alignment=Qt.AlignmentFlag.AlignLeft)

        v.addWidget(g)

        dg = QGroupBox("Загрузка звуков")
        dgrid = QGridLayout(dg)
        dgrid.setHorizontalSpacing(8)
        dgrid.setVerticalSpacing(8)
        dgrid.addWidget(QLabel("Папка загрузки по умолчанию:"), 0, 0)
        self.download_dir_edit = QLineEdit()
        self.download_dir_edit.setReadOnly(True)
        dgrid.addWidget(self.download_dir_edit, 0, 1)
        self.download_dir_browse_btn = QPushButton("Выбрать папку...")
        self.download_dir_browse_btn.clicked.connect(self.choose_download_dir)
        dgrid.addWidget(self.download_dir_browse_btn, 1, 1, alignment=Qt.AlignmentFlag.AlignLeft)
        self.download_dir_warning = QLabel("")
        self.download_dir_warning.setObjectName("muted")
        self.download_dir_warning.setWordWrap(True)
        dgrid.addWidget(self.download_dir_warning, 2, 0, 1, 2)
        v.addWidget(dg)

        v.addStretch(1)
        self.devices_tab = w
        self.tabs.addTab(w, "Устройства")

    def _build_theme_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        g = QGroupBox("Тема оформления")
        gv = QVBoxLayout(g)
        gv.addWidget(QLabel("Выберите тему:"))
        self.theme_combo = QComboBox()
        for key in THEME_ORDER:
            info = THEMES.get(key, {})
            self.theme_combo.addItem(info.get("name", key), key)
        self.theme_combo.currentIndexChanged.connect(self.on_theme_changed)
        gv.addWidget(self.theme_combo)
        hint = QLabel("Доступны классические, мемные и абсурдные терминальные темы. Выбор сохраняется автоматически.")
        hint.setObjectName("muted")
        hint.setWordWrap(True)
        gv.addWidget(hint)
        v.addWidget(g)
        v.addStretch(1)
        self.tabs.addTab(w, "Тема")

    def _build_test_tab(self):
        w = QWidget()
        v = QVBoxLayout(w)
        v.setSpacing(8)

        # Output test
        out_g = QGroupBox("Тест звука / динамиков")
        out_l = QVBoxLayout(out_g)
        row = QHBoxLayout()
        self.test_sound_btn = QPushButton("[Тест звука]")
        self.test_sound_btn.clicked.connect(self.play_test_sound)
        self.stop_test_btn = QPushButton("[Стоп тест]")
        self.stop_test_btn.clicked.connect(self.stop_tests)
        row.addWidget(self.test_sound_btn)
        row.addWidget(self.stop_test_btn)
        row.addStretch(1)
        out_l.addLayout(row)
        out_l.addWidget(QLabel("Активность вывода (SoundpadAppSink monitor):"))
        self.out_level = QProgressBar()
        self.out_level.setRange(0, 100)
        self.out_level.setValue(0)
        out_l.addWidget(self.out_level)
        out_hint = QLabel("Тест воспроизводится через саундпад (SoundpadAppSink), чтобы проверить наушники и маршрутизацию.")
        out_hint.setObjectName("muted")
        out_hint.setWordWrap(True)
        out_l.addWidget(out_hint)
        v.addWidget(out_g)

        # Mic test
        mic_g = QGroupBox("Калибровка микрофона")
        mic_l = QVBoxLayout(mic_g)
        mic_l.addWidget(QLabel("Уровень выбранного физического микрофона:"))
        self.mic_level = QProgressBar()
        self.mic_level.setRange(0, 100)
        self.mic_level.setValue(0)
        mic_l.addWidget(self.mic_level)
        mic_l.addWidget(QLabel("Уровень VirtualMicMix.monitor (что уходит в виртуальный микрофон):"))
        self.mix_level = QProgressBar()
        self.mix_level.setRange(0, 100)
        self.mix_level.setValue(0)
        mic_l.addWidget(self.mix_level)

        mrow = QHBoxLayout()
        self.mic_test_btn = QPushButton("[Проверить микрофон]")
        self.mic_test_btn.clicked.connect(self.toggle_mic_monitor)
        self.mic_during_btn = QPushButton("[Проверить микрофон во время звука]")
        self.mic_during_btn.clicked.connect(self.check_mic_during_sound)
        mrow.addWidget(self.mic_test_btn)
        mrow.addWidget(self.mic_during_btn)
        mrow.addStretch(1)
        mic_l.addLayout(mrow)
        mic_hint = QLabel("Говорите в микрофон и наблюдайте уровни. Во время проверки со звуком должен быть виден и голос, и активность микса.")
        mic_hint.setObjectName("muted")
        mic_hint.setWordWrap(True)
        mic_l.addWidget(mic_hint)
        v.addWidget(mic_g)

        v.addStretch(1)
        self.tabs.addTab(w, "Тест")

    # ---- sync ----
    def _sync_from_main(self):
        self.refresh_devices(select_current=True)
        self._set_combo_by_data(self.theme_combo, self.mw.config.get("theme", "dark"))
        boost = int(self.mw.config.get("mic_boost", 100) or 100)
        boost = max(100, min(300, boost))
        if hasattr(self, "mic_boost_slider"):
            self.mic_boost_slider.blockSignals(True)
            self.mic_boost_slider.setValue(boost)
            self.mic_boost_slider.blockSignals(False)
            self.mic_boost_label.setText(f"Усиление звуков в микрофон: {boost}%")
        if hasattr(self, "download_dir_edit"):
            d = self.mw.get_download_dir()
            self.download_dir_edit.setText(str(d))
            if hasattr(self, "download_dir_warning") and not self.download_dir_warning.text():
                if not d.exists() or not d.is_dir():
                    self.download_dir_warning.setText("у вас нет каталога по умолчанию")
                else:
                    self.download_dir_warning.setText("")

    def _set_combo_by_data(self, combo: QComboBox, data_value: Any):
        combo.blockSignals(True)
        idx = -1
        for i in range(combo.count()):
            if combo.itemData(i) == data_value:
                idx = i
                break
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    def refresh_devices(self, select_current: bool = False):
        sinks = self.mw.router.list_sinks()
        sources = self.mw.router.list_sources()
        cur_sink = self.mw.config.get("headphones_sink")
        cur_mic = self.mw.config.get("mic_source")
        cur_mode = self.mw.config.get("mode", "both")

        self.headphones_combo.blockSignals(True)
        self.mic_combo.blockSignals(True)
        self.mode_combo.blockSignals(True)
        self.headphones_combo.clear()
        self.mic_combo.clear()
        for s in sinks:
            self.headphones_combo.addItem(s.get("description", s["name"]), s["name"])
        for s in sources:
            self.mic_combo.addItem(s.get("description", s["name"]), s["name"])
        if self.headphones_combo.count() == 0:
            self.headphones_combo.addItem("(нет устройств вывода)", None)
        if self.mic_combo.count() == 0:
            self.mic_combo.addItem("(нет устройств ввода)", None)
        self.headphones_combo.blockSignals(False)
        self.mic_combo.blockSignals(False)
        self.mode_combo.blockSignals(False)

        if select_current:
            self._set_combo_by_data(self.headphones_combo, cur_sink)
            self._set_combo_by_data(self.mic_combo, cur_mic)
            self._set_combo_by_data(self.mode_combo, cur_mode)

        # also refresh main combos
        self.mw.refresh_device_combos(select_current=True)

    # ---- handlers ----
    def on_headphones_changed(self, _idx):
        val = self.headphones_combo.currentData()
        if not val:
            return
        self.mw.set_headphones_sink(val)

    def on_mic_changed(self, _idx):
        val = self.mic_combo.currentData()
        if not val:
            return
        self.mw.set_mic_source(val)

    def on_mode_changed(self, _idx):
        val = self.mode_combo.currentData() or "both"
        self.mw.set_output_mode(val)

    def on_theme_changed(self, _idx):
        key = self.theme_combo.currentData() or "dark"
        self.mw.apply_theme(key)

    def on_mic_boost_changed(self, value: int):
        try:
            value = int(value)
        except Exception:
            value = 100
        value = max(100, min(300, value))
        if hasattr(self, "mic_boost_label"):
            self.mic_boost_label.setText(f"Усиление звуков в микрофон: {value}%")
        try:
            self.mw.set_mic_boost(value)
        except Exception:
            pass

    def choose_download_dir(self):
        start_dir = str(self.mw.get_download_dir())
        if not os.path.isdir(start_dir):
            start_dir = str(Path.home())
        d = QFileDialog.getExistingDirectory(self, "Выберите папку загрузки", start_dir)
        if not d:
            return
        self.mw.set_download_dir(d)
        self.download_dir_edit.setText(str(self.mw.get_download_dir()))
        if self.mw.is_download_dir_valid():
            self.download_dir_warning.setText("")
        else:
            self.download_dir_warning.setText("у вас нет каталога по умолчанию")

    # ---- tests ----
    def play_test_sound(self):
        tone_path = os.path.join(tempfile.gettempdir(), "soundpad_test_tone.wav")
        try:
            generate_test_tone(tone_path)
        except Exception as e:
            QMessageBox.warning(self, "Тест", f"Не удалось создать тестовый сигнал: {e}")
            return
        if not self.mw._ensure_player():
            QMessageBox.warning(self, "Тест", "Плеер недоступен (mpv/libmpv).")
            return
        try:
            try:
                self.mw.player.stop()
            except Exception:
                pass
            self.mw.player.play(tone_path)
            self.mw.status_label.setText("STATUS: test sound playing")
            self.start_output_monitor()
        except Exception as e:
            QMessageBox.warning(self, "Тест", f"Ошибка воспроизведения: {e}")

    def start_output_monitor(self):
        self.stop_output_monitor()
        src = f"{APP_SINK_NAME}.monitor"
        self.output_test_monitor = LevelMonitorThread(src, self)
        self.output_test_monitor.level.connect(lambda v: self.out_level.setValue(int(v * 100)))
        self.output_test_monitor.start()
        # auto-stop monitor after short period
        QTimer.singleShot(2500, self.stop_output_monitor)

    def stop_output_monitor(self):
        if self.output_test_monitor:
            try:
                self.output_test_monitor.level.disconnect()
            except Exception:
                pass
            self.output_test_monitor.stop()
            self.output_test_monitor.wait(500)
            self.output_test_monitor = None
        self.out_level.setValue(0)

    def toggle_mic_monitor(self):
        if self.mic_monitor or self.mix_monitor:
            self.stop_mic_monitors()
            self.mic_test_btn.setText("[Проверить микрофон]")
            return
        self.start_mic_monitors(include_mix=True)
        self.mic_test_btn.setText("[Стоп проверку микрофона]")

    def start_mic_monitors(self, include_mix: bool = True):
        self.stop_mic_monitors()
        mic_src = self.mw.config.get("mic_source")
        if mic_src:
            self.mic_monitor = LevelMonitorThread(mic_src, self)
            self.mic_monitor.level.connect(lambda v: self.mic_level.setValue(int(v * 100)))
            self.mic_monitor.start()
        if include_mix:
            mix_src = f"{VIRT_MIC_NAME}.monitor"
            self.mix_monitor = LevelMonitorThread(mix_src, self)
            self.mix_monitor.level.connect(lambda v: self.mix_level.setValue(int(v * 100)))
            self.mix_monitor.start()

    def stop_mic_monitors(self):
        for attr in ("mic_monitor", "mix_monitor"):
            mon = getattr(self, attr)
            if mon:
                try:
                    mon.level.disconnect()
                except Exception:
                    pass
                mon.stop()
                mon.wait(500)
                setattr(self, attr, None)
        self.mic_level.setValue(0)
        self.mix_level.setValue(0)

    def check_mic_during_sound(self):
        self.start_mic_monitors(include_mix=True)
        self.play_test_sound()
        self.mic_test_btn.setText("[Стоп проверку микрофона]")

    def stop_tests(self):
        try:
            self.mw.stop_playback()
        except Exception:
            pass
        self.stop_output_monitor()
        self.stop_mic_monitors()
        self.mic_test_btn.setText("[Проверить микрофон]")

    def closeEvent(self, event):
        self.stop_tests()
        super().closeEvent(event)

    def reject(self):
        self.stop_tests()
        super().reject()

    def accept(self):
        self.stop_tests()
        super().accept()


# ---------------------- main window ----------------------
class MainWindow(QMainWindow):
    playback_ended = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.resize(1150, 720)
        self.setMinimumSize(200, 200)

        self.pool = QThreadPool.globalInstance()
        self.scraper = MyInstantsScraper(CACHE_DIR)
        self.router = AudioRouter()
        self.player: Optional[mpv.MPV] = None
        self._player_ready = False
        self.current_playing_id: Optional[str] = None
        self.last_played_id: Optional[str] = None

        self.config = load_json(CONFIG_PATH, {})
        self.data = load_json(DATA_PATH, {})
        self._ensure_data_shapes()

        self._status_raw = "idle"
        self.group_grids: Dict[str, SoundGrid] = {}
        self.group_scrolls: Dict[str, QScrollArea] = {}
        self.tray_icon = None
        self._really_quit = False

        self._setup_player()
        self._build_ui()
        self.playback_ended.connect(self._on_playback_naturally_ended)
        self.apply_theme(self.config.get("theme", "dark"), save=False)
        self._setup_shortcuts()
        self._setup_tray()
        self._init_audio()
        self._load_initial_sounds()
        self._refresh_playback_indicators()

    # ---------- data ----------
    def _ensure_data_shapes(self):
        self.data.setdefault("favorites", [])
        self.data.setdefault("groups", {})
        self.data.setdefault("sounds", {})
        self.config.setdefault("headphones_sink", None)
        self.config.setdefault("mic_source", None)
        self.config.setdefault("mode", "both")
        self.config.setdefault("theme", "dark")
        self.config.setdefault("mic_boost", 100)
        self.config.setdefault("download_dir", str(Path.home() / "Downloads"))
        if self.config.get("theme") not in THEMES:
            self.config["theme"] = "dark"

    def save_state(self):
        save_json(CONFIG_PATH, self.config)
        save_json(DATA_PATH, self.data)

    def _favorites_set(self) -> set:
        return set(self.data.get("favorites", []))

    def _remember_sound(self, sound: Dict[str, Any]) -> Dict[str, Any]:
        sid = sound.get("id")
        if not sid:
            return sound
        sounds = self.data.setdefault("sounds", {})
        existing = sounds.get(sid, {})
        merged = {**existing, **{k: v for k, v in sound.items() if v is not None}}
        sounds[sid] = merged
        return merged

    # ---------- player ----------
    def _setup_player(self):
        self.player = None
        self._player_ready = False

    def _ensure_player(self) -> bool:
        if self.player is not None and self._player_ready:
            return True
        if mpv is None:
            print("[player] python-mpv не установлен/не импортируется")
            return False
        try:
            locale.setlocale(locale.LC_NUMERIC, "C")
        except Exception:
            try:
                locale.setlocale(locale.LC_NUMERIC, "C.UTF-8")
            except Exception:
                pass

        def _init_mpv(**kwargs):
            player = mpv.MPV(**kwargs)
            try:
                @player.event_callback('end-file')
                def _on_end_file(event):
                    # called from mpv thread; emit queued signal to update UI safely
                    try:
                        self.playback_ended.emit()
                    except Exception:
                        pass
            except Exception:
                try:
                    @player.property_observer('eof-reached')
                    def _on_eof(name, value):
                        if value:
                            try:
                                self.playback_ended.emit()
                            except Exception:
                                pass
                except Exception:
                    pass
            return player

        try:
            self.player = _init_mpv(
                audio_device=f"pulse/{APP_SINK_NAME}",
                video=False,
                terminal=False,
                ytdl=False,
                keep_open=False,
                vo="null",
            )
            self._player_ready = True
            return True
        except Exception as e:
            print(f"[player] mpv init with audio_device failed: {e}")
            try:
                self.player = _init_mpv(
                    video=False,
                    terminal=False,
                    ytdl=False,
                    keep_open=False,
                    vo="null",
                )
                self._player_ready = True
                return True
            except Exception as e2:
                self.player = None
                self._player_ready = False
                print(f"[player] mpv fallback init failed: {e2}")
                return False

    def stop_playback(self):
        if self.player:
            try:
                self.player.command("stop")
            except Exception:
                try:
                    self.player.stop()
                except Exception:
                    pass
        new_last = self.current_playing_id or self.last_played_id
        self._set_playback_state_and_refresh(None, new_last)
        if hasattr(self, "status_label"):
            self.set_status("stopped")

    @pyqtSlot()
    def _on_playback_naturally_ended(self):
        # end-file may fire for manual stop too; treat as stopped with last_played preserved
        if self.current_playing_id is None:
            return
        ended_id = self.current_playing_id
        self._set_playback_state_and_refresh(None, ended_id)

    def play_sound(self, sound: Dict[str, Any]):
        sound = self._remember_sound(sound)
        if not self._ensure_player():
            QMessageBox.warning(self, "Плеер", "python-mpv/libmpv недоступен. Проверьте установку mpv, libmpv1 и python-mpv.")
            return
        self.set_status(f"loading {sound.get('name','')}...")
        task = Task(self.scraper.resolve_local_path, sound)
        task.signals.finished.connect(lambda path, s=sound: self._on_sound_ready(s, path))
        task.signals.error.connect(lambda err: self._on_task_error("Ошибка загрузки звука", err))
        self.pool.start(task)

    @pyqtSlot(object, object)
    def _on_sound_ready(self, sound: Dict[str, Any], path_obj: Any):
        if not path_obj:
            self.set_status("error (cache/download failed)")
            return
        path = str(path_obj)
        sound["local_path"] = path
        sound = self._remember_sound(sound)

        if not self._ensure_player():
            self.set_status("player unavailable")
            return
        try:
            try:
                self.player.stop()
            except Exception:
                pass
            sid = sound.get("id")
            self._set_playback_state_and_refresh(sid, sid or self.last_played_id)
            self.player.play(path)
            self.set_status(f"playing {sound.get('name','')}")
            # Save state asynchronously to avoid UI stutter during playback start
            try:
                self.pool.start(Task(self.save_state))
            except Exception:
                try:
                    self.save_state()
                except Exception:
                    pass
        except Exception as e:
            self._set_playback_state_and_refresh(None, self.last_played_id)
            self.set_status("play error")
            print(f"[player] play error: {e}")

    # ---------- UI ----------
    def current_theme_key(self) -> str:
        key = self.config.get("theme", "dark")
        return key if key in THEMES else "dark"

    def theme_labels(self) -> Dict[str, str]:
        return get_theme_labels(self.current_theme_key())

    def set_status(self, msg: str):
        self._status_raw = msg or ""
        if not hasattr(self, "status_label"):
            return
        self.status_label.setText(format_status(self.current_theme_key(), self._status_raw))

    def _build_ui(self):
        labels = self.theme_labels()
        central = QWidget()
        root = QVBoxLayout(central)
        root.setContentsMargins(6, 6, 6, 6)
        root.setSpacing(6)

        # statusline
        statusline = QHBoxLayout()
        statusline.setSpacing(6)

        self.out_label = QLabel("OUT:")
        statusline.addWidget(self.out_label)
        self.headphones_combo = QComboBox()
        self.headphones_combo.setMinimumWidth(80)
        self.headphones_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.headphones_combo.currentIndexChanged.connect(self.on_headphones_changed)
        statusline.addWidget(self.headphones_combo, 1)

        self.mic_label = QLabel("MIC:")
        statusline.addWidget(self.mic_label)
        self.mic_combo = QComboBox()
        self.mic_combo.setMinimumWidth(80)
        self.mic_combo.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        self.mic_combo.currentIndexChanged.connect(self.on_mic_changed)
        statusline.addWidget(self.mic_combo, 1)

        self.mode_label = QLabel("MODE:")
        statusline.addWidget(self.mode_label)
        self.mode_combo = QComboBox()
        self.mode_combo.addItem(labels.get("mode_both", "Virtual Mic + Наушники (SoundpadAppSink)"), "both")
        self.mode_combo.addItem(labels.get("mode_headphones", "Только в наушники"), "headphones_only")
        self.mode_combo.currentIndexChanged.connect(self.on_mode_changed)
        statusline.addWidget(self.mode_combo, 1)

        self.settings_btn = QPushButton(labels.get("settings", "[Настройки]"))
        self.settings_btn.clicked.connect(self.open_settings)
        statusline.addWidget(self.settings_btn)

        self.stop_btn = QPushButton(labels.get("stop", "[STOP]"))
        self.stop_btn.setObjectName("stopButton")
        self.stop_btn.clicked.connect(self.stop_playback)
        statusline.addWidget(self.stop_btn)

        self.status_label = QLabel(format_status(self.current_theme_key(), self._status_raw))
        self.status_label.setObjectName("statusLabel")
        self.status_label.setMinimumWidth(80)
        self.status_label.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Preferred)
        statusline.addWidget(self.status_label, 1)

        root.addLayout(statusline)

        # tabs
        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)
        root.addWidget(self.tabs, 1)

        # MyInstants tab
        self.mi_tab = QWidget()
        mi_layout = QVBoxLayout(self.mi_tab)
        mi_layout.setContentsMargins(4, 4, 4, 4)
        mi_layout.setSpacing(4)

        search_row = QHBoxLayout()
        self.search_input = QLineEdit()
        self.search_input.setPlaceholderText(labels.get("search_placeholder", "Поиск на MyInstants..."))
        self.search_input.returnPressed.connect(self.do_search)
        self.search_btn = QPushButton(labels.get("search_btn", "[Поиск]"))
        self.search_btn.clicked.connect(self.do_search)
        self.trending_btn = QPushButton(labels.get("trending_btn", "[Тренды]"))
        self.trending_btn.clicked.connect(self.load_trending)
        self.upload_btn = QPushButton("Загрузить звук")
        self.upload_btn.setToolTip("Загрузить свои аудиофайлы в группу «Загрузки»")
        self.upload_btn.clicked.connect(self.upload_sounds_dialog)
        self.add_group_btn = QPushButton(labels.get("add_group", "[ + Группа ]"))
        self.add_group_btn.clicked.connect(self.create_group)
        search_row.addWidget(self.search_input, 1)
        search_row.addWidget(self.search_btn)
        search_row.addWidget(self.trending_btn)
        search_row.addWidget(self.upload_btn)
        search_row.addWidget(self.add_group_btn)
        mi_layout.addLayout(search_row)

        self.mi_grid = SoundGrid(self.play_sound, self.toggle_favorite, self.show_sound_menu, fav_on=labels.get("fav_on", "[*]"), fav_off=labels.get("fav_off", "[ ]"), empty_text=labels.get("no_sounds", "Нет звуков"))
        self.mi_scroll = QScrollArea()
        self.mi_scroll.setWidgetResizable(True)
        self.mi_scroll.setWidget(self.mi_grid)
        self.mi_scroll.verticalScrollBar().valueChanged.connect(self._on_mi_scroll)
        mi_layout.addWidget(self.mi_scroll, 1)

        bottom_row = QHBoxLayout()
        self.load_more_btn = QPushButton(labels.get("load_more", "[ Загрузить ещё ]"))
        self.load_more_btn.clicked.connect(self.load_more_sounds)
        self.load_more_btn.setEnabled(False)
        bottom_row.addWidget(self.load_more_btn)
        bottom_row.addStretch(1)
        mi_layout.addLayout(bottom_row)

        self.tabs.addTab(self.mi_tab, labels.get("myinstants_tab", format_tab_label(self.current_theme_key(), "MyInstants")))

        # MyInstants feed state
        self.mi_mode = "trending"
        self.mi_query = ""
        self.mi_page = 0
        self.mi_loading = False
        self.mi_has_more = True
        self.mi_sounds: List[Dict[str, Any]] = []
        self.mi_seen_ids = set()

        # Favorites tab
        self.fav_grid = SoundGrid(self.play_sound, self.toggle_favorite, self.show_sound_menu, fav_on=labels.get("fav_on", "[*]"), fav_off=labels.get("fav_off", "[ ]"), empty_text=labels.get("no_sounds", "Нет звуков"))
        self.fav_scroll = QScrollArea()
        self.fav_scroll.setWidgetResizable(True)
        self.fav_scroll.setWidget(self.fav_grid)
        self.tabs.addTab(self.fav_scroll, labels.get("favorites_tab", format_tab_label(self.current_theme_key(), "Избранное")))

        # custom group tabs
        self.group_grids = {}
        self.group_scrolls = {}
        for name in list(self.data.get("groups", {}).keys()):
            self._add_group_tab(name, save=False)

        self.setAcceptDrops(True)
        self.setCentralWidget(central)
        self.setStatusBar(QStatusBar())

    def _add_group_tab(self, name: str, save: bool = True):
        if name in self.group_grids:
            return
        labels = self.theme_labels()
        self.data.setdefault("groups", {}).setdefault(name, [])
        grid = SoundGrid(self.play_sound, self.toggle_favorite, self.show_sound_menu, fav_on=labels.get("fav_on", "[*]"), fav_off=labels.get("fav_off", "[ ]"), empty_text=labels.get("no_sounds", "Нет звуков"))
        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(grid)
        self.tabs.addTab(scroll, format_tab_label(self.current_theme_key(), name))
        self.group_grids[name] = grid
        self.group_scrolls[name] = scroll
        if save:
            self.save_state()
        self.refresh_group_tab(name)

    def apply_theme(self, theme_key: str, save: bool = True):
        if theme_key not in THEMES:
            theme_key = "dark"
        self.config["theme"] = theme_key
        self.setStyleSheet(build_qss(theme_key))
        self._apply_theme_ui_texts()
        # full refresh so themed labels/empty text and markers are consistent
        self._refresh_all_visible_grids()
        if save:
            self.save_state()

    def _apply_theme_ui_texts(self):
        labels = self.theme_labels()
        self.setWindowTitle(labels.get("window_title", "Soundpad"))

        if hasattr(self, "settings_btn"):
            self.settings_btn.setText(labels.get("settings", "[Настройки]"))
        if hasattr(self, "stop_btn"):
            self.stop_btn.setText(labels.get("stop", "[STOP]"))
        if hasattr(self, "search_input"):
            self.search_input.setPlaceholderText(labels.get("search_placeholder", "Поиск на MyInstants..."))
        if hasattr(self, "search_btn"):
            self.search_btn.setText(labels.get("search_btn", "[Поиск]"))
        if hasattr(self, "trending_btn"):
            self.trending_btn.setText(labels.get("trending_btn", "[Тренды]"))
        if hasattr(self, "add_group_btn"):
            self.add_group_btn.setText(labels.get("add_group", "[ + Группа ]"))
        if hasattr(self, "load_more_btn"):
            self.load_more_btn.setText(labels.get("loading_more", "[ Загрузка... ]") if getattr(self, "mi_loading", False) else labels.get("load_more", "[ Загрузить ещё ]"))

        # mode combo labels (preserve selection/data)
        if hasattr(self, "mode_combo"):
            current_mode = self.mode_combo.currentData() or self.config.get("mode", "both")
            self.mode_combo.blockSignals(True)
            self.mode_combo.clear()
            self.mode_combo.addItem(labels.get("mode_both", "Virtual Mic + Наушники (SoundpadAppSink)"), "both")
            self.mode_combo.addItem(labels.get("mode_headphones", "Только в наушники"), "headphones_only")
            self._set_combo_by_data(self.mode_combo, current_mode)
            self.mode_combo.blockSignals(False)

        # tabs
        if hasattr(self, "tabs") and hasattr(self, "mi_tab"):
            idx = self.tabs.indexOf(self.mi_tab)
            if idx >= 0:
                self.tabs.setTabText(idx, labels.get("myinstants_tab", format_tab_label(self.current_theme_key(), "MyInstants")))
        if hasattr(self, "tabs") and hasattr(self, "fav_scroll"):
            idx = self.tabs.indexOf(self.fav_scroll)
            if idx >= 0:
                self.tabs.setTabText(idx, labels.get("favorites_tab", format_tab_label(self.current_theme_key(), "Избранное")))
        if hasattr(self, "tabs") and hasattr(self, "group_scrolls"):
            for name, scroll in self.group_scrolls.items():
                idx = self.tabs.indexOf(scroll)
                if idx >= 0:
                    self.tabs.setTabText(idx, format_tab_label(self.current_theme_key(), name))

        # update grid label configs
        fav_on = labels.get("fav_on", "[*]")
        fav_off = labels.get("fav_off", "[ ]")
        empty = labels.get("no_sounds", "Нет звуков")
        if hasattr(self, "mi_grid"):
            self.mi_grid.set_theme_labels(fav_on, fav_off, empty)
        if hasattr(self, "fav_grid"):
            self.fav_grid.set_theme_labels(fav_on, fav_off, empty)
        if hasattr(self, "group_grids"):
            for g in self.group_grids.values():
                g.set_theme_labels(fav_on, fav_off, empty)

        # re-render status with themed prefix
        self.set_status(getattr(self, "_status_raw", "idle"))

    def _setup_shortcuts(self):
        QShortcut(QKeySequence(Qt.Key.Key_Escape), self, activated=self.stop_playback)

    # ---------- settings ----------
    def open_settings(self):
        dlg = SettingsDialog(self, self)
        dlg.exec()

    # ---------- audio init & combos ----------
    def _init_audio(self):
        ok, msg = self.router.available()
        if not ok:
            self.set_status(f"audio error - {msg}")
            self.refresh_device_combos(select_current=False)
            return
        self.refresh_device_combos(select_current=True)

        cfg_sink = self.config.get("headphones_sink")
        cfg_mic = self.config.get("mic_source")
        cfg_mode = self.config.get("mode", "both")

        try:
            mic_boost = int(self.config.get("mic_boost", 100) or 100)
            self.router.setup(cfg_sink, cfg_mic, cfg_mode, mic_boost=mic_boost)
            self.set_status("audio ready")
        except Exception as e:
            self.set_status("audio setup failed")
            print(f"[audio] setup failed: {e}")
        self._ensure_player()

    def refresh_device_combos(self, select_current: bool = False):
        sinks = self.router.list_sinks()
        sources = self.router.list_sources()
        sink_names = [s["name"] for s in sinks]
        src_names = [s["name"] for s in sources]

        if select_current:
            cfg_sink = self.config.get("headphones_sink")
            cfg_mic = self.config.get("mic_source")
            cfg_mode = self.config.get("mode", "both")
            if cfg_sink not in sink_names:
                cfg_sink = self.router.get_default_sink()
            if cfg_mic not in src_names:
                cfg_mic = self.router.get_default_source()
            self.config["headphones_sink"] = cfg_sink
            self.config["mic_source"] = cfg_mic
            self.config["mode"] = cfg_mode if cfg_mode in ("both", "headphones_only") else "both"
            self.save_state()
        else:
            cfg_sink = self.config.get("headphones_sink")
            cfg_mic = self.config.get("mic_source")
            cfg_mode = self.config.get("mode", "both")

        self._populate_combo(self.headphones_combo, sinks)
        self._populate_combo(self.mic_combo, sources)
        self._set_combo_by_data(self.headphones_combo, cfg_sink)
        self._set_combo_by_data(self.mic_combo, cfg_mic)
        self._set_combo_by_data(self.mode_combo, cfg_mode)

    def _populate_combo(self, combo: QComboBox, items):
        combo.blockSignals(True)
        combo.clear()
        for s in items:
            combo.addItem(s.get("description", s["name"]), s["name"])
        if combo.count() == 0:
            combo.addItem("(нет устройств)", None)
        combo.blockSignals(False)

    def _set_combo_by_data(self, combo: QComboBox, data_value: Any):
        combo.blockSignals(True)
        idx = -1
        for i in range(combo.count()):
            if combo.itemData(i) == data_value:
                idx = i
                break
        if idx >= 0:
            combo.setCurrentIndex(idx)
        combo.blockSignals(False)

    # public setters used by settings dialog and combos
    def set_headphones_sink(self, sink_name: str):
        if not sink_name:
            return
        self.config["headphones_sink"] = sink_name
        self.save_state()
        self._set_combo_by_data(self.headphones_combo, sink_name)
        try:
            self.router.set_headphones(sink_name)
            self.set_status("headphones updated")
        except Exception as e:
            print(f"[audio] headphones change failed: {e}")

    def set_mic_source(self, source_name: str):
        if not source_name:
            return
        self.config["mic_source"] = source_name
        self.save_state()
        self._set_combo_by_data(self.mic_combo, source_name)
        try:
            self.router.set_microphone(source_name)
            self.set_status("microphone updated")
        except Exception as e:
            print(f"[audio] mic change failed: {e}")

    def set_output_mode(self, mode: str):
        mode = mode if mode in ("both", "headphones_only") else "both"
        self.config["mode"] = mode
        self.save_state()
        self._set_combo_by_data(self.mode_combo, mode)
        try:
            self.router.set_mode(mode)
            self.set_status("mode updated")
        except Exception as e:
            print(f"[audio] mode change failed: {e}")

    def set_mic_boost(self, value: int):
        try:
            value = int(value)
        except Exception:
            value = 100
        value = max(100, min(300, value))
        self.config["mic_boost"] = value
        self.save_state()
        try:
            self.router.set_mic_boost(value)
        except Exception:
            pass

    @pyqtSlot(int)
    def on_headphones_changed(self, _idx: int):
        val = self.headphones_combo.currentData()
        if val:
            self.set_headphones_sink(val)

    @pyqtSlot(int)
    def on_mic_changed(self, _idx: int):
        val = self.mic_combo.currentData()
        if val:
            self.set_mic_source(val)

    @pyqtSlot(int)
    def on_mode_changed(self, _idx: int):
        val = self.mode_combo.currentData() or "both"
        self.set_output_mode(val)

    # ---------- sounds loading ----------
    def _load_initial_sounds(self):
        self.refresh_favorites_tab()
        self.load_trending()

    def _reset_mi_feed(self, mode: str, query: str = ""):
        self.mi_mode = mode
        self.mi_query = query
        self.mi_page = 0
        self.mi_has_more = True
        self.mi_loading = False
        self.mi_sounds = []
        self.mi_seen_ids = set()
        self.mi_grid.set_sounds([], self._favorites_set())
        self.load_more_btn.setEnabled(False)

    def load_trending(self):
        self._reset_mi_feed("trending", "")
        self.load_more_sounds()

    def do_search(self):
        q = self.search_input.text().strip()
        if q:
            self._reset_mi_feed("search", q)
        else:
            self._reset_mi_feed("trending", "")
        self.load_more_sounds()

    def load_more_sounds(self):
        if self.mi_loading or not self.mi_has_more:
            return
        next_page = self.mi_page + 1
        self.mi_loading = True
        self.load_more_btn.setEnabled(False)
        self.load_more_btn.setText(self.theme_labels().get("loading_more", "[ Загрузка... ]"))
        if self.mi_mode == "search" and self.mi_query:
            self.set_status(f"searching '{self.mi_query}' page {next_page}...")
            task = Task(self.scraper.search, self.mi_query, next_page)
        else:
            self.set_status(f"loading trending page {next_page}...")
            task = Task(self.scraper.fetch_trending, next_page)
        task.signals.finished.connect(lambda sounds, p=next_page: self._on_sounds_loaded(sounds, p))
        task.signals.error.connect(lambda err: self._on_task_error("Ошибка загрузки звуков", err))
        self.pool.start(task)

    @pyqtSlot(int)
    def _on_mi_scroll(self, value: int):
        try:
            sb = self.mi_scroll.verticalScrollBar()
            if not self.mi_has_more or self.mi_loading:
                return
            if value >= sb.maximum() - 120:
                self.load_more_sounds()
        except Exception:
            pass

    @pyqtSlot(object, int)
    def _on_sounds_loaded(self, sounds_obj: Any, page: int):
        sounds = sounds_obj or []
        self.mi_loading = False
        self.load_more_btn.setText(self.theme_labels().get("load_more", "[ Загрузить ещё ]"))

        added = 0
        for s in sounds:
            s = self._remember_sound(s)
            sid = s.get("id")
            if not sid or sid in self.mi_seen_ids:
                continue
            self.mi_seen_ids.add(sid)
            self.mi_sounds.append(s)
            added += 1

        if sounds:
            self.mi_page = max(self.mi_page, page)
            self.mi_has_more = len(sounds) >= 20
        else:
            self.mi_has_more = False

        self.save_state()
        self.mi_grid.set_sounds(self.mi_sounds, self._favorites_set())
        self.load_more_btn.setEnabled(self.mi_has_more)

        if self.mi_sounds:
            self.set_status(f"loaded {len(self.mi_sounds)} sounds (page {self.mi_page}, +{added})")
        else:
            self.set_status("no sounds found (check network/search)")

    def _on_task_error(self, title: str, err: str):
        print(f"[task error] {title}: {err}")
        self.mi_loading = False
        if hasattr(self, "load_more_btn"):
            self.load_more_btn.setText(self.theme_labels().get("load_more", "[ Загрузить ещё ]"))
            self.load_more_btn.setEnabled(bool(getattr(self, "mi_has_more", False) and getattr(self, "mi_sounds", [])))
        self.set_status("error")

    # ---------- favorites & groups ----------
    def toggle_favorite(self, sound: Dict[str, Any]):
        sound = self._remember_sound(sound)
        sid = sound.get("id")
        if not sid:
            return
        favs = self.data.setdefault("favorites", [])
        if sid in favs:
            favs = [x for x in favs if x != sid]
        else:
            favs.append(sid)
        self.data["favorites"] = favs
        self.save_state()
        # favorites tab content changes; other tabs only need marker updates
        self.refresh_favorites_tab()
        for grid in [getattr(self, "mi_grid", None), *getattr(self, "group_grids", {}).values()]:
            if not grid:
                continue
            try:
                if hasattr(grid, "_favorites"):
                    grid._favorites = self._favorites_set()
                if hasattr(grid, "refresh_markers"):
                    grid.refresh_markers()
            except Exception:
                pass

    def refresh_favorites_tab(self):
        fav_ids = self.data.get("favorites", [])
        sounds_map = self.data.get("sounds", {})
        fav_sounds = [sounds_map[sid] for sid in fav_ids if sid in sounds_map]
        self.fav_grid.set_sounds(fav_sounds, self._favorites_set())

    def refresh_group_tab(self, name: str):
        grid = self.group_grids.get(name)
        if not grid:
            return
        sounds = self.data.get("groups", {}).get(name, [])
        sounds_map = self.data.get("sounds", {})
        resolved = []
        for s in sounds:
            sid = s.get("id")
            if sid and sid in sounds_map:
                resolved.append(sounds_map[sid])
            else:
                resolved.append(s)
        self.data["groups"][name] = resolved
        grid.set_sounds(resolved, self._favorites_set())

    def _refresh_all_visible_grids(self):
        self.refresh_favorites_tab()
        for name in list(self.group_grids.keys()):
            self.refresh_group_tab(name)
        if hasattr(self, "mi_sounds"):
            self.mi_grid.set_sounds(self.mi_sounds, self._favorites_set())

    def _set_playback_state_and_refresh(self, new_playing_id: Optional[str], new_last_played_id: Optional[str]):
        prev_playing = getattr(self, "current_playing_id", None)
        prev_last = getattr(self, "last_played_id", None)
        self.current_playing_id = new_playing_id
        self.last_played_id = new_last_played_id
        affected = {sid for sid in (prev_playing, prev_last, new_playing_id, new_last_played_id) if sid}
        grids = [getattr(self, "mi_grid", None), getattr(self, "fav_grid", None), *getattr(self, "group_grids", {}).values()]
        for grid in grids:
            if not grid or not hasattr(grid, "set_playback_state"):
                continue
            try:
                grid.set_playback_state(self.current_playing_id, self.last_played_id)
                if affected and hasattr(grid, "refresh_markers_for_ids"):
                    grid.refresh_markers_for_ids(affected)
                elif hasattr(grid, "refresh_markers"):
                    # fallback (initial/unknown state)
                    if affected:
                        grid.refresh_markers_for_ids(affected)
                    else:
                        grid.refresh_markers()
            except Exception:
                pass

    def _refresh_playback_indicators(self):
        # Fallback: refresh only markers in-place (no grid rebuild)
        ids = {sid for sid in (getattr(self, "current_playing_id", None), getattr(self, "last_played_id", None)) if sid}
        for grid in [getattr(self, "mi_grid", None), getattr(self, "fav_grid", None), *getattr(self, "group_grids", {}).values()]:
            if not grid or not hasattr(grid, "set_playback_state"):
                continue
            try:
                grid.set_playback_state(self.current_playing_id, self.last_played_id)
                if ids and hasattr(grid, "refresh_markers_for_ids"):
                    grid.refresh_markers_for_ids(ids)
                elif hasattr(grid, "refresh_markers"):
                    grid.refresh_markers()
            except Exception:
                pass

    def create_group(self):
        name, ok = QInputDialog.getText(self, "Новая группа", "Имя группы:")
        if not ok:
            return
        name = (name or "").strip()
        if not name:
            return
        if name in self.data.get("groups", {}):
            QMessageBox.information(self, "Группа", "Такая группа уже существует.")
            return
        self._add_group_tab(name, save=True)

    def add_sound_to_group(self, sound: Dict[str, Any], group_name: str):
        sound = self._remember_sound(sound)
        groups = self.data.setdefault("groups", {})
        if group_name not in groups:
            groups[group_name] = []
        lst = groups[group_name]
        sid = sound.get("id")
        if not any(x.get("id") == sid for x in lst):
            lst.append(sound)
        self.save_state()
        self.refresh_group_tab(group_name)

    def show_sound_menu(self, sound: Dict[str, Any], global_pos):
        sound = self._remember_sound(sound)
        menu = QMenu(self)
        sid = sound.get("id")
        favs = set(self.data.get("favorites", []))
        if sid in favs:
            fav_act = menu.addAction("Убрать из избранного")
        else:
            fav_act = menu.addAction("Добавить в избранное [*]")
        rename_act = menu.addAction("Переименовать…")
        menu.addSeparator()
        groups = list(self.data.get("groups", {}).keys())
        group_menu = menu.addMenu("Добавить в группу")
        if not groups:
            empty_act = group_menu.addAction("(нет групп)")
            empty_act.setEnabled(False)
        group_actions = {}
        for g in groups:
            act = group_menu.addAction(g)
            group_actions[act] = g
        menu.addSeparator()
        download_act = menu.addAction("Скачать...")
        copy_act = menu.addAction("Сохранить в кэш сейчас")

        chosen = menu.exec(global_pos)
        if not chosen:
            return
        if chosen == fav_act:
            self.toggle_favorite(sound)
            return
        if chosen == rename_act:
            self.rename_sound(sound)
            return
        if chosen == download_act:
            self.download_sound_to_folder(sound)
            return
        if chosen == copy_act:
            self._cache_sound_async(sound)
            return
        if chosen in group_actions:
            self.add_sound_to_group(sound, group_actions[chosen])

    def rename_sound(self, sound: Dict[str, Any]):
        sound = self._remember_sound(sound)
        sid = sound.get("id")
        if not sid:
            return
        current_name = sound.get("name", "")
        new_name, ok = QInputDialog.getText(self, "Переименовать звук", "Новое название:", text=current_name)
        if not ok:
            return
        new_name = (new_name or "").strip()
        if not new_name or new_name == current_name:
            return
        sound["name"] = new_name
        stored = self.data.setdefault("sounds", {}).get(sid, {})
        stored["name"] = new_name
        self.data["sounds"][sid] = {**stored, **{k: v for k, v in sound.items() if v is not None}}
        # update name in group entries that store copies
        for gname, items in self.data.get("groups", {}).items():
            for it in items:
                if isinstance(it, dict) and it.get("id") == sid:
                    it["name"] = new_name
        self.save_state()
        self._refresh_all_visible_grids()

    def _cache_sound_async(self, sound: Dict[str, Any]):
        self.set_status("caching...")
        task = Task(self.scraper.ensure_cached, sound)
        task.signals.finished.connect(lambda p, s=sound: self._on_cached(s, p))
        task.signals.error.connect(lambda err: self._on_task_error("Ошибка кэширования", err))
        self.pool.start(task)

    def _on_cached(self, sound, path_obj):
        if path_obj:
            sound["local_path"] = str(path_obj)
            self._remember_sound(sound)
            self.save_state()
            self.set_status("cached")
        else:
            self.set_status("cache failed")

    # ---------- tray ----------
    def _create_tray_icon(self) -> QIcon:
        icon_path = APP_DIR / "icon.png"
        if icon_path.exists():
            return QIcon(str(icon_path))
        # Terminal-style minimalist fallback icon: "ST" (soundterminal)
        size = 64
        pm = QPixmap(size, size)
        pm.fill(Qt.GlobalColor.transparent)
        painter = QPainter(pm)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing, True)

        bg = QColor("#0c0f14")
        border = QColor("#2f3542")
        accent = QColor("#00ff66")
        dim = QColor("#3f4757")

        # terminal window block
        margin = 4
        rect = pm.rect().adjusted(margin, margin, -margin - 1, -margin - 1)
        painter.setPen(border)
        painter.setBrush(bg)
        painter.drawRoundedRect(rect, 8, 8)

        # top bar hint
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(dim)
        painter.drawRoundedRect(rect.left() + 2, rect.top() + 2, rect.width() - 4, 10, 4, 4)

        # prompt + cursor hint
        prompt_font = painter.font()
        prompt_font.setFamily("Monospace")
        prompt_font.setBold(True)
        prompt_font.setPointSize(9)
        painter.setFont(prompt_font)
        painter.setPen(accent)
        painter.drawText(rect.left() + 8, rect.top() + 10, ">_")

        # main letters
        main_font = painter.font()
        main_font.setFamily("Monospace")
        main_font.setBold(True)
        main_font.setPointSize(24)
        painter.setFont(main_font)
        painter.setPen(accent)
        text_rect = rect.adjusted(0, 10, 0, -2)
        painter.drawText(text_rect, int(Qt.AlignmentFlag.AlignCenter), "ST")

        painter.end()
        return QIcon(pm)

    def _setup_tray(self):
        self.tray_icon = None
        self._really_quit = False
        if not QSystemTrayIcon.isSystemTrayAvailable():
            return
        icon = self._create_tray_icon()
        self.setWindowIcon(icon)
        tray = QSystemTrayIcon(icon, self)
        tray.setToolTip("Soundpad")

        menu = QMenu(self)
        self.tray_action_show = QAction("Показать/Скрыть", self)
        self.tray_action_show.triggered.connect(self.toggle_window_visibility)
        menu.addAction(self.tray_action_show)

        self.tray_action_stop = QAction("Стоп", self)
        self.tray_action_stop.triggered.connect(self.stop_playback)
        menu.addAction(self.tray_action_stop)

        menu.addSeparator()
        self.tray_action_quit = QAction("Выход", self)
        self.tray_action_quit.triggered.connect(self.quit_app)
        menu.addAction(self.tray_action_quit)

        tray.setContextMenu(menu)
        tray.activated.connect(self._on_tray_activated)
        tray.show()
        self.tray_icon = tray

    def _on_tray_activated(self, reason):
        if reason == QSystemTrayIcon.ActivationReason.Trigger:
            self.toggle_window_visibility()

    def toggle_window_visibility(self):
        if self.isVisible() and not self.isMinimized():
            self.hide()
        else:
            self.showNormal()
            self.raise_()
            self.activateWindow()

    def quit_app(self):
        self._really_quit = True
        try:
            if self.tray_icon:
                self.tray_icon.hide()
        except Exception:
            pass
        self.close()




    # ---------- download/export ----------
    def get_download_dir(self) -> Path:
        raw = self.config.get("download_dir") or str(Path.home() / "Downloads")
        try:
            return Path(os.path.expanduser(str(raw))).resolve()
        except Exception:
            return (Path.home() / "Downloads").resolve()

    def is_download_dir_valid(self) -> bool:
        try:
            d = self.get_download_dir()
            return d.exists() and d.is_dir()
        except Exception:
            return False

    def set_download_dir(self, path: str):
        self.config["download_dir"] = str(path)
        self.save_state()

    def open_settings_for_download_dir(self, message: str = "у вас нет каталога по умолчанию"):
        dlg = SettingsDialog(self, self)
        try:
            # show on devices tab and display warning
            if hasattr(dlg, "tabs") and hasattr(dlg, "devices_tab"):
                idx = dlg.tabs.indexOf(dlg.devices_tab)
                if idx >= 0:
                    dlg.tabs.setCurrentIndex(idx)
            if hasattr(dlg, "download_dir_warning"):
                dlg.download_dir_warning.setText(message)
        except Exception:
            pass
        dlg.exec()

    def _download_target_path(self, src_path: Path, sound: Dict[str, Any]) -> Path:
        d = self.get_download_dir()
        d.mkdir(parents=True, exist_ok=True)
        ext = src_path.suffix or ".mp3"
        base_name = sound.get("name") or src_path.stem or "sound"
        safe = re.sub(r'[\\/:*?"<>|]+', "_", str(base_name)).strip() or "sound"
        candidate = d / f"{safe}{ext}"
        i = 1
        while candidate.exists():
            candidate = d / f"{safe} ({i}){ext}"
            i += 1
        return candidate

    def download_sound_to_folder(self, sound: Dict[str, Any]):
        sound = self._remember_sound(sound)
        if not self.is_download_dir_valid():
            self.open_settings_for_download_dir("у вас нет каталога по умолчанию")
            return
        self.set_status("downloading...")

        def _job():
            src = self.scraper.resolve_local_path(sound)
            if not src:
                raise RuntimeError("Не удалось получить файл звука")
            src = Path(src)
            if not src.exists():
                raise RuntimeError("Файл звука не найден")
            target = self._download_target_path(src, sound)
            if src.resolve() != target.resolve():
                shutil.copy2(str(src), str(target))
            return target

        task = Task(_job)
        task.signals.finished.connect(lambda p: self.set_status(f"downloaded: {Path(p).name}") if p else self.set_status("download failed"))
        task.signals.error.connect(lambda err: self.set_status("download failed"))
        self.pool.start(task)



    # ---------- uploads / downloads ----------
    def _ensure_downloads_group(self):
        self.data.setdefault("groups", {})
        if DOWNLOADS_GROUP_NAME not in self.data["groups"]:
            self.data["groups"][DOWNLOADS_GROUP_NAME] = []
        if DOWNLOADS_GROUP_NAME not in self.group_grids:
            self._add_group_tab(DOWNLOADS_GROUP_NAME, save=True)
        else:
            self.save_state()

    def _focus_group_tab(self, name: str):
        scroll = self.group_scrolls.get(name)
        if scroll and hasattr(self, "tabs"):
            idx = self.tabs.indexOf(scroll)
            if idx >= 0:
                self.tabs.setCurrentIndex(idx)

    def upload_sounds_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Загрузить звук",
            str(Path.home()),
            "Audio Files (*.mp3 *.wav *.ogg *.flac *.m4a *.aac *.opus *.wma *.aiff *.aif);;All Files (*)",
        )
        if files:
            self.import_sound_files(files)

    def _is_audio_file(self, path: Path) -> bool:
        return path.suffix.lower() in AUDIO_EXTS

    def _unique_dest_path(self, dest_dir: Path, filename: str) -> Path:
        safe = re.sub(r'[\\/:*?"<>|]+', "_", (filename or "").strip()) or "sound"
        base = Path(safe)
        stem = base.stem or "sound"
        ext = base.suffix or ".mp3"
        candidate = dest_dir / f"{stem}{ext}"
        i = 1
        while candidate.exists():
            candidate = dest_dir / f"{stem} ({i}){ext}"
            i += 1
        return candidate

    def import_sound_files(self, paths: List[str]):
        if not paths:
            return
        try:
            DOWNLOADS_DIR.mkdir(parents=True, exist_ok=True)
        except Exception as e:
            self.set_status(f"import error: {e}")
            return

        self._ensure_downloads_group()
        groups = self.data.setdefault("groups", {})
        dl = groups.setdefault(DOWNLOADS_GROUP_NAME, [])

        existing_ids = {s.get("id") for s in dl if isinstance(s, dict) and s.get("id")}
        existing_paths = set()
        for s in dl:
            lp = s.get("local_path") if isinstance(s, dict) else None
            if lp:
                try:
                    existing_paths.add(str(Path(lp).resolve()))
                except Exception:
                    existing_paths.add(str(lp))

        added = 0
        errors = 0
        for p in paths:
            try:
                src = Path(p)
                if not src.exists() or not src.is_file():
                    continue
                if not self._is_audio_file(src):
                    continue
                dest = self._unique_dest_path(DOWNLOADS_DIR, src.name)
                shutil.copy2(str(src), str(dest))

                try:
                    resolved = str(dest.resolve())
                except Exception:
                    resolved = str(dest)
                if resolved in existing_paths:
                    continue

                sid = hashlib.sha1(f"{resolved}|{dest.stat().st_size}|{int(dest.stat().st_mtime_ns)}".encode("utf-8", "ignore")).hexdigest()[:16]
                sound = self._remember_sound({
                    "id": sid,
                    "name": dest.stem or src.stem or "sound",
                    "local_path": str(dest),
                })

                if sid in existing_ids or any((isinstance(x, dict) and x.get("id") == sid) for x in dl):
                    existing_paths.add(resolved)
                    continue

                dl.append(sound)
                existing_ids.add(sid)
                existing_paths.add(resolved)
                added += 1
            except Exception as e:
                errors += 1
                print(f"[import] failed {p}: {e}")

        self.save_state()
        self.refresh_group_tab(DOWNLOADS_GROUP_NAME)
        self._refresh_all_visible_grids()
        self._focus_group_tab(DOWNLOADS_GROUP_NAME)

        if added and errors:
            self.set_status(f"imported {added}, errors {errors}")
        elif added:
            self.set_status(f"imported {added} sound(s)")
        elif errors:
            self.set_status(f"import failed ({errors})")
        else:
            self.set_status("no sounds imported")

    def dragEnterEvent(self, event):
        md = event.mimeData()
        if md and md.hasUrls():
            for u in md.urls():
                if u.isLocalFile():
                    try:
                        p = Path(u.toLocalFile())
                        if self._is_audio_file(p):
                            event.acceptProposedAction()
                            return
                    except Exception:
                        pass
        event.ignore()

    def dragMoveEvent(self, event):
        self.dragEnterEvent(event)

    def dropEvent(self, event):
        md = event.mimeData()
        paths = []
        if md and md.hasUrls():
            for u in md.urls():
                if u.isLocalFile():
                    try:
                        p = Path(u.toLocalFile())
                        if self._is_audio_file(p):
                            paths.append(str(p))
                    except Exception:
                        pass
        if paths:
            self.import_sound_files(paths)
            event.acceptProposedAction()
        else:
            event.ignore()



    # ---------- lifecycle ----------
    def closeEvent(self, event):
        # If tray is available, hide to tray on close unless explicitly quitting.
        if getattr(self, "tray_icon", None) is not None and self.tray_icon.isVisible() and not getattr(self, "_really_quit", False):
            event.ignore()
            self.hide()
            try:
                self.tray_icon.showMessage("Soundpad", "Приложение свернуто в трей", QSystemTrayIcon.MessageIcon.Information, 1500)
            except Exception:
                pass
            return
        try:
            self.save_state()
        except Exception:
            pass
        try:
            self.stop_playback()
        except Exception:
            pass
        try:
            if self.player:
                self.player.terminate()
        except Exception:
            pass
        try:
            self.router.cleanup()
        except Exception:
            pass
        super().closeEvent(event)


def main():
    CACHE_DIR.mkdir(parents=True, exist_ok=True)
    app = QApplication(sys.argv)
    app.setApplicationName("Soundpad")
    win = MainWindow()
    win.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    main()
