"""Motor de audio en tiempo real: micrófono -> efectos -> cable virtual (+ escucha y soundboard)."""
import threading
import collections
import wave

import numpy as np
import sounddevice as sd
from scipy.signal import lfilter, butter

SR = 48000
BLOCK = 256  # ~5 ms a 48 kHz

# Parámetros por defecto (todos editables desde la interfaz)
DEFAULT_PARAMS = {
    "gate_db": -60.0,      # puerta de ruido (dBFS). -60 = casi apagada
    "pitch": 0.0,          # semitonos (-12..+12)
    "ring_freq": 0.0,      # Hz del modulador en anillo (0 = off)
    "ring_mix": 0.0,       # 0..1
    "whisper": 0.0,        # 0..1 mezcla de susurro
    "drive": 0.0,          # 0..1 distorsión
    "bits": 16,            # 16 = off, 3..15 = bitcrusher
    "downsample": 1,       # 1 = off, 2..16
    "lowcut": 0.0,         # Hz pasa-altos (0 = off)
    "highcut": 0.0,        # Hz pasa-bajos (0 = off)
    "tremolo_rate": 0.0,   # Hz (0 = off)
    "tremolo_depth": 0.0,  # 0..1
    "echo_time": 0.25,     # s
    "echo_fb": 0.0,        # 0..0.9 realimentación
    "echo_mix": 0.0,       # 0..1
    "reverb_size": 0.7,    # 0..0.98
    "reverb_mix": 0.0,     # 0..1
    "volume": 1.0,         # 0..3
}


def db_to_lin(db):
    return 10.0 ** (db / 20.0)


class PitchShifter:
    """Desplazador de tono granular de dos cabezales (baja latencia)."""

    def __init__(self, window=int(0.04 * SR)):
        self.W = window
        self.hist = np.zeros(window + 4, dtype=np.float32)
        self.phase = 0.0

    def process(self, x, semitones):
        if abs(semitones) < 0.01:
            self.hist = np.concatenate([self.hist, x])[-(self.W + 4):]
            return x
        ratio = 2.0 ** (semitones / 12.0)
        buf = np.concatenate([self.hist, x])
        base = len(self.hist)
        n = len(x)
        step = (1.0 - ratio) / self.W
        idx = np.arange(1, n + 1)
        p1 = np.mod(self.phase + idx * step, 1.0)
        p2 = np.mod(p1 + 0.5, 1.0)
        self.phase = float(p1[-1])
        pos = base + np.arange(n)

        def tap(p):
            r = pos - p * self.W
            i0 = np.floor(r).astype(np.int64)
            frac = r - i0
            i1 = np.minimum(i0 + 1, len(buf) - 1)
            return (buf[i0] * (1 - frac) + buf[i1] * frac) * np.sin(np.pi * p) ** 2

        y = tap(p1) + tap(p2)
        self.hist = buf[-(self.W + 4):]
        return y.astype(np.float32)


class Comb:
    """Filtro peine/pasa-todo con historial circular. Requiere delay >= tamaño de bloque."""

    def __init__(self, delay, gain, allpass=False):
        self.delay, self.gain, self.allpass = max(delay, BLOCK), gain, allpass
        self.xh = np.zeros(self.delay)  # últimas `delay` entradas
        self.yh = np.zeros(self.delay)  # últimas `delay` salidas

    def process(self, x):
        n = len(x)
        y_d = self.yh[:n]  # y[n-D]
        if self.allpass:
            y = -self.gain * x + self.xh[:n] + self.gain * y_d
        else:
            y = x + self.gain * y_d
        self.xh = np.concatenate([self.xh[n:], x])
        self.yh = np.concatenate([self.yh[n:], y])
        return y


class Reverb:
    COMBS = [1557, 1617, 1491, 1422]
    ALLP = [556, 441]

    def __init__(self):
        self.size = None
        self.combs = []
        self.allps = [Comb(int(d * SR / 44100), 0.5, allpass=True) for d in self.ALLP]

    def process(self, x, size):
        if size != self.size:
            self.size = size
            self.combs = [Comb(int(d * SR / 44100), size) for d in self.COMBS]
        y = sum(c.process(x) for c in self.combs) * 0.25
        for ap in self.allps:
            y = ap.process(y)
        return y * (1 - size) * 2.0


class Filter:
    def __init__(self):
        self.key = None
        self.ba = None
        self.zi = None

    def process(self, x, kind, freq):
        key = (kind, round(freq))
        if key != self.key:
            self.key = key
            self.ba = butter(2, freq / (SR / 2), btype=kind)
            self.zi = np.zeros(max(len(self.ba[0]), len(self.ba[1])) - 1)
        y, self.zi = lfilter(self.ba[0], self.ba[1], x, zi=self.zi)
        return y


