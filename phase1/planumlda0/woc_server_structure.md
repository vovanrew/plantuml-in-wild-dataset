# World of Code (WoC) Server Structure Documentation

## Overview

The World of Code infrastructure consists of multiple servers (da0-da7+) with a distributed storage architecture designed for petabyte-scale data processing. Understanding this architecture is crucial for efficient data access and processing.

## Storage Architecture

The WoC system uses a **two-tier storage architecture**:

### 1. NFS-Mounted Storage (Network/Shared)
Accessible from all servers via Network File System (NFS)

### 2. Local Storage (Machine-Specific)
Fast local disk storage unique to each physical server

---

## NFS-Mounted Storage (Shared Across All Servers)

### Home Directories (`~/` or `/home/username/`)

**Physical Location:** da2 server
**Mounted To:** All da servers (da0, da1, da2, da3, ...)
**Access:** Available from any server

**Characteristics:**
- ✅ Your files are visible from any da server
- ✅ Persistent and backed up
- ✅ Perfect for scripts, code, and small files
- ⚠️ Network I/O overhead when accessed from non-da2 servers
- ⚠️ Limited quota
- ❌ Poor performance for large file operations from other servers

**Use Cases:**
- Store scripts and code (`~/lookup/*.perl`)
- Configuration files
- Small result files
- Documentation

**Example:**
```bash
# From any server (da0, da1, da3, etc.)
[username@da0]~% ls ~/lookup/
# This reads from da2 over NFS

[username@da7]~% cat ~/my_script.pl
# Same files, still reading from da2
```

---

### WoC Data Directories (`/da*_data/`)

**Physical Locations:**
- `/da0_data/` → physically on da0
- `/da1_data/` → physically on da1
- `/da2_data/` → physically on da2
- `/da3_data/` → physically on da3
- ... and so on

**Mounted To:** All da servers via NFS cross-mounting
**Access:** Available from any server (but with network overhead if remote)

**Characteristics:**
- ✅ All servers can access all data directories
- ✅ WoC datasets, basemaps, and relationship maps
- ✅ Read-optimized for parallel processing
- ⚠️ Network overhead when accessing remote server's data
- 📖 Generally read-only for most users

**Directory Structure:**
```
/da0_data/
├── basemaps/
│   ├── gz/           # Compressed sorted files
│   ├── *.tch         # TokyoCabinet hash databases
│   └── *.s           # Sorted text files
├── play/
│   └── username/     # User scratch space
└── ...

/da7_data/
├── basemaps/
│   └── gz/
└── ...
```

**Use Cases:**
- Reading WoC maps (c2p, b2f, a2c, etc.)
- Accessing blob data
- Querying relationship databases

**Example:**
```bash
# From da0, accessing data on da7 (works via NFS)
[username@da0]~% zcat /da7_data/basemaps/gz/a2cFull.V3.0.s | grep 'Warner Losh'

# Wildcard access across all servers
[username@da0]~% zcat /da?_data/basemaps/gz/a2cFull.V3.?.s | grep 'Warner'
# ↑ Automatically reads from whichever servers have matching files
```

---

## Local Storage (Machine-Specific)

### Scratch Space (`/data/play/username/`)

**Physical Location:** Local disk on EACH individual server
**NOT NFS Mounted:** Each server has its own separate `/data/play/`
**Access:** Only from the specific server you're on

**Characteristics:**
- ✅ Fast local disk I/O (no network overhead)
- ✅ Best for large temporary files
- ✅ No impact on NFS or other users
- ❌ NOT shared between servers
- ❌ Files on da0's `/data/play/` are different from da3's `/data/play/`
- ⚠️ Not backed up (ephemeral storage)
- ⚠️ May be cleaned periodically

**Use Cases:**
- Large intermediate processing files
- Temporary data extraction
- Job-specific outputs
- High-throughput I/O operations

**Example:**
```bash
# Create your scratch directory
[username@da0]~% mkdir -p /data/play/username/myproject/

# Process large data with fast local I/O
[username@da0]~% cd /data/play/username/myproject/
[username@da0]~% zcat /da0_data/basemaps/b2fFull.s | \
    ./process_large_dataset.pl > output.txt
# ↑ Fast: reading from local da0_data, writing to local /data/play

# Important: Files here are LOCAL ONLY
[username@da3]~% ls /data/play/username/myproject/
# ↑ This is a DIFFERENT directory on da3 (will be empty!)
```

