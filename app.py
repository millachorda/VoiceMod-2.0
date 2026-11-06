"""VoiceMod 2.0 — cambiador de voz en tiempo real. Interfaz web (pywebview) + motor de audio en Python."""
import ctypes
import json
import os
import random
import shutil
import threading

import numpy as np
import sounddevice as sd
import webview

from engine import AudioEngine, DEFAULT_PARAMS, load_wav, SR
from presets import PRESETS, META, CATEGORIES

try:
    import keyboard  # atajos globales
except Exception:
    keyboard = None

APP_NAME = "VoiceMod 2.0"
HERE = os.path.dirname(os.path.abspath(__file__))
SOUNDS_DIR = os.path.join(HERE, "sonidos")
CONFIG = os.path.join(HERE, "config.json")
CUSTOM = os.path.join(HERE, "voces_personalizadas.json")
ICON = os.path.join(HERE, "icono.ico")

SOUND_EMOJI = {"bocina": "📯", "tada": "🎉", "fallo": "👎", "redoble": "🥁", "pitido": "🔔", "laser": "✨",
               "risa": "😂", "aplauso": "👏", "explosion": "💥", "pedo": "💨", "grito": "😱", "alarma": "🚨"}


def load_json(path, default):
    try:
        with open(path, encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return default


def save_json(path, data):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)


def make_default_sounds():
    """Crea unos efectos de sonido sintetizados la primera vez."""
    import wave
    os.makedirs(SOUNDS_DIR, exist_ok=True)
    if os.listdir(SOUNDS_DIR):
        return
    t = lambda d: np.arange(int(SR * d)) / SR

    def save(name, a):
        a = np.clip(a / (np.max(np.abs(a)) + 1e-9) * 0.9, -1, 1)
        with wave.open(os.path.join(SOUNDS_DIR, name), "wb") as w:
            w.setnchannels(1); w.setsampwidth(2); w.setframerate(SR)
            w.writeframes((a * 32767).astype(np.int16).tobytes())

    saw = lambda f, x: 2 * ((f * x) % 1) - 1
    x = t(1.2)
    save("bocina.wav", sum(saw(f, x) for f in (440, 554, 659)) * np.minimum(1, (1.2 - x) * 8))
    notes = [523, 659, 784, 1047]
    save("tada.wav", np.concatenate([np.sin(2 * np.pi * f * t(0.15)) * np.exp(-t(0.15) * 6) for f in notes[:-1]]
                                    + [np.sin(2 * np.pi * notes[-1] * t(0.8)) * np.exp(-t(0.8) * 3)]))
    x = t(0.5)
    save("fallo.wav", np.concatenate([saw(f, x) * np.exp(-x * 2) for f in (392, 370, 349)]
                                     + [saw(330, t(1.0)) * np.exp(-t(1.0) * 1.5)]))
    x = t(2.0)
    rng = np.random.default_rng(1)
    save("redoble.wav", rng.standard_normal(len(x)) * (0.5 + 0.5 * np.sin(2 * np.pi * 18 * x)) * np.minimum(1, x * 2))
    save("pitido.wav", np.sin(2 * np.pi * 1000 * t(0.25)))
    x = t(1.0)
    save("laser.wav", np.sin(2 * np.pi * np.cumsum(2000 * np.exp(-x * 4) + 200) / SR) * np.exp(-x * 3))


def art_name(name):
    """Nombre de archivo seguro para una imagen generada."""
    import hashlib
    return hashlib.md5(("v2" + name).encode("utf-8")).hexdigest()[:12]


def is_cable(n):
    n = n.lower()
    return any(k in n for k in ("cable", "virtual", "vb-audio", "voicemeeter"))


