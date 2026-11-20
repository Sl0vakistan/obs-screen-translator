; Inno Setup script. Run through build.ps1, which passes /DAppVersion and builds dist\OBS Screen Translator\ first.
#define AppName "OBS Screen Translator"
#ifndef AppVersion
  #define AppVersion "0.0.0"
#endif

[Setup]
AppId={{8F2C6C4E-3D1B-4E7A-9A51-6B7D0C2E4F19}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisher=OBS Screen Translator contributors
DefaultDirName={autopf}\{#AppName}
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
ArchitecturesAllowed=x64compatible
ArchitecturesInstallIn64BitMode=x64compatible
LicenseFile=LICENSE
OutputDir=dist
OutputBaseFilename=OBS-Screen-Translator-Setup-{#AppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayName={#AppName}

[Languages]
Name: "en"; MessagesFile: "compiler:Default.isl"
Name: "sk"; MessagesFile: "compiler:Languages\Slovak.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked

[Files]
Source: "dist\{#AppName}\*"; DestDir: "{app}"; Flags: recursesubdirs ignoreversion
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "README.sk.md"; DestDir: "{app}"; Flags: ignoreversion
Source: "LICENSE"; DestDir: "{app}"; Flags: ignoreversion
Source: "THIRD_PARTY_NOTICES.md"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#AppName}"; Filename: "{app}\{#AppName}.exe"
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\{#AppName}.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\{#AppName}.exe"; Description: "{cm:LaunchProgram,{#AppName}}"; Flags: nowait postinstall skipifsilent
