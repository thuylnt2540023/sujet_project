#!/bin/bash
# Usage: ./run_download.sh <filename> [dirHost] [dirPort] [outputFolder] [myHost] [compress] [fragmentKB]
# Defaults:                             localhost 1099    ./shared       auto     false     512
# Example: ./run_download.sh movie.mp4 192.168.1.100 1099 ./output 192.168.1.20 true 256
if [ -z "$1" ]; then
    echo "Usage: $0 <filename> [dirHost] [dirPort] [outputFolder] [myHost] [compress] [fragmentKB]"
    exit 1
fi
java -cp build Download "$@"
