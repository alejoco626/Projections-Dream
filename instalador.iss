#ifndef AppVersion
  #define AppVersion "1.0.0"
#endif

[Setup]
; Este identificador NO debe cambiar nunca: es lo que permite que cada version nueva reemplace a la anterior.
AppId={{8E2B6C31-5D47-4A9B-9F13-7C0A4E6D2B58}
AppName=Proyecciones Dream
AppVersion={#AppVersion}
AppPublisher=Dream & Travel
DefaultDirName={autopf}\Projections Dream
DisableDirPage=yes
DisableProgramGroupPage=yes
PrivilegesRequired=lowest
OutputDir=Output
OutputBaseFilename=Projections_Dream_Setup
SetupIconFile=Logo_Ovalado.ico
UninstallDisplayIcon={app}\Projections_Dream.exe
Compression=lzma2
SolidCompression=yes
WizardStyle=modern
CloseApplications=yes
RestartApplications=no

[Languages]
#if FileExists(CompilerPath + "Languages\Spanish.isl")
Name: "spanish"; MessagesFile: "compiler:Languages\Spanish.isl"
#endif

[Tasks]
Name: "desktopicon"; Description: "Crear un acceso directo en el escritorio"; Flags: unchecked

[Files]
Source: "dist\Projections_Dream.exe"; DestDir: "{app}"; Flags: ignoreversion

[Icons]
Name: "{autoprograms}\Proyecciones Dream"; Filename: "{app}\Projections_Dream.exe"
Name: "{autodesktop}\Proyecciones Dream"; Filename: "{app}\Projections_Dream.exe"; Tasks: desktopicon

[InstallDelete]
; Limpia restos de versiones anteriores antes de copiar la nueva. Los datos del usuario
; viven en su carpeta personal (ProyeccionesVendedores) y nunca se tocan.
Type: files; Name: "{app}\Projections_Dream*.exe"
Type: filesandordirs; Name: "{app}\_internal"

[Run]
; Instalacion normal: pregunta si abrir el programa al terminar.
Filename: "{app}\Projections_Dream.exe"; Description: "Abrir Proyecciones Dream"; Flags: nowait postinstall skipifsilent
; Actualizacion automatica (modo silencioso): vuelve a abrir el programa sola.
Filename: "{app}\Projections_Dream.exe"; Flags: nowait skipifnotsilent

[Code]
function SetEnvironmentVariable(lpName, lpValue: String): Boolean;
  external 'SetEnvironmentVariableW@kernel32.dll stdcall';

function InitializeSetup(): Boolean;
begin
  { El programa reabierto no debe heredar la carpeta temporal del anterior (error "Failed to load Python DLL"). }
  SetEnvironmentVariable('PYINSTALLER_RESET_ENVIRONMENT', '1');
  Result := True;
end;
