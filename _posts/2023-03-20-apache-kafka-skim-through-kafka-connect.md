---
layout: post
title: Apache Kafka - Skim Through Kafka Connect 
subheading: 
author: taehyeok-jang
categories: [stream-processing]
tags: [kafka]
---



이번 글에서는 Kafka Connect를 소개하고 Kafka Connect를 도입하기 위해 필요한 고려사항을 살펴본 이후에, Kafka Connect를 사용한 간단한 파이프라인을 만들어보겠습니다. 



## What is Kafka Connect?

![ingest-data-upstream-systems](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/1262f09a-5c1f-49b5-b5b3-1538c196112d)

![kafka_connect_architecture](/Users/jth/Desktop/Screenshot/kafka_connect_architecture.png)

Kafka Connect는 Apache Kafka의 컴포넌트들 중 하나로, database, 클라우드 서비스, 검색 인덱스, 파일 시스템, 키-값 저장소와 같은 다른 시스템과의 streaming을 수행하는 데 사용됩니다.

Kafka Connect를 사용하면 다양한 소스에서 Kafka로 데이터를 streaming하는 것(source)은 물론, Kafka에서 다양한 외부 시스템으로 데이터를 streaming하는 것(sink)이 쉬워집니다. 위의 다이어그램은 이러한 source와 sink가 가능한 대상 시스템들의 일부를 보여줍니다. Kafka Connect에는 외부 시스템과 Kafka Connect 간의 connection 및 streaming을 위한 수백 가지 다른 connector가 있습니다. d아래는 몇 가지 예시입니다. 

- RDBMS (Oracle, SQL Server, Db2, Postgres, MySQL)
- Cloud object stores (Amazon S3, Azure Blob Storage, Google Cloud Storage)
- NoSQL and document stores (Elasticsearch, MongoDB, Cassandra)
- Cloud data warehouses (Snowflake, Google BigQuery, Amazon Redshift)



## Related KIPs (Kafka Improvement Proposal) 

다음은 Kafka Connect의 기반 기술이 되는 Kafka의 여러 개선에 알아보겠습니다. KIP는 Kafka Improvement Proposal의 약자로 Apache Kafka 커뮤니티에서 사용하는 공식적인 프로세스입니다. Kafka의 여러 이슈들 중에서 major change에 해당하는 이슈에 대해 제안하고 논의하기 위해 사용됩니다. 

### KIP-98: Exactly Once Delivery and Transactional Messaging

