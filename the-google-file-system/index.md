```markdown
---
layout: post
title: (Paper Review) The Google File System - Part 1
subheading: Exploring the Core Concepts and Architecture of GFS
author: Taehyeok Jang
categories: [distributed-systems]
tags: [paper-review, distributed-systems, file-system]
---

## Background

The Google File System (GFS) was introduced in 2003 in SOSP '03 as Google's distributed file system for storing and processing massive amounts of data. It has evolved over time and is currently used within Google under the name Colossus. Google Cloud Platform (GCP) also offers a file system service based on Colossus.

Although the paper is nearly 20 years old, the design and implementation of GFS for efficiently and reliably storing large amounts of data, as well as the considerations in its design process, are still relevant today. By reading the paper, one can gain insights into GFS's wisdom in overcoming the unique challenges of distributed systems to provide an efficient file system.

This review of the GFS paper is written in two parts. Although I wanted to summarize briefly, I found that the paper contains many significant details that warranted inclusion in the post.

## Abstract

The paper designs and implements the Google File System (GFS), a scalable distributed file system for processing large amounts of distributed data. GFS operates on a cluster of commodity hardware and provides fault tolerance while delivering high aggregate performance to a large number of clients.

While sharing the goals of previous distributed file systems, GFS's design took into consideration both the current and future application workload and technological environment of Google. This approach prompted a re-exploration of traditional file systems and an exploration of radically different design points.

GFS successfully addressed Google's storage needs. It has been used as a storage platform for both data generation and processing in development and research that deal with large datasets. These massive clusters store hundreds of terabytes over thousands of machines and are accessed simultaneously by hundreds of clients.

The paper presents:

- File system extensions designed to support distributed applications.
- An in-depth discussion of various aspects of GFS design.
- Measurements from both micro-benchmarks and real-world use.

## 1. Introduction

GFS emerged to satisfy Google's rapidly growing needs in data processing. Its design reflects Google's current and future application workload and technological environment, prompting a re-evaluation of traditional file systems and the exploration of radically different design points.

First, component failure is the norm rather than the exception in distributed systems. Clusters consisting of thousands of machines are composed of low-cost commodity machines and accessed by a comparable number of clients. The quantity and quality of machines mean they may not always function and might not recover. Errors arise from various sources, including application bugs, operating system bugs, human errors, disk failures, memory, connectors, network, and power supplies. As such, continuous monitoring, error detection, fault tolerance, and automatic recovery are essential features of the system.

Second, files are typically very large compared to traditional standards. File sizes of several gigabytes are common. Given the rapidly growing data within applications, it is difficult to manage billions of tiny files, even if the file system can support them. Therefore, design assumptions and parameters, such as I/O operation and block size, must be reconsidered.

Third, most files undergo mutation by appending new data rather than overwriting existing data. Random writes are rare, and once written, the data is mostly read or accessed sequentially. Considering this access pattern to large files, append operations should focus on performance optimization and atomicity guarantees. On the other hand, caching data blocks at the client loses its appeal.

Fourth, co-designing file systems and their APIs with applications increases overall system flexibility. For example, GFS simplifies the consistency model to simplify the file system and introduces atomic append operations to allow multiple clients to access files without additional synchronization.

Several GFS clusters are currently deployed for various purposes. The largest cluster features over 300 terabytes of disk storage and 1,000 nodes, heavily accessed by hundreds of clients from separate machines.

## 2. Design Overview

### 2.1 Assumptions

In designing GFS, certain assumptions, which present both challenges and opportunities, guide our approach. These assumptions are based on several key observations we've made:

- The system is built from inexpensive commodity hardware and failures are inevitable.
- It stores a modest number of large files. Storing files over 100MB, often several gigabytes, is common.
- Workloads consist of two types of reads: large streaming reads and small random reads.
- The workload involves large, sequential writes that append data to files, which are rarely modified once written.
- The system requires well-defined semantics for concurrent appends by multiple clients to the same file.
- High sustained bandwidth is prioritized over low latency, as most of Google's applications process vast data in bulk at high rates, with few having strict response-time requirements.

### 2.2 Interface

GFS offers a familiar file system interface but does not implement a standard API like POSIX. Files are organized hierarchically in directories identified by path names. The interface supports operations such as:

- Create, delete, open, close, read, and write files.
- Snapshot and record append operations.

Record append is particularly useful, allowing multiple clients to access the same file while ensuring atomicity for each client's append. This feature supports operations like multi-way merging and producer-consumer queuing, facilitating the implementation of large distributed applications.

### 2.3 Architecture

![GFS Architecture](https://1.bp.blogspot.com/-DPELgKlFiL0/X0Io6pJlnZI/AAAAAAAADio/5Ya6IwZOpAIrAVfAd7qNi2Mv6iKh3vWqwCLcBGAsYHQ/s640/GFS-Fig1.png)

Figure 1 represents a GFS cluster. A GFS cluster comprises a single master, numerous chunkservers, and is accessed by multiple clients, with each component operating as a user-level server process on a commercial Linux machine.

Files are divided into fixed-size chunks, each possessing an immutable, globally unique 64-bit chunk handle (ID) assigned by the master at creation. To ensure reliability, each chunk is replicated across multiple chunkservers. The default replication factor is three, though replication levels can be set arbitrarily for different regions of the file namespace.

The master oversees all file system metadata, including namespace, access control information, file-to-chunk mappings, and chunk location data. It also manages system-wide activities like chunk lease management, orphaned chunk garbage collection, and chunk migration between chunkservers.

GFS clients are linked to applications implementing the file system API. Clients perform metadata operations via communication with the master, while direct data communication occurs with the chunkservers.

Neither GFS clients nor chunkservers cache file data, as caching benefits are minimal due to applications predominantly streaming large files or handling files too large for caching. By eliminating caching, coherence issues are avoided, simplifying both client and system design overall. Chunkservers store chunks as local files, and Linux buffer cache manages frequently accessed data in memory.

### 2.4 Single Master

The single master architecture simplifies the design, enabling the master to leverage sophisticated chunk placement and global knowledge for replication decisions. However, the master must avoid becoming a bottleneck by minimizing its involvement in read/write operations. Clients obtain information from the master regarding which chunkservers to contact for data exchange rather than reading/writing through the master. Figure 1 illustrates how clients, the master, and chunkservers interact for reads.

### 2.5 Chunk Size

One crucial design parameter is chunk size, set to 64MB in GFS, far larger than typical file system block sizes. Chunk replicas are stored as plain Linux files on each chunkserver and expand only when necessary. This lazy space allocation helps avoid space waste due to internal fragmentation.

Large chunk sizes offer several advantages:

1. They reduce the need for client interaction with the master, as read/write operations tend to occur within a single chunk. This benefit is maximized in applications where read/write operations are sequential.
   
2. They reduce network overhead by allowing persistent TCP connections when accessing the same chunkserver.

3. They limit the size of metadata the master must maintain, allowing multiple benefits from fitting metadata in memory.

There are potential drawbacks, even with lazy space allocation. Applications experiencing high client access rates to a particular chunk can lead to hotspot scenarios on that chunkserver. The issue was identified during GFS testing and resolved by increasing the file's replication factor and distributing application execution across different times to alleviate bottlenecks.

### 2.6 Metadata

The master stores three primary types of metadata:

1. File and chunk namespaces.
2. Mappings from files to chunks.
3. Locations of each chunk's replicas.

The first two types are stored in memory and logged persistently for mutation operations on local disks and remote machines. Operation logs ensure that master updates are simple, reliable, and consistent. However, replica locations are not stored persistently and are instead reflected by polling chunkservers during startup and on a periodic basis.

#### 2.6.1 In-Memory Data Structure

Storing metadata in memory allows swift master operations and facilitates background master state scans. These frequent scans support operations like chunk garbage collection, re-replication due to chunkserver failures, and chunk migration for load and disk usage balancing.

The potential problem of memory capacity being insufficient due to numerous chunks is practically negligible, as the master requires less than 64 bytes of metadata for a 64MB chunk.

When scaling memory for these massive clusters, it is generally not problematic to scale up.

#### 2.6.2 Chunk Locations

The master does not persistently store the chunkserver locations of each replica. Instead, it tracks chunkservers from startup, using periodic heartbeat messages to monitor and update states.

Initially, GFS intended to store this information persistently, but the polling approach was deemed a simpler solution. This design eliminates synchronization issues between the master and chunkserver.

Another way to simply understand the design is to recognize that chunkservers bear the final responsibility for any chunk. The master is obligated to maintain a consistent view, despite the possibility of chunkserver failures.

#### 2.6.3 Operation Log

The operation log acts as a historical record for crucial metadata changes and is fundamental to GFS. It serves as both the persistent record of metadata and the logical time order for current operations.

Given its significance, the operation log must be reliably stored and not visible to clients until metadata is persistently recorded. It is saved on multiple remote machines, and log records are flush before responding to clients.

The operation log allows the master to restore the file system by replaying these logs. To reduce startup time, the master keeps the log succinct by frequently updating checkpoints, which enable it to load the latest checkpoint and execute any remaining log records.

Creating a checkpoint can be time-consuming, so the master's internal state remains configured to generate new checkpoints without delay for incoming mutations. The master switches to a new log file using a separate thread, accommodating all mutations following the latest checkpoint.

### 2.7 Consistency Model

GFS supports Google's distributed applications by employing a relaxed consistency model.

#### 2.7.1 Guarantees by GFS

![Consistency Guarantees](https://1.bp.blogspot.com/--glHtB9TGaE/X0Ips-BKr0I/AAAAAAAADjA/A4vMGB2aASwwUfSYeUWMRImUHcBNE8UzACLcBGAsYHQ/w410-h180/GFS-Tab1.png)

**File Namespace Mutation:**  
File namespace mutations are atomic and executed exclusively by the master. Namespace locking ensures atomicity and correctness, while the master operation log defines the complete order of operations.

**Data Mutation:** 
The state of the file region following data mutations depends on the type of mutation, its success, and any concurrent operations, as shown in Table 1.

- **Consistent:** All clients see the same data.
- **Defined:** Consistent and reflects all concurrent mutations.

Typically, data from concurrent mutations comprises portions of the modifications. Failed mutations render the region inconsistent, potentially showing different data to different clients. Below, we’ll explore how applications distinguish defined and undefined regions.

**Write:** Data is written at an application-specified file offset.  
**Record Append:** Appends data atomically at least once under concurrent mutations, but at an offset of GFS's choosing.

The resulting file region after multiple mutations is defined and holds data from the final mutation. GFS achieves this by:

a) Applying mutations to all replicas of a chunk in the same order.
b) Checking stale chunks with version numbers upon chunkserver failure.

Since clients cache chunk locations, interactions with a stale replica remain bound to the cache entry’s timeout and until the file is reopened. As most files are append-only, outdated data is likely to return premature ends, mitigating potential adverse application impacts.

Post-mutation component failures can corrupt or destroy data. GFS uses periodic handshakes between the master and chunkserver to confirm this, and detects data corruption through checksums.

#### 2.7.2 Implications for Applications

GFS applications can accommodate the relaxed consistency model using several simple techniques already required for other purposes, such as:

- Relying on appends over overwrites.
- Checkpointing.
- Writing self-validating and self-identifying records.

One typical case involves a single writer creating a file from beginning to end. After writing data, the application either atomically renames the file or periodically checkpoints the progress, incorporating an application-level checksum so readers only access defined states of the file.

Another common use case entails multiple writers concurrently appending to a file for merged results or producer-consumer scenarios. The at-least-once semantic of record append preserves writer output, while readers handle padding or duplicates accordingly with hypergraphical views for verification and filtering.

## 3. System Interactions

GFS's minimal master involvement in system design allows for precise interactions among clients, master, and chunkservers.

![System Interactions](https://1.bp.blogspot.com/-GniHhMBsJRY/X0IqFMEg00I/AAAAAAAADjI/sQdbRu9z6lYCUQkZ1--X7kd3IHBwmockgCLcBGAsYHQ/s640/GFS-Fig2.png)

### 3.1 Leases and Mutation Order

A mutation modifies a chunk's contents or metadata, applied to all its replicas. GFS ensures consistency in mutation order across replicas through leases. A master-allocated lease assigns one replica as the primary, which organizes mutations in serial order, with all secondary replicas adhering to this order. The lease mechanism is designed to minimize master management overhead, initially timing out after 60 seconds, but extending indefinitely during active mutations, facilitated by signals piggybacked on heartbeat communication between master and chunkserver.

Figure 2 illustrates control flow for a write operation:

1. The client requests the master for the chunkserver holding the current lease (primary) and the locations of the other (secondary) replicas. If not yet assigned, the master allocates a lease to one of the replicas.
2. The master provides the client with information about the primary and secondary.
3. The client pushes data to all replicas. Each chunkserver stores the data in its internal LRU buffer cache, from which it ages out if needed.
4. After all replicas acknowledge, the client sends a write request to the primary, which assigns serial numbers for mutations and applies them in order.
5. The primary forwards the write request to secondaries, which apply mutations in order.
6. Once all secondaries respond to the primary, the operation is considered complete.
7. The primary responds to the client. Any errors encountered result in operation failure; retrying from this point allows the client to continue with failed mutations.

For large write operations, data must be cycled into multiple write operations. An identical state in all replicas renders consistent yet undefined regions. 

### 3.2 Data Flow

We achieve efficient network utilization by decoupling data and control flow. Control flow trades from the client to the primary, followed by secondaries, while data flow is linearly pushed to well-chosen chunkserver chains. The objective is to maximize each machine's bandwidth, avoid network bottlenecks and high-latency links, and minimize latency needed for data pushing.

Chaining pipeline techniques on TCP connections further reduce latency. Once data arrives at a chunkserver, it immediately starts forwarding to the next replica. Under the presumption of absent network congestion, the ideal time required for elapse is:

\[ B/T + RL \] (where B: transferred bytes, T: network throughput, R: replicas, L: latency between two machines)

### 3.3 Atomic Record Appends

GFS supports atomic record appends. In typical writes, the client specifies an offset, prohibiting concurrent writes to the same region. However, record append lacks clients specifying offsets and GFS appends data at an offset of its choosing, atomically and at least once. Clients can append to the same file atomically without additional synchronization.

When a record append fails on any replica, the client retries the operation, potentially leading to replicas having different data representations including duplicates. GFS doesn't ensure bytewise equality across replicas, only that each atomic unit is at-least-once written over the defined states. Applications can address inconsistency as discussed in 2.7.2.

### 3.4 Snapshot

A snapshot operation generates a copy of a file or directory tree, achieving minimal disruption to ongoing mutations in near-instant timeframes.

Like AFS, GFS uses copy-on-write techniques for implementing snapshots. Snapshot operation follows these steps:

1. The master revokes chunk leases it receives snapshot requests for. Subsequent writes involve master interactions, enabling the master to create new copies.
2. Upon lease revocation or expiration, the master logs the operation on disk, replicating the source file's metadata into a snapshot, and applying the log to in-memory states.
3. The master recognizes a request involving a lease, deferring client's lease-holder request and selecting new chunk C'.
4. All chunkservers holding chunk C receive instructions to create C', quickly achieved through local replication.
5. At this point, the request resumes normally, allowing the master to lease C', enabling clients to use C' transparently.

## References

- Sanjay Ghemawat, Howard Gobioff, & Shun-Tak Leung (2003). The Google File System. In *Proceedings of the 19th ACM Symposium on Operating Systems Principles* (pp. 20–43).
- [GFS Paper](https://courses.cs.washington.edu/courses/cse490h/11wi/CSE490H_files/gfs.pdf)
- [Stanford Lecture Slides](https://cs.stanford.edu/~matei/courses/2015/6.S897/slides/gfs.pdf)
```
