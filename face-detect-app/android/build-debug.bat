@echo off
chcp 65001 >nul
echo ========================================
echo   FaceDetect Android Build
echo ========================================

setlocal enabledelayedexpansion

REM ── Paths ──────────────────────────────────
set "SCRIPT_DIR=%~dp0"
set "GRADLE_HOME=C:\Users\q1948\.gradle\wrapper\dists\gradle-8.10-bin\deqhafrv1ntovfmgh0nh3npr9\gradle-8.10"

REM Try to find ANDROID_HOME from common locations
if not defined ANDROID_HOME (
    if exist "%LOCALAPPDATA%\Android\Sdk" (
        set "ANDROID_HOME=%LOCALAPPDATA%\Android\Sdk"
    ) else if exist "C:\Android\Sdk" (
        set "ANDROID_HOME=C:\Android\Sdk"
    ) else (
        set "ANDROID_HOME=%USERPROFILE%\AppData\Local\Android\Sdk"
    )
)

set "PATH=%GRADLE_HOME%\bin;%ANDROID_HOME%\cmdline-tools\latest\bin;%ANDROID_HOME%\platform-tools;%PATH%"

echo ANDROID_HOME=%ANDROID_HOME%
echo GRADLE_HOME=%GRADLE_HOME%
echo.

REM ── Prerequisites check ───────────────────
echo Checking prerequisites...

if not exist "%GRADLE_HOME%\bin\gradle.bat" (
    echo [ERROR] Gradle not found at %GRADLE_HOME%
    echo Update GRADLE_HOME in build.bat
    pause
    exit /b 1
)
echo [OK] Gradle found

if not exist "%ANDROID_HOME%\platforms\android-34" (
    echo [ERROR] Android SDK platform 34 not found at %ANDROID_HOME%\platforms\android-34
    echo Install it via Android Studio SDK Manager
    pause
    exit /b 1
)
echo [OK] Android SDK platform 34 found

if not exist "%ANDROID_HOME%\build-tools\34.0.0" (
    echo [ERROR] Build-tools 34.0.0 not found
    pause
    exit /b 1
)
echo [OK] Build-tools 34.0.0 found

echo.
echo ========================================
echo   Building Debug APK...
echo ========================================
echo.

cd /d "%SCRIPT_DIR%"

REM Set local.properties for Gradle
echo sdk.dir=%ANDROID_HOME% > "%SCRIPT_DIR%local.properties"

"%GRADLE_HOME%\bin\gradle.bat" assembleDebug --no-daemon

echo.
echo ========================================
echo   Build Complete
echo ========================================

set "APK=%SCRIPT_DIR%app\build\outputs\apk\debug\app-debug.apk"
if exist "!APK!" (
    echo APK: !APK!
    for %%A in ("!APK!") do echo Size: %%~zA bytes
) else (
    echo APK not found at expected path
)

pause
