; BananaPhone Windows installer (Inno Setup 6)
; Built by CI: ISCC.exe /DMyAppVersion=<version> packaging\installer.iss
; Expects the PyInstaller one-folder build at dist\BananaPhone\

#ifndef MyAppVersion
  #define MyAppVersion "dev"
#endif

[Setup]
AppId={{4FBDCD11-6B0E-49D0-B346-14C110B7CB1F}}
AppName=BananaPhone
AppVersion={#MyAppVersion}
AppPublisher=Casco Digital
AppPublisherURL=https://github.com/cascodigital/bananaphone_v2
DefaultDirName={autopf}\BananaPhone
DefaultGroupName=BananaPhone
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=BananaPhone-Setup-{#MyAppVersion}
SetupIconFile=..\assets\bananaphone.ico
UninstallDisplayIcon={app}\BananaPhone.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
ArchitecturesInstallIn64BitMode=x64compatible

[Tasks]
Name: "desktopicon"; Description: "Create a &desktop icon"; GroupDescription: "Additional icons:"; Flags: unchecked

[Files]
Source: "..\dist\BananaPhone\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs

[Icons]
Name: "{group}\BananaPhone"; Filename: "{app}\BananaPhone.exe"
Name: "{autodesktop}\BananaPhone"; Filename: "{app}\BananaPhone.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\BananaPhone.exe"; Description: "Launch BananaPhone"; Flags: nowait postinstall skipifsilent
