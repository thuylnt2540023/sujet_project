# Test Scenarios & Performance Metrics
## Distributed File Download System Performance Evaluation

**Document Type**: Product Management - Testing Strategy  
**Scope**: Performance optimization of file distribution across daemon network  
**Date**: March 2026  
**Status**: Guidance for Testing Phase

---

## Executive Summary

This document defines two primary test scenarios to evaluate the distributed file download system's performance characteristics. The tests focus on:
- **Scalability**: How system throughput scales with added daemon resources
- **Optimization**: Finding the optimal piece size for maximum efficiency

---

## Testing Objectives

| Objective | Purpose | Success Criteria |
|-----------|---------|-----------------|
| **Scale-out Impact** | Measure throughput improvement as daemons increase | Linear or super-linear scaling up to 10 daemons |
| **Optimal Piece Size** | Identify piece size that minimizes transfer time | Single piece size showing <5% variance from optimum |
| **Resource Efficiency** | Validate daemon capability-based distribution model | Scenario 2 outperforms Scenario 1 by 10-20% |
| **Real-world Applicability** | Test with realistic file sizes | 100MB, 1GB, 2.7GB represent production scenarios |

---

## Test Scenario 1: Equal Division Model

### Description
**File size is equally divided by number of daemons**

The downloader calculates the number of daemons available and divides the file into equal segments. Each daemon receives exactly one segment of size `FileSize / NumberOfDaemons`.

### When to Use
- Baseline performance measurement
- Systems with uniform daemon capabilities
- Simple load-balancing scenarios

### Example Calculation
```
File Size: 2.7GB = 2,900,000 KB
Number of Daemons: 5
Segment Size per Daemon: 2,900,000 / 5 = 580,000 KB
```

### Expected Characteristics
- **Pros**: Simple implementation, predictable distribution
- **Cons**: Inefficient if daemons have varying speeds; wastes fast daemon capacity
- **Optimal Scenario**: Uniform network conditions and daemon performance

---

## Test Scenario 2: Capability-Based Segmentation Model

### Description
**File size is segmented into fixed-size parts; daemons distribute segments based on their capabilities**

The file is divided into fixed-size segments (determined during testing). The system allocates segments to daemons proportional to their stated or measured capabilities (CPU, bandwidth, availability).

### When to Use
- Heterogeneous daemon environments (different network speeds, hardware specs)
- Production deployments with variable daemon quality
- Maximizing overall throughput in mixed environments

### Example Calculation
```
File Size: 2.7GB = 2,900,000 KB
Piece Size: 5MB = 5,000 KB
Total Segments: 2,900,000 / 5,000 = 580 segments

Daemon 1 (Fast): Capability Score 10 → 145 segments
Daemon 2 (Fast): Capability Score 10 → 145 segments
Daemon 3 (Slow): Capability Score 5 → 72 segments
Daemon 4 (Slow): Capability Score 5 → 72 segments
Daemon 5 (Slow): Capability Score 5 → 72 segments
Total: 580 segments ✓
```

### Expected Characteristics
- **Pros**: Maximizes fast daemon utilization; reduces idle time
- **Cons**: Requires capability measurement; more complex implementation
- **Optimal Scenario**: Heterogeneous daemon performance; production environments

---

## Figure 1: Transfer Time vs. Number of Providers

### Specification

**Title**: Scalability Analysis - Transfer Time by Number of Daemons

**Test Setup**:
- **Number of Downloaders**: 1
- **Daemons**: 1 to 10 (x-axis)
- **File Sizes**: 3 lines (100MB, 1GB, 2.7GB)
- **Piece Size**: Fixed optimal value (determined from Figure 2 analysis)

**Axes**:
- **X-axis**: Number of Daemons (1, 2, 3, 4, 5, 6, 7, 8, 9, 10)
- **Y-axis**: Transfer Time (seconds or minutes, whichever is appropriate)
- **Series**: 
  - Line 1: 100MB files (expected: 10-60 seconds range)
  - Line 2: 1GB files (expected: 100-600 seconds range)
  - Line 3: 2.7GB files (expected: 270-1600 seconds range)

### Expected Outcomes

| File Size | 1 Daemon | 5 Daemons | 10 Daemons | Theoretical Scale |
|-----------|----------|-----------|------------|-------------------|
| 100MB | 10s | 4s | 2.5s | Linear (10x reduction) |
| 1GB | 100s | 40s | 25s | Linear (10x reduction) |
| 2.7GB | 270s | 108s | 67.5s | Linear (10x reduction) |

### Key Metrics to Capture

