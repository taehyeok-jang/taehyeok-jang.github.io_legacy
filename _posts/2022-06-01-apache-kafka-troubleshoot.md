---
layout: post
title: Apache Kafka - Troubleshoot 
subheading: 
author: taehyeok-jang
categories: [stream-processing]
tags: [kafka, troubleshoot]

---

 

이 글은 Apache Kafka를 사용하면서 발생할 수 있는 문제들과 그 해결책에 대해서 정리한 글입니다. 



## Producer에서 발생하는 문제 

### NotLeaderForPartitionException: This server is not the leader for that topic-partition.. Going to request metadata update now 

```
WARN [Producer clientId=test-producer] Received invalid metadata error in produce request on partition <topic> due to org.apache.kafka.common.errors.NotLeaderForPartitionException: This server is not the leader for that topic-partition.. Going to request metadata update now (org.apache.kafka.clients.producer.internals.Sender)
```



#### Cause

Kafka producer에서 produce 및 fetch 요청은 partition의 leader replica로 보내집니다. NotLeaderForPartitionException 예외는 해당 요청이 현재 partition의 leader replica가 아닌 곳으로 보내질 때 발생합니다.

클라이언트는 각 partition의 leader에 대한 metadata 정보를 캐시로 유지합니다. 캐시 관리의 전체 과정은 아래에 나와 있습니다. producer config에서 `metadata.max.age.ms`(default 5분)을 설정하여 아래 과정이 정기적으로 발생하도록 해야합니다.

![apache_kafka_metadata_req](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/37c27ac2-897b-4cc3-b392-5b54c843a272)



#### Resolution 

이 문제는 실제로 개발자가 직접 이 문제를 해결할 필요는 없습니다. 

이는 Kafka cluster 운영 중 old node에서 new node로의 failover의 일부로 예상되는 동작이기 때문입니다. 클러스터 내 node가 교체되면 partition leader가 변경될 것으로 예상됩니다. 모든 partition leader는 한 번 이상 변경되지만 node 수와 한 번에 교체되는 node 수에 따라 더 많이 변경될 수 있습니다.

또한 producer에서는 주기적 poll (metadata.max.age.ms 마다) 또는 NotLeaderForPartitionException가 발생한 즉시 cluster metadata 캐시를 업데이트하여 문제 없이 메시지를 produce 합니다. 하지만 종종 broker 측의 문제로 인해 (overloaded throughput, node replacement requests in parallel) 동시에 여러 node 교체가 발생할 수 있습니다. 이때 마찬가지로 동일한 문제가 발생할 수 있지만 실제로는 영향이 없습니다. 



## Consumer에서 발생하는 문제 

### CommitFailedException: Commit cannot be completed since the group has already rebalanced and assigned the partitions to another member

```
org.apache.kafka.clients.consumer.CommitFailedException: Commit cannot be completed since the group has already rebalanced and assigned the partitions to another member. This means that the time between subsequent calls to poll() was longer than the configured max.poll.interval.ms, which typically implies that the poll loop is spending too much time message processing. You can address this either by increasing the session timeout or by reducing the maximum size of batches returned in poll() with max.poll.records.
at org.apache.kafka.clients.consumer.internals.ConsumerCoordinator$OffsetCommitResponseHandler.handle(ConsumerCoordinator.java:775)
```



#### Cause 

Kafka consumer에서 메시지를 poll하여 처리하는 도중에, consumer group에서 rebalancing 이 발생하여 해당 consumer가 consumer group에서 제외되어 commit에 실패했습니다.

consumer application 운영 중 이 에러가 처음 발생했을 때 일시적인 문제라고 생각하고 대수롭지 않게 여겼습니다. 분산 시스템에서는 네트워크 지연 등으로 인한 부분 실패가 빈번하게 발생할 수 있고, 이를 대비하여 consumer 로직을 at-least-once 방식으로 구현하여 commit에 실패한 메시지들이 금방 재시도 처리될 것이기 때문입니다. 하지만 지속적으로 이 문제가 발생하여 원인에 대해 제대로 살펴보고 해결하기로 했습니다.



#### Rebalance? 

![apache_kafka_rebalancing](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/b3f3865c-2b27-4595-a9e4-90cda5312a1b)

(figure. rebalancing process)

