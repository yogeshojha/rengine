#!/usr/bin/env bash
# Builds the extension jar with nothing but a JDK 17+.
set -euo pipefail
cd "$(dirname "$0")"

MONTOYA_VERSION="2025.5"
MONTOYA_JAR="lib/montoya-api-${MONTOYA_VERSION}.jar"
VERSION="$(sed -n 's/.*String VERSION = "\(.*\)".*/\1/p' src/main/java/io/rengine/connector/ReNgineConnector.java)"
OUT="build/rengine-connector-${VERSION}.jar"

if [ ! -f "$MONTOYA_JAR" ]; then
  mkdir -p lib
  curl -fsSL -o "$MONTOYA_JAR" \
    "https://repo1.maven.org/maven2/net/portswigger/burp/extensions/montoya-api/${MONTOYA_VERSION}/montoya-api-${MONTOYA_VERSION}.jar"
fi

rm -rf build/classes
mkdir -p build/classes
javac --release 17 -Xlint:all -cp "$MONTOYA_JAR" -d build/classes $(find src/main/java -name '*.java')
cp -r src/main/resources/META-INF build/classes/
jar --create --file "$OUT" -C build/classes .

BINARIES="../../binaries"
mkdir -p "$BINARIES"
cp "$OUT" "$BINARIES/"
echo "$OUT"
echo "binaries/$(basename "$OUT")"
