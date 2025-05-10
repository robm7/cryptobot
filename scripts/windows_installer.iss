; Inno Setup Script for CryptoBot Windows Installer
; This script creates a professional Windows installer for CryptoBot

#define MyAppName "CryptoBot"
#define MyAppVersion "1.0.0"
#define MyAppPublisher "CryptoBot Team"
#define MyAppURL "https://cryptobot.example.com"
#define MyAppExeName "cryptobot.exe"
#define MyAppLauncherName "quick_start_launcher.exe"

[Setup]
; Basic setup information
AppId={{CRYPTOBOT-TRADING-SYSTEM}}
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
LicenseFile=..\LICENSE
OutputDir=..\dist\installer
OutputBaseFilename=cryptobot-setup
Compression=lzma
SolidCompression=yes
WizardStyle=modern
SetupIconFile=..\static\favicon.ico
UninstallDisplayIcon={app}\{#MyAppExeName}
PrivilegesRequired=admin
ArchitecturesInstallIn64BitMode=x64

; Include .NET Framework check if needed
; #include "dotnetfx.iss"

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode
Name: "startmenu"; Description: "Create Start Menu shortcuts"; GroupDescription: "{cm:AdditionalIcons}"; Flags: checked
Name: "autostart"; Description: "Start CryptoBot at system startup"; GroupDescription: "Startup options:"; Flags: unchecked

[Components]
Name: "main"; Description: "Core Application"; Types: full compact custom; Flags: fixed
Name: "strategies"; Description: "Trading Strategies"; Types: full custom
Name: "strategies\mean_reversion"; Description: "Mean Reversion Strategy"; Types: full custom
Name: "strategies\breakout"; Description: "Breakout Strategy"; Types: full custom
Name: "strategies\momentum"; Description: "Momentum Strategy"; Types: full custom
Name: "exchanges"; Description: "Exchange Connectors"; Types: full custom
Name: "exchanges\binance"; Description: "Binance Connector"; Types: full custom
Name: "exchanges\kraken"; Description: "Kraken Connector"; Types: full custom
Name: "exchanges\coinbase"; Description: "Coinbase Connector"; Types: full custom
Name: "dashboard"; Description: "Web Dashboard"; Types: full custom
Name: "backtesting"; Description: "Backtesting Module"; Types: full custom

[Files]
; Main application files
Source: "..\dist\cryptobot\*"; DestDir: "{app}"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main
Source: "..\dist\cryptobot\{#MyAppExeName}"; DestDir: "{app}"; Flags: ignoreversion; Components: main
Source: "..\dist\cryptobot\{#MyAppLauncherName}"; DestDir: "{app}"; Flags: ignoreversion; Components: main

; Strategy files
Source: "..\dist\cryptobot\strategies\mean_reversion.py*"; DestDir: "{app}\strategies"; Flags: ignoreversion; Components: strategies\mean_reversion
Source: "..\dist\cryptobot\strategies\breakout_reset.py*"; DestDir: "{app}\strategies"; Flags: ignoreversion; Components: strategies\breakout
Source: "..\dist\cryptobot\strategies\*.py*"; DestDir: "{app}\strategies"; Flags: ignoreversion; Components: strategies

; Exchange connectors
Source: "..\dist\cryptobot\exchanges\binance\*"; DestDir: "{app}\exchanges\binance"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: exchanges\binance
Source: "..\dist\cryptobot\exchanges\kraken\*"; DestDir: "{app}\exchanges\kraken"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: exchanges\kraken
Source: "..\dist\cryptobot\exchanges\coinbase\*"; DestDir: "{app}\exchanges\coinbase"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: exchanges\coinbase

; Dashboard files
Source: "..\dist\cryptobot\templates\*"; DestDir: "{app}\templates"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: dashboard
Source: "..\dist\cryptobot\static\*"; DestDir: "{app}\static"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: dashboard

; Backtesting module
Source: "..\dist\cryptobot\backtest\*"; DestDir: "{app}\backtest"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: backtesting

; Configuration files
Source: "..\config\default_config.json"; DestDir: "{app}\config"; Flags: ignoreversion; Components: main

; Documentation
Source: "..\README.md"; DestDir: "{app}"; Flags: ignoreversion isreadme; Components: main
Source: "..\docs\*"; DestDir: "{app}\docs"; Flags: ignoreversion recursesubdirs createallsubdirs; Components: main

[Icons]
; Start Menu shortcuts
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Components: main; Tasks: startmenu
Name: "{group}\{#MyAppName} Launcher"; Filename: "{app}\{#MyAppLauncherName}"; Components: main; Tasks: startmenu
Name: "{group}\Documentation"; Filename: "{app}\docs\user_guide.md"; Components: main; Tasks: startmenu
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"; Tasks: startmenu

; Desktop shortcuts
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon
Name: "{autodesktop}\{#MyAppName} Launcher"; Filename: "{app}\{#MyAppLauncherName}"; Tasks: desktopicon

; Quick Launch shortcuts
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon

; Autostart
Name: "{commonstartup}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Parameters: "--minimized"; Tasks: autostart

[Run]
; Run after installation options
Filename: "{app}\{#MyAppLauncherName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}}"; Flags: nowait postinstall skipifsilent
Filename: "{app}\docs\user_guide.md"; Description: "View Documentation"; Flags: postinstall shellexec skipifsilent

[Registry]
; Register application in Windows
Root: HKLM; Subkey: "SOFTWARE\{#MyAppName}"; Flags: uninsdeletekey
Root: HKLM; Subkey: "SOFTWARE\{#MyAppName}"; ValueType: string; ValueName: "InstallPath"; ValueData: "{app}"
Root: HKLM; Subkey: "SOFTWARE\{#MyAppName}"; ValueType: string; ValueName: "Version"; ValueData: "{#MyAppVersion}"
Root: HKLM; Subkey: "SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}_is1"; ValueType: string; ValueName: "DisplayIcon"; ValueData: "{app}\{#MyAppExeName},0"

; File associations
Root: HKCR; Subkey: ".cbt"; ValueType: string; ValueName: ""; ValueData: "CryptoBotTradeFile"; Flags: uninsdeletevalue
Root: HKCR; Subkey: "CryptoBotTradeFile"; ValueType: string; ValueName: ""; ValueData: "CryptoBot Trade File"; Flags: uninsdeletekey
Root: HKCR; Subkey: "CryptoBotTradeFile\DefaultIcon"; ValueType: string; ValueName: ""; ValueData: "{app}\{#MyAppExeName},0"
Root: HKCR; Subkey: "CryptoBotTradeFile\shell\open\command"; ValueType: string; ValueName: ""; ValueData: """{app}\{#MyAppExeName}"" ""%1"""

[Code]
// Check for prerequisites
function InitializeSetup(): Boolean;
var
  PythonInstalled: Boolean;
  ErrorCode: Integer;
begin
  // Check if Python is installed
  PythonInstalled := RegKeyExists(HKEY_LOCAL_MACHINE, 'SOFTWARE\Python\PythonCore') or 
                     RegKeyExists(HKEY_CURRENT_USER, 'SOFTWARE\Python\PythonCore');
                     
  if not PythonInstalled then
  begin
    if MsgBox('Python is required but not detected. Would you like to download and install it now?', 
              mbConfirmation, MB_YESNO) = IDYES then
    begin
      // Download and run Python installer
      if not ShellExec('open', 
                      'https://www.python.org/ftp/python/3.9.13/python-3.9.13-amd64.exe',
                      '', '', SW_SHOW, ewNoWait, ErrorCode) then
      begin
        MsgBox('Failed to launch Python installer. Please download and install Python 3.9 or later manually.', 
               mbError, MB_OK);
      end;
    end;
  end;
  
  Result := True; // Continue with setup regardless
end;

// Custom installation steps
procedure CurStepChanged(CurStep: TSetupStep);
var
  ResultCode: Integer;
begin
  if CurStep = ssPostInstall then
  begin
    // Create data directory
    CreateDir(ExpandConstant('{userappdata}\{#MyAppName}\data'));
    
    // Copy default configuration if it doesn't exist
    if not FileExists(ExpandConstant('{userappdata}\{#MyAppName}\config.json')) then
      FileCopy(ExpandConstant('{app}\config\default_config.json'), 
               ExpandConstant('{userappdata}\{#MyAppName}\config.json'), False);
               
    // Run post-installation script if it exists
    if FileExists(ExpandConstant('{app}\scripts\post_install.bat')) then
      Exec(ExpandConstant('{app}\scripts\post_install.bat'), '', '', SW_HIDE, ewWaitUntilTerminated, ResultCode);
  end;
end;

// Handle uninstallation
procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
var
  KeepUserData: Boolean;
begin
  if CurUninstallStep = usUninstall then
  begin
    KeepUserData := MsgBox('Would you like to keep your user data and configuration files?', 
                           mbConfirmation, MB_YESNO) = IDYES;
    if not KeepUserData then
      DelTree(ExpandConstant('{userappdata}\{#MyAppName}'), True, True, True);
  end;
end;