---
layout: post
title: Clickhouse Internal  
subheading: 
author: taehyeok-jang
categories: [database]
tags: [clickhouse, internal]

---

## Introduction 

ClickHouse is an open source column-oriented distributed OLAP database, also refered as a SQL data warehouse. 

- Open source 
    - Since 2009, 22K+ GitHub stars, 900+ contributors, 300+ releases 
- Column-oriented
    - Best for aggregations 
    - Files per column
    - Sorting and indexing
    - Background merges 
- Distributed 
    - Replication 
    - Sharding 
    - Multi-master 
    - Cross-region 
- OLAP
    - Analytics use cases
    - Aggregations
    - Visualizations 
    - Mostly immutable data 

## Key Features 

- ANSI-compatible SQL

Most SQL-compatible UIs, editors, applications, frameworks will just work!

- Lots of writes

Up to several million writes per second - in fact, we'll see 2.5M writes per second later!

- Distributed

Replicated and sharded, largest known cluster consists of about 4,000 servers.

- Highly efficient storage

Lots of encoding and compression options - we'll see 20x compression later.

- Very fast queries

Scan and process even billions of rows per second and use vectorized query execution.

- Joins and lookups

Allows separating fact and dimension tables in a star schema.



## Architecture 

<img width="1322" alt="clickhouse-getting_started_with_03" src="https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/8aa03a01-9a69-494c-b4ba-41bc2f1db4ad">

- Distributed mode 

ClickHouse supports both shard and replication across a distributed cluster. 

- Coordination

ClickHouse Keeper provides the coordination system for data replication and distributed DDL queries execution. ClickHouse Keeper is compatible with ZooKeeper.
ClickHouse Keeper uses the RAFT algorithm implementation, similar to Kafka broker's RAFT implementation. 

<->
Unlike ClickHouse, Apache HBase and Google BigTable has a master server that coordinates a whole cluster. 

The master is responsible for, 
- assigning tablets to tablet servers, 
- detecting the addition and expiration of tablet servers, 
- balancing tablet-server load, 
- and garbage collection of files in GFS. 
- In addition, it handles schema changes such as table and column family creations.

<img width="1322" alt="clickhouse-getting_started_with_02" src="https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/026da380-d2a3-44e6-8395-e86be03bef04">




## MergeTree 
### Table Engine
https://www.alibabacloud.com/blog/selecting-a-clickhouse-table-engine_597726?spm=a2c65.11461447.0.0.530e484b9y6QtJ

ClickHouse provides about 28 table engines for different purposes. For example, 
- Log family for small table data analysis, however 
- MergeTree family for big-volume data analysis 
- Integration for external data integration.


However Log, Special, and Integration are mainly used for special purposes in relatively limited scenarios. **MergeTree family is the officially recommended storage engine,** which supports almost all ClickHouse core functions.

There are a wide range of MergeTree table engines including MergeTree, ReplacingMergeTree, CollapsingMergeTree, VersionedCollapsingMergeTree, SummingMergeTree, and AggregatingMergeTree,... (some supports data aggregation and deduplication) 

- Example

We adopts 'ReplacingMergeTree' for internal data pipeline project. 

- Does MergeTree remove some rows by compacting process?


Some MergeTree families such as ReplacingMergeTree, SummingMergeTree, AggregatingMergeTree does replace / sum / aggregate rows. 

### MergeTree as LSM-Tree

- LSM-Tree?

=> read this article! [(Paper Review) Algorithms Behind Modern Storage Systems](https://taehyeok-jang.github.io/database/2020/09/27/algorithms-behind-modern-storage-systems.html#h-introduction) 



![LSM_Tree_(1)](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/af82c9e1-49c9-47db-ab42-256fb2b5efca)



MergeTree has the same core idea as LSM-Tree, to solve the performance problem of random disk writing.
MergeTree storage structure sorts the written data first and then stores it. Orderly data storage has two core advantages:

- When column-store files are compressed by blocks, the column values in the sort key are continuous or repeated, so t**he column-store blocks can be compressed at an excellent data compression ratio.**
- Orderly storage **is an index structure that helps accelerate queries.** The approximate position interval where the target rows are can be located quickly based on the equivalence condition or range condition of the columns in the sort key.



### MergeTree Internal 

```sql
CREATE TABLE user_action_log (
  `time` DateTime DEFAULT CAST('1970-01-01 08:00:00', 'DateTime') COMMENT 'Log time',
  `action_id` UInt16 DEFAULT CAST(0, 'UInt16') COMMENT 'Log behavior type id',
  `action_name` String DEFAULT '' COMMENT 'Log behavior type name',
  `region_name` String DEFAULT '' COMMENT 'Region name',
  `uid` UInt64 DEFAULT CAST(0, 'UInt64') COMMENT 'User id',
  `level` UInt32 DEFAULT CAST(0, 'UInt32') COMMENT 'Current level',
  `trans_no` String DEFAULT '' COMMENT 'Transaction serial number',
  `ext_head` String DEFAULT '' COMMENT 'Extended log head',
  `avatar_id` UInt32 DEFAULT CAST(0, 'UInt32') COMMENT 'Avatar id',
  `scene_id` UInt32 DEFAULT CAST(0, 'UInt32') COMMENT 'Scene id',
  `time_ts` UInt64 DEFAULT CAST(0, 'UInt64') COMMENT 'Second timestamp',
  index avatar_id_minmax (avatar_id) type minmax granularity 3
) ENGINE = MergeTree()
PARTITION BY (toYYYYMMDD(time), toHour(time), region_name)
ORDER BY (action_id, scene_id, time_ts, level, uid)
PRIMARY KEY (action_id, scene_id, time_ts, level);
```



The following figure shows the MergeTree storage structure logic of the table:

![9b6058003d49ce37745344a93c5f3250ea276ba9_(1)](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/6d6d8bdf-be22-42c3-b935-64c09b87cbf2)

- Partition 

A single partition contains multiple MergeTree Data Parts. In the storage structure of the MergeTree table, **each data partition is independent of each other with no logical connections.**

- Data Part

A new MergeTree Data Part is generated for each batch insert operation.

Once these Data Parts are generated, they are immutable. The generation and destruction of Data Parts are mainly related **to writing and asynchronous Merge (compaction).**



### Data Part

Plz note that inside one data part, there are **1) primary key index, 2) mark identifiers, 3) data files, 4) etc (minmax_idx, skipping index, ...)** 

