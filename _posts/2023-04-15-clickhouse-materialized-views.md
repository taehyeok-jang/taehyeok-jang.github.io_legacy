---
layout: post
title: Clickhouse - Materialized View
subheading: 
author: taehyeok-jang
categories: [database]
tags: [clickhouse, materialized-view]
---



이전 글에서 살펴보았듯이, ClickHouse는 distributed column-oriented SQL data warehouse로 anlaytical purpose에 필요한 저장, 연산 등 핵심적인 역할을 수행할 수 있습니다. 그러나 여전히, ClickHouse의 Materialized View를 통해서 aggregation과 같은 computation의 영역에서 성능과 데이터 관리성을 더 높일 수 있습니다. 

이번 글에서는 ClickHouse의 materialized view에 대해서 알아보고 몇가지 활용 사례에 대해서도 살펴보겠습니다.



## What is a Materialized View? 

<img src="https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/77eefcbc-cb92-44d2-bab0-fbfc43a7f9b8" alt="materialized_view_5a321dc56d" style="zoom: 33%;" />



Materialized view는 ClickHouse에서 지원하는 view의 한 종류입니다. view (normal view)는 SELECT query 라고 할 수 있습니다. 하지만 normal view는 아무런 데이터도 저장하지 않는 반면 materialized view는 실제로 별도의 테이블에 SELECT query의 결과로 얻어지는 데이터들을 저장합니다. materialized view는 source table과 연결되어, 새로운 데이터가 source table에 insert 되었을 때 동일한 row가 materialized view에도 저장됩니다. 

| Type         | **Description**                                              |
| :----------- | :----------------------------------------------------------- |
| Normal       | Nothing more than a **saved query**. When reading from a view, this saved query is used as a subquery in the **FROM** clause. |
| Materialized | **Stores the results** of the corresponding **SELECT** query. |

ClickHouse에서는 materialized view를 통해서 다음과 같은 작업을 할 수 있습니다.

- compute aggregates, 
- read data from Kafka, 
- implement last point queries, and 
- reorganize table primary indexes and sort order. 

이러한 기능들을 단순히 제공하는 것을 넘어서, ClickHouse는 이 materialized view 기능을 large dataset을 대상으로 여러 node들에서 수행될 수 있도록 하는 확장성을 제공합니다. 



## Using Materialized View: Computing Sums

materialized view를 통해서 sum 연산을 해보도록 하겠습니다.

테스트 dataset은 [wikistat](https://clickhouse.com/docs/en/getting-started/example-datasets/wikistat) 을 활용하였으며 데이터의 크기는 총 1B row입니다. 

```
CREATE TABLE wikistat
(
    `time` DateTime CODEC(Delta(4), ZSTD(1)),
    `project` LowCardinality(String),
    `subproject` LowCardinality(String),
    `path` String,
    `hits` UInt64
)
ENGINE = MergeTree
ORDER BY (path, time);


INSERT INTO wikistat SELECT *
FROM s3('https://ClickHouse-public-datasets.s3.amazonaws.com/wikistat/partitioned/wikistat*.native.zst') LIMIT 1e9

...
Query id: 66b182ad-2422-4319-854f-50056aebba96
← Progress: 1.00 billion rows, 1.99 GB (2.27 million rows/s., 4.52 MB/s.)

Elapsed: 499.015 sec. Processed 1.00 billion rows, 1.99 GB (2.00 million rows/s., 3.99 MB/s.)
Peak memory usage: 362.64 MiB.
```



특정 날짜에 project 별로 방문자수 별 랭킹을 확인하는 query를 실행해보겠습니다. ClickHouse Cloud 기준으로 query가 수행되는데 약 15초가 걸렸습니다. 

```
SELECT
    project,
    sum(hits) AS h
FROM wikistat
WHERE date(time) = '2015-05-01'
GROUP BY project
ORDER BY h DESC
LIMIT 10

Query id: bd1509b8-27ac-4830-a569-1b8edf3b1cdc

┌─project─┬────────h─┐
│ en      │ 32651529 │
│ es      │  3843097 │
│ de      │  3581099 │
│ fr      │  2970210 │
│ it      │  1719488 │
│ ja      │  1387605 │
│ pt      │  1173172 │
│ commons │   962568 │
│ zh      │   931435 │
│ tr      │   735252 │
└─────────┴──────────┘

10 rows in set. Elapsed: 14.869 sec. Processed 972.80 million rows, 10.53 GB (65.43 million rows/s., 708.05 MB/s.)
```



ClickHouse가 column-oriented 저장소로서 aggregation 연산에 특화되어 있지만 10B row의 크기 때문에 시간이 상당히 소요되었습니다. 만약 전체 연산에서 이 쿼리를 빈번하게 호출한다면 그때마다 병목이 발생합니다.



이때 materialized view를 활용해서 최적화가 가능합니다. 

materialized view는 원하는 만큼 생성할 수 있지만 materialized view를 여러개 생성하면 storage load가 발생할 수 있기 때문에 테이블 별로 10개 이하의 materialized view를 권장한다고 합니다. 

```
CREATE TABLE wikistat_top_projects
(
    `date` Date,
    `project` LowCardinality(String),
    `hits` UInt32
)
ENGINE = SummingMergeTree
ORDER BY (date, project);

Ok.

CREATE MATERIALIZED VIEW wikistat_top_projects_mv TO wikistat_top_projects AS
SELECT
    date(time) AS date,
    project,
    sum(hits) AS hits
FROM wikistat
GROUP BY
    date,
    project;
```



- `wikistat_top_projects` is the name of the table that we’re going to use to save a materialized view,
- `wikistat_top_projects_mv` is the name of the materialized view itself (the trigger),
- we’ve used [SummingMergeTree](https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/summingmergetree/) because we would like to have our hits value summarized for each date/project pair,
- everything that comes after `AS` is the query that the materialized view will be built from.









## References

- ClickHouse 
  - [https://clickhouse.com/blog/using-materialized-views-in-clickhouse](https://clickhouse.com/blog/using-materialized-views-in-clickhouse)
  - [https://clickhouse.com/docs/en/sql-reference/statements/create/view#materialized-view](https://clickhouse.com/docs/en/sql-reference/statements/create/view#materialized-view)
  - [https://learn.clickhouse.com/learner_module/show/1043451?lesson_id=5684730&section_id=48330606](https://learn.clickhouse.com/learner_module/show/1043451?lesson_id=5684730&section_id=48330606)
  - [https://clickhouse.com/docs/knowledgebase/are_materialized_views_inserted_asynchronously](https://clickhouse.com/docs/knowledgebase/are_materialized_views_inserted_asynchronously)
  - [https://clickhouse.com/docs/en/integrations/kafka/kafka-table-engine](https://clickhouse.com/docs/en/integrations/kafka/kafka-table-engine)
  
- Affinity 
  - [https://altinity.com/blog/clickhouse-materialized-views-illuminated-part-1](https://altinity.com/blog/clickhouse-materialized-views-illuminated-part-1)
  - [https://altinity.com/blog/clickhouse-materialized-views-illuminated-part-2](https://altinity.com/blog/clickhouse-materialized-views-illuminated-part-2)
- ETC
  - [https://quoeamaster.medium.com/several-things-you-need-to-know-about-materialized-view-in-clickhouse-ec57b890ef6c](https://quoeamaster.medium.com/several-things-you-need-to-know-about-materialized-view-in-clickhouse-ec57b890ef6c)

