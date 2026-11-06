"""Genera build_tools/file_version.txt (recurso de versión del .exe) a partir de version.py."""
import os, sys
ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
sys.path.insert(0, ROOT)
from version import VERSION

t = tuple(int(x) for x in VERSION.split(".")) + (0,)
TEMPLATE = f"""VSVersionInfo(
  ffi=FixedFileInfo(filevers={t}, prodvers={t}, mask=0x3f, flags=0x0, OS=0x40004, fileType=0x1, subtype=0x0, date=(0, 0)),
  kids=[
    StringFileInfo([StringTable('0C0A04B0', [
      StringStruct('CompanyName', 'millachorda'),
      StringStruct('FileDescription', 'VoiceMod 2.0 - Cambiador de voz en tiempo real'),
      StringStruct('FileVersion', '{VERSION}'),
      StringStruct('InternalName', 'VoiceMod 2.0'),
      StringStruct('LegalCopyright', 'Codigo abierto - github.com/millachorda/VoiceMod-2.0'),
      StringStruct('OriginalFilename', 'VoiceMod 2.0.exe'),
      StringStruct('ProductName', 'VoiceMod 2.0'),
      StringStruct('ProductVersion', '{VERSION}')])]),
    VarFileInfo([VarStruct('Translation', [0x0C0A, 1200])])
  ]
)
"""
with open(os.path.join(ROOT, "build_tools", "file_version.txt"), "w", encoding="utf-8") as f:
    f.write(TEMPLATE)
print("file_version.txt ->", VERSION)