rebalance는 consumer group들을 재조정하는 작업을 의미합니다. 새로운 consumer가 consumer group에 추가되거나, consumer consumer에서 특정한 consumer가 제외되었을 때 각 consumer들이 소비하고 있는 partition들에 대한 재조정이 필요한데 이를 rebalancing 이라 합니다.

consumer가 소속 consumer group에서 제외되는 rebalancing이 발생하는 원인은 다음의 두가지입니다.

- consumer의 메시지 처리 지연으로 인해 poll이 호출되는 간격이 `max.poll.interval.ms`를 초과하는 경우
- consumer 인스턴스 자체의 문제로 GroupCoordinator가 `session.timeout.ms` 이내에 heartbeat를 수신 받지 못한 경우 (heartbeat signal은 consumer에서 3초(default)에 한번씩 주기적으로 broker에 보내집니다)

위의 상황에서 Kafka의 GroupCoordinator는 해당 consumer에 문제가 있는 것으로 판단하여 consumer group에서 제외시킵니다. 



#### Resolution 

consumer의 메시지 처리 지연의 경우 문제 해결을 위해 두가지 접근이 가능합니다. 먼저 한번의 poll로 가져오는 메시지의 수를 줄이는 것입니다. `max.poll.records` (default 500)으로 개수를 조정할 수 있습니다. 두번째는 poll을 호출되는 간격을 늘리는 것입니다. `max.poll.interval.ms` (default 5분)를 더 높은 값으로 설정합니다.

GroupCoordinator가 heartbeat를 제대로 수신 받지 못한 경우에는 consumer가 heartbeat를 더 자주 보내도록 하거나 GroupCoordinator에게 조금 더 신호를 오래 기다리도록 할 수 있습니다. `heartbeat.interval.ms` (default 2초)를 더 낮은 값으로, `session.timeout.ms` (default 10초)를 더 높은 값으로 설정합니다. 



#### Trade-off

위의 제안에 따라 설정들을 조정함으로써 consumer가 consumer group으로부터 제외되는 상황을 방지할 수 있지만 모든 상황에서 맞는 해결 방법은 아닙니다.

consumer의 메시지 처리 지연의 경우 `max.poll.records` 를 너무 낮게 설정하면 (ex. max.poll.records=1) consumer와 broker 간 요청이 증가하여 broker에 네트워크 부하가 발생합니다. 또 메시지 처리 지연 문제 자체를 해결할 필요가 있습니다. consumer application에서 long query 등의 작업으로 인해 한 개의 메시지를 처리를 처리하는데 오랜 시간이 걸린다면 이를 해결하는 것이 좋겠습니다. 만약 message throughput이 굉장히 높은 상황임에도 불구하고, commit 실패가 반복해서 일어난다고 `max.poll.records`는 작게, `max.poll.interval.ms`를 높게 설정하면 해당 topic의 lag으로 이어질 수도 있습니다.

![apache_kafka_consumer_lag_metric](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/dc28c892-1f62-4e56-8d67-5e60601c08dc)

heartbeat와 관련된 문제에서도 주의가 필요합니다. consumer 어플리케이션이 실제로 shut-down 된 상황에서도 GroupCoordinator는 `session.timeout.ms` 만큼 기다리게되므로 무작정 값을 높게 설정했다가는 rebalancing을 하기까지 불필요한 시간이 소요될 수 있습니다. 따라서 서버의 성능이나 어플리케이션의 상황에 맞춰서 적정하게 값을 조정하는 것이 좋겠습니다. 



## References

- Apache Kafka offical document 
  - [https://kafka.apache.org/documentation](https://kafka.apache.org/documentation)
- Kafka Internal 
  - [KafkaConsumer Client Internals - NAVER D2](https://d2.naver.com/helloworld/0974525)
- Problems in Producer 
  - [Stack Overflow - Kafka producer fails to send messages with NOT_LEADER_FOR_PARTITION exception](https://stackoverflow.com/questions/61798565/kafka-producer-fails-to-send-messages-with-not-leader-for-partition-exception)
- Problems in Consumer 
  - [https://www.confluent.io/blog/kafka-lag-monitoring-and-metrics-at-appsflyer/](https://www.confluent.io/blog/kafka-lag-monitoring-and-metrics-at-appsflyer/)
  - [https://github.com/ClickHouse/ClickHouse/issues/44884](https://github.com/ClickHouse/ClickHouse/issues/44884)





