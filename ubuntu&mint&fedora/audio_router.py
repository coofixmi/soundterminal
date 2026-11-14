import atexit
import re
import shutil
import subprocess
import time
from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple


APP_SINK_NAME = "SoundpadAppSink"
VIRT_MIC_NAME = "VirtualMicMix"


@dataclass
class ModuleIds:
    app_sink: Optional[int] = None
    virt_mic: Optional[int] = None
    loopback_monitor_to_headphones: Optional[int] = None
    loopback_monitor_to_mic: Optional[int] = None
    loopback_mic_to_mix: Optional[int] = None


class AudioRouterError(Exception):
    pass


class AudioRouter:
    def __init__(self):
        self.modules = ModuleIds()
        self.headphones_sink: Optional[str] = None
        self.physical_mic: Optional[str] = None
        self.mode: str = "both"  # "both" or "headphones_only"
        self.mic_boost: int = 100
        self._pactl = shutil.which("pactl")
        atexit.register(self.cleanup)

    # ---------- helpers ----------
    def _ensure_pactl(self):
        if not self._pactl:
            raise AudioRouterError("pactl не найден. Установите pulseaudio-utils или pipewire-pulse.")

    def _run(self, args: List[str], check: bool = False) -> subprocess.CompletedProcess:
        self._ensure_pactl()
        try:
            return subprocess.run(
                [self._pactl] + args,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                check=check,
            )
        except Exception as e:
            raise AudioRouterError(f"Ошибка запуска pactl: {e}")

    def available(self) -> Tuple[bool, str]:
        if not self._pactl:
            return False, "pactl не найден"
        p = self._run(["info"])
        if p.returncode != 0:
            return False, (p.stderr or p.stdout or "pactl недоступен").strip()
        return True, "ok"

    # ---------- device listing ----------
    def list_sinks(self) -> List[Dict[str, str]]:
        p = self._run(["list", "short", "sinks"])
        items = []
        if p.returncode != 0:
            return items
        for line in p.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[1]
            if name in (APP_SINK_NAME, VIRT_MIC_NAME):
                continue
            # exclude obvious monitors-as-sinks if any
            desc = self._get_sink_description(name)
            items.append({"name": name, "description": desc or name})
        return items

    def list_sources(self) -> List[Dict[str, str]]:
        p = self._run(["list", "short", "sources"])
        items = []
        if p.returncode != 0:
            return items
        for line in p.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) < 2:
                parts = line.split()
            if len(parts) < 2:
                continue
            name = parts[1]
            if name.endswith(".monitor"):
                continue
            if name in (APP_SINK_NAME, VIRT_MIC_NAME):
                continue
            desc = self._get_source_description(name)
            items.append({"name": name, "description": desc or name})
        return items

    def _get_sink_description(self, name: str) -> str:
        return self._get_description("sink", name)

    def _get_source_description(self, name: str) -> str:
        return self._get_description("source", name)

    def _get_description(self, kind: str, name: str) -> str:
        p = self._run(["list", f"{kind}s"])
        if p.returncode != 0:
            return name
        # simple parse: find block with Name: <name> and Description:
        blocks = p.stdout.split("\n\n")
        target = f"Name: {name}"
        for b in blocks:
            if target in b:
                for line in b.splitlines():
                    line = line.strip()
                    if line.startswith("Description:"):
                        return line.split(":", 1)[1].strip()
        return name

    def get_default_sink(self) -> Optional[str]:
        p = self._run(["get-default-sink"])
        if p.returncode == 0:
            v = p.stdout.strip()
            if v and v not in (APP_SINK_NAME, VIRT_MIC_NAME):
                return v
        # fallback first real sink
        sinks = self.list_sinks()
        return sinks[0]["name"] if sinks else None

    def get_default_source(self) -> Optional[str]:
        p = self._run(["get-default-source"])
        if p.returncode == 0:
            v = p.stdout.strip()
            if v and not v.endswith(".monitor") and v not in (APP_SINK_NAME, VIRT_MIC_NAME):
                return v
        sources = self.list_sources()
        return sources[0]["name"] if sources else None

    # ---------- module management ----------
    def _load_module(self, module: str, args: str) -> Optional[int]:
        p = self._run(["load-module", module] + (args.split() if args else []))
        if p.returncode != 0:
            err = (p.stderr or p.stdout or "").strip()
            print(f"[audio_router] load-module failed {module} {args}: {err}")
            return None
        out = p.stdout.strip()
        try:
            return int(out)
        except Exception:
            print(f"[audio_router] cannot parse module id: {out}")
            return None

    def _unload_module(self, mod_id: Optional[int]):
        if mod_id is None:
            return
        self._run(["unload-module", str(mod_id)])

    def _find_modules_by_sink_name(self, sink_name: str) -> List[int]:
        p = self._run(["list", "short", "modules"])
        ids = []
        if p.returncode != 0:
            return ids
        for line in p.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            try:
                mid = int(parts[0])
            except Exception:
                continue
            modname = parts[1]
            args = parts[2] if len(parts) > 2 else ""
            if modname == "module-null-sink" and f"sink_name={sink_name}" in args:
                ids.append(mid)
        return ids

    def _cleanup_stale_named_sinks(self):
        # best-effort cleanup of previous runs
        for name in (APP_SINK_NAME, VIRT_MIC_NAME):
            for mid in self._find_modules_by_sink_name(name):
                self._unload_module(mid)

    def _cleanup_loopbacks_related(self):
        p = self._run(["list", "short", "modules"])
        if p.returncode != 0:
            return
        for line in p.stdout.strip().splitlines():
            parts = line.split("\t")
            if len(parts) < 3:
                continue
            try:
                mid = int(parts[0])
            except Exception:
                continue
            modname = parts[1]
            args = parts[2] if len(parts) > 2 else ""
            if modname == "module-loopback" and (APP_SINK_NAME in args or VIRT_MIC_NAME in args):
                self._unload_module(mid)

    # ---------- setup & routing ----------
    def setup(self, headphones_sink: Optional[str] = None, physical_mic: Optional[str] = None, mode: str = "both", mic_boost: Optional[int] = None):
        ok, msg = self.available()
        if not ok:
            raise AudioRouterError(msg)

        self.headphones_sink = headphones_sink or self.get_default_sink()
        self.physical_mic = physical_mic or self.get_default_source()
        self.mode = mode if mode in ("both", "headphones_only") else "both"
        if mic_boost is not None:
            self.mic_boost = max(100, min(300, int(mic_boost)))

        # clean previous state
        self.cleanup()
        self._cleanup_stale_named_sinks()
        self._cleanup_loopbacks_related()

        # create sinks
        self.modules.app_sink = self._load_module(
            "module-null-sink",
            f"sink_name={APP_SINK_NAME} rate=48000 channels=2 sink_properties=device.description=SoundpadAppSink",
        )
        self.modules.virt_mic = self._load_module(
            "module-null-sink",
            f"sink_name={VIRT_MIC_NAME} rate=48000 channels=2 sink_properties=device.description=VirtualMicMix",
        )
        if not self.modules.app_sink or not self.modules.virt_mic:
            raise AudioRouterError("Не удалось создать виртуальные устройства SoundpadAppSink/VirtualMicMix")

        self._apply_loopbacks()

    def _sink_input_indices_by_owner_module(self, module_id: Optional[int]) -> List[int]:
        if module_id is None:
            return []
        p = self._run(["list", "sink-inputs"])
        if p.returncode != 0:
            return []
        indices: List[int] = []
        cur_idx: Optional[int] = None
        for line in p.stdout.splitlines():
            m = re.match(r"^Sink Input #(\d+)", line)
            if m:
                cur_idx = int(m.group(1))
                continue
            if cur_idx is None:
                continue
            m_owner = re.match(r"\s*Owner Module:\s*(\d+)", line)
            if m_owner and int(m_owner.group(1)) == module_id:
                indices.append(cur_idx)
                cur_idx = None
        return indices

    def _set_module_stream_volume(self, module_id: Optional[int], volume: int, retries: int = 10, delay: float = 0.05):
        volume = max(0, min(300, int(volume)))
        if module_id is None:
            return
        last_indices: List[int] = []
        for i in range(max(1, retries)):
            indices = self._sink_input_indices_by_owner_module(module_id)
            if indices:
                last_indices = indices
                for idx in indices:
                    self._run(["set-sink-input-volume", str(idx), f"{volume}%"])
                return
            if i < retries - 1:
                try:
                    time.sleep(delay)
                except Exception:
                    pass
        # final attempt already done if found; if not found, nothing to set
        for idx in last_indices:
            self._run(["set-sink-input-volume", str(idx), f"{volume}%"])

    def apply_mic_boost(self):
        # Boost only app sounds sent to the virtual mic; keep headphones and physical mic paths unchanged.
        self._set_module_stream_volume(self.modules.loopback_monitor_to_mic, self.mic_boost)

    def set_mic_boost(self, value: int):
        self.mic_boost = max(100, min(300, int(value)))
        self.apply_mic_boost()

    def _apply_loopbacks(self):
        # (re)create loopbacks according to current selections/mode
        self._unload_module(self.modules.loopback_monitor_to_headphones)
        self._unload_module(self.modules.loopback_monitor_to_mic)
        self._unload_module(self.modules.loopback_mic_to_mix)
        self.modules.loopback_monitor_to_headphones = None
        self.modules.loopback_monitor_to_mic = None
        self.modules.loopback_mic_to_mix = None

        # Use a stable latency and prevent streams from being moved automatically.
        # latency_msec=1 often causes underruns/static noise in the virtual mic mix.
        loopback_opts = "latency_msec=30 source_dont_move=true sink_dont_move=true"

        if self.headphones_sink:
            self.modules.loopback_monitor_to_headphones = self._load_module(
                "module-loopback",
                f"source={APP_SINK_NAME}.monitor sink={self.headphones_sink} {loopback_opts}",
            )
        if self.mode == "both":
            self.modules.loopback_monitor_to_mic = self._load_module(
                "module-loopback",
                f"source={APP_SINK_NAME}.monitor sink={VIRT_MIC_NAME} {loopback_opts}",
            )
        if self.physical_mic:
            self.modules.loopback_mic_to_mix = self._load_module(
                "module-loopback",
                f"source={self.physical_mic} sink={VIRT_MIC_NAME} {loopback_opts}",
            )

        self.apply_mic_boost()

    def set_headphones(self, sink_name: str):
        self.headphones_sink = sink_name
        self._apply_loopbacks()

    def set_microphone(self, source_name: str):
        self.physical_mic = source_name
        self._apply_loopbacks()

    def set_mode(self, mode: str):
        self.mode = mode if mode in ("both", "headphones_only") else "both"
        self._apply_loopbacks()

    def cleanup(self):
        # unload in reverse-ish order
        for attr in (
            "loopback_mic_to_mix",
            "loopback_monitor_to_mic",
            "loopback_monitor_to_headphones",
            "virt_mic",
            "app_sink",
        ):
            mid = getattr(self.modules, attr, None)
            self._unload_module(mid)
            setattr(self.modules, attr, None)
