; SaySense Windows installer (Inno Setup 6)
; Built by CI: ISCC.exe /DMyAppVersion=<version> packaging\installer.iss
; Expects the PyInstaller one-folder build at dist\SaySense\

#ifndef MyAppVersion
  #define MyAppVersion "dev"
#endif

[Setup]
AppId={{4FBDCD11-6B0E-49D0-B346-14C110B7CB1F}}
AppName=SaySense
AppVersion={#MyAppVersion}
AppPublisher=Casco Digital
AppPublisherURL=https://github.com/cascodigital/bananaphone_v2
DefaultDirName={autopf}\SaySense
DefaultGroupName=SaySense
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=SaySense-Setup-{#MyAppVersion}
SetupIconFile=..\assets\bananaphone.ico
UninstallDisplayIcon={app}\SaySense.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\SaySense\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\SaySense"; Filename: "{app}\SaySense.exe"
Name: "{autodesktop}\SaySense"; Filename: "{app}\SaySense.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\SaySense.exe"; Description: "Launch SaySense"; Flags: nowait postinstall skipifsilent
