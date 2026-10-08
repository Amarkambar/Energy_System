; ============================================================
;  Energy Diagnostics System — Inno Setup Script
;  Builds: EnergyDiagnostics_Setup.exe
;  Run: "C:\Program Files\Inno Setup 7\ISCC.exe" installer\setup.iss
; ============================================================

#define AppName      "Energy Diagnostics System"
#define AppVersion   "1.0.0"
#define AppPublisher "Amarkambar"
#define AppURL       "https://github.com/Amarkambar/Energy_System"
#define AppExeName   "Launch_EnergyDiagnostics.bat"
#define AppIcon      "installer\app_icon.ico"
#define WizardBanner "installer\wizard_banner.bmp"

[Setup]
AppId={{7A3F2E1B-4C8D-4A2F-9E6B-1234567890AB}
AppName={#AppName}
AppVersion={#AppVersion}
AppPublisherURL={#AppURL}
AppSupportURL={#AppURL}
AppUpdatesURL={#AppURL}
DefaultDirName={autopf}\EnergyDiagnostics
DefaultGroupName={#AppName}
AllowNoIcons=yes
; SourceDir = project root (parent of installer/)
; All Source: paths in [Files] are relative to SourceDir
SourceDir=..
OutputDir=installer\dist
OutputBaseFilename=EnergyDiagnostics_Setup_v{#AppVersion}
; Compression
Compression=lzma2/max
SolidCompression=yes
; Appearance
WizardStyle=modern
WizardImageFile=installer\wizard_banner.bmp
SetupIconFile=installer\app_icon.ico
; Requires admin for Program Files
PrivilegesRequired=admin
; Min Windows 10
MinVersion=10.0



[Languages]
Name: "english"; MessagesFile: "compiler:Default.isl"

[Tasks]
Name: "desktopicon";    Description: "Create a &desktop shortcut";    GroupDescription: "Additional icons:"
Name: "quicklaunchicon"; Description: "Create a &Quick Launch shortcut"; GroupDescription: "Additional icons:"; OnlyBelowVersion: 6.1; Check: not IsAdminInstallMode

[Files]
; ── Backend (Python code) ─────────────────────────────────────────────────
Source: "backend\*"; DestDir: "{app}\backend"; Flags: ignoreversion recursesubdirs createallsubdirs; \
  Excludes: "*.pyc,__pycache__,venv,.env,data\cache,data\real,models\saved"

; ── Frontend (built React app — served by FastAPI as static files) ────────
Source: "frontend\dist\*"; DestDir: "{app}\backend\static"; Flags: ignoreversion recursesubdirs createallsubdirs

; ── Launcher script ───────────────────────────────────────────────────────
Source: "installer\Launch_EnergyDiagnostics.bat"; DestDir: "{app}"; Flags: ignoreversion

; ── README ───────────────────────────────────────────────────────────────
Source: "README.md"; DestDir: "{app}"; Flags: ignoreversion

; ── Dataset ──────────────────────────────────────────────────────────────
Source: "data\energy_pattern_dataset_4.csv"; DestDir: "{app}\backend\data"; Flags: ignoreversion

[Icons]
; Start Menu
Name: "{group}\{#AppName}";      Filename: "{app}\Launch_EnergyDiagnostics.bat"; IconFilename: "{app}\backend\static\favicon.ico"; Comment: "Launch Energy Diagnostics System"
Name: "{group}\Uninstall {#AppName}"; Filename: "{uninstallexe}"

; Desktop shortcut
Name: "{autodesktop}\{#AppName}"; Filename: "{app}\Launch_EnergyDiagnostics.bat"; IconFilename: "{app}\backend\static\favicon.ico"; Tasks: desktopicon

[Run]
; Open the app after install
Filename: "{app}\Launch_EnergyDiagnostics.bat"; Description: "Launch Energy Diagnostics now"; Flags: postinstall nowait skipifsilent shellexec

[UninstallDelete]
Type: filesandordirs; Name: "{app}\backend\.installed"
Type: filesandordirs; Name: "{app}\backend\data\cache"

[Code]
// Check if Python 3.10+ is installed on the system
function IsPythonInstalled(): Boolean;
var
  PythonPath: String;
begin
  Result := RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.10\InstallPath', '', PythonPath) or
            RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.11\InstallPath', '', PythonPath) or
            RegQueryStringValue(HKLM, 'SOFTWARE\Python\PythonCore\3.12\InstallPath', '', PythonPath);
end;

procedure InitializeWizard();
begin
  if not IsPythonInstalled() then
    MsgBox('Python 3.10 or higher is required but was not detected.' + #13#10 +
           'Please download and install Python from https://www.python.org' + #13#10 +
           'Then re-run this installer.', mbInformation, MB_OK);
end;
