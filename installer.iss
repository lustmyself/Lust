; Lust Installer Script for Inno Setup
; This creates a proper Windows installer that registers the app

#define MyAppName "Lust"
#define MyAppVersion "1.4.9.69"
#define MyAppVersionInfo "1.4.9.69"
#define MyAppPublisher "Lust Team"
#define MyAppURL "https://github.com/lustmyself/Lust"
#define MyAppExeName "Lust.exe"
#define MyAppDescription "Effortless skin changer for League of Legends"
; Must match config.SINGLE_INSTANCE_MUTEX_NAME (used by the app to enforce single-instance)
#define MyAppMutex "Local\LustSingleInstance"

[Setup]
; NOTE: The value of AppId uniquely identifies this application.
; Do not use the same AppId value in installers for other applications.
AppId={{18B5D16F-154B-43C8-A6DF-21CB903DE869}}
UsePreviousAppDir=no
AppName={#MyAppName}
AppVersion={#MyAppVersion}
AppVerName={#MyAppName} {#MyAppVersion}
AppPublisher={#MyAppPublisher}
AppPublisherURL={#MyAppURL}
AppSupportURL={#MyAppURL}
AppUpdatesURL={#MyAppURL}
DefaultDirName={autopf}\{#MyAppName}
DefaultGroupName={#MyAppName}
AllowNoIcons=yes
OutputDir=installer
OutputBaseFilename=Lust_Setup_{#MyAppVersion}
SetupIconFile=assets\icon.ico
Compression=lzma
SolidCompression=yes
WizardStyle=modern
PrivilegesRequired=admin
ArchitecturesAllowed=x64
ArchitecturesInstallIn64BitMode=x64
UninstallDisplayName={#MyAppName}
UninstallDisplayIcon={app}\{#MyAppExeName}
VersionInfoVersion={#MyAppVersionInfo}
VersionInfoCompany={#MyAppPublisher}
VersionInfoDescription={#MyAppDescription}
VersionInfoProductName={#MyAppName}
; Prevent install/uninstall while Lust is running (mutex is created by the running app)
AppMutex={#MyAppMutex}

[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon"; Description: "{cm:CreateDesktopIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked
Name: "quicklaunchicon"; Description: "{cm:CreateQuickLaunchIcon}"; GroupDescription: "{cm:AdditionalIcons}"; Flags: unchecked; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; Main application files
; hashes.game.txt is user-managed and must be preserved across installations.
Source: "dist\Lust\*"; DestDir: "{app}"; Excludes: "injection\tools\hashes.game.txt"; Flags: ignoreversion recursesubdirs createallsubdirs
; NOTE: Don't use "Flags: ignoreversion" on any shared system files

[Icons]
Name: "{group}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; IconFilename: "{app}\icon.ico"
Name: "{group}\{cm:UninstallProgram,{#MyAppName}}"; Filename: "{uninstallexe}"
Name: "{autodesktop}\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: desktopicon; IconFilename: "{app}\icon.ico"
Name: "{userappdata}\Microsoft\Internet Explorer\Quick Launch\{#MyAppName}"; Filename: "{app}\{#MyAppExeName}"; Tasks: quicklaunchicon; IconFilename: "{app}\icon.ico"

[Run]
Filename: "{app}\{#MyAppExeName}"; Description: "{cm:LaunchProgram,{#StringChange(MyAppName, '&', '&&')}} (as Administrator)"; Flags: nowait postinstall skipifsilent shellexec; Verb: runas

[UninstallRun]
; Uninstall Pengu Loader (removes its IFEO activation and disables the native hook)
Filename: "{app}\_internal\Pengu Loader\Pengu Loader.exe"; Parameters: "--uninstall --silent"; Flags: runhidden waituntilterminated skipifdoesntexist
; Always remove the Lust auto-start scheduled task (created via schtasks /TN "Lust")
Filename: "{sys}\schtasks.exe"; Parameters: "/Delete /TN Lust /F"; Flags: runhidden

[UninstallDelete]
Type: filesandordirs; Name: "{app}\_internal"
Type: filesandordirs; Name: "{app}\injection\overlay"
Type: filesandordirs; Name: "{app}\injection\mods"
; Remove user data stored in AppData
; Lust stores user data in %LOCALAPPDATA%\Lust
Type: filesandordirs; Name: "{localappdata}\Lust"
; Note: State files are now stored in user data directory, not in app directory

[Code]
function _IsLeagueRunning(): Boolean;
var
  WbemLocator, WMIService, Processes: Variant;
begin
  Result := False;
  try
    WbemLocator := CreateOleObject('WbemScripting.SWbemLocator');
    WMIService := WbemLocator.ConnectServer('localhost', 'root\CIMV2');
    Processes := WMIService.ExecQuery(
      'SELECT Name FROM Win32_Process WHERE ' +
      'Name="LeagueClient.exe" OR ' +
      'Name="LeagueClientUx.exe" OR ' +
      'Name="LeagueClientUxRender.exe" OR ' +
      'Name="League of Legends.exe"'
    );
    Result := (Processes.Count > 0);
  except
    { If WMI fails, don't block the uninstall }
    Result := False;
  end;
end;

function InitializeUninstall(): Boolean;
var
  LustRunning: Boolean;
  LeagueRunning: Boolean;
begin
  LustRunning := CheckForMutexes('{#MyAppMutex}');
  LeagueRunning := _IsLeagueRunning();

  if LustRunning and LeagueRunning then
  begin
    MsgBox(
      '{#MyAppName} and League of Legends are both currently running.'#13#10 +
      'Please close both applications and try uninstalling again.',
      mbCriticalError,
      MB_OK
    );
    Result := False;
    exit;
  end;

  if LustRunning then
  begin
    MsgBox(
      '{#MyAppName} is currently running.'#13#10 +
      'Please close it completely (including the tray) and try uninstalling again.',
      mbCriticalError,
      MB_OK
    );
    Result := False;
    exit;
  end;

  if LeagueRunning then
  begin
    MsgBox(
      'League of Legends is currently running.'#13#10 +
      'Please close League of Legends and try uninstalling again.',
      mbCriticalError,
      MB_OK
    );
    Result := False;
    exit;
  end;

  Result := True;
end;

function _ContainsTextLower(const Haystack: string; const NeedleLower: string): Boolean;
begin
  Result := Pos(NeedleLower, LowerCase(Haystack)) > 0;
end;

procedure _DeleteStartupValuesIfMatch(const RootKey: Integer; const SubKey: string);
var
  Names: TArrayOfString;
  I: Integer;
  Val: string;
  ValLower: string;
begin
  if not RegGetValueNames(RootKey, SubKey, Names) then
    exit;

  for I := 0 to GetArrayLength(Names) - 1 do
  begin
    if RegQueryStringValue(RootKey, SubKey, Names[I], Val) then
    begin
      ValLower := LowerCase(Val);

      { Remove legacy/broken startup entries that invoke rundll32 on Pengu Loader core.dll.
        This is what produces the RunDLL "module not found" dialog after uninstall. }
      if (_ContainsTextLower(ValLower, 'rundll32') and _ContainsTextLower(ValLower, 'pengu loader\core.dll')) or
         _ContainsTextLower(ValLower, '\lust\_internal\pengu loader\core.dll') then
      begin
        RegDeleteValue(RootKey, SubKey, Names[I]);
      end;
    end;
  end;
end;

const
  RunKey      = 'Software\Microsoft\Windows\CurrentVersion\Run';
  RunOnceKey  = 'Software\Microsoft\Windows\CurrentVersion\RunOnce';
  RunKey6432  = 'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\Run';
  RunOnce6432 = 'Software\WOW6432Node\Microsoft\Windows\CurrentVersion\RunOnce';

procedure _CleanupStartupRegistry();
begin
  { 64-bit and user/machine startup keys }
  _DeleteStartupValuesIfMatch(HKCU, RunKey);
  _DeleteStartupValuesIfMatch(HKLM, RunKey);
  _DeleteStartupValuesIfMatch(HKCU, RunOnceKey);
  _DeleteStartupValuesIfMatch(HKLM, RunOnceKey);

  { 32-bit view keys (defensive) }
  _DeleteStartupValuesIfMatch(HKCU, RunKey6432);
  _DeleteStartupValuesIfMatch(HKLM, RunKey6432);
  _DeleteStartupValuesIfMatch(HKCU, RunOnce6432);
  _DeleteStartupValuesIfMatch(HKLM, RunOnce6432);
end;

const
  IfeoKey = 'SOFTWARE\Microsoft\Windows NT\CurrentVersion\Image File Execution Options\LeagueClientUx.exe';

{ Pengu hooks the client with an IFEO debugger: rundll32 "<dir>\core.dll", #6000.
  If that core.dll is gone (Lust uninstalled or moved), Windows shows a RunDLL
  "module not found" error on every League start, so remove the dead entry.
  A working Pengu install elsewhere keeps its key. }
procedure _RemoveDeadPenguIfeo();
var
  Debugger: string;
  StartPos: Integer;
  Rest: string;
  EndPos: Integer;
  DllPath: string;
begin
  if not RegQueryStringValue(HKLM, IfeoKey, 'Debugger', Debugger) then
    exit;
  if not _ContainsTextLower(Debugger, 'core.dll') then
    exit;

  DllPath := '';
  StartPos := Pos('"', Debugger);
  if StartPos > 0 then
  begin
    Rest := Copy(Debugger, StartPos + 1, Length(Debugger));
    EndPos := Pos('"', Rest);
    if EndPos > 0 then
      DllPath := Copy(Rest, 1, EndPos - 1);
  end;

  if (DllPath = '') or not FileExists(DllPath) then
    RegDeleteKeyIncludingSubkeys(HKLM, IfeoKey);
end;

const
  LegacyUninstallKey = 'SOFTWARE\Microsoft\Windows\CurrentVersion\Uninstall\{#MyAppName}';

procedure _CleanupLegacyUninstallEntry();
var
  InstallLocation: string;
  DisplayName: string;
  Publisher: string;
begin
  { Inno owns the AppId-based Apps entry. Remove only our duplicate from older
    installers, and only when it belongs to this installation. }
  if RegQueryStringValue(HKLM, LegacyUninstallKey, 'InstallLocation', InstallLocation) and
     RegQueryStringValue(HKLM, LegacyUninstallKey, 'DisplayName', DisplayName) and
     RegQueryStringValue(HKLM, LegacyUninstallKey, 'Publisher', Publisher) and
     (CompareText(AddBackslash(InstallLocation), AddBackslash(ExpandConstant('{app}'))) = 0) and
     (DisplayName = '{#MyAppName}') and (Publisher = '{#MyAppPublisher}') then
  begin
    RegDeleteKeyIncludingSubkeys(HKLM, LegacyUninstallKey);
  end;
end;

procedure _DeleteLocalAppDataLust();
begin
  { Ensure user data is removed before running external cleanup }
  DelTree(ExpandConstant('{localappdata}\Lust'), True, True, True);
end;

procedure CurUninstallStepChanged(CurUninstallStep: TUninstallStep);
begin
  if CurUninstallStep = usUninstall then
  begin
    _CleanupStartupRegistry();
    _CleanupLegacyUninstallEntry();
  end;

  if CurUninstallStep = usPostUninstall then
  begin
    _DeleteLocalAppDataLust();
    { Remove the entire install directory (Program Files\Lust) in case
      runtime-generated files (logs, caches, etc.) were left behind. }
    DelTree(ExpandConstant('{app}'), True, True, True);
    { Safety net if Pengu's own --uninstall could not run }
    _RemoveDeadPenguIfeo();
  end;
end;

procedure CurStepChanged(CurStep: TSetupStep);
begin
  if CurStep = ssPostInstall then
  begin
    { Clean up a dead hook left by an older Lust uninstall }
    _RemoveDeadPenguIfeo();

    { Inno writes the Apps entry itself: drop the duplicate older installers wrote }
    _CleanupLegacyUninstallEntry();
  end;
end;