class Processor:
    def __init__(self):
        self.params = dict(DEFAULT_PARAMS)
        self.enabled = True     # voz activada
        self.muted = False      # micrófono silenciado
        self.pitch = PitchShifter()
        self.reverb = Reverb()
        self.echo = None
        self.hp, self.lp = Filter(), Filter()
        self.env_zi = np.zeros(1)
        self.gate_gain = 1.0
        self.t = 0  # contador de muestras para osciladores
        self.held = 0.0
        self.rng = np.random.default_rng()

    def set_params(self, p):
        new = dict(DEFAULT_PARAMS)
        new.update(p)
        self.params = new  # sustitución atómica

    def process(self, x):
        p = self.params
        n = len(x)
        x = x.astype(np.float64)
        if self.muted:
            self.pitch.process(np.zeros(n, np.float32), 0)
            return np.zeros(n)
        if not self.enabled:
            return x

        # Puerta de ruido suavizada
        rms = np.sqrt(np.mean(x * x) + 1e-12)
        target = 1.0 if rms > db_to_lin(p["gate_db"]) else 0.0
        g = np.linspace(self.gate_gain, self.gate_gain + (target - self.gate_gain) * 0.3, n)
        self.gate_gain = g[-1]
        x = x * g

        if p["pitch"]:
            x = self.pitch.process(x.astype(np.float32), p["pitch"]).astype(np.float64)
        else:
            self.pitch.process(x.astype(np.float32), 0)

        tt = (self.t + np.arange(n)) / SR
        self.t += n

        if p["whisper"] > 0:
            env, self.env_zi = lfilter([0.01], [1, -0.99], np.abs(x), zi=self.env_zi)
            noise = self.rng.standard_normal(n) * env * 1.2
            x = x * (1 - p["whisper"]) + noise * p["whisper"]

        if p["ring_freq"] > 0 and p["ring_mix"] > 0:
            mod = np.sin(2 * np.pi * p["ring_freq"] * tt)
            x = x * (1 - p["ring_mix"]) + x * mod * p["ring_mix"]

        if p["drive"] > 0:
            k = 1 + p["drive"] * 30
            x = np.tanh(x * k) / np.tanh(k) * 0.8

        ds = int(p["downsample"])
        if ds > 1:
            held = np.repeat(x[::ds], ds)[:n]
            x = held
        bits = int(p["bits"])
        if bits < 16:
            q = 2 ** (bits - 1)
            x = np.round(x * q) / q

        if p["lowcut"] > 20:
            x = self.hp.process(x, "highpass", min(p["lowcut"], SR / 2 - 100))
        if 20 < p["highcut"] < SR / 2 - 100:
            x = self.lp.process(x, "lowpass", p["highcut"])

        if p["tremolo_rate"] > 0 and p["tremolo_depth"] > 0:
            x = x * (1 - p["tremolo_depth"] * (0.5 + 0.5 * np.sin(2 * np.pi * p["tremolo_rate"] * tt)))

        if p["echo_mix"] > 0 and p["echo_fb"] > 0:
            d = max(BLOCK, int(p["echo_time"] * SR))
            if self.echo is None or self.echo.delay != d or self.echo.gain != p["echo_fb"]:
                self.echo = Comb(d, p["echo_fb"])
            y = self.echo.process(x)
            x = x + p["echo_mix"] * (y - x)

        if p["reverb_mix"] > 0:
            x = x * (1 - p["reverb_mix"] * 0.5) + self.reverb.process(x, p["reverb_size"]) * p["reverb_mix"]

        return x * p["volume"]


def load_wav(path):
    """Carga un WAV (8/16/24/32 bits) como float32 mono a SR."""
    with wave.open(path, "rb") as w:
        ch, sw, rate, frames = w.getnchannels(), w.getsampwidth(), w.getframerate(), w.getnframes()
        raw = w.readframes(frames)
    if sw == 1:
        a = (np.frombuffer(raw, np.uint8).astype(np.float32) - 128) / 128
    elif sw == 2:
        a = np.frombuffer(raw, np.int16).astype(np.float32) / 32768
    elif sw == 3:
        b = np.frombuffer(raw, np.uint8).reshape(-1, 3)
        a = (b[:, 0].astype(np.int32) | (b[:, 1].astype(np.int32) << 8) | (b[:, 2].astype(np.int32) << 16))
        a = np.where(a >= 2 ** 23, a - 2 ** 24, a).astype(np.float32) / 2 ** 23
    else:
        a = np.frombuffer(raw, np.int32).astype(np.float32) / 2 ** 31
    a = a.reshape(-1, ch).mean(axis=1)
    if rate != SR:
        n = int(len(a) * SR / rate)
        a = np.interp(np.linspace(0, len(a) - 1, n), np.arange(len(a)), a).astype(np.float32)
    return a


