#!/usr/bin/env bash
# Compiles the extension and the harnesses and runs the offline checks.
set -euo pipefail
cd "$(dirname "$0")"
MONTOYA_JAR="$(./build.sh --fetch-only)"
rm -rf build/classes build/test-classes
mkdir -p build/classes build/test-classes
javac --release 17 -Xlint:all -Werror -cp "$MONTOYA_JAR" -d build/classes $(find src/main/java -name '*.java')
javac --release 17 -Xlint:all -Werror -cp "$MONTOYA_JAR:build/classes" -d build/test-classes $(find src/test/java -name '*.java')
java -cp "$MONTOYA_JAR:build/classes:build/test-classes" io.rengine.connector.ActionsHarness
