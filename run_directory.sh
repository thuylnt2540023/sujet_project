#!/bin/bash
# Usage: ./run_directory.sh [rmiPort] [myHost]
# Defaults: 1099 auto-detect
# Example: ./run_directory.sh 1099 192.168.1.100
PORT=${1:-1099}
HOST=${2:-$(hostname -I 2>/dev/null | awk '{print $1}')}
echo "Starting Directory on $HOST:$PORT"
java -cp build -Djava.rmi.server.hostname=$HOST Directory $PORT $HOST