class Api:
    """Métodos llamados desde JavaScript (window.pywebview.api.*)."""

    def __init__(self):
        self._window = None
        self._eng = AudioEngine()
        self.cfg = load_json(CONFIG, {})
        self.custom = load_json(CUSTOM, {})
        self.current = self.cfg.get("voz", "Normal")
        self.params = {}
        self.cache = {}
        self.test_state = ""
        self.notice = None
        self._eng.sound_volume = self.cfg.get("vol_sonidos", 0.8)
        self._eng.sounds_to_mic = self.cfg.get("sonidos_al_micro", True)
        self._eng.monitor_on = self.cfg.get("escucharme", False)
        self._select(self.current)
        self._hotkeys()

    # ---------- datos ----------
    def _voices(self):
        out = []
        for i, name in enumerate(PRESETS):
            cat, emoji, c1, c2, desc = META.get(name, ("Humanas", "🎙️", "#444", "#222", ""))
            out.append(dict(name=name, cat=cat, emoji=emoji, c1=c1, c2=c2, desc=desc,
                            img=f"img/voces/{i:02d}.jpg", custom=False))
        for name in self.custom:
            fn = art_name(name) + ".jpg"
            path = os.path.join(HERE, "ui", "img", "personal", fn)
            if not os.path.exists(path):
                try:
                    import make_art; make_art.custom_art(path, name)
                except Exception:
                    pass
            out.append(dict(name=f"★ {name}", cat="Mis voces", emoji="🎛️", c1="#8b5cf6", c2="#06b6d4",
                            desc="Voz personalizada", img=f"img/personal/{fn}" if os.path.exists(path) else None, custom=True))
        return out

    def _sounds(self):
        files = sorted(f for f in os.listdir(SOUNDS_DIR) if f.lower().endswith(".wav"))
        self.sound_files = files
        res = []
        for f in files:
            base = os.path.splitext(f)[0]
            emo = next((e for k, e in SOUND_EMOJI.items() if k in base.lower()), "🔊")
            fn = art_name(base) + ".jpg"
            path = os.path.join(HERE, "ui", "img", "sonidos", fn)
            if not os.path.exists(path):
                try:
                    import make_art; make_art.sound_art(path, base, emo)
                except Exception:
                    pass
            res.append(dict(file=f, name=base.replace("_", " ").capitalize(), emoji=emo,
                            img=f"img/sonidos/{fn}" if os.path.exists(path) else None))
        return res

    def init(self):
        apis = [a["name"] for a in sd.query_hostapis()]
        api = self.cfg.get("api", "MME")
        if api not in apis:
            api = apis[0]
        return dict(voices=self._voices(), categories=CATEGORIES + ["Mis voces"], sounds=self._sounds(),
                    params=self.params, defaults=DEFAULT_PARAMS, current=self.current, apis=apis, api=api,
                    devices=self.devices(api), cfg=self.cfg, favs=self.cfg.get("favoritas", []),
                    toggles=self._toggles(), sfx_volume=self._eng.sound_volume, hotkeys=keyboard is not None)

    def devices(self, api):
        apis = sd.query_hostapis()
        idx = next(i for i, a in enumerate(apis) if a["name"] == api)
        devs = sd.query_devices()
        ins = [dict(id=i, name=d["name"]) for i, d in enumerate(devs) if d["hostapi"] == idx and d["max_input_channels"] > 0]
        outs = [dict(id=i, name=d["name"]) for i, d in enumerate(devs) if d["hostapi"] == idx and d["max_output_channels"] > 0]
        mons = [dict(id=i, name=d["name"]) for i, d in enumerate(devs) if d["hostapi"] == idx and d["max_output_channels"] > 0 and not is_cable(d["name"])]

        def pick(lst, saved, hint):
            names = [d["name"] for d in lst]
            if saved in names:
                return saved
            good = [n for n in names if hint(n)]
            return good[0] if good else (names[0] if names else "")
        normal = lambda n: not is_cable(n) and "asignador" not in n.lower() and "mapper" not in n.lower()
        return dict(inputs=ins, outputs=outs, monitors=mons,
                    sel_in=pick(ins, self.cfg.get("entrada"), normal),
                    sel_out=pick(outs, self.cfg.get("salida"), is_cable),
                    sel_mon=pick(mons, self.cfg.get("escuchar"), normal),
                    has_cable=any(is_cable(d["name"]) for d in outs))

    def _toggles(self):
        return dict(enabled=self._eng.proc.enabled, muted=self._eng.proc.muted,
                    monitor=self._eng.monitor_on, sfx_to_mic=self._eng.sounds_to_mic)

    def _dev_id(self, api, kind, name):
        d = self.devices(api)
        return next((x["id"] for x in d[kind] if x["name"] == name), None)

    # ---------- motor ----------
    def start(self, api, entrada, salida, escuchar):
        self.cfg.update(api=api, entrada=entrada, salida=salida, escuchar=escuchar)
        self._save_cfg()
        try:
            i = self._dev_id(api, "inputs", entrada)
            o = self._dev_id(api, "outputs", salida)
            m = self._dev_id(api, "monitors", escuchar) if self._eng.monitor_on else None
            self._eng.start(i, o, m)
            return dict(ok=True)
        except Exception as e:
            self._eng.stop()
            return dict(ok=False, error=str(e))

    def stop(self):
        self._eng.stop()
        return True

    def toggle(self, key, value):
        value = bool(value)
        if key == "enabled":
            self._eng.proc.enabled = value
        elif key == "muted":
            self._eng.proc.muted = value
        elif key == "sfx_to_mic":
            self._eng.sounds_to_mic = value
            self.cfg["sonidos_al_micro"] = value
        elif key == "monitor":
            self._eng.monitor_on = value
            self.cfg["escucharme"] = value
            if self._eng.running:
                try:
                    mid = self._dev_id(self.cfg.get("api", "MME"), "monitors", self.cfg.get("escuchar")) if value else None
                    self._eng.set_monitor_device(mid)
                except Exception as e:
                    return dict(ok=False, error=str(e))
        self._save_cfg()
        return dict(ok=True, toggles=self._toggles())

    # ---------- voces ----------
    def _voice_params(self, name):
        if name.startswith("★ "):
            return self.custom.get(name[2:])
        return PRESETS.get(name)

    def _select(self, name):
        p = self._voice_params(name)
        if p is None:
            name, p = "Normal", {}
        self.current = name
        self.params = dict(DEFAULT_PARAMS); self.params.update(p)
        self._eng.proc.set_params(self.params)
        self.cfg["voz"] = name

    def voice(self, name):
        self._select(name)
        self._save_cfg()
        return dict(current=self.current, params=self.params)

    def random_voice(self):
        return self.voice(random.choice([v["name"] for v in self._voices() if v["name"] != self.current]))

    def param(self, key, value):
        self.params[key] = float(value)
        self._eng.proc.set_params(self.params)
        return True

    def save_custom(self, name):
        name = name.strip()[:40]
        if not name:
            return None
        self.custom[name] = dict(self.params)
        save_json(CUSTOM, self.custom)
        self._select(f"★ {name}")
        return dict(voices=self._voices(), current=self.current, params=self.params)

    def delete_custom(self, name):
        if name.startswith("★ "):
            self.custom.pop(name[2:], None)
            save_json(CUSTOM, self.custom)
            if self.current == name:
                self._select("Normal")
        return dict(voices=self._voices(), current=self.current, params=self.params)

    def set_favs(self, favs):
        self.cfg["favoritas"] = favs
        self._save_cfg()
        return True

    def test_voice(self, seconds=4):
        if not self._eng.running:
            return dict(ok=False, error="Primero pulsa INICIAR")
        if self.test_state:
            return dict(ok=False, error="Ya hay una prueba en curso")
        mid = self._dev_id(self.cfg.get("api", "MME"), "monitors", self.cfg.get("escuchar"))

        def run():
            try:
                self.test_state = "grabando"
                self._eng.rec_target = 0
                import time
                threading.Timer(seconds, lambda: setattr(self, "test_state", "reproduciendo")).start()
                self._eng.test_voice(seconds, mid, dict(self.params))
            finally:
                self.test_state = ""
        threading.Thread(target=run, daemon=True).start()
        return dict(ok=True)

    # ---------- soundboard ----------
    def play(self, f):
        if f not in self.cache:
            try:
                self.cache[f] = load_wav(os.path.join(SOUNDS_DIR, f))
            except Exception as e:
                return dict(ok=False, error=f"No se pudo cargar {f}: {e}")
        if not self._eng.running:
            return dict(ok=False, error="Pulsa INICIAR para que suenen los efectos")
        self._eng.play(self.cache[f])
        return dict(ok=True)

    def stop_sounds(self):
        self._eng.stop_sounds()
        return True

    def sfx_volume(self, v):
        self._eng.sound_volume = float(v)
        self.cfg["vol_sonidos"] = float(v)
        return True

    def add_sounds(self):
        paths = self._window.create_file_dialog(webview.FileDialog.OPEN, allow_multiple=True,
                                               file_types=("Audio WAV (*.wav)",))
        for p in paths or []:
            shutil.copy(p, SOUNDS_DIR)
        return self._sounds()

    def delete_sound(self, f):
        try:
            os.remove(os.path.join(SOUNDS_DIR, os.path.basename(f)))
            self.cache.pop(f, None)
        except Exception:
            pass
        return self._sounds()

    def open_folder(self):
        os.startfile(SOUNDS_DIR)
        return True

    def open_url(self, url):
        if url.startswith("https://"):
            os.startfile(url)
        return True

    # ---------- estado (lo consulta la interfaz ~25 veces/s) ----------
    def state(self):
        lv = lambda x: max(0.0, min(1.0, (20 * np.log10(x + 1e-9) + 60) / 60))
        run = self._eng.running
        n, self.notice = self.notice, None
        return dict(running=run, inp=lv(self._eng.in_level) if run else 0, out=lv(self._eng.out_level) if run else 0,
                    spec=self._eng.spectrum(32) if run else [0] * 32, current=self.current,
                    toggles=self._toggles(), test=self.test_state, playing=len(self._eng.sounds), notice=n)

    # ---------- atajos ----------
    def _hotkeys(self):
        if keyboard is None:
            return
        def voice_i(i):
            vs = self._voices()
            if i < len(vs):
                self._select(vs[i]["name"]); self.notice = f"Voz: {vs[i]['name']}"
        def sound_i(i):
            if i < len(getattr(self, "sound_files", [])):
                self.play(self.sound_files[i])
        def flip(attr, label):
            setattr(self._eng.proc, attr, not getattr(self._eng.proc, attr))
            self.notice = f"{label}: {'sí' if getattr(self._eng.proc, attr) else 'no'}"
        try:
            for i in range(1, 10):
                keyboard.add_hotkey(f"ctrl+shift+{i}", sound_i, args=(i - 1,))
            keyboard.add_hotkey("ctrl+shift+0", self._eng.stop_sounds)
            keyboard.add_hotkey("ctrl+alt+v", flip, args=("enabled", "Voz activada"))
            keyboard.add_hotkey("ctrl+alt+m", flip, args=("muted", "Micrófono silenciado"))
            keyboard.add_hotkey("ctrl+alt+r", lambda: (self.random_voice(), setattr(self, "notice", f"Voz: {self.current}")))
        except Exception:
            pass

    def _save_cfg(self):
        save_json(CONFIG, self.cfg)

    def shutdown(self):
        self._save_cfg()
        self._eng.stop()
        if keyboard:
            try:
                keyboard.unhook_all()
            except Exception:
                pass


