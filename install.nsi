; Name of installer
Name "CuPED"

; The installer file to write.
OutFile "dist\CuPED Installer.exe"

; The default installation directory.
InstallDir "$PROGRAMFILES\CuPED"
InstallDirRegKey HKLM "Software\CuPED" "Install_Dir"

; Application privileges for Vista.
RequestExecutionLevel admin

; Use new XP-style controls when running on Windows XP.
XPStyle on

; LicenseData needs to have \r\n endlines.
LicenseData "COPYING.DOS"

; Icon to use with installer.
Icon "bin\icons\cuped\Cupedlotsofhearts.ico"
UninstallIcon "${NSISDIR}\Contrib\Graphics\Icons\orange-uninstall.ico"

; Pages

Page license
Page components
Page directory
Page instfiles

UninstPage uninstConfirm
UninstPage instfiles

Section "CuPED (core)"
    SectionIn RO

    ; Set output path to be the installation directory.
    SetOutPath $INSTDIR

    ; Files to install.
    File /r "dist\*"

    ; Save the installation path in the registry.
    WriteRegStr HKLM "SOFTWARE\CuPED" "Install_Dir" "$INSTDIR"

    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CuPED" "DisplayName" "CuPED"
    WriteRegStr HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CuPED" "UninstallString" '"$INSTDIR\uninstall.exe"'
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CuPED" "NoModify" 1
    WriteRegDWORD HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CuPED" "NoRepair" 1
    WriteUninstaller "uninstall.exe"
SectionEnd

; Optional: create Start Menu shortcuts.
Section "Start Menu Shortcuts"
    CreateDirectory "$SMPROGRAMS\CuPED"
    CreateShortCut "$SMPROGRAMS\CuPED\CuPED.lnk" "$INSTDIR\main.exe" "" "$INSTDIR\main.exe" 0
    CreateShortCut "$SMPROGRAMS\CuPED\Uninstall CuPED.lnk" "$INSTDIR\uninstall.exe" "" "$INSTDIR\uninstall.exe" 0
SectionEnd

; Uninstaller.
Section "Uninstall"
    ; Remove registry keys.
    DeleteRegKey HKLM "Software\Microsoft\Windows\CurrentVersion\Uninstall\CuPED"
    DeleteRegKey HKLM SOFTWARE\CuPED

    ; Remove files and uninstaller.
    Delete "$INSTDIR\main.exe"
    Delete "$INSTDIR\python26.dll"
    Delete "$INSTDIR\w9xpopen.exe"
    Delete "$INSTDIR\bin\win32\ffmpeg.exe"
    Delete "$INSTDIR\bin\win32\yamdi.exe"

    ; Remove start menu shortcuts, if any.
    Delete "$SMPROGRAMS\CuPED\*.*"

    ; Remove directories.
    RMDir "$SMPROGRAMS\CuPED"
    RMDir /r "$INSTDIR"
SectionEnd
