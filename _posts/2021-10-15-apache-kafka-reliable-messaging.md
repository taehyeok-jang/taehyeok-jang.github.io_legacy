---
layout: post
title: Apache Kafka - Processing Semantics 
subheading: 
author: taehyeok-jang
categories: [stream-processing]
tags: [kafka]
---



이 글은 [Apache Kafka 공식 문서](https://kafka.apache.org/documentation/#semantics)와 관련 자료를 읽고 정리한 글입니다.





## Introduction 


Reliable messaging in Apache Kafka can be achieved by designing a system with a combination of Kafka broker setup, and producer & consumer configurations. By implementing these setup and configurations, Apache Kafka can provide a reliable messaging system that is able to handle failures and ensure message delivery. 

- On broker side, Kafka's built-in replication feature ensures fault tolerance.
- On producer side, records are sent asynchronously and the acknowledgement level is set to "all" with a minimum number of in-sync replicas set to 2. Additionally, idempotence is enabled to avoid duplication.
- On consumer side, auto-commit is disabled to ensure at-least-once processing.



## Broker 

### Kafka Broker is fault tolerant with replication 

- Message simply gets destroyed in the transit from producer to leader
- Leader of the partition is down
- All brokers are down (disastrous...) however such a situation rarely occurs in multi IDC architecture.



In distributed systems, fault tolerance can be achieved with enough redundancy. 

https://kafka.apache.org/documentation/#brokerconfigs_offsets.topic.replication.factor (default value: 3) 

=> Set offsets.topic.replication.factor >= 3



## Producer

### Producer sends a record asynchronously 

### Set acks = all, and min.insync.replicas = 2

### Set enable.idempotence=true to avoid duplication 

### Set retries=n with enough buffer memory



## Consumer 

### Set enable.auto.commit=false for processing at-least-once 

#### At-most-once

#### At-least-once 



## Limitation



## References 