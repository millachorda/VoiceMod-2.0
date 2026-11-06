; Instalador de VoiceMod 2.0 (Inno Setup 6).  iscc /DAppVersion=2.0.0 build_tools\installer.iss
#ifndef AppVersion
  #define AppVersion "2.0.0"
#endif
#define AppName "VoiceMod 2.0"
#define AppExe "VoiceMod 2.0.exe"

[Setup]
AppId={{6E2B7C1A-4F3D-4B8E-9A21-5C7D0F2E8B41}
AppName={#AppName}
AppVersion={#AppVersion}
AppVerName={#AppName} {#AppVersion}
AppPublisher=millachorda
AppPublisherURL=https://github.com/millachorda/VoiceMod-2.0
AppSupportURL=https://github.com/millachorda/VoiceMod-2.0/issues
AppUpdatesURL=https://github.com/millachorda/VoiceMod-2.0/releases
DefaultDirName={localappdata}\Programs\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=..\dist
OutputBaseFilename=VoiceMod-2.0-Setup
SetupIconFile=..\icono.ico
UninstallDisplayIcon={app}\{#AppExe}
UninstallDisplayName={#AppName}
WizardStyle=modern
WizardImageFile=wizard.png
WizardSmallImageFile=wizard_small.png
Compression=lzma2/ultra64
SolidCompression=yes
CloseApplications=force
RestartApplications=no
VersionInfoVersion={#AppVersion}
VersionInfoProductName={#AppName}

[Languages]
Name: "es"; MessagesFile: "compiler:Languages\Spanish.isl"

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; GroupDescription: "Accesos directos:"
Name: "startup"; Description: "Abrir VoiceMod 2.0 al iniciar Windows"; GroupDescription: "Inicio:"; Flags: unchecked

[Files]
Source: "..\dist\VoiceMod 2.0\*"; DestDir: "{app}"; Flags: recursesubdirs createallsubdirs ignoreversion

[InstallDelete]
; versiones anteriores: limpiar el programa (los datos del usuario están en %APPDATA%)
Type: filesandordirs; Name: "{app}\_internal"

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppExe}"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppExe}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Microsoft\Windows\CurrentVersion\Run"; ValueType: string; ValueName: "{#AppName}"; ValueData: """{app}\{#AppExe}"""; Flags: uninsdeletevalue; Tasks: startup

[Run]
Filename: "{app}\{#AppExe}"; Description: "Abrir {#AppName}"; Flags: nowait postinstall

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