class AudioEngine:
    def __init__(self):
        self.proc = Processor()
        self.stream = None
        self.monitor_stream = None
        self.monitor_on = False
        self.monitor_q = collections.deque(maxlen=8)
        self.sounds = []  # [array, pos]
        self.sound_volume = 0.8
        self.sounds_to_mic = True
        self.lock = threading.Lock()
        self.in_level = 0.0
        self.out_level = 0.0
        self.status = ""
        self.scope = collections.deque(maxlen=8)  # últimos bloques de salida (para el espectro)
        self.rec = None        # grabación de prueba (lista de bloques crudos)
        self.rec_target = 0

    # --- soundboard ---
    def play(self, data):
        with self.lock:
            self.sounds.append([data, 0])

    def stop_sounds(self):
        with self.lock:
            self.sounds.clear()

    def _mix_sounds(self, n):
        out = np.zeros(n)
        with self.lock:
            alive = []
            for s in self.sounds:
                data, pos = s
                chunk = data[pos:pos + n]
                out[:len(chunk)] += chunk
                s[1] = pos + n
                if s[1] < len(data):
                    alive.append(s)
            self.sounds = alive
        return out * self.sound_volume

    # --- streams ---
    def _callback(self, indata, outdata, frames, time, status):
        if status:
            self.status = str(status)
        x = indata[:, 0]
        self.in_level = float(np.sqrt(np.mean(x.astype(np.float64) ** 2)))
        if self.rec is not None and len(self.rec) * frames < self.rec_target:
            self.rec.append(x.copy())
        y = self.proc.process(x)
        sfx = self._mix_sounds(frames)
        mic_out = y + sfx if self.sounds_to_mic else y
        mic_out = np.clip(mic_out, -1, 1)
        self.out_level = float(np.sqrt(np.mean(mic_out ** 2)))
        self.scope.append(mic_out)
        outdata[:] = mic_out[:, None].astype(np.float32)
        if self.monitor_on:
            self.monitor_q.append(np.clip(y + sfx, -1, 1).astype(np.float32))

    def _monitor_cb(self, outdata, frames, time, status):
        if self.monitor_q:
            blk = self.monitor_q.popleft()
            m = min(len(blk), frames)
            outdata[:m, :] = blk[:m, None]
            outdata[m:, :] = 0
        else:
            outdata[:] = 0

    def start(self, in_dev, out_dev, mon_dev=None):
        self.stop()
        out_ch = sd.query_devices(out_dev)["max_output_channels"]
        self.stream = sd.Stream(device=(in_dev, out_dev), samplerate=SR, blocksize=BLOCK,
                                channels=(1, min(out_ch, 2)) if out_ch else 1, dtype="float32",
                                latency="low", callback=self._wrap_cb(min(out_ch, 2)))
        self.stream.start()
        self.set_monitor_device(mon_dev)

    def _wrap_cb(self, ch):
        def cb(indata, outdata, frames, time, status):
            tmp = np.empty((frames, 1), np.float32)
            self._callback(indata, tmp, frames, time, status)
            outdata[:] = np.repeat(tmp, ch, axis=1)
        return cb

    def set_monitor_device(self, mon_dev):
        if self.monitor_stream:
            self.monitor_stream.stop(); self.monitor_stream.close()
            self.monitor_stream = None
        self.monitor_q.clear()
        if mon_dev is not None:
            self.monitor_stream = sd.OutputStream(device=mon_dev, samplerate=SR, blocksize=BLOCK,
                                                  channels=1, dtype="float32", latency="low",
                                                  callback=self._monitor_cb)
            self.monitor_stream.start()

    def stop(self):
        for s in (self.stream, self.monitor_stream):
            if s:
                try:
                    s.stop(); s.close()
                except Exception:
                    pass
        self.stream = self.monitor_stream = None

    @property
    def running(self):
        return self.stream is not None and self.stream.active

    def spectrum(self, bands=40):
        """Espectro logarítmico (0..1) de la salida reciente."""
        if not self.scope:
            return [0.0] * bands
        x = np.concatenate(list(self.scope))[-2048:]
        if len(x) < 2048:
            x = np.pad(x, (2048 - len(x), 0))
        mag = np.abs(np.fft.rfft(x * np.hanning(2048)))
        freqs = np.fft.rfftfreq(2048, 1 / SR)
        edges = np.geomspace(60, 12000, bands + 1)
        out = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            m = mag[(freqs >= lo) & (freqs < hi)]
            v = float(m.max()) if len(m) else 0.0
            out.append(max(0.0, min(1.0, (20 * np.log10(v + 1e-9) + 10) / 60)))
        return out

    def test_voice(self, seconds, mon_dev, params):
        """Graba `seconds` del micro sin efecto y lo reproduce con la voz actual."""
        import time
        self.rec, self.rec_target = [], int(seconds * SR)
        while len(self.rec) * BLOCK < self.rec_target:
            time.sleep(0.05)
            if not self.running:
                self.rec = None
                return False
        raw = np.concatenate(self.rec); self.rec = None
        pr = Processor(); pr.set_params(params)
        y = np.concatenate([pr.process(raw[i:i + BLOCK]) for i in range(0, len(raw) - BLOCK + 1, BLOCK)])
        sd.play(np.clip(y, -1, 1).astype(np.float32), SR, device=mon_dev, blocking=True)
        return True
