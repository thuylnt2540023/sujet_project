# Song Song P2P: Test Scenarios & Performance Metrics

**Version**: 2.0 (March 2026)  
**Purpose**: Standardized performance evaluation and optimization analysis  
**Status**: Ready for testing phase

---

## Table of Contents

1. [Project Requirements](#project-requirements)
2. [Testing Objectives](#testing-objectives)
3. [Test Scenario 1: Scalability Analysis](#test-scenario-1-scalability-analysis)
4. [Test Scenario 2: Optimal Piece Size](#test-scenario-2-optimal-piece-size)
5. [Performance Metrics Reference](#performance-metrics-reference)
6. [Test Execution Guide](#test-execution-guide)
7. [Interpretation & Analysis](#interpretation--analysis)

---

## Project Requirements

### Context: Peer-to-Peer Parallel Downloads

The Song Song system addresses the challenge of efficiently downloading large files in a heterogeneous peer-to-peer network with:

- **Bandwidth asymmetry**: Upload speed ≠ Download speed (ADSL-like)
- **Multiple sources**: Files served by multiple daemon peers
- **Parallel segments**: Large files split into small pieces
- **Dynamic topology**: Peers join/leave at any time

### Key Design Principles

1. **Distributed architecture**: No single source bottleneck
2. **Parallel downloads**: Multiple segments from multiple peers simultaneously
3. **Intelligent distribution**: Match segment allocation to peer capabilities
4. **Resilience**: Recover gracefully from peer failures
5. **Observation**: Measure and optimize based on data

### Expected Outcomes

This testing strategy validates:

| Goal | Metric | Target |
|------|--------|--------|
| **Scalability** | Throughput vs. # of daemons | Linear scaling (80%+) |
| **Optimization** | Transfer time vs. piece size | <5% variance from optimal |
| **Efficiency** | Capability-based vs. Equal division | 10-20% improvement |
| **Applicability** | Real-world file sizes | 100MB, 1GB, 2.7GB test success |

---

## Testing Objectives

### Objective 1: Scalability Impact Measurement

**Why**: Validate that adding daemons improves throughput proportionally

**Metric**: Transfer time vs. number of daemons  
**Success**: Linear or super-linear scaling up to 10 daemons (80%+ efficiency)

### Objective 2: Optimal Piece Size Discovery

**Why**: Identify segment size that minimizes transfer time  
**Metric**: Transfer time vs. piece size  
**Success**: Single piece size showing <5% variance from optimum

### Objective 3: Distribution Model Efficiency

**Why**: Compare naive equal-division vs. capability-based distribution  
**Metric**: Throughput improvement  
**Success**: Capability-based outperforms equal-division by 10-20%

### Objective 4: Real-World Applicability

**Why**: Ensure system works with production-scale files  
**Metric**: Coverage of file size range  
**Success**: Successfully download 100MB, 1GB, 2.7GB

---

## Test Scenario 1: Scalability Analysis

### Title: Transfer Time vs. Number of Providers

Measure how system throughput scales as daemon count increases.

### Test Design

**Fixed Parameters**:
- Number of downloaders: 1
- Piece size: Fixed optimal (determined from Figure 2 analysis)
- File sizes: 3 different (100MB, 1GB, 2.7GB)

**Variable Parameter**:
- Number of daemons: 1, 2, 3, 4, 5, 6, 7, 8, 9, 10

**Repetitions**: 3 per configuration (average results)

### Expected Characteristics

#### Equal Division Model (Baseline)
```
File Size: 1GB
Number of Daemons: 5
Segment per Daemon: 1GB / 5 = 200MB
Expected Transfer Time: Single daemon time / 5

Simple but suboptimal if daemons have varying speeds
```

#### Capability-Based Model (Optimized)
```
File Size: 1GB = 1000 segments @ 5MB piece
Daemon 1 (Fast, score 10): 200 segments = 1GB * (10/50) = 200MB
Daemon 2 (Fast, score 10): 200 segments = 200MB
Daemon 3 (Slow, score 5):  100 segments = 100MB
Daemon 4 (Slow, score 5):  100 segments = 100MB
Daemon 5 (Slow, score 5):  100 segments = 100MB
Total: 1000 segments = 1GB ✓

Maximizes utilization of fast daemons; reduces idle time
```

### Metrics Specification

#### Axes Definition

**X-Axis**: Number of Daemons
```
1, 2, 3, 4, 5, 6, 7, 8, 9, 10
```

**Y-Axis**: Transfer Time (seconds or minutes)
```
Range depends on network bandwidth
- 100MB: 10-60 seconds
- 1GB: 100-600 seconds
- 2.7GB: 270-1600 seconds
```

#### Data Series

| Series | File Size | Expected Range | Notes |
|--------|-----------|-----------------|-------|
| Line 1 | 100MB | 10-60 sec | Rapid improvement 1→3 daemons |
| Line 2 | 1GB | 100-600 sec | Proportional to 100MB |
| Line 3 | 2.7GB | 270-1600 sec | Proportional to 100MB |

### Expected Outcomes

#### Theoretical Scaling

```
File Size: 100MB (baseline)

Daemons | Theoretical Time | Efficiency | Achievable %
--------|-----------------|-----------|---------------
1       | 100s (baseline) | 100%      | 100%
2       | 50s             | 100%      | 95% (overhead)
3       | 33s             | 100%      | 90% (overhead)
5       | 20s             | 100%      | 85% (congestion)
10      | 10s             | 100%      | 80% (congestion)
```

#### Key Metrics

1. **Transfer Time (T)**: Absolute time from start to completion
   ```
   T = FileSize / AvailableBandwidth
   ```

2. **Throughput (TP)**: Data transfer rate
   ```
   TP = FileSize / TransferTime (MB/s)
   ```

3. **Scaling Efficiency (SE)**: Percentage of theoretical improvement realized
   ```
   SE = [TP(N daemons) / TP(1 daemon)] / N × 100%
   
   Example:
   - 1 daemon: 10 MB/s
   - 5 daemons: 40 MB/s
   - SE = (40 / 10) / 5 × 100% = 80%
   ```

### Success Criteria

| Metric | Target | Acceptable | Concerning |
|--------|--------|-----------|-----------|
| Scaling Efficiency @ 5 daemons | 95%+ | >85% | <75% |
| Scaling Efficiency @ 10 daemons | 90%+ | >75% | <60% |
| File Size Proportionality | ±5% variance | ±10% | >10% |
| Linear Pattern | Consistent | Smooth curve | Unstable swings |

### Interpretation Guide

#### Ideal Pattern
```
Transfer Time (seconds)
                       100MB
        |
     60 |    ╱╲
        |   ╱  ╲           ← 100MB (steepest drop)
     50 |  ╱    ╲
     40 | ╱      ╲
        |╱        ╲         1GB (proportional, slower)
     30|          ╲   ╱╲
        |           ╲ ╱  ╲
     20|            ╲╱    ╲     2.7GB (proportional, slowest)
        |                  ╲
     10|                    ╲___
        |_____________________
        1   2   3   4   5   6...10
        
        Number of Daemons
```

**What to look for**:
- ✓ Rapid improvement 1→3 daemons (steep initial slope)
- ✓ Diminishing returns 6→10 daemons (flattening slope)
- ✓ All three sizes maintain proportional relationships
- ✓ Smooth curves without sudden jumps

#### Concerning Patterns

1. **Flat Line** → Network saturation at the source, not piece-size limited
2. **Declining After Peak** → Coordination overhead dominates
3. **One size breaks pattern** → Possible chunk size mismatch
4. **Worse than linear** → Serious network contention or synchronization overhead

### Test Execution

```bash
# Setup on Directory instance
aws ssm start-session --target <instance-0-id>
cd /home/ubuntu

# Ensure data files available in ./shared/
ls -lh shared/test-100mb shared/test-1gb shared/test-2.7gb

# Run test suite
./scripts/test-p2p-scenarios.sh 127.0.0.1 1099 ./results

# Outputs: CSV files with raw metrics
cat results/figure1-scalability.csv
```

---

## Test Scenario 2: Optimal Piece Size

### Title: Optimal Segment Size for Maximum Throughput

Find the piece size that minimizes transfer time for a large file.

### Test Design

**Fixed Parameters**:
- File size: 2.7GB (largest realistic file)
- Number of daemons: 10 (constant, maximizes parallelism opportunity)
- Number of downloaders: 1

**Variable Parameter**:
- Piece size: 256KB, 512KB, 1MB, 2MB, 5MB, 10MB

**Repetitions**: 3 per piece size (average results)

### Theoretical Foundation

#### Trade-offs by Piece Size

| Piece Size | Pros | Cons | Use Case |
|-----------|------|------|----------|
| **256KB** | Fine-grained distribution; fast adaptive re-sync | Massive overhead; 11,520 TCP connections | Edge case; rarely optimal |
| **512KB** | Better granularity than 1MB | Still significant overhead; 5,760 connections | Small file optimization |
| **1MB** | Industry standard; good balance | May be suboptimal for 10 daemons; 2,880 connections | General purpose |
| **2MB** | Less overhead; better batch efficiency | Fewer distribution opportunities; 1,440 connections | **Often optimal** |
| **5MB** | Minimal overhead; good parallelism opportunity | Reduced adaptability to daemon variance; 576 connections | **Often optimal** |
| **10MB** | Minimal overhead; maximum parallelism | Coarse-grained; poor failure recovery; 288 chunks | Large clusters |

#### Network Overhead Model

```
Total Cost = Data Transfer Time + Overhead

Overhead includes:
- TCP handshakes
- RMI lookups
- Metadata transfers
- Synchronization
- Daemon coordination

Optimal = Balance between small chunks (many TCP opens) 
          and large chunks (poor distribution)
```

### Expected Pattern

```
Transfer Time (seconds)
        |
     85 |     ╱╲
        |    ╱  ╲      ← Optimal sweet spot (likely 2-5MB)
     80 |   ╱    ╲
        |  ╱      ╲___
     75 | ╱           ╲___
        | ╱                ╲
     70 |                   ╲___
        |________________________________
        256KB  512KB  1MB  2MB  5MB  10MB
        
        Piece Size (x-axis, logarithmic or linear)
```

**U-shaped curve** with pronounced minimum at optimal piece size.

### Metrics Specification

#### Axes Definition

**X-Axis**: Piece Size (logarithmic scale preferred)
```
256KB (0.25MB)
512KB (0.5MB)
1MB
2MB
5MB
10MB
```

**Y-Axis**: Transfer Time (seconds)
```
For 2.7GB with 10 daemons:
Expected range: 60-100 seconds
```

#### Calculation Examples

| Piece Size | # Segments | Characteristics |
|-----------|-----------|------------------|
| 256KB | 11,520 | Excessive overhead dominates |
| 512KB | 5,760 | Still high overhead |
| 1MB | 2,880 | Good balance for most cases |
| 2MB | 1,440 | **Predicted optimal** |
| 5MB | 576 | **Predicted optimal** (less granular) |
| 10MB | 288 | Few chunks; poor distribution |

### Expected Outcomes

#### Predicted Optimal Range

```
Piece Size Recommendation: 2MB - 5MB

- Below optimal (256KB - 1MB): TCP overhead too high
- Optimal (2MB - 5MB): Sweet spot for 10 daemons
- Above optimal (10MB): Underutilizes daemons
```

#### Key Metrics

1. **Transfer Time (T)**: Absolute time to download 2.7GB
   ```
   T = Total bytes / Effective bandwidth
   ```

2. **Number of Segments (S)**: File divided into pieces
   ```
   S = FileSize / PieceSize
   
   Examples:
   - 2.7GB @ 256KB = 11,520 segments (too many)
   - 2.7GB @ 5MB = 576 segments (optimal)
   - 2.7GB @ 10MB = 288 segments (too few)
   ```

3. **Throughput (TP)**: Effective data rate
   ```
   TP = 2.7GB / TransferTime
   ```

4. **Daemon Utilization**: % of daemons with active downloads
   ```
   If S > N (segments > daemons), all daemons utilized
   If S << N, some daemons idle
   
   Examples:
   - 256KB: 11,520 segments > 10 daemons → 100% utilization
   - 10MB: 288 segments > 10 daemons → 100% utilization
   - 20MB: 144 segments ≈ 10 daemons → ~90% utilization
   ```

### Success Criteria

| Metric | Target | Acceptable | Issues |
|--------|--------|-----------|--------|
| Optimal Identified | ±1 step from prediction | ±2 steps | >2 steps = investigate |
| Time Variance | <5% across 3 runs | <10% | >10% = unstable |
| No outliers | All sizes within 15% of best | <20% spread | >20% = significant variance |
| Curve shape | Clear U-shape | Smooth minimum | Flat or erratic = bottleneck elsewhere |

### Interpretation Guide

#### Ideal Outcome: Clear Optimum
```
Transfer Time (seconds)
     |
  85 |
  82 |     X
  80 |    XXX      ← Clear U-shape with minimum
  78 |   XXXXX
  76 | XXXXXXX    
  74 |XXXXXXXXX
  72 | XXXXXXX
  70 |  XXXXX
  68 |   XXX
  66 |    X
     |______________
     250K 500K 1M 2M 5M 10M
```

**Interpretation**: Piece size optimization is critical; use 2-5MB for best results.

#### Acceptable Outcome: Flat-Bottomed U
```
Transfer Time (seconds)
     |
  75 |     X X
  74 |    X X X    ← Minimum not sharp
  73 |   X X X X
  72 |  XXXXXXXXX   ← Multiple sizes perform similarly
  71 | XXXXXXXXXX
     |______________
     250K 500K 1M 2M 5M 10M
```

**Interpretation**: Multiple piece sizes work similarly well; choose middle range (1-5MB) for robustness.

#### Concerning Outcome: No Clear Pattern
```
Transfer Time (seconds)
     |
  100|  X  X  X   ← High variance
  95 |   XXXXX     ← No clear optimum
  90 | XXXXXXXXX
  85 |XXXXXXXXXXX  ← Flat or random
  80 |XXXXXXXXXXX
     |______________
     250K 500K 1M 2M 5M 10MB
```

**Interpretation**: Bottleneck is network throughput, not piece size. Adding daemons won't help; increase bandwidth limits.

---

## Performance Metrics Reference

### Standard Measurement Procedure

#### 1. Baseline (1 daemon, 100MB file)

```bash
# Run as control
Start Time = T0
java -cp build Download test-100mb 127.0.0.1 1099 output localhost false 256

# Record: Transfer Time, Throughput
Transfer Time = T1 - T0
Throughput = 100MB / Transfer Time
```

#### 2. Scale Test (N daemons)

```bash
# Repeat with different daemon counts
for N in 1 2 3 5 10; do
  # Calculate expected time
  Expected = BaselineTime / N
  
  # Run download
  ActualTime = measure_download(100MB, N daemons, 256KB piece)
  
  # Calculate efficiency
  Efficiency = (BaselineTime / ActualTime) / N × 100%
  
  # Record
  Record(N, ActualTime, Efficiency)
done
```

#### 3. Piece Size Test

```bash
# Fixed: 2.7GB, 10 daemons
for PieceSize in 256KB 512KB 1MB 2MB 5MB 10MB; do
  Start = now()
  java -cp build Download test-2.7gb 127.0.0.1 1099 output localhost false $PieceSize
  End = now()
  
  TransferTime = End - Start
  Throughput = 2.7GB / TransferTime
  
  Record(PieceSize, TransferTime, Throughput)
done
```

### CSV Output Format

#### Scenario 1: Scalability
```csv
Number_of_Daemons,File_Size_MB,Transfer_Time_Seconds,Throughput_MBps,Scaling_Efficiency_Percent
1,100,50,2.0,100
2,100,27,3.7,92
3,100,19,5.3,88
5,100,12,8.3,83
10,100,7,14.2,71
1,1000,500,2.0,100
2,1000,270,3.7,92
...
```

#### Scenario 2: Piece Size
```csv
Piece_Size_KB,Transfer_Time_Seconds,Throughput_MBps,Segments,Daemon_Utilization_Percent
256,95,28.8,11520,100
512,87,31.0,5760,100
1024,78,34.6,2880,100
2048,72,37.5,1440,100
5120,69,39.1,576,100
10240,75,36.0,288,100
```

### Interpretation Methods

#### Method 1: Graph Analysis
- Plot transfer time vs. daemon count (Scenario 1)
- Plot transfer time vs. piece size (Scenario 2)
- Visually identify patterns and anomalies

#### Method 2: Statistical Analysis
```
Scaling Efficiency = (Throughput @ N daemons) / (Throughput @ 1 daemon) / N × 100%

Example:
- 1 daemon: 2 MB/s
- 10 daemons: 14 MB/s
- Efficiency = (14 / 2) / 10 × 100% = 70%

Target: >80% efficiency at 10 daemons
```

#### Method 3: Variance Analysis
```
Coefficient of Variation (CV) = StdDev / Mean × 100%

For piece size test:
- If CV < 5%: Stable performance across piece sizes
- If CV 5-10%: Small variation, multiple sizes acceptable
- If CV > 10%: Large variation, piece size is critical
```

---

## Test Execution Guide

### Prerequisites

```bash
# 1. Directory service running
aws ssm start-session --target <instance-0-id>
ps aux | grep Java  # Verify Directory process

# 2. At least 10 Daemon instances running & registered
ps aux | grep Daemon  # Should show multiple processes

# 3. Test files available
ls -lh /home/ubuntu/shared/test-*

# 4. Java compiled
ls -la /home/ubuntu/sujet_project/build/*.class
```

### Step 1: Single Daemon Baseline

```bash
# From Directory instance
cd /home/ubuntu

# Warm up cache
java -cp sujet_project/build Download test-100mb 127.0.0.1 1099 output localhost false 256

# Baseline run
time java -cp sujet_project/build Download test-100mb 127.0.0.1 1099 output localhost false 256
# Record: Transfer Time

# Repeat 3 times
# Record average: BaselineTime
```

### Step 2: Scalability Test (Scenario 1)

```bash
# Run from Directory instance
# Already in /home/ubuntu

# Create output directory
mkdir -p test-results

# For each daemon count
for DAEMONS in 1 2 3 4 5 6 7 8 9 10; do
  echo "Testing with $DAEMONS daemons..."
  
  # For each file size
  for SIZE in test-100mb test-1gb test-2.7gb; do
    # Run 3 times
    for RUN in 1 2 3; do
      echo "  $SIZE (run $RUN)..."
      
      # Time the download
      /usr/bin/time -v \
        java -cp sujet_project/build \
        Download $SIZE 127.0.0.1 1099 output/$SIZE-$DAEMONS-$RUN localhost false 256 \
        > test-results/$SIZE-$DAEMONS-$RUN.log 2>&1
      
      # Extract metrics
      # Transfer Time from output
      # Throughput from "Bytes transferred" / "Total time"
    done
  done
done

# Consolidate results into CSV
cat > test-results/scenario1-scalability.csv <<EOF
Number_of_Daemons,File_Size_MB,Transfer_Time_Seconds,Throughput_MBps
...
EOF
```

### Step 3: Piece Size Test (Scenario 2)

```bash
# Testing piece size sensitivity
# Fixed: 2.7GB, 10 daemons

for PIECESIZE in 256 512 1024 2048 5120 10240; do
  echo "Testing piece size: ${PIECESIZE}KB..."
  
  for RUN in 1 2 3; do
    echo "  Run $RUN..."
    
    /usr/bin/time -v \
      java -cp sujet_project/build \
      Download test-2.7gb 127.0.0.1 1099 output/piece-$PIECESIZE-$RUN localhost false $PIECESIZE \
      > test-results/piece-$PIECESIZE-$RUN.log 2>&1
  done
done

# Consolidate into CSV
cat > test-results/scenario2-piece-size.csv <<EOF
Piece_Size_KB,Transfer_Time_Seconds,Throughput_MBps
...
EOF
```

### Step 4: Data Consolidation

```bash
# Extract metrics and create final CSVs
python3 << 'PYTHON'
import os
import json

# Parse logs and consolidate
results = []
for log_file in os.listdir('test-results'):
    if log_file.endswith('.log'):
        # Extract metrics from /usr/bin/time output
        # Parse transfer time, throughput, etc.
        pass

# Save to CSV
import csv
with open('test-results/final-metrics.csv', 'w') as f:
    writer = csv.writer(f)
    writer.writerows(results)
PYTHON
```

---

## Interpretation & Analysis

### Figure 1 Analysis: Scalability

#### How to Read the Graph

```
Y-Axis: Transfer Time (seconds)
X-Axis: Number of Daemons (1-10)

If point is LOWER → BETTER (faster download)

Three lines:
- Bottom line (100MB): Fastest transfers
- Middle line (1GB): 10x slower than 100MB
- Top line (2.7GB): 27x slower than 100MB
```

#### Good Scalability Signs
```
1. All three lines parallel and declining
   ✓ File size effects are proportional
   ✓ Piece size is appropriate for all files

2. Steep drop from 1→3 daemons
   ✓ Initial parallelization very effective
   ✓ Low coordination overhead

3. Diminishing returns 5→10 daemons
   ✓ Normal as bottleneck shifts to network
   ✓ Not a problem up to 80% efficiency
```

#### Poor Scalability Signs
```
1. Line flattens or rises with more daemons
   ✗ Network congestion or coordination overhead
   ✗ May need larger piece sizes or fewer daemons

2. One file size breaks from pattern
   ✗ Piece size mismatch for that file size
   ✗ May need adaptive piece sizing

3. High variance (jump between runs)
   ✗ System instability
   ✗ Check for background processes or network interference
```

### Figure 2 Analysis: Piece Size

#### How to Read the Graph

```
Y-Axis: Transfer Time (seconds)
X-Axis: Piece Size (logarithmic: 256KB → 10MB)

LOWER Y-value = BETTER

U-shaped curve:
- Left branch (256KB-1MB): Falling as overhead decreases
- Bottom (2MB-5MB): Optimal zone
- Right branch (10MB): Rising as parallelism lost
```

#### Good Optimization Signs
```
1. Clear minimum (not flat)
   ✓ Piece size genuinely matters
   ✓ Use identified optimal value

2. Minimum in range 1MB-5MB
   ✓ Aligns with industry practice
   ✓ Easy to remember and set in production

3. <5% performance difference within ±1 size
   ✓ Robust; small changes in piece size acceptable
   ✓ Can use nearby value if needed
```

#### Poor Optimization Signs
```
1. Flat line across all piece sizes
   ✗ Network is bottleneck, not piece size
   ✗ Piece size doesn't matter; use any value

2. Minimum at extremes (256KB or 10MB)
   ✗ System poorly balanced
   ✗ May need to: change daemon count, tune bandwidth, 
      increase network capacity

3. High variance (>10% between runs)
   ✗ Results unreliable
   ✗ May be system load, background processes, network jitter
   ✗ Retry with isolated system
```

### Document Results

#### Report Template

```markdown
# Performance Test Report
Date: [Date]
Configuration: [Instance count, file sizes, bandwidth]

## Scenario 1: Scalability Analysis

### Summary
- Baseline (1 daemon, 100MB): X seconds (Y MB/s)
- 10 daemons: Z seconds (W MB/s)
- Efficiency @ 10 daemons: E%

### Key Findings
- ✓ Linear scaling observed (or concerning pattern X)
- ✓ File sizes scale proportionally
- [Other observations]

### Graph
[Embed Figure 1]

## Scenario 2: Optimal Piece Size

### Summary
- Optimal piece size: XMB
- Transfer time (baseline): Y seconds
- Transfer time (optimal): Z seconds
- Improvement: (Y-Z)/Y × 100% = X%

### Key Findings
- Piece size sweet spot confirmed at XMB
- [Other findings]

### Graph
[Embed Figure 2]

## Recommendations
1. [Recommendation 1]
2. [Recommendation 2]
3. [Recommendation 3]
```

---

## Next Steps: Enhancement Opportunities

Based on test results, consider:

### Enhancement 1: Failure & Recovery
- Test daemon disconnection mid-download
- Verify segment re-fetching from remaining daemons
- Measure throughput impact of failures

### Enhancement 2: Dynamic Adaptation
- Measure daemon speeds dynamically
- Allocate segments based on measured bandwidth
- Quantify improvement vs. static allocation

### Enhancement 3: Data Compression
- Compare uncompressed vs. GZIP transfers
- Measure CPU cost vs. bandwidth savings
- Identify optimal compression level

---

**Version 2.0** | Updated March 16, 2026 | Test-Ready