---

## Visual Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                    NFS Layer (Shared Across All Servers)            │
├─────────────────────────────────────────────────────────────────────┤
│  /home/username/              (physically on da2, mounted to all)   │
│  /da0_data/                   (physically on da0, mounted to all)   │
│  /da1_data/                   (physically on da1, mounted to all)   │
│  /da2_data/                   (physically on da2, mounted to all)   │
│  /da3_data/                   (physically on da3, mounted to all)   │
│  ...                                                                 │
└─────────────────────────────────────────────────────────────────────┘
              ↑ All accessible from any da server (via network)

┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐
│    da0      │  │    da1      │  │    da2      │  │    da3      │
├─────────────┤  ├─────────────┤  ├─────────────┤  ├─────────────┤
│ /data/play/ │  │ /data/play/ │  │ /data/play/ │  │ /data/play/ │
│   username/ │  │   username/ │  │   username/ │  │   username/ │
│             │  │             │  │             │  │             │
│   (local)   │  │   (local)   │  │   (local)   │  │   (local)   │
└─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘
      ↑                ↑                ↑                ↑
   only on da0     only on da1     only on da2     only on da3
```

---

## SSH Access vs NFS Mount Access

### Important Distinction

**SSH access ≠ NFS mount access**

- **SSH access** = Ability to log into a server and run commands on that machine
- **NFS mount access** = Ability to read/write filesystems that are mounted on your current server

### Practical Implication

Even if you can only SSH to da0 and da2, you can still access `/da4_data/`, `/da7_data/`, etc. from da0, because those directories are **NFS-mounted at the filesystem level**.

```bash
# Scenario: You can SSH to da0 and da2, but NOT to da7

# ✅ This WORKS (filesystem access via NFS mount):
[username@da0]~% ls /da7_data/basemaps/
[username@da0]~% zcat /da7_data/basemaps/gz/a2cFull.V3.0.s | grep pattern
# ↑ You're reading da7's data from da0 via NFS

# ❌ This FAILS (no SSH permission):
[username@da0]~% ssh da7
Permission denied
# ↑ You cannot log into da7

# ✅ But commands like this still work:
[username@da0]~% zcat /da?_data/basemaps/gz/lb2fFullV0.s | grep -i readme
# ↑ Reads from ALL mounted /da*_data/ directories, including da7
```

### Key Point

**The wildcard pattern `/da?_data/`** works by accessing the NFS-mounted filesystems, **not by SSH-ing to other servers**. As long as the directories are mounted on your current server, you can access them.

```
Your SSH access: [da0] ✅  [da2] ✅  [da7] ❌