![4d88ee03dec493f26a091508d43f5c668238bc33-2_(1)](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/90bf925f-4362-4b4d-8173-9a9b0cd89b7f)



#### Primary Key Index (primary.idx)

It is capable of quickly finding the primary key rows. It stores the primary key value of the start row in each Granule, while the data in MergeTree storage is strictly sorted according to the primary 

#### Mark Identifiers (column_1.mrk, column_2.mrk, ...) 

Mark identifier is related to two important concepts in MergeTree columnar storage, namely, Granule and Block.

- Block

Block is the compression unit for the column-store file. Each Block of a column-store file contains several Granules.

The specific number of Granules is controlled by the 'min_compress_block_size' parameter. It checks whether the current Block size has reached the set value when the data in a Granule is written in a Block. If so, the current Block is compressed and then written to the disk.

- Granule

Granule is a logical concept to divide data by rows.

In earlier versions, the amount of rows a Granule makes up is set by the 'index_granularity'  parameter. It ensures that the sum size of all columns in a Granule does not exceed the specified value

- Mark identifier

Neither the data size nor the number of rows are fixed in the Block of MergeTree, and the Granule is not a fixed-length logical concept.

Therefore, additional information is needed to find a Granule quickly. **Mark identifier files can provide the solution.** It records the number of rows of each Granule and the offset of the Block where it locates in the column-store compressed file. It also records the offset of a Granule in the decompressed Block.



#### Data Files (column_1.bin, column_2.bin, ...) 

column_1.bin, column_2.bin, and others are **column-store files after the single column is compressed by block.**

To be more specific, a single column of data may correspond to multiple column-store files.



## MergeTree Query 

It is roughly divided into two parts: index retrieval and data scanning.

### Index Retrieval

MergeTree storage extracts the KeyCondition of the partition key and the primary key in the query when receiving a select query.

1. prune irrelevant data partitions with the partition key KeyCondition first.
2. select the rough Mark Ranges using the primary key index.
3. filter the Mark Ranges generated by the primary key index with skipping index

### Data Scanning 

MergeTree provides three different modes for data scanning: Final Mode, Sorted Mode, **Normal Mode**

Data is scanned in parallel among multiple Data Parts, which can achieve very high data reading throughput for a single query.

The following describes several key performance optimizations in the Normal mode:

- **Parallel Scanning**

ClickHouse adds the Mark Range parallelism feature to the MergeTree Data Part parallelism feature. Users can set the parallelism in the data scanning process at will.

- Data Cache 
- SIMD Deserialization 
- PreWhere Filtering 



## Materialized View 

https://clickhouse.com/docs/en/guides/developer/cascading-materialized-views



## Optimization 

### Compression

The compression rate is **closely co-related to which pattern and how sparse and distributed given dataset is**, but basically that we can expect to achieve significant amount of raw dataset would be compressed. 

Examples. 

- uk_price_paid 

https://clickhouse.com/docs/en/getting-started/example-datasets/uk-price-paid/

7.54GB (raw) → 299.65MB (compressed) (25.76x)

```
0 rows in set. Elapsed: 848.875 sec. Processed 27.84 million rows, 7.54 GB (32.79 thousand rows/s., 8.88 MB/s.)
=> 

SELECT formatReadableSize(total_bytes)
FROM system.tables
WHERE name = 'uk_price_paid'

Query id: edc4dddc-e1b1-49fe-9505-3576222162d2
┌─formatReadableSize(total_bytes)─┐
│ 299.65 MiB                      │
└─────────────────────────────────┘
```



