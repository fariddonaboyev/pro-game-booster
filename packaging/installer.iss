#define AppVer GetEnv("APP_VERSION")
[Setup]
AppName=PRO Game Booster
AppVersion={#AppVer}
AppPublisher=PRO
DefaultDirName={autopf}\PRO Game Booster
DefaultGroupName=PRO Game Booster
OutputDir=..\dist
OutputBaseFilename=PROGameBooster-Setup
Compression=lzma2
SolidCompression=yes
ArchitecturesInstallIn64BitMode=x64compatible
PrivilegesRequired=admin
UninstallDisplayIcon={app}\PROGameBooster.exe

[Tasks]
Name: "desktopicon"; Description: "Ish stolida yorliq"; Flags: checkedonce

[Files]
Source: "..\dist\PROGameBooster.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{group}\PRO Game Booster"; Filename: "{app}\PROGameBooster.exe"
Name: "{autodesktop}\PRO Game Booster"; Filename: "{app}\PROGameBooster.exe"; Tasks: desktopicon

[Run]
Filename: "{app}\PROGameBooster.exe"; Description: "PRO Game Booster ni ishga tushirish"; Flags: nowait postinstall skipifsilent shellexec
