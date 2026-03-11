# SongSong Project

Parallel Download Infrastructure for Large Files — A distributed system that enables downloading files in parallel from multiple sources.

## Features

### 1. Parallel Download

File is split into fragments (default 512 KB, configurable). Each source (Daemon) is assigned a worker thread. All workers pull fragments from a shared queue concurrently — faster sources automatically handle more fragments.

### 2. Load Balancing

Directory tracks the number of active fragment transfers on each Daemon (`load` counter). When Download requests sources, Directory returns them **sorted by load ascending** — least busy Daemon is prioritized. Daemon calls `incrementLoad` when it starts serving a fragment and `decrementLoad` when done.

### 3. Heartbeat & Dead Client Detection

Each Daemon sends a heartbeat to Directory every **5 seconds** via RMI. Directory runs a background cleaner thread every 10 seconds: if a Daemon has not sent a heartbeat for **15 seconds**, it is considered dead and removed from the registry. This handles both graceful shutdown (`Ctrl+C` triggers `unregister()`) and unexpected crashes (heartbeat timeout).

### 4. Dynamic File List Update

On each heartbeat, Daemon rescans its shared folder. If new files are detected (e.g., a file just downloaded by another Download process on the same machine), the updated file list is sent to Directory. This means a client that just finished downloading a file **automatically becomes a source** for other clients.

### 5. Failure Handling & Retry

If a source fails mid-transfer, the fragment is put back into the shared queue for another worker (different source) to pick up. Each fragment is retried up to **3 times**. After all initial workers finish, if fragments remain, Download fetches a **fresh source list** from Directory and launches a second wave of workers.

### 6. Data Compression

When enabled, Daemon compresses each fragment with GZIP before sending. Compression is **conditional**: if the compressed size is not smaller than the original, raw data is sent instead. Download automatically decompresses when needed. Effective for text-based files; minimal benefit for already-compressed files (mp4, zip, jpg).

### 7. Logging & Statistics

Each component writes logs to `logs/` directory with host and port in the filename:

| Component | Log file |
|-----------|----------|
| Directory | `logs/directory-{host}-{port}.log` |
| Daemon    | `logs/daemon-{host}-{port}.log` |
| Download  | `logs/download-{host}-{filename}.log` |

**Daemon log** records per-fragment serve stats:
```
[SERVE] GET_FRAGMENT client=/10.0.0.5:54321 file=test.bin offset=0 len=524288 compressed=false sent_bytes=524288 time_ms=15 speed_KB/s=34132
```

**Download log** records per-fragment download stats and a summary:
```
[FRAG] idx=0 offset=0 len=262144 source=10.0.0.1:6000 time_ms=120 speed_KB/s=2133 progress=5%
...
[SUMMARY] file_size=10485760 fragment_size=262144 total_time_ms=2500 avg_speed_KB/s=4096
[SUMMARY] source=10.0.0.1:6000 fragments=12 bytes=6291456 time_ms=1500 speed_KB/s=4096
[SUMMARY] source=10.0.0.2:6001 fragments=8  bytes=4194304 time_ms=1200 speed_KB/s=3413
```

Use these logs to compare performance across different fragment sizes and number of sources.

### 8. Security

Path traversal protection: Daemon validates that requested filenames resolve within the shared folder only.

---

## Architecture

```
                    Directory (RMI Server)
                    ┌──────────────────────┐
         ┌────────►│ - File registry       │◄────────┐
         │   RMI   │ - Client registry     │  RMI    │
         │         │ - Load tracking       │         │
         │         │ - Heartbeat monitor   │         │
         │         └───────────────────────┘         │
         │              ▲         │                  │
         │          RMI │         │ RMI              │
         │              │         ▼                  │
    Daemon A          Daemon B                    Daemon C
    (TCP:6000)        (TCP:6001)                 (TCP:6002)
         ▲                ▲                          ▲
         │    TCP Socket  │                          │
         └────────────────┼──────────────────────────┘
                          │
                      Download
                  (parallel fragments)
```

**Communication:**
- Daemon ↔ Directory: **RMI** (register, heartbeat, load tracking)
- Download → Directory: **RMI** (get sources for file)
- Download → Daemon: **TCP Socket** (get file size, get fragment)

---

## How to Run

### Prerequisites

- Java 17 (JDK)
- Linux (tested on Ubuntu/WSL)

