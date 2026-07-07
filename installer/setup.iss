; Inno Setup script for Zametka
; Build with Inno Setup Compiler (https://jrsoftware.org/isinfo.php)

#define MyAppName "Zametka"
#define MyAppVersion "0.2.2"
#define MyAppPublisher "Zametka Team"
#define MyAppURL "https://github.com/i000993i/Zametka-DBS"
#define MyAppExeName "Zametka.exe"

[Setup]
AppId={{B8F4A3D2-5C7E-4A1B-9F0D-2E8C6A4B3D1F}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=..\dist
OutputBaseFilename=Zametka-Setup-{#MyAppVersion}
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=lowest
DisableProgramGroupPage=no

[Languages]
Name: "russian"; MessagesFile: "compiler:Languages\Russian.isl"
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "Create a desktop shortcut"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce
Name: "startmenuicon"; Description: "Add to Start Menu"; GroupDescription: "Additional shortcuts:"; Flags: checkedonce

[Files]
Source: "..\dist\Zametka\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs
Source: "..\assets\app_icon.ico"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\{#MyAppName}\Zametka"; Filename: "{app}\{#MyAppExeName}"; Tasks: startmenuicon
Name: "{autoprograms}\{#MyAppName}\Uninstall Zametka"; Filename: "{uninstallexe}"; Tasks: startmenuicon
Name: "{autodesktop}\Zametka"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon

[Registry]
Root: HKCU; Subkey: "Software\Classes\Zametka"; ValueType: string; ValueName: ""; ValueData: "Zametka Note"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\Zametka\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.md"; ValueType: string; ValueName: ""; ValueData: "Zametka"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.md\OpenWithProgids"; ValueType: string; ValueName: "Zametka"; ValueData: ""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.markdown"; ValueType: string; ValueName: ""; ValueData: "Zametka"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.markdown\OpenWithProgids"; ValueType: string; ValueName: "Zametka"; ValueData: ""; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.mdown"; ValueType: string; ValueName: ""; ValueData: "Zametka"; Flags: uninsdeletekey
Root: HKCU; Subkey: "Software\Classes\.mdown\OpenWithProgids"; ValueType: string; ValueName: "Zametka"; ValueData: ""; Flags: uninsdeletekey

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "Launch Zametka"; Flags: postinstall nowait skipifsilent

[UninstallRun]
Filename: "{app}\{#MyAppExeName}"; Parameters: "--unregister"; Flags: runhidden
