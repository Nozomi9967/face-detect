#!/bin/bash

# Build script for FaceDetect Android app
# Prerequisites: Android SDK with build-tools 34, Java 11+

set -e

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
GRADLE_HOME="/c/Users/q1948/.gradle/wrapper/dists/gradle-8.10-bin/deqhafrv1ntovfmgh0nh3npr9/gradle-8.10"
ANDROID_HOME="${ANDROID_HOME:-/c/Users/q1948/AppData/Local/Android/Sdk}"

export ANDROID_HOME
export PATH="$GRADLE_HOME/bin:$ANDROID_HOME/cmdline-tools/latest/bin:$ANDROID_HOME/platform-tools:$PATH"

echo "=== FaceDetect Android Build ==="
echo "ANDROID_HOME=$ANDROID_HOME"

# Verify prerequisites
echo ""
echo "Checking prerequisites..."

if [ ! -x "$GRADLE_HOME/bin/gradle" ]; then
    echo "ERROR: Gradle 8.10 not found at $GRADLE_HOME"
    echo "Please install Gradle 8.10 or update GRADLE_HOME in this script."
    exit 1
fi
echo "[OK] Gradle 8.10 found"

if [ ! -d "$ANDROID_HOME/platforms/android-34" ]; then
    echo "ERROR: Android SDK platform 34 not found at $ANDROID_HOME/platforms/android-34"
    echo "Please install Android SDK Platform 34 via Android Studio SDK Manager."
    exit 1
fi
echo "[OK] Android SDK platform 34 found"

if [ ! -d "$ANDROID_HOME/build-tools/34.0.0" ]; then
    echo "ERROR: Android build-tools 34.0.0 not found"
    echo "Please install via Android Studio SDK Manager."
    exit 1
fi
echo "[OK] Build-tools 34.0.0 found"

# Verify Java
if ! java -version 2>&1 | grep -q 'version "1[1-9]'; then
    echo "WARNING: Java 11+ recommended. Current version:"
    java -version 2>&1 || true
fi

echo ""
echo "=== Building Debug APK ==="
cd "$SCRIPT_DIR"

"$GRADLE_HOME/bin/gradle" assembleDebug

echo ""
echo "=== Build Complete ==="
APK_PATH="$SCRIPT_DIR/app/build/outputs/apk/debug/app-debug.apk"
if [ -f "$APK_PATH" ]; then
    echo "APK: $APK_PATH"
    echo "Size: $(du -h "$APK_PATH" | cut -f1)"
else
    echo "WARNING: APK not found at expected path"
fi
