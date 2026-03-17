# Song Song — Parallel P2P Download Infrastructure

<div align="center">

**Master 1 · System Architecture · USTH · 2025–2026**

| Student ID | Name                   | Email                            |
| :--------: | :--------------------- | :------------------------------- |
|  2540008   | Nguyễn Phong Châu      | chaunp.2540008@usth.edu.vn       |
|  2540023   | Lê Nghiêm Thanh Thủy   | thuylnt.2540023@usth.edu.vn      |

</div>

---

## 1. Architecture

The system follows a **three-tier architecture** inspired by the BitTorrent model, implemented entirely in Java without any third-party networking library.

```
                  ┌─────────────────────────────────┐
                  │      Directory  (RMI :1099)      │
                  │  · file → Daemon registry        │
                  │  · per-Daemon load counters      │
                  │  · heartbeat & timeout sweep     │
                  └──┬──────────────────────────┬───┘
                     │                          │
          RMI: register / unregister /    RMI: getSourcesForFile
          heartbeat(5s) / ±load           returns sources sorted
                     │                    by load asc.
         ┌───────────┴───────────┐             │
         │                       │             │
 ┌───────▼───────┐   ┌───────────▼───────┐     │
 │   Daemon A    │   │     Daemon B      │  ···│···
 │  TCP :6000    │   │    TCP :6001      │     │
 │  ./shared1/   │   │    ./shared2/     │     │
 └───────┬───────┘   └───────────┬───────┘     │
         │                       │             │
         │   TCP: GET_SIZE /     │             │
         │   GET_FRAGMENT        │    ┌────────▼────────┐
         └───────────────────────┴───►│    Download     │
                                      │  (N workers,    │
                                      │  shared queue)  │
                                      └─────────────────┘
```

| Channel | Protocol | Calls |
|:---:|:---:|---|
| Daemon → Directory | Java RMI | `register`, `unregister`, `heartbeat(fileList)`, `incrementLoad`, `decrementLoad` |
| Download → Directory | Java RMI | `getSourcesForFile` — returns `List<ClientInfo>` sorted by `load` asc. |
| Download → Daemon | Raw TCP (binary) | `GET_SIZE (0x00)`, `GET_FRAGMENT (0x01)` |

The Directory is backed by two `ConcurrentHashMap`s: `fileToClients` (filename → set of Daemon IDs) and `clients` (Daemon ID → `ClientInfo`). Mutations are `synchronized` to prevent races under concurrent registrations and sweeps.

---

## 2. Core Algorithm — Parallel Download

### 2.1 Work-Stealing Fragment Queue

All parallelism is driven by a single `ConcurrentLinkedQueue<Integer>` shared across worker threads:

1. File size is queried from any live Daemon via TCP.
2. The file is partitioned into fragments of size $S$ (default 512 KB). Fragment $i$ spans bytes $[i \cdot S,\ \min((i+1)\cdot S,\ F))$ where $F$ is the file length.
3. All fragment indices $0 \ldots N-1$ are enqueued.
4. **One thread per Daemon** is launched. Each loops: `poll()` → download fragment → `raf.seek(offset); raf.write(data)` → repeat until empty.

Faster Daemons naturally drain more of the queue; no explicit central scheduler is needed. The output file is pre-allocated with `RandomAccessFile.setLength(fileSize)` to allow fully concurrent, out-of-order writes without locking beyond the `seek+write` pair.

### 2.2 Binary TCP Fragment Protocol

```
Request:   [ cmd:byte | filename:UTF | offset:long | length:int | compress:boolean ]
Response:  [ status:int | compressed:boolean | dataLen:int | data:bytes ]
```

Two commands are defined: `GET_SIZE (0x00)` and `GET_FRAGMENT (0x01)`. The `status` field lets the Daemon signal errors (`-1` file not found, `-2` bad offset) without closing the connection abruptly.

### 2.3 Two-Wave Fault Tolerance

On any fragment exception, the index is re-queued (up to `MAX_RETRIES = 3`). After all wave-1 workers join, if the queue is still non-empty, a **wave 2** begins: Download calls `getSourcesForFile` again — picking up any Daemons that came online mid-transfer — and launches a fresh worker set. This covers both transient failures and late-joining peers.

---

## 3. Enhancements

### 3.1 Heartbeat & Automatic Re-registration

Each Daemon sends a heartbeat every **5 s** via RMI, piggybacking its file list only when the list has changed (delta update). The Directory's sweeper thread runs every **10 s** and evicts any client silent for more than **15 s**, handling ungraceful crashes. Graceful shutdown (`Ctrl+C`) triggers a JVM shutdown hook that calls `unregister()` immediately.

If the Directory evicts a Daemon and then receives a heartbeat from it, `heartbeat()` returns `false`; the Daemon detects this and silently re-registers. As a by-product, any file just downloaded is broadcast on the next heartbeat, making the downloader an instant new source with no extra configuration.

### 3.2 Load-Aware Source Selection

The Directory keeps a live `load` integer per Daemon, incremented on `CMD_GET_FRAGMENT` receipt and decremented on completion. `getSourcesForFile` returns the list sorted by load ascending. The Download client filters out sources with `load > MAX_LOAD (10)`, falling back to the single least-loaded node if all are saturated. This prevents hot-spotting under concurrent downloads.

### 3.3 Conditional GZIP Compression

When compression is requested, each fragment is individually compressed by the Daemon. The compressed payload is sent **only if** it is strictly smaller than the raw data; otherwise raw bytes are sent with a `compressed=false` header flag. The Download client decompresses transparently using `GZIPInputStream`. This yields meaningful savings for text or sparse binary files, and zero overhead for already-compressed formats (MP4, ZIP, JPEG).

---

## 4. Parallelism Validation — Test Design

All tests run on **AWS EC2 t3.micro instances** with bandwidth throttled via `tc netem` (upload cap ~1–2 MB/s per node) to reproduce ADSL-class asymmetric links. Data is extracted from `[SUMMARY]` lines in `logs/download-*.log`.

| Figure | Fixed parameters | Variable | Hypothesis |
|:---:|---|---|---|
| **Fig. 1** | File = 50 MB, frag = 256 KB | Daemons: 1 → 2 → 3 → 4 | Near-linear speedup until RMI overhead dominates |
| **Fig. 2** | Daemons = 3, frag = 256 KB | File: 1, 5, 10, 25, 50, 100 MB | Parallelism gain negligible below ~5 MB |
| **Fig. 3** | File = 50 MB, Daemons = 3 | Fragment: 64, 128, 256, 512, 1024 KB | Sweet spot balances queue overhead vs. socket setup |

Each scenario is repeated **3 times** and the median total transfer time is reported. Per-source throughput breakdowns (from `[SUMMARY] source=…` entries) confirm that the work-stealing queue distributes load proportionally to each Daemon's available bandwidth.

---

*[Pages 3–4: Performance figures and quantitative analysis — to be added]*

*[Page 5: Conclusions and future work — to be added]*