[https://cwiki.apache.org/confluence/display/KAFKA/KIP-98+-+Exactly+Once+Delivery+and+Transactional+Messaging](https://cwiki.apache.org/confluence/display/KAFKA/KIP-98+-+Exactly+Once+Delivery+and+Transactional+Messaging)

이전 버전의 Kafka에서는 at-least-once semantics을 지원하여, producer가 retry를 하는 상황에서 broker에 메시지가 중복으로 저장되었습니다. 또한 부분 실패 시에 메세지가 일부 topic partition에만 저장되는 문제가 있었습니다. 

하지만 producer id, transactional id 를 각각 도입하여, broker에서 중복 메시지를 제거하고 부분 실패 상황에서도 메시지를 transactional(all or nothing)한 방식으로 저장할 수 있게 되었습니다. 

### KIP-318: Make Kafka Connect Source idempotent

[https://cwiki.apache.org/confluence/display/KAFKA/KIP-318%3A+Make+Kafka+Connect+Source+idempotent](https://cwiki.apache.org/confluence/display/KAFKA/KIP-318%3A+Make+Kafka+Connect+Source+idempotent)

Kafka의 exactly-once delivery, transactional messaging을 Kafka Connect에도 적용하였습니다. 

### KIP-618: Exactly-Once Support for Source Connectors

https://cwiki.apache.org/confluence/display/KAFKA/KIP-618%3A+Exactly-Once+Support+for+Source+Connectors

위 개선들을 통해 Kafka Connect에서 sink에 대한 exactly-once delivery는 지원이 가능했지만 source에서는 여전히 불가능했었습니다. 

이번 개선에서는 atomic offset writes, per-connector offset topics을 통해 source에서도 exactly-once delivery가 가능하도록 하였습니다. 



## Kafka Connect vs Own Kafka Producer/Consumer? 

Kafka Connect을 도입하기에 앞서 다음과 같은 고민이 들 수도 있습니다. 데이터 처리 스트리밍을 구현하는 것은 Kafka Producer/Consumer를 조합하는 방식으로도 가능한데 별도의 플랫폼을 구축하는 것이 필요한지? 개발 팀에게 익숙한 Kafka 스택을 넘어서 굳이 새로운 기술을 채택해야하는지? 

하지만 Kafka를 데이터 저장소에 연결하는 앱을 작성하는 것은 간단해 보이지만, 이 과정에서 고려해야 할 점들이 다양하게 있습니다. 아래 문제들은 application에서 producer/consumer을 통해 직접 구현했을 때 해결해야 할 문제들이며 이를 개발하고 검증하려면 오랜 노력이 필요합니다.

- 부분 실패 및 재시작 처리 
- logging 
- data load에 따른 scale up/down
- 분산 모드에서 실행 
- Serialization 및 data format 

Kafka Connect는 이미 위의 모든 문제를 해결하면서 성장한 framework입니다. 또한 configuration 관리, offset storage, parallelization, error handling, 다양한 데이터 유형 지원 및 표준 관리 REST API와 기능을 제공합니다. 따라서 단순히 어플리케이션 로직 처리가 아니라 **스트리밍 플랫폼을 구축하기를 원한다면 Kafka Connect**을 사용하는 것을 추천합니다. 



## CDC by Query-based vs Log-based

대표적인 관계형 데이터베이스인 MySQL에 Kafka Connect를 연결하기 위한 connector로 두가지를 찾을 수 있습니다.

- JDBC Connector (query-based)
- Debezium Connector (log-based)

위 connector들은 데이터 저장소에서 데이터 변화를 감지(CDC, changed data capture)하기 위한 각각의 방식을 채택하고 있으며 아래 장단점들을 가지고 있습니다. Query-based는 비교적 쉬운 설정 및 낮은 비용이 장점인 반면, Log-based는 DB에 별도의 부하가 없는 점, 실시간 데이터 변화 감지 등이 장점입니다. 



### Query-based CDC

#### 장점 

1. Usually easier to setup
2. Requires fewer permissions

### 단점

1. Impact of polling the DB
2. Needs specific columns in source schema to track changes
3. Can't track deletes
4. Can't track multiple events between polling interval

### Log-based CDC

#### 장점

1. All data changes are captured
2. Low delays of events while avoiding increased CPU load
3. No impact on data model
4. Can capture deletes
5. Can capture old record state and further meta data

#### 단점 

1. More setup steps
2. Higher system previleges required
3. Can be expensive for some proprietary DB





## Kafka Connect 실습 

Kafka Connect을 통해 file stream을 읽는 스트리밍 파이프라인을 구성해보겠습니다. 실습은 Udemy의 Kafka Connect 강의를 참고하였습니다. 

![udemy_apache_kafka_connect](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/6f95fea4-5057-4e09-8e6d-64eb65f7220e)



Kafka Connect는 standalone, distributed mode로 실행이 가능하며 실습에서는 distributed mode로 실행하겠습니다.



Kafka Connect 설정 파일입니다. 

```shell
# config/connect-distributed.properties

bootstrap.servers=ec2-kafka:9092
group.id=connect-cluster

key.converter=org.apache.kafka.connect.json.JsonConverter
value.converter=org.apache.kafka.connect.json.JsonConverter
key.converter.schemas.enable=true
value.converter.schemas.enable=true

offset.storage.topic=connect-offsets
offset.storage.replication.factor=1

config.storage.topic=connect-configs
config.storage.replication.factor=

status.storage.topic=connect-status
status.storage.replication.factor=1

offset.flush.interval.ms=10000
```



Kafka Connect를 distributed mode로 실행합니다. 

```shell
> bin/connect-distributed.sh config/connect-distributed.properties

> curl -s localhost:8083
{"version":"2.5.0","commit":"<commit>","kafka_cluster_id":"<cluster_id>"}
> curl -s localhost:8083/connector-plugins
[{"class":"org.apache.kafka.connect.file.FileStreamSinkConnector","type":"sink","version":"2.5.0"},
{"class":"org.apache.kafka.connect.file.FileStreamSourceConnector","type":"source","version":"2.5.0"},
{"class":"org.apache.kafka.connect.mirror.MirrorCheckpointConnector","type":"source","version":"1"},
{"class":"org.apache.kafka.connect.mirror.MirrorHeartbeatConnector","type":"source","version":"1"},
{"class":"org.apache.kafka.connect.mirror.MirrorSourceConnector","type":"source","version":"1"}]
```



Kafka Connect가 실행되었으면 FileStreamSourceConnector 등록합니다. source에서 데이터 스트림을 읽어서 'connect-test' topic에 저장합니다. 

```shell
curl --request POST 'localhost:8083/connectors' \
--header 'Content-Type: application/json' \
--data-raw '{
    "name": "file-source-connector",
    "config": {
        "connector.class": "org.apache.kafka.connect.file.FileStreamSourceConnector",
        "tasks.max": "1",
        "topic": "connect-test",
        "file": "~/test.txt"
    }
}'
```



파일에 텍스트를 입력합니다.

```java
> echo hello >> test.txt
> echo world >> test.txt
> echo !!! >> test.txt
> echo ??? >> test.txt
```



데이터가 source로부터 잘 입력되었는지 확인합니다. 

```
> ./kafka-console-consumer.sh --bootstrap-server ec2-kafka:9092 --topic connect-test --from-beginning                   
{"schema":{"type":"string","optional":false},"payload":"hello"}
{"schema":{"type":"string","optional":false},"payload":"world"}
{"schema":{"type":"string","optional":false},"payload":"!!!"}
{"schema":{"type":"string","optional":false},"payload":"???"}
```





## References

- What is Kafka Connect?
  - [https://developer.confluent.io/courses/kafka-connect/intro/](https://developer.confluent.io/courses/kafka-connect/intro/)

- Related KIPs (Kafka Improvement Proposal) 
  - [Kafka Improvement Proposal](https://cwiki.apache.org/confluence/display/KAFKA/Kafka+Improvement+Proposals)
- Kafka Connect vs Own Kafka Producer/Consumer? 
  - [https://stackoverflow.com/questions/59495694/kafka-design-questions-kafka-connect-vs-own-consumer-producer](https://stackoverflow.com/questions/59495694/kafka-design-questions-kafka-connect-vs-own-consumer-producer)
  - [https://medium.com/@stephane.maarek/the-kafka-api-battle-producer-vs-consumer-vs-kafka-connect-vs-kafka-streams-vs-ksql-ef584274c1e](https://medium.com/@stephane.maarek/the-kafka-api-battle-producer-vs-consumer-vs-kafka-connect-vs-kafka-streams-vs-ksql-ef584274c1e)
  - [https://community.cloudera.com/t5/Support-Questions/When-to-use-Kafka-Connect-vs-Producer-and-Consumer/m-p/160485#M122870](https://community.cloudera.com/t5/Support-Questions/When-to-use-Kafka-Connect-vs-Producer-and-Consumer/m-p/160485#M122870)
- CDC by Query-based vs Log-based
  - [https://stackoverflow.com/questions/65612131/usability-of-binary-log-in-data-streaming-in-mysql-what-are-the-drawbacks-and-a](https://stackoverflow.com/questions/65612131/usability-of-binary-log-in-data-streaming-in-mysql-what-are-the-drawbacks-and-a)
- Kafka Connect 실습 
  - [https://www.udemy.com/course/kafka-connect/](https://www.udemy.com/course/kafka-connect/)
