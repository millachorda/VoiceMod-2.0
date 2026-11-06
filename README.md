<p align="center"><img src="ui/img/logo.png" width="120" alt="VoiceMod 2.0"></p>

<h1 align="center">VoiceMod 2.0</h1>
<p align="center">A free, open-source voice changer for Windows that runs in real time. Every feature is unlocked.</p>

---

## Features
- **46 voices** in 7 categories: Human, Fun, Creatures, Horror, Machines and Environments, plus your own voices.
- **Voice lab** with 18 parameters you can change live: pitch, robot, whisper, distortion, bitcrusher, EQ, tremolo, echo, reverb, noise gate and volume. You can save your own voices.
- **Soundboard** with no limit on sounds: add your own WAV files and send them straight to your microphone.
- **Live spectrum view** and input/output level meters.
- **Test voice:** record yourself for 4 seconds and hear the result with the current effect.
- **Listen to yourself** through your headphones while you talk.
- **Global shortcuts** that work inside games and Discord.
- Low latency: 48 kHz audio processed in 5 ms blocks, with a custom DSP engine written in NumPy.

## Installation
1. Install [Python 3.11+](https://www.python.org/downloads/).
2. `pip install -r requirements.txt`
3. Install a virtual audio cable, for example [VB-Cable](https://vb-audio.com/Cable/), which is free.
4. Double-click **`Iniciar VoiceMod 2.0.bat`**, or run `python app.py`.

## Using it in Discord, OBS or games
1. In the app, go to **Ajustes y audio** (Settings and audio). Pick your microphone, and pick the cable as the output.
2. Click **INICIAR** (Start).
3. In Discord, open *Voice & Video*. Set the input to **CABLE Output** and turn off noise suppression.

## Global shortcuts
| Shortcut | Action |
|---|---|
| Ctrl+Alt+R | Random voice |
| Ctrl+Alt+V | Turn the effect on or off |
| Ctrl+Alt+M | Mute the microphone |
| Ctrl+Shift+1…9 | Play a sound |
| Ctrl+Shift+0 | Stop all sounds |

## Project structure
| File | Contents |
|---|---|
| `app.py` | Window (pywebview) and the bridge to the interface |
| `engine.py` | Real-time audio engine and effects |
| `presets.py` | Voice definitions |
| `make_art.py` | Generates the icon and the images |
| `ui/` | Interface (HTML, CSS, JS) |

*Independent project. It is not affiliated with Voicemod S.L.*