- nyc_taxi

https://clickhouse.com/docs/en/getting-started/example-datasets/nyc-taxi

228.06MB (raw) → 121.23MB (compressed) (1.88x)

```
0 rows in set. Elapsed: 61.972 sec. Processed 3.00 million rows, 228.06 MB (48.41 thousand rows/s., 3.68 MB/s.)
=> 

┌─formatReadableSize(total_bytes)─┐
│ 121.23 MiB                      │
└─────────────────────────────────┘
```





## Use Cases

https://clickhouse.com/docs/en/about-us/adopters

- CloudFlare
  - All DNS AND HTTP logs (over 10M of rows/s) 
  - Moved from PostgreSQL to ClickHouse 
  - 50+ servers, 120 TB per server 
  - https://blog.cloudflare.com/log-analytics-using-clickhouse/
  - https://blog.cloudflare.com/http-analytics-for-6m-requests-per-second-using-clickhouse/
- Uber 
  - Centralized logging platform 
  - Moved from ELK to ClickHouse 
  - 80% queries are aggregations
  - [Uber Engineering Blog - Fast and Reliable Schema-Agnostic Log Analytics Platform](https://www.uber.com/en-KR/blog/logging/)
  - https://presentations.clickhouse.com/meetup40/uber.pdf
- eBay
  - OLAP platform 
  - Moved from Druid to ClickHouse 
  - Reduced HW cost by over 90% - from 900 to 90 servers!
  - [eBay Engineering Blog - Our Online Analytical Processing Journey with ClickHouse on Kubernetes](https://tech.ebayinc.com/engineering/ou-online-analytical-processing/)



## Reference

- Apache HBase, Google BigTable 
  - [https://data-flair.training/blogs/hbase-architecture/](https://data-flair.training/blogs/hbase-architecture/)
  - [https://www.slideshare.net/quipo/nosql-databases-why-what-and-when/127-Google_BigTable_Architecture_fs_metadata](https://www.slideshare.net/quipo/nosql-databases-why-what-and-when/127-Google_BigTable_Architecture_fs_metadata)
- ClickHouse doc
  - [https://clickhouse.com/docs/en/home/](https://clickhouse.com/docs/en/home/)
  - [https://clickhouse.com/docs/en/faq/general/why-clickhouse-is-so-fast/](https://clickhouse.com/docs/en/faq/general/why-clickhouse-is-so-fast/)
  - [https://www.alibabacloud.com/blog/clickhouse-kernel-analysis-storage-structure-and-query-acceleration-of-mergetree_597727](https://www.alibabacloud.com/blog/clickhouse-kernel-analysis-storage-structure-and-query-acceleration-of-mergetree_597727)
  - [https://clickhouse.com/company/events/getting-started-with-clickhouse](https://clickhouse.com/company/events/getting-started-with-clickhouse)

- Conferences 
  - [Secrets of ClickHouse Query Performance](https://www.youtube.com/watch?v=6WICfakG84c)
  - [The Secrets of ClickHouse Performance Optimizations at BDTC 2019](https://www.youtube.com/watch?v=ZOZQCQEtrz8)
  - [Introducing ClickHouse -- The Fastest Data Warehouse You've Never Heard Of (Robert Hodges, Altinity)](https://www.youtube.com/watch?v=fGG9dApIhDU)
  - [A Day in the Life of a ClickHouse Query — Intro to ClickHouse Internals ClickHouse Tutorial](https://www.youtube.com/watch?v=XpkFEj1rVXg)



### Additional Ref 

- [https://clickhouse.com/docs/en/concepts/why-clickhouse-is-so-fast](https://clickhouse.com/docs/en/concepts/why-clickhouse-is-so-fast)
- [https://altinity.com/blog/2020/1/1/clickhouse-cost-efficiency-in-action-analyzing-500-billion-rows-on-an-intel-nuc](https://altinity.com/blog/2020/1/1/clickhouse-cost-efficiency-in-action-analyzing-500-billion-rows-on-an-intel-nuc)
- [http://www.cs.columbia.edu/~kar/pubsk/simd.pdf](http://www.cs.columbia.edu/~kar/pubsk/simd.pdf)
- [https://www.sciencedirect.com/topics/computer-science/single-instruction-multiple-data](https://www.sciencedirect.com/topics/computer-science/single-instruction-multiple-data)

- Blog 
  - [https://clickhouse.com/blog/introduction-to-the-clickhouse-query-cache-and-design](https://clickhouse.com/blog/introduction-to-the-clickhouse-query-cache-and-design)
  - [https://clickhouse.com/blog/using-ttl-to-manage-data-lifecycles-in-clickhouse](https://clickhouse.com/blog/using-ttl-to-manage-data-lifecycles-in-clickhouse)
  - [https://clickhouse.com/blog/data-formats-clickhouse-csv-tsv-parquet-native](https://clickhouse.com/blog/data-formats-clickhouse-csv-tsv-parquet-native)



