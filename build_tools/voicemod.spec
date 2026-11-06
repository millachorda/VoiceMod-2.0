# Empaqueta VoiceMod 2.0 con PyInstaller:  pyinstaller build_tools/voicemod.spec
import os
ROOT = os.path.abspath(os.path.join(SPECPATH, ".."))
R = lambda *p: os.path.join(ROOT, *p)

datas = [(R("ui", f), "ui") for f in ("index.html", "style.css", "app.js")]
datas += [(R("ui", "img", "logo.png"), os.path.join("ui", "img"))]
for sub in ("voces", "modulos", "ajustes"):
    datas.append((R("ui", "img", sub), os.path.join("ui", "img", sub)))
datas += [(R("icono.ico"), "."), (R("sonidos"), "sonidos")]

a = Analysis([R("app.py")], pathex=[ROOT], datas=datas,
             hiddenimports=["clr", "webview.platforms.winforms", "make_art"],
             excludes=["tkinter", "matplotlib", "pandas", "IPython", "pytest"])
pyz = PYZ(a.pure)
exe = EXE(pyz, a.scripts, [], exclude_binaries=True, name="VoiceMod 2.0", icon=R("icono.ico"),
          console=False, version=R("build_tools", "file_version.txt") if os.path.exists(R("build_tools", "file_version.txt")) else None)
coll = COLLECT(exe, a.binaries, a.datas, name="VoiceMod 2.0")
