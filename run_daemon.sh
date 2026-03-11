#!/bin/bash
# Usage: ./run_daemon.sh [dirHost] [dirPort] [sharedFolder] [myHost] [daemonPort]
# Defaults: localhost 1099 ./shared auto-detect 6000
# Example: ./run_daemon.sh 192.168.1.100 1099 ./shared 192.168.1.10 6000
java -cp build Daemon "$@"
