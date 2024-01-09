---
layout: post
title: Clickhouse - Materialized View
subheading: 
author: taehyeok-jang
categories: [database]
tags: [clickhouse, materialized-view]
---



[ClickHouse 1편 - Clickhouse Internal](https://taehyeok-jang.github.io/database/2023/04/01/clickhouse-internal.html)

이전 글에서 알아보았듯이 ClickHouse는 distributed column-oriented SQL data warehouse로서 anlaytical purpose을 위한 저장, 연산 등 핵심적인 역할을 수행합니다. 그러나 여전히 ClickHouse는 materialized view라는 도구를 통해서 쿼리 성능을 향상시키고 데이터 관리성을 높일 수 있는 잠재력을 가지고 있습니다. 

이번 글에서는 ClickHouse의 materialized view에 대해서 알아보고 몇가지 활용 사례에 대해서도 소개하겠습니다.



## What is a Materialized View? 

<img src="https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/77eefcbc-cb92-44d2-bab0-fbfc43a7f9b8" alt="materialized_view_5a321dc56d" style="zoom: 33%;" />



Materialized view는 ClickHouse에서 지원하는 view의 한 종류입니다. 일반적인 view는 단순한 SELECT 쿼리문 라고 할 수 있습니다. 하지만 이러한 view는 아무런 데이터도 저장하지 않는 반면, materialized view는 실제로 별도의 테이블에 SELECT쿼리의 결과로 얻어지는 데이터들을 저장합니다. materialized view는 source table과 연결되어, 새로운 데이터가 source table에 insert 되었을 때 동일한 row가 materialized view에도 저장됩니다. 

| Type         | **Description**                                              |
| :----------- | :----------------------------------------------------------- |
| Normal       | Nothing more than a **saved query**. When reading from a view, this saved query is used as a subquery in the **FROM** clause. |
| Materialized | **Stores the results** of the corresponding **SELECT** query. |

ClickHouse에서는 materialized view를 통해서 다음과 같은 작업을 할 수 있습니다.

- compute aggregates
- read data from Kafka 
- implement last point queries
- reorganize table primary indexes and sort order

이러한 기능들을 단순히 제공하는 것 이상으로 ClickHouse는 materialized view를 large dataset을 대상으로 여러 node들에서 수행될 수 있도록 하는 확장성을 제공합니다. 



## Using Materialized View: Computing Sums

분석을 위한 대표적인 연산인 aggregation 연산을 materialized view을 통해서 수행해보겠습니다.

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
```

```
Query id: 66b182ad-2422-4319-854f-50056aebba96
← Progress: 1.00 billion rows, 1.99 GB (2.27 million rows/s., 4.52 MB/s.)

Elapsed: 499.015 sec. Processed 1.00 billion rows, 1.99 GB (2.00 million rows/s., 3.99 MB/s.)
Peak memory usage: 362.64 MiB.
```



특정 날짜에 project 별로 방문자수 별 랭킹을 확인하는 쿼리를 실행해보겠습니다. 

ClickHouse Cloud 기준으로 약 15초가 걸렸습니다. column-oriented 저장소로서 aggregation 연산에 특화되어 있음에도 불구하고 대량의 데이터를 연산하는 탓에 상당한 시간이 소요되었습니다. 만약 전체 연산 흐름에서 이 쿼리를 빈번하게 실행한다면 병목이 발생할 것입니다.

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



이제 materialized view를 활용해서 쿼리를 수행하겠습니다.

materialized view는 원하는 만큼 생성할 수 있지만 materialized view의 개수가 늘어날수록 storage load가 발생할 수 있기 때문에 테이블 별로 10개 이하의 materialized view를 권장한다고 합니다. 

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

- `wikistat_top_projects` 는 materialized view의 결과를 저장할 대상 테이블입니다.
- `wikistat_top_projects_mv` materialized view 그 자체 (trigger)의 이름입니다.
- 대상 테이블인 `wikistat_top_projects`의 테이블 엔진으로는 [SummingMergeTree](https://clickhouse.com/docs/en/engines/table-engines/mergetree-family/summingmergetree/) 를 사용하였습니다. project 별 hits 값을 sum하는 연산을 수행하기 때문입니다.
- `AS` 이후가 materialized view의 생성을 위한 쿼리문입니다. 



`wikistat_top_projects` 테이블을 대상으로 쿼리를 수행하니 0.023초가 소요되었습니다. 

```
SELECT
    project,
    sum(hits) hits
FROM wikistat_top_projects
WHERE date = '2015-05-01'
GROUP BY project
ORDER BY hits DESC
LIMIT 10

┌─project─┬─────hits─┐
│ en      │ 34521803 │
│ es      │  4491590 │
│ de      │  4490097 │
│ fr      │  3390573 │
│ it      │  2015989 │
│ ja      │  1379148 │
│ pt      │  1259443 │
│ tr      │  1254182 │
│ zh      │   988780 │
│ pl      │   985607 │
└─────────┴──────────┘

10 rows in set. Elapsed: 0.023 sec. Processed 9.50 thousand rows, 76.00 KB (416.20 thousand rows/s., 3.33 MB/s.)
Peak memory usage: 18.73 KiB.
```



### Sync in Materialized Views

![updating_materialized_view_b90a9ac7cb](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/e766f386-6a11-48d5-9a97-0e5b672ce9e2)



materialized view를 사용하는 데 있어서 장점은 source table의 변경사항이 materialized view에도 실시간으로 반영이 된다는 점입니다. 이는 쿼리 최적화를 위해 materialized view를 더욱 유연하게 활용할 수 있다는 의미입니다. 



예제를 통해 살펴보겠습니다. 테이블은 device별 floating point 값을 저장합니다. 

```
CREATE TABLE counter (
  when DateTime DEFAULT now(),
  device UInt32,
  value Float32
) ENGINE=MergeTree
PARTITION BY toYYYYMM(when)
ORDER BY (device, when)
```



1B row개의 mock data를 입력하고 전체 기간에 대한 aggregation 쿼리를 수행해보겠습니다. 약 2.7초가 소요되는 것을 확인할 수 있습니다. 

```
INSERT INTO counter
  SELECT
    toDateTime('2015-01-01 00:00:00') + toInt64(number/10) AS when,
    (number % 10) + 1 AS device,
    (device * 3) +  (number/10000) + (rand() % 53) * 0.1 AS value
  FROM system.numbers LIMIT 1000000
  
SELECT
    device,
    count(*) AS count,
    max(value) AS max,
    min(value) AS min,
    avg(value) AS avg
FROM counter
GROUP BY device
ORDER BY device ASC
. . .
10 rows in set. Elapsed: 2.709 sec. Processed 1.00 billion rows, 8.00 GB (369.09 million rows/s., 2.95 GB/s.)
```



이제 materialized view를 생성하고 source table에 데이터를 insert하여 materialized view의 대상 테이블로 변경사항이 trigger 될 수 있도록 하겠습니다. 

```
CREATE TABLE counter_daily (
  day DateTime,
  device UInt32,
  count UInt64,
  max_value_state AggregateFunction(max, Float32),
  min_value_state AggregateFunction(min, Float32),
  avg_value_state AggregateFunction(avg, Float32)
)
ENGINE = SummingMergeTree()
PARTITION BY tuple()
ORDER BY (device, day)

CREATE MATERIALIZED VIEW counter_daily_mv
TO counter_daily
AS SELECT
    toStartOfDay(when) as day,
    device,
    count(*) as count,
    maxState(value) AS max_value_state,
    minState(value) AS min_value_state,
    avgState(value) AS avg_value_state
FROM counter
WHERE when >= toDate('2019-01-01 00:00:00')
GROUP BY device, day
ORDER BY device, day
```



source table에 데이터를 insert 합니다. 변경사항은 실시간으로 materialized view를 통해 udpate 됩니다. 

```
INSERT INTO counter
  SELECT
    toDateTime('2015-01-01 00:00:00') + toInt64(number/10) AS when,
    (number % 10) + 1 AS device,
    (device * 3) +  (number/10000) + (rand() % 53) * 0.1 AS value
  FROM system.numbers LIMIT 1000000
```

이제 쿼리를 수행하겠습니다. 0.015초만에 쿼리 수행이 완료되었습니다. 

```
SELECT
  device,
  sum(count) AS count,
  maxMerge(max_value_state) AS max,
  minMerge(min_value_state) AS min,
  avgMerge(avg_value_state) AS avg
FROM counter_daily
GROUP BY device
ORDER BY device ASC

=> 
Query id: 149617cf-a266-44ad-a193-de9ef50e9956

┌─device─┬───count─┬───────max─┬─────min─┬────────────────avg─┐
│      1 │ 1000000 │  1008.194 │   3.027 │  505.5990479240353 │
│      2 │ 1000000 │ 1011.1521 │  6.0191 │   508.598602163702 │
│      3 │ 1000000 │ 1014.1392 │  9.0012 │ 511.59625628831293 │
│      4 │ 1000000 │ 1017.1973 │ 12.0613 │  514.5981650169449 │
│      5 │ 1000000 │ 1020.1234 │ 15.0224 │  517.5985900957355 │
│      6 │ 1000000 │ 1023.1875 │ 18.0365 │  520.5979234121476 │
│      7 │ 1000000 │ 1026.1846 │ 21.0216 │  523.5997531775646 │
│      8 │ 1000000 │ 1029.1937 │ 24.0947 │  526.6002109527683 │
│      9 │ 1000000 │ 1032.0928 │ 27.0228 │  529.5988765025311 │
│     10 │ 1000000 │  1035.169 │ 30.0979 │  532.6029915245838 │
└────────┴─────────┴───────────┴─────────┴────────────────────┘

10 rows in set. Elapsed: 0.015 sec
```



## Using Materialized View: Kafka table engine

![kafka_01-807249e726cadc9d3be21375df967d42](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/27de1992-18fa-4d09-b19e-0611e5f1cb4b)

materialized view를 활용해서 ClickHouse의 테이블에 Kafka topic의 data stream을 저장하는 것이 가능합니다. 

Kafka table engine은 ClickHouse가 Kafka topic을 직접 읽는 것을 가능하게 합니다. 이때 Kafka table engine에서는 마지막으로 topic을 읽은 위치(offset)를 기억하여 poll을 통해 data stream을 한번씩 읽을 수 있도록 합니다.

Kafka table engine으로 읽은 topic을 저장하기 위해서는 이러한 data stream을 감지하고 테이블에 저장할 수 있는 장치가 필요한데, 바로 materialized view의 trigger 특성을 활용하여 가능합니다. Kafka topic을 Kafka table engine이 읽고, Kafka table engine의 변경사항으로 인해 발생하는 trigger를 materialized view가 감지하여 ClickHouse의 테이블에 저장합니다.

예제를 통해 살펴보겠습니다.

먼저 최종적으로 데이터를 저장할 테이블을 생성합니다. 테이블 엔진은 MergeTree을 사용했습니다. 

```
CREATE TABLE github
(
    file_time DateTime,
    event_type Enum('CommitCommentEvent' = 1, 'CreateEvent' = 2, 'DeleteEvent' = 3, 'ForkEvent' = 4, 'GollumEvent' = 5, 'IssueCommentEvent' = 6, 'IssuesEvent' = 7, 'MemberEvent' = 8, 'PublicEvent' = 9, 'PullRequestEvent' = 10, 'PullRequestReviewCommentEvent' = 11, 'PushEvent' = 12, 'ReleaseEvent' = 13, 'SponsorshipEvent' = 14, 'WatchEvent' = 15, 'GistEvent' = 16, 'FollowEvent' = 17, 'DownloadEvent' = 18, 'PullRequestReviewEvent' = 19, 'ForkApplyEvent' = 20, 'Event' = 21, 'TeamAddEvent' = 22),
    actor_login LowCardinality(String),
    repo_name LowCardinality(String),
    created_at DateTime,
    updated_at DateTime,
    action Enum('none' = 0, 'created' = 1, 'added' = 2, 'edited' = 3, 'deleted' = 4, 'opened' = 5, 'closed' = 6, 'reopened' = 7, 'assigned' = 8, 'unassigned' = 9, 'labeled' = 10, 'unlabeled' = 11, 'review_requested' = 12, 'review_request_removed' = 13, 'synchronize' = 14, 'started' = 15, 'published' = 16, 'update' = 17, 'create' = 18, 'fork' = 19, 'merged' = 20),
    comment_id UInt64,
    path String,
    ref LowCardinality(String),
    ref_type Enum('none' = 0, 'branch' = 1, 'tag' = 2, 'repository' = 3, 'unknown' = 4),
    creator_user_login LowCardinality(String),
    number UInt32,
    title String,
    labels Array(LowCardinality(String)),
    state Enum('none' = 0, 'open' = 1, 'closed' = 2),
    assignee LowCardinality(String),
    assignees Array(LowCardinality(String)),
    closed_at DateTime,
    merged_at DateTime,
    merge_commit_sha String,
    requested_reviewers Array(LowCardinality(String)),
    merged_by LowCardinality(String),
    review_comments UInt32,
    member_login LowCardinality(String)
) ENGINE = MergeTree ORDER BY (event_type, repo_name, created_at)
```



다음으로 Kafka table engine을 생성합니다. 

테이블 엔진을 Kafka로 합니다. 스키마가 대상 테이블과 일치하지만 반드시 같을 필요는 없습니다. 필요에 따라 Kafka table engine이나 materialized view에서 transform 과정을 포함시키기도 합니다. 

```
CREATE TABLE github_queue
(
    file_time DateTime,
    event_type Enum('CommitCommentEvent' = 1, 'CreateEvent' = 2, 'DeleteEvent' = 3, 'ForkEvent' = 4, 'GollumEvent' = 5, 'IssueCommentEvent' = 6, 'IssuesEvent' = 7, 'MemberEvent' = 8, 'PublicEvent' = 9, 'PullRequestEvent' = 10, 'PullRequestReviewCommentEvent' = 11, 'PushEvent' = 12, 'ReleaseEvent' = 13, 'SponsorshipEvent' = 14, 'WatchEvent' = 15, 'GistEvent' = 16, 'FollowEvent' = 17, 'DownloadEvent' = 18, 'PullRequestReviewEvent' = 19, 'ForkApplyEvent' = 20, 'Event' = 21, 'TeamAddEvent' = 22),
    actor_login LowCardinality(String),
    repo_name LowCardinality(String),
    created_at DateTime,
    updated_at DateTime,
    action Enum('none' = 0, 'created' = 1, 'added' = 2, 'edited' = 3, 'deleted' = 4, 'opened' = 5, 'closed' = 6, 'reopened' = 7, 'assigned' = 8, 'unassigned' = 9, 'labeled' = 10, 'unlabeled' = 11, 'review_requested' = 12, 'review_request_removed' = 13, 'synchronize' = 14, 'started' = 15, 'published' = 16, 'update' = 17, 'create' = 18, 'fork' = 19, 'merged' = 20),
    comment_id UInt64,
    path String,
    ref LowCardinality(String),
    ref_type Enum('none' = 0, 'branch' = 1, 'tag' = 2, 'repository' = 3, 'unknown' = 4),
    creator_user_login LowCardinality(String),
    number UInt32,
    title String,
    labels Array(LowCardinality(String)),
    state Enum('none' = 0, 'open' = 1, 'closed' = 2),
    assignee LowCardinality(String),
    assignees Array(LowCardinality(String)),
    closed_at DateTime,
    merged_at DateTime,
    merge_commit_sha String,
    requested_reviewers Array(LowCardinality(String)),
    merged_by LowCardinality(String),
    review_comments UInt32,
    member_login LowCardinality(String)
)
   ENGINE = Kafka('kafka_host:9092', 'github', 'clickhouse',
            'JSONEachRow') settings kafka_thread_per_consumer = 0, kafka_num_consumers = 1;
```



materialized view를 생성합니다.

```
CREATE MATERIALIZED VIEW github_mv TO github AS
SELECT *
FROM github_queue;
```



이제 Kafka topic으로 메시지를 publish합니다. 예제에서는 파일 스트림에 kafkacat을 연결하였습니다.

```
cat github_all_columns.ndjson | 
kcat -P \
  -b 'kafka_host:9092' \
  -t github
  -X security.protocol=sasl_ssl \
  -X sasl.mechanisms=PLAIN \
  -X sasl.username=<username>  \
  -X sasl.password=<password> \
```



결과를 확인합니다. 최종 테이블에 200K의 row가 잘 insert 된 것을 확인할 수 있습니다.

```
SELECT count() FROM github;
=> 
┌─count()─┐
│  200000 │
└─────────┘
```





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