1. **Transfer Time (T)**: Time from download start to completion
2. **Throughput (TP)**: `FileSize / TransferTime` (MB/s)
3. **Scaling Efficiency (SE)**: `Throughput(N daemons) / Throughput(1 daemon)` × 100%
   - 100% = Perfect linear scaling
   - <100% = Overhead from coordination/network contention
   - >100% = Super-linear gain (unlikely but possible with caching)

### Success Criteria

| Metric | Target | Acceptable Range |
|--------|--------|-----------------|
| Scaling Efficiency (5 daemons) | 95%+ | >85% |
| Scaling Efficiency (10 daemons) | 90%+ | >75% |
| File Size Scalability | Linear | ±10% variance |

### Interpretation Guide

**Ideal Pattern**: Lines should show
- Rapid improvement from 1→3 daemons (steep slope)
- Diminishing returns 6→10 daemons (flattening slope)
- All three sizes maintain proportional relationships

**Concerning Patterns**:
- Flat or declining lines → Network bottleneck or contention
- One file size breaking pattern → Possible chunk size mismatch
- Worse than linear → Serious coordination overhead

---

## Figure 2: Transfer Time vs. Piece Size (Optimal Tuning)

### Specification

**Title**: Piece Size Optimization - Transfer Time for 2.7GB across 10 Daemons

**Test Setup**:
- **Number of Downloaders**: 1
- **File Size**: 2.7GB (constant)
- **Daemons**: 10 (constant, all uniform performance)
- **Piece Sizes**: 256KB, 512KB, 1MB, 2MB, 5MB, 10MB (x-axis)

**Axes**:
- **X-axis**: Piece Size (logarithmic or linear)
  - 256KB = 0.25MB
  - 512KB = 0.5MB
  - 1MB
  - 2MB
  - 5MB
  - 10MB
- **Y-axis**: Transfer Time (seconds)
- **Single Series**: Time for constant 2.7GB file across 10 daemons

### Expected Pattern

```
Transfer Time (seconds)
        |
     85 |     ╱╲
        |    ╱  ╲      ← Ideal sweet spot (likely 2-5MB)
     80 |   ╱    ╲
        |  ╱      ╲___
     75 | ╱           ╲___
        | ╱                ╲
     70 |                   ╲___
        |________________________________
        256KB  512KB  1MB  2MB  5MB  10MB
        
Piece Size (x-axis)
```

### Rationale for Each Piece Size

| Piece Size | Characteristics | Pros | Cons |
|-----------|-----------------|------|------|
| **256KB** | Very small | Fine-grained distribution; fast re-sync | Excessive metadata overhead; more TCP handshakes |
| **512KB** | Small | Better granularity than 1MB | Still significant overhead |
| **1MB** | Standard | Common in industry; reasonable balance | Possible suboptimal for 10 daemons |
| **2MB** | Medium | Less overhead; better batch efficiency | Fewer distribution opportunities |
| **5MB** | Medium-large | Often optimal in practice | Reduced adaptability to daemon variance |
| **10MB** | Large | Minimal overhead; maximum parallelism opportunity | Coarse-grained; poor recovery if daemon fails mid-segment |

### Expected Outcomes

**Predicted Optimal Range**: 2MB - 5MB

- **Below Optimal**: Too many small chunks → TCP handshake overhead dominates
- **At Optimal**: Balanced network efficiency and distribution flexibility
- **Above Optimal**: Too few chunks → Cannot fully parallelize across 10 daemons; wasted daemon capacity

### Key Metrics to Capture

1. **Transfer Time (T)**: Absolute time to download 2.7GB
2. **Number of Segments**: `FileSize / PieceSize`
   - 256KB: 11,520 segments
   - 512KB: 5,760 segments
   - 1MB: 2,880 segments
   - 2MB: 1,440 segments
   - 5MB: 576 segments
   - 10MB: 288 segments
3. **Throughput (TP)**: `2.7GB / TransferTime`
4. **Daemon Utilization (DU)**: % of daemons with active downloads
   - Expected: 100% for all piece sizes (with 10 daemons)

### Success Criteria

| Metric | Target | Acceptable |
|--------|--------|-----------|
| Optimal Piece Size Identified | ±1 step | ±2 steps from target |
| Transfer Time Variance | <5% | <10% |
| No piece size performs >15% worse | Required | — |

### Interpretation Guide

**Ideal Outcome**:
- Clear "U-shaped" curve with pronounced minimum
- Optimal piece size matches theoretical predictions
- Performance within 5% of optimum across ±1 adjacent size

**Acceptable Outcome**:
- Flat bottomed "U" (multiple sizes perform similarly)
- Optimal within middle range (1-5MB)
- <10% variance between worst and best

