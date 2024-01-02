---
layout: post
title: Apache Kafka - How to Achieve Reliable Messaging
subheading: 
author: taehyeok-jang
categories: [stream-processing]
tags: [kafka]
---



이 글은 [Apache Kafka 공식 문서](https://kafka.apache.org/documentation/#semantics)와 관련 자료를 읽고 정리한 글입니다.



## Introduction 


Reliable messaging in Apache Kafka can be achieved by designing a system with a combination of Kafka broker setup, and producer & consumer configurations. By implementing these setup and configurations, Apache Kafka can provide a reliable messaging system that is able to handle failures and ensure message delivery. 

- On broker side, 

Kafka's built-in replication feature ensures fault tolerance.

- On producer side, 

records are sent asynchronously and the acknowledgement level is set to "all" with a minimum number of in-sync replicas set to 2. Additionally, idempotence is enabled to avoid duplication.

- On consumer side, 

auto-commit is disabled to ensure at-least-once processing.



## Broker 

### Kafka Broker is fault tolerant with replication 

- Message simply gets destroyed in the transit from producer to leader
- Leader of the partition is down
- All brokers are down (disastrous...) however such a situation rarely occurs in multi IDC architecture.

In distributed systems, fault tolerance can be achieved with enough redundancy. Apache Kafka also provides an option to achieve the redundancy. 

https://kafka.apache.org/documentation/#brokerconfigs_offsets.topic.replication.factor (default value: 3) 

=> Set offsets.topic.replication.factor >= 3

![event-driven-kafka-2_(1)](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/03aaa9a4-ea2d-4ece-9de7-69e74736d481)



## Producer

### Producer sends a record asynchronously 

**The send is asynchronous and this method will return immediately once the record has been stored in the buffer of records waiting to be sent**. This allows sending many records in parallel without blocking to wait for the response after each one.

<img width="957" alt="apache_kafka_producer_internal" src="https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/82f5739c-3f6b-4c65-a7f7-f6928fb9faac">



### Set acks = all, and min.insync.replicas = 2

[https://kafka.apache.org/documentation/#producerconfigs_acks](https://kafka.apache.org/documentation/#producerconfigs_acks)

[https://kafka.apache.org/documentation/#brokerconfigs_min.insync.replicas](https://kafka.apache.org/documentation/#brokerconfigs_min.insync.replicas)

When used together, min.insync.replicas and acks allow you to enforce greater durability guarantees. A typical scenario would be to create a topic with a replication factor of 3, set min.insync.replicas to 2, and produce with acks of "all".

![apache_kafka_producer_config_01](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/ec7b2784-a6c7-4ff4-a1f1-18894ba34c81)

We simply need to configure `acks` property in producer to `all`. Meaning of different values of acks property is as follows: 

- acks=0 : The default is `acks=0`, which means producer will send the message and forget, it won't wait for any acknowledgement from the leader of the partition to which the message is to be produced. 
- acks=1 : Means leader sends acknowledgement to the producer after it writes the message to its own replica without waiting for followers to replicate the messages. So, if the leader fails before any follower replicates the message, the record is lost. 
- acks=all : With this, once the leader receives acknowledgements from in-sync replicas, telling they have replicated the message, it will send back the acknowledgement to the producer. This guarantees that the record will not be lost as long as at least one in-sync replica remains alive. 



![apache_kafka_producer_config_02](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/6b2a9d1c-06eb-4af8-8575-240a301b5245)



The property min.insync.replicas specifies the minimum number of replicas that must acknowledge before leader send back acknowledgement to the client. If this minimum is not satisfied, then the producer will raise an exception (either NotEnoughReplicas or NotEnoughReplicasAfterAppend).  

![apache_kafka_producer_config_03](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/7cbe5f41-3d3e-4589-b6e3-828fa96fade1)



### Set enable.idempotence=true to avoid duplication 

[https://kafka.apache.org/documentation/#producerconfigs_enable.idempotence](https://kafka.apache.org/documentation/#producerconfigs_enable.idempotence)

This happens when producer fails to receive acknowledgement before resending the message. So, the message is already persisted in leader replica, but producer did not receive any acknowledgement from leader or the acknowledgement is received after the producer resend timer is expired and hence producer resends the message causing duplication.

When set to 'true', the producer will ensure that exactly one copy of each message is written in the stream.



### Set retries=n with enough buffer memory

[https://kafka.apache.org/documentation/#producerconfigs_retries](https://kafka.apache.org/documentation/#producerconfigs_retries)

[https://kafka.apache.org/documentation/#producerconfigs_buffer.memory](https://kafka.apache.org/documentation/#producerconfigs_buffer.memory)

When broker breaks down temporarily, producer gets exception. With multiple retries with enough buffer, all records can be eventually sent again. 

![apache_kafka_producer_config_04_(1)](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/679bf69d-b77e-433c-b9a3-5896debd7baf)



## Consumer 

[https://kafka.apache.org/documentation/#consumerconfigs_enable.auto.commit](https://kafka.apache.org/documentation/#consumerconfigs_enable.auto.commit)

### Set enable.auto.commit=false for processing at-least-once 

By default, commit occurs automatically periodically in the background. If we want to manually commit, then we should set enable.auto.commit property of consumer to false and then call Consumer.commit(). 

=> With enable.auto.commit=false, consumer never commits before data processing is done. This may cause duplicated processing, but never misses processing records. 



#### At-most-once

enable.auto.commit=true (by default)

![apache_kafka_consumer_auto_commit_01](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/4f96b3d8-4f6d-400c-8d5e-731145c8977d)

![apache_kafka_consumer_auto_commit_02](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/34f79c55-b3fe-42a2-bdfd-73fcb0a0b721)



#### At-least-once 

enable.auto.commit=false

![apache_kafka_consumer_manual_commit](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/35b4dac5-0ebd-4220-b9d2-08a1133c6798)





## Limitation

As we mentioned above, producer sends a record asynchronously. Therefore records in the buffer may be lost in several below scenarios, 

- When application aborts unexpectedly
- When Kafka broker breaks down for a long time 



## References 

- [Kafka: The Definitive Guide](https://www.oreilly.com/library/view/kafka-the-definitive/9781492043072/)
- [https://kafka.apache.org/documentation/](https://kafka.apache.org/documentation/#producerconfigs_acks)
- Attachments
  - [https://kafka.apache.org/0110/javadoc/index.html?org/apache/kafka/clients/producer/KafkaProducer.html](https://kafka.apache.org/0110/javadoc/index.html?org/apache/kafka/clients/producer/KafkaProducer.html)
  - [https://towardsdatascience.com/10-configs-to-make-your-kafka-producer-more-resilient-ec6903c63e3f](https://towardsdatascience.com/10-configs-to-make-your-kafka-producer-more-resilient-ec6903c63e3f)
  - [https://blog.ippon.tech/event-driven-architecture-getting-started-with-kafka-part-2/](https://blog.ippon.tech/event-driven-architecture-getting-started-with-kafka-part-2/)
  - [https://www.esolutions.tech/delivery-guarantees-provided-by-Kafka](https://www.esolutions.tech/delivery-guarantees-provided-by-Kafka)