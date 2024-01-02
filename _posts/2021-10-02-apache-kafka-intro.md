---
layout: post
title: Apache Kafka - Introduction 
subheading: 
author: taehyeok-jang
categories: [stream-processing]
tags: [kafka]

---



이 글은 Apache Kafka의 공식 문서를 읽고 정리한 글입니다. 



## Introduction 

[https://kafka.apache.org/intro](https://kafka.apache.org/intro)

Kafka는 'distributed commit log' 또는 'distributed streaming platform'이라고 합니다. 

file system이나 database의 commit log는 system의 상태를 일관성 있게 기록할 수 있도록 모든 transaction을 지속적으로 기록하는 기능을 제공합니다. 이와 유사하게 Kafka도 data를 지속해서 저장하고 읽을 수 있습니다. 또한 시스템 실패에 대비하고 확장에 따른 성능 저하를 방지하기 위해 data를 분산 처리합니다. 

### Topic and Partitions

![kafka-topics](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/1724732a-3a04-4da3-9e59-24ee712c31bd)

Kafka의 message는 topic으로 분류되며 database의 table이나 file system의 directory와 유사합니다. 한 topic은 여러 개의 partition으로 구성되어 있으며 message는 각 partition에 추가되는 형태로만 추가됩니다. 특정 topic으로 message를 발행했을 때 어떤 partition에 속할지는 message key에 대한 hash로 결정됩니다. 

메시지 처리 순서는 topic이 아닌 partition 별로 유지 관리됩니다. 그림에서 알 수 있듯이 각 partition은 서로 다른 서버에 분산될 수 있습니다. 즉, 하나의 topic이 여러 서버에 걸쳐 scale out 할 수 있음을 의미함으로 단일 서버일 때보다 parallelism, concurrency이 높고 훨씬 성능이 우수합니다.

- 주의!

한번 확장한 partition은 절대 줄일 수 없기 때문에 partition을 늘리는 경우는 충분히 고려해야 합니다.

### Producers and Consumers

Producer는 기본적으로 partitioning에 대해 신경쓰지 않지만 custom partitioner를 사용해서 특정 partition에 message를 고정적으로 대응시킬 수 있습니다.

Consumer는 하나 이상의 topic을 구독하여 message가 생성된 순서로 읽으며, message의 offset을 유지하여 읽는 message의 위치를 알 수 있습니다. Partition에 수록된 message는 고유한 offset을 가지며 zookeeper나 kafka에서는 각 partition에서 마지막으로 읽은 message의 offset을 저장하고 있으므로 일시 중단된 consumer가 다시 시작하더라도 그 다음 message부터 읽는 것이 가능합니다.

### Brokers and Clusters

![cluster_broker_producer_consumer](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/d5a7c4aa-b7e0-4918-8452-1b9ea5cb4c09)

하나의 Kafka 서버를 broker라고 합니다. Broker는 producer로부터 message를 수신하면 offset을 지정한 후 해당 message를 disk에 저장합니다. 또한 consumer의 partition read 요청에 응답하고 disk에 수록된 message를 전송합니다. 시스템 성능에 따라 다르지만, 하나의 broker는 초당 수천개의 topic과 수백만개의 message를 처리할 수 있습니다.

Broker는 cluster의 일부로 동작하도록 설계되어 있으며 하나의 cluster는 여러 개의 broker로 구성되어 있습니다. 그 중 하나는 자동으로 선정되는 cluster controller 기능을 수행합니다. Controller는 cluster 내 각 broker에게 담당 partition을 할당하고 broker들이 정상적으로 동작하는지 모니터링합니다. 각 partition은 한 broker가 소유하며, 해당 broker를 partition leader라고 합니다. 또한 fault-tolerant한 성질을 보장하기 위해 한 partition은 여러 broker에 나누어 저장될 수 있는데 이를 replication이라고 합니다.



## Why Kafka?

### Multiple Producers

여러 client가 여러 topic을 사용하거나 같은 topic을 동시에 사용해도 Kafka는 무리 없이 많은 producer의 message를 처리할 수 있습니다. 따라서 여러 시스템으로부터 data를 수집하고 일관성을 유지하는 데 이상적입니다.

### Multiple Consumers

많은 consumer가 상호 간섭 없이 어떤 message stream도 읽을 수 있게 지원합니다. 기존에 queue system에서는 한 client가 특정 message를 소비하면 다른 client에서 그 message를 사용할 수 없게 되었습니다. 하지만 Kafka는 pub/sub pattern과 messaging queue의 확장성을 둘 다 취하여 scalable한 pub/sub model을 구현하였습니다.

### Disk-Based Retention

Kafka는 다중 consumer를 처리할 수 있을 뿐만 아니라 지속해서 message를 보존할 수 있습니다. 따라서 consumer가 지속적으로 실행되지 않아도 되며, message 폭주로 인해 consumer가 message를 읽는 데 실패하더라도 data가 유실될 위험이 없습니다.

### Scalable

Kafka는 확장성이 좋아서 어떤 크기의 data도 쉽게 처리할 수 있습니다. 따라서 처음에는 하나의 broker로 시작한 후 3대의 broker로 구성된 소규모의 개발용 cluster로 확장하면 좋습니다. 그 다음에 data 증가에 따라 10대에서 수백에 이르는 대규모 cluster로 업무용 환경을 구축하면 됩니다. cluster expansion은 cluster가 online 상태일 때도 cluster 사용에 영향을 주지 않고 가능합니다.



## References

- images 
  - [https://www.javatpoint.com/kafka-topics](https://www.javatpoint.com/kafka-topics)
  - [https://blogs.sap.com/2021/03/16/cloud-integration-what-you-need-to-know-about-the-kafka-adapter/](https://blogs.sap.com/2021/03/16/cloud-integration-what-you-need-to-know-about-the-kafka-adapter/)
