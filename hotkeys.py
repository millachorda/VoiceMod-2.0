"""Atajos globales con RegisterHotKey (API oficial de Windows).

A diferencia de un gancho de teclado, Windows solo nos avisa cuando se pulsa una de las
combinaciones registradas: la app nunca ve el resto de lo que escribes.
Formato de combinación: "ctrl+shift+f5", "alt+num 3", "f8"...
"""
import ctypes
import queue
import threading
from ctypes import wintypes

user32 = ctypes.windll.user32
kernel32 = ctypes.windll.kernel32

MODS = {"alt": 0x1, "ctrl": 0x2, "shift": 0x4, "win": 0x8}
MOD_NOREPEAT = 0x4000
WM_HOTKEY = 0x0312
WM_APP_WAKE = 0x8001

KEYS = {f"f{i}": 0x6F + i for i in range(1, 25)}
KEYS.update({chr(c).lower(): c for c in range(ord("A"), ord("Z") + 1)})
KEYS.update({str(d): 0x30 + d for d in range(10)})
KEYS.update({f"num {d}": 0x60 + d for d in range(10)})
KEYS.update({"num *": 0x6A, "num +": 0x6B, "num -": 0x6D, "num .": 0x6E, "num /": 0x6F,
             "space": 0x20, "enter": 0x0D, "tab": 0x09, "backspace": 0x08, "insert": 0x2D, "delete": 0x2E,
             "home": 0x24, "end": 0x23, "page up": 0x21, "page down": 0x22,
             "up": 0x26, "down": 0x28, "left": 0x25, "right": 0x27,
             "pause": 0x13, "scroll lock": 0x91, "print screen": 0x2C})


def parse(combo):
    """'ctrl+shift+f5' -> (modificadores, código de tecla)."""
    mods, vk = 0, None
    for part in combo.lower().split("+"):
        part = part.strip()
        if part in MODS:
            mods |= MODS[part]
        elif part in KEYS:
            vk = KEYS[part]
        else:
            raise ValueError(f"Tecla no reconocida: {part}")
    if vk is None:
        raise ValueError("Falta la tecla principal")
    return mods, vk


class HotkeyManager:
    """Hilo con su propia cola de mensajes de Windows; registra y escucha los atajos."""

    def __init__(self):
        self._ops = queue.Queue()
        self._ready = threading.Event()
        self._callbacks = {}
        self._tid = None
        threading.Thread(target=self._loop, daemon=True, name="atajos").start()
        self._ready.wait(3)

    def _loop(self):
        self._tid = kernel32.GetCurrentThreadId()
        msg = wintypes.MSG()
        user32.PeekMessageW(ctypes.byref(msg), None, 0, 0, 0)  # crea la cola de mensajes
        self._ready.set()
        while user32.GetMessageW(ctypes.byref(msg), None, 0, 0) > 0:
            if msg.message == WM_HOTKEY:
                cb = self._callbacks.get(msg.wParam)
                if cb:
                    threading.Thread(target=cb, daemon=True).start()
            elif msg.message == WM_APP_WAKE:
                while not self._ops.empty():
                    fn, done = self._ops.get()
                    try:
                        done.result = fn()
                    except Exception as e:
                        done.result = e
                    done.set()

    def _call(self, fn):
        """Ejecuta fn en el hilo de los atajos (RegisterHotKey lo exige)."""
        done = threading.Event()
        self._ops.put((fn, done))
        user32.PostThreadMessageW(self._tid, WM_APP_WAKE, 0, 0)
        done.wait(3)
        if isinstance(getattr(done, "result", None), Exception):
            raise done.result
        return getattr(done, "result", None)

    def set_all(self, binds):
        """binds: {combinación: función}. Sustituye todos los atajos. Devuelve las que fallaron."""
        def apply():
            for hid in list(self._callbacks):
                user32.UnregisterHotKey(None, hid)
            self._callbacks.clear()
            failed = []
            for i, (combo, cb) in enumerate(binds.items(), start=1):
                try:
                    mods, vk = parse(combo)
                except ValueError:
                    failed.append(combo); continue
                if user32.RegisterHotKey(None, i, mods | MOD_NOREPEAT, vk):
                    self._callbacks[i] = cb
                else:
                    failed.append(combo)  # ya la usa otra aplicación
            return failed
        return self._call(apply)

    def stop(self):
        try:
            self.set_all({})
        except Exception:
            pass