def style_window(window):
    """Icono de la ventana y barra de título oscura (Windows 11)."""
    try:
        import clr
        clr.AddReference("System.Drawing")
        from System.Drawing import Icon
        from System import Action
        form = window.native

        def apply():
            form.Icon = Icon(ICON)
            hwnd = form.Handle.ToInt64()
            dwm = ctypes.windll.dwmapi
            on = ctypes.c_int(1)
            dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 20, ctypes.byref(on), 4)  # modo oscuro
            color = ctypes.c_int(0x00140E0D)  # BGR de #0d0e14
            dwm.DwmSetWindowAttribute(ctypes.c_void_p(hwnd), 35, ctypes.byref(color), 4)
        form.Invoke(Action(apply))
    except Exception as e:
        print("No se pudo aplicar el estilo de ventana:", e)


def main():
    make_default_sounds()
    try:  # icono propio en la barra de tareas en vez del de Python
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID("VoiceMod2.App")
    except Exception:
        pass
    api = Api()
    window = webview.create_window(APP_NAME, url=os.path.join(HERE, "ui", "index.html"), js_api=api,
                                   width=1320, height=840, min_size=(1080, 700), background_color="#0d0e14")
    api._window = window
    window.events.shown += lambda: style_window(window)
    window.events.closed += api.shutdown
    webview.start(http_server=True, icon=ICON)


if __name__ == "__main__":
    main()