**Concerning Patterns**:
- No clear optimum (flat line) → Possible network throughput limits instead of piece size issues
- Optimum at extremes (256KB or 10MB) → System poorly balanced
- >20% variance → Unstable performance, requires investigation

---

## Performance Metrics Summary Table

### Primary KPIs

| KPI | Formula | Figure 1 | Figure 2 | Target |
|-----|---------|---------|---------|--------|
| **Transfer Time** | `T` (seconds) | Y-axis | Y-axis | Minimize |
| **Throughput** | `FileSize / T` (MB/s) | Derived | Derived | Maximize |
| **Scaling Efficiency** | `TP(N) / TP(1)` × 100% | X measure | — | >85% |
| **Piece Size Efficiency** | `TP(optimal) / TP(tested)` × 100% | — | Per piece | >95% |
| **Daemon Utilization** | Daemons with active downloads / Total | Implicit | 100% target | Maximize |

### Secondary Metrics (Observational)

| Metric | Measurement | Purpose |
|--------|------------|---------|
| **CPU Usage** | Average per daemon (%) | Detect bottlenecks |
| **Memory Usage** | Peak RAM per daemon (MB) | Validate resource footprint |
| **Network Latency** | Avg RTT per peer (ms) | Detect degradation |
| **Error Rate** | Failed segments / Total segments (%) | Reliability baseline |
| **Segment Recovery Time** | Time to re-download failed segment (s) | Resilience measure |

---

## Test Execution Plan

### Phase 1: Figure 1 Testing (Scalability)
```
For each File Size in [100MB, 1GB, 2.7GB]:
  For each NumDaemons in [1, 2, 3, 4, 5, 6, 7, 8, 9, 10]:
    Run download 3 times (for variance measurement)
    Record: Transfer Time, Throughput
    Calculate: Scaling Efficiency
```
**Effort**: 30 test runs per file size = 90 total runs
**Duration**: ~2-3 hours (assuming 30-60s per run)

### Phase 2: Figure 2 Testing (Optimization)
```
For each PieceSize in [256KB, 512KB, 1MB, 2MB, 5MB, 10MB]:
  Run download 5 times (higher variance with piece size variations)
  Record: Transfer Time, Throughput
  Calculate: Segment count, efficiency metrics
```
**Effort**: 30 test runs (5 repetitions × 6 piece sizes)
**Duration**: ~40 minutes (assuming 80s per run for 2.7GB)

### Phase 3: Validation & Analysis
- Identify optimal piece size from Figure 2
- Re-run Figure 1 with optimal piece size (if not already tested)
- Document findings and recommendations

**Total Testing Time**: ~4 hours (including setup, teardown, analysis)

---

## Expected Deliverables

1. **Figure 1 Graph**: 3-line chart showing scalability trends
2. **Figure 2 Graph**: Single line chart showing optimal piece size
3. **Performance Report** including:
   - Scaling efficiency analysis
   - Recommended piece size and rationale
   - Hardware/network recommendations
   - Comparison of Scenario 1 vs Scenario 2 (if both tested)

---

## Success Definition

### Minimum Requirements
- ✅ Figure 1 shows linear or near-linear scaling (>80% efficiency at 5 daemons)
- ✅ Figure 2 identifies a single optimal piece size
- ✅ 2.7GB downloads complete in <5 minutes with 10 daemons

### Ideal Outcomes
- ✅ Figure 1 shows >90% scaling efficiency up to 10 daemons
- ✅ Figure 2 shows <5% performance variance in optimal range
- ✅ Scenario 2 (capability-based) outperforms Scenario 1 (equal division) by 10-20%
- ✅ Performance reproducible across multiple test runs

---

## Risk & Mitigations

| Risk | Impact | Mitigation |
|------|--------|-----------|
| Network congestion during tests | Unreliable results | Test during off-peak hours; isolate test network |
| Daemon crashes mid-download | Data loss; test failure | Implement segment retry logic; use test monitoring |
| Piece size causes memory exhaustion | OOM crashes | Start with smaller piece sizes; monitor memory usage |
| Scaling plateaus early (4-6 daemons) | Throughput limit found | Investigate I/O saturation; test with smaller files first |

---

## Next Steps

1. **Setup Test Environment**: Prepare 10 daemon instances; configure monitoring
2. **Implement Test Suite**: Automation scripts for Figure 1 & 2 testing
3. **Run Phase 1**: Collect scalability data
4. **Analyze & Tune**: Identify optimal piece size range
5. **Run Phase 2**: Test piece size variations
6. **Document Findings**: Create final performance report with recommendations