### Compile

```bash
cd /path/to/sujet_project
bash compile.sh
```

### Step 1 — Start Directory

On the directory machine:

```bash
./run_directory.sh [rmiPort] [myHost]
```

| Parameter | Default | Description |
|-----------|---------|-------------|
| rmiPort   | 1099    | RMI registry port |
| myHost    | auto    | IP of this machine |

Example:
```bash
./run_directory.sh 1099 172.20.242.201
```

### Step 2 — Start Daemon(s)

On each machine that shares files:

```bash
./run_daemon.sh [dirHost] [dirPort] [sharedFolder] [myHost] [daemonPort]
```

| Parameter    | Default     | Description |
|-------------|-------------|-------------|
| dirHost     | localhost   | IP of the Directory machine |
| dirPort     | 1099        | RMI port of Directory |
| sharedFolder| ./shared    | Folder containing files to share |
| myHost      | auto        | IP of this machine (important for cross-machine) |
| daemonPort  | 6000        | TCP port for serving fragments |

Examples:
```bash
# Single machine test — 3 Daemons with different ports and folders
./run_daemon.sh localhost 1099 ./shared1 localhost 6000
./run_daemon.sh localhost 1099 ./shared2 localhost 6001
./run_daemon.sh localhost 1099 ./shared3 localhost 6002

# Cross-machine — Directory at 172.20.242.201
./run_daemon.sh 172.20.242.201 1099 ./shared 192.168.1.10 6000
```

### Step 3 — Download a File

On the machine that wants to download:

```bash
./run_download.sh <filename> [dirHost] [dirPort] [outputFolder] [myHost] [compress] [fragmentKB]
```

| Parameter   | Default   | Description |
|-------------|-----------|-------------|
| filename    | *required*| Name of file to download |
| dirHost     | localhost | IP of the Directory machine |
| dirPort     | 1099      | RMI port of Directory |
| outputFolder| ./shared  | Output directory (default = shared folder, so file auto-registered) |
| myHost      | auto      | IP of this machine (for log filename) |
| compress    | false     | Enable GZIP compression (true/false) |
| fragmentKB  | 512       | Fragment size in KB |

Examples:
```bash
# Basic download
./run_download.sh movie.mp4 172.20.242.201 1099 ./output 172.20.242.201

# With compression and 256KB fragments
./run_download.sh movie.mp4 172.20.242.201 1099 ./output 172.20.242.201 true 256

# Save to shared folder (auto-becomes source for others)
./run_download.sh movie.mp4 172.20.242.201 1099 ./shared 172.20.242.201 false 512
```

### Shutdown

Press `Ctrl+C` to stop any component. Recommended order: **Download → Daemon → Directory**.

- `Ctrl+C` on Daemon: triggers shutdown hook → calls `unregister()` → Directory removes it immediately
- If Daemon crashes without `Ctrl+C`: Directory detects via heartbeat timeout after 15 seconds

---

## Full Example — Single Machine Test

```bash
# Terminal 1: Directory
./run_directory.sh

# Terminal 2: Create test file + start Daemon 1
mkdir -p shared1
dd if=/dev/urandom of=shared1/testfile.bin bs=1M count=50
./run_daemon.sh localhost 1099 ./shared1 localhost 6000

# Terminal 3: Copy same file + start Daemon 2
mkdir -p shared2
cp shared1/testfile.bin shared2/
./run_daemon.sh localhost 1099 ./shared2 localhost 6001

# Terminal 4: Download (parallel from 2 sources)
mkdir -p output
./run_download.sh testfile.bin localhost 1099 ./output localhost false 256
```

## Performance Testing

Run downloads with different fragment sizes to find the optimal value:

```bash
./run_download.sh testfile.bin localhost 1099 ./output1 localhost false 64
./run_download.sh testfile.bin localhost 1099 ./output2 localhost false 128
./run_download.sh testfile.bin localhost 1099 ./output3 localhost false 256
./run_download.sh testfile.bin localhost 1099 ./output4 localhost false 512
./run_download.sh testfile.bin localhost 1099 ./output5 localhost false 1024
```

Compare the `[SUMMARY]` lines in `logs/download-*.log` to find the best fragment size.

To measure the effect of number of sources, run with 1, 2, 3 Daemons and compare total download times.
