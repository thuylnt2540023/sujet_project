#!/bin/bash
set -e
mkdir -p build
javac -d build src/*.java
echo "Compiled successfully. Classes in build/"