But from da0, you can still access:
/da0_data/ ✅ (local)
/da2_data/ ✅ (NFS mount)
/da7_data/ ✅ (NFS mount, even though you can't SSH!)
```

---

## When Does Current Directory Matter?

### Commands with Absolute Paths (Output to stdout)

**Short answer: Current directory does NOT matter**

```bash
# These three commands produce IDENTICAL results:
[username@da0]~% zcat /da?_data/basemaps/gz/lb2fFullV0.s | grep -i readme | head -n 5

[username@da0]~/project% zcat /da?_data/basemaps/gz/lb2fFullV0.s | grep -i readme | head -n 5

[username@da0]/data/play/username/project% zcat /da?_data/basemaps/gz/lb2fFullV0.s | grep -i readme | head -n 5
```

**Why?** The command uses:
- ✅ Absolute paths (`/da?_data/...`)
- ✅ Output to stdout (terminal), not a file
- ✅ No relative path references

### When Current Directory DOES Matter

#### 1. Writing Output to a File

```bash
# Output file is created in CURRENT directory
zcat /da?_data/basemaps/gz/lb2fFullV0.s | grep -i readme > output.txt

# From home (slower - writes to da2 via NFS):
[username@da0]~% zcat ... > output.txt
# Creates: /home/username/output.txt

# From scratch (faster - writes to local disk):
[username@da0]/data/play/username/project% zcat ... > output.txt
# Creates: /data/play/username/project/output.txt
```

#### 2. Using Relative Paths

```bash
# Depends on current directory
cat ../data/file.txt
./my_script.pl
grep pattern *.txt
```

#### 3. Scripts That Reference Local Files

```bash
# Must be in the directory containing the script
[username@da0]~% cd /data/play/username/project/
[username@da0]/data/play/username/project% ./process.pl
```

### Decision Table: Does pwd Matter?

| Command Pattern | Current Directory Matters? | Why |
|----------------|---------------------------|-----|
| `zcat /da?_data/... \| grep \| head` | ❌ No | Absolute paths, stdout output |
| `zcat /da?_data/... > file.txt` | ✅ Yes | Output file created in pwd |
| `cat ~/file.txt \| grep pattern` | ❌ No | Absolute path, stdout output |
| `./script.pl` | ✅ Yes | Relative path reference |
| `grep pattern *.txt` | ✅ Yes | Operates on files in pwd |
| `perl ~/lookup/script.pl < /da0_data/input.s` | ❌ No | All paths are absolute |

### Best Practice for Location

**For read-only queries:**
```bash
# Run from anywhere - same result
zcat /da?_data/basemaps/gz/*.s | grep pattern | head
```

**For processing pipelines with output:**
```bash
# Run from /data/play/ for better performance
cd /data/play/username/project/
zcat /da0_data/basemaps/large_file.gz | \
    ~/lookup/process.pl > output.txt
# ↑ Output writes to fast local disk
```

---

## Storage Decision Tree

**Where should I store my file?**

```
Is it code/scripts?
├─ YES → ~/lookup/
└─ NO ↓

Is it a small final result to keep?
├─ YES → ~/results/
└─ NO ↓

Is it a large temporary/intermediate file?
├─ YES → /data/play/username/
└─ NO ↓

Are you reading WoC data?
└─ YES → /da*_data/basemaps/
```

---

## Best Practices

### ✅ DO:

1. **Store scripts in home directory**
   ```bash
   ~/lookup/my_analysis.perl
   ```

2. **Process large data in local scratch**
   ```bash
   mkdir -p /data/play/username/project1/
   cd /data/play/username/project1/
   # Do heavy I/O here
   ```

3. **Copy final small results to home**
   ```bash
   cp summary.txt ~/results/
   ```

4. **Read from local data when possible**
   ```bash
   # If you're on da0, prefer reading from /da0_data/
   zcat /da0_data/basemaps/c2pFull0.s | process.pl
   ```

5. **Use wildcards for distributed data**
   ```bash
   zcat /da?_data/basemaps/gz/*.s | grep pattern
   ```

### ❌ DON'T:

1. **Don't do large I/O to home from non-da2 servers**
   ```bash
   # BAD: Heavy write to home from da0
   [username@da0]~% huge_process > ~/bigfile.txt  # ❌ Loads NFS

   # GOOD: Write to local scratch
   [username@da0]~% huge_process > /data/play/username/bigfile.txt  # ✅
   ```

2. **Don't assume `/data/play/` is shared**
   ```bash
   # BAD: Expecting da3 to see files written on da0
   [username@da0]~% echo "data" > /data/play/username/file.txt
   [username@da3]~% cat /data/play/username/file.txt  # ❌ File not found!
   ```

3. **Don't ignore network overhead**
   ```bash
   # SLOW: Reading da7's data from da0
   [username@da0]~% zcat /da7_data/large_file.gz  # ⚠️ Network transfer

   # BETTER: SSH to da7 and process locally
   [username@da0]~% ssh da7
   [username@da7]~% zcat /da7_data/large_file.gz  # ✅ Local read
   ```

---

## Common Workflows

### Workflow 1: Small Analysis Script

```bash
# 1. Write script in home (accessible from anywhere)
[username@da0]~% vim ~/lookup/find_authors.perl

# 2. Run it reading from WoC data
[username@da0]~% ~/lookup/find_authors.perl < /da0_data/basemaps/a2cFull0.s

# 3. Save small results to home
[username@da0]~% ~/lookup/find_authors.perl > ~/results/authors.txt
```

### Workflow 2: Large Data Processing

```bash
# 1. Create local scratch space
[username@da0]~% mkdir -p /data/play/username/plantuml_extraction/
[username@da0]~% cd /data/play/username/plantuml_extraction/

# 2. Process large data (all I/O stays local)
[username@da0]~% zcat /da0_data/basemaps/b2fFull*.s | \
    ~/lookup/selBlobsByExt.perl > large_output.txt

# 3. Copy only final summary to home
[username@da0]~% wc -l large_output.txt > ~/results/summary.txt
```

### Workflow 3: Parallel Processing Across Servers

```bash
# 1. Submit jobs to different servers
for i in {0..7}; do
  ssh da$i "cd /data/play/username/ && \
    zcat /da${i}_data/basemaps/c2pFull*.s | \
    ~/lookup/process.pl > output_da${i}.txt"
done

# 2. Collect results (each server writes locally, then copies to home)
for i in {0..7}; do
  ssh da$i "cp /data/play/username/output_da${i}.txt ~/results/"
done

# 3. Merge results on one server
[username@da0]~% cat ~/results/output_da*.txt > ~/results/merged.txt
```

---

## Performance Considerations

### Fast Operations ⚡

| Operation | Location | Why |
|-----------|----------|-----|
| Read local data | `/da0_data/` on da0 | Local disk, no network |
| Write to scratch | `/data/play/username/` | Local disk, no NFS |
| Small file to home | `~/result.txt` from da2 | Same server as home |

### Slow Operations 🐌

| Operation | Location | Why |
|-----------|----------|-----|
| Large write to home | `~/bigfile` from da0 | NFS + network to da2 |
| Read remote data | `/da7_data/` from da0 | Network transfer |
| Heavy I/O to home | `~/temp/*` from da3 | Impacts all users' NFS |

---

## Gotchas and Tips

### Gotcha 1: Local Storage Isn't Shared

```bash
# Files in /data/play/ are SERVER-SPECIFIC
[username@da0]~% echo "test" > /data/play/username/file.txt
[username@da3]~% cat /data/play/username/file.txt
# ❌ Error: No such file (it's on da0, not da3!)
```

**Solution:** Use home directory for files you need everywhere, or explicitly copy between servers.

### Gotcha 2: Home Directory Network Overhead

```bash
# You're on da0, but home is on da2
[username@da0]~% time cat ~/large_file.txt
# Slow: reads over network from da2

[username@da2]~% time cat ~/large_file.txt
# Fast: local read on da2
```

**Solution:** For heavy processing, work on da2 or use local scratch space.

### Gotcha 3: Wildcard Patterns and Version Numbers

```bash
# Different servers may have different versions
/da0_data/basemaps/c2pFull.V3.0.s
/da7_data/basemaps/c2pFull.V3.2.s

# Use wildcards to automatically pick available versions
zcat /da?_data/basemaps/c2pFull.V3.?.s
```

---

## Quick Reference

| Storage Type | Path | Shared? | Speed | Use For |
|--------------|------|---------|-------|---------|
| **Home** | `~/` | ✅ Yes (NFS) | 🐌 Slow from non-da2 | Scripts, configs, small results |
| **WoC Data** | `/da*_data/` | ✅ Yes (NFS) | ⚡/🐌 Fast if local | Reading WoC datasets |
| **Scratch** | `/data/play/` | ❌ No (Local) | ⚡ Fast | Large temp files, heavy I/O |

---

## Additional Resources

- **Tutorial:** `/Users/vovapolischuk/indiehacker/projects/university/lookup/tutorial.md`
- **README:** `/Users/vovapolischuk/indiehacker/projects/university/lookup/README.md`
- **WoC Documentation:** https://worldofcode.org/

---

## Summary

**Think of it as two tiers:**

1. **NFS (Shared)** = "Everyone sees it"
   - Home directories (`~/`)
   - WoC data (`/da*_data/`)
   - Accessible from anywhere
   - Slower for large operations

2. **Local (Machine-Specific)** = "Fast but isolated"
   - Scratch space (`/data/play/`)
   - Only on specific server
   - Fast local I/O
   - Perfect for temporary processing

**Golden Rule:** *Scripts in home, data in scratch, results in home.*
