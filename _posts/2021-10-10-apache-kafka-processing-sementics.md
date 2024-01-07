---
layout: post
title: Apache Kafka - Processing Semantics
subheading: 
author: taehyeok-jang
categories: [stream-processing]
tags: [kafka]

---



이 글은 [Apache Kafka 공식 문서](https://kafka.apache.org/documentation/#semantics)와 관련 자료를 읽고 정리한 글입니다.



## Intro

Apache Kafka는 세 가지 message delivery guarantees을 제공합니다.

- *At most once*—Messages may be lost but are never redelivered.
- *At least once*—Messages are never lost but may be redelivered.
- *Exactly once*—this is what people actually want, each message is delivered once and only once. (hard to achieve)

여러 시스템들이 'exactly once' delivery semantics을 제공한다고 주장하지만, 이러한 주장들은 producer/consumer의 처리 실패, kafka cluster의 완전한 장애 등의 상황에서 종종 유지되지 않습니다. 또한 실제 분산시스템 상에서 'exactly once'는 불가능하다고 알려져있습니다. 

Kafka의 접근 방식은 메시지가 log에 commit되는 개념을 중심으로 단순하며, 한 개의 broker라도 활성 상태로 남아 있다면 commit된 메시지가 손실되지 않는다는 것을 보장합니다.



## Producer

- Prior to 0.11.0.0,

Apache Kafka의 0.11.0.0 버전 이전에는, producer가 네트워크 오류로 인해 메시지 재전송을 시도할 때 메시지가 중복되어서 저장될 가능성이 있었습니다. 

- Since 0.11.0.0,

하지만 idempotent delivery option을 통해서 이제 Kafka는 재전송이 중복을 초래하지 않습니다. 또한 여러 topic partitions으로 한번에 메시지를 저장하거나 아예 저장하지 않는 (all or none) transaction과 같은 semantic을 도입하여 exactly-once processing semantic을 지원합니다.



## Consumer

consumer 관점에서, Kafka는 모든 repliaca에서 일관된 offset을 가진 정확한 로그 복제본을 유지합니다. conusmer는 이 log에서 자신의 offset를 제어하며, 메시지를 처리하고 offset를 업데이트하는 몇 가지 옵션이 있으며, 각각은 다른 delivery guarantee를 보장합니다.

'at-most-once'와 'at-least-once'은 메세지를 읽고, 처리하며, offset을 commit하는 순서를 다르게 배열함으로써 가능합니다. 반면, 'exactly-once' guarantee는 Apache Kafka 버전 0.11.0.0에서 도입된 transactional 기능을 활용합니다.

- at-most-once

It can read the messages, then save its position in the log, and finally process the messages.

- at-least-once

It can read the messages, process the messages, and finally save its position



## Exactly-Once

Apache Kafka에서 'exactly-once' 처리는 메시지를 전송하거나 처리할 때 중복 없이 단 한 번만 성공적으로 수행되도록 보장하는 것을 의미합니다. 이것은 데이터 파이프라인에서 중요한 속성이며, 데이터 손실이나 중복을 방지하여 결과의 정확성을 보장합니다. Kafka는 0.11 버전부터 이 기능을 지원하기 시작했습니다.

### Exactly-Once의 구성 요소

Idempotent Producer:

- Idempotent Producer는 동일한 메시지를 여러 번 전송하더라도 브로커에서는 오직 한 번만 기록되도록 보장합니다.
- 각 메시지에는 고유한 시퀀스 번호가 할당되며, 브로커는 중복을 감지하고 제거합니다.
- 네트워크 오류나 기타 문제로 인해 전송이 중복될 경우에도 안전합니다.

Transactional Messaging:

- Kafka는 transaction을 지원하여 여러 메시지 작업을 하나의 원자적 단위로 묶을 수 있습니다.
- transaction 내의 모든 메시지는 전부 성공하거나 전부 실패하며, 중간 상태에서 멈추지 않습니다.
- 이를 통해 다중 partitions과 topic에 걸쳐 일관된 상태를 유지할 수 있습니다.

Consumer의 Exactly-Once 처리:

- consumer는 처리한 메시지에 대한 offset을 추적하여 어디까지 처리했는지 기록합니다.
- 장애 발생 후 재시작할 때, 마지막으로 커밋된 오프셋부터 다시 시작하여 중복 처리를 방지합니다.



### Exactly-Once의 동작 방식

1. producer는 트랜잭션을 시작하고, 여러 메시지를 여러 patitions과 topic에 걸쳐 보냅니다.
2. 모든 메시지가 성공적으로 보내지면, producer는 transaction을 커밋합니다.
3. 만약 중간에 실패가 발생하면, transaction은 롤백되고, 모든 메시지는 broker에 의해 무시됩니다.
4. consumer는 커밋된 transaction의 메시지만 처리하고, offset을 기록하여 중복 처리를 방지합니다.



### 한계점

위에서 이야기한대로 Apache Kafka의 모든 구성요소(producer, consumer, broker)를 올바르게 설정하고 구성한다면 exactly-once processing semantics을 구현할 수 있을 것입니다. 하지만 분산시스템 상에서는 외부 시스템과의 연계, 복잡한 어플리케이션 로직 처리 등 실패 요소가 완전한 exactly-once를 실현하는 것은 여전히 도전적인 문제로 남아있습니다. 



## Conclusion 

지금까지 Apache Kafka에서 제공하는 여러가지 processing semantics에 대해 알아보았습니다. 각 semantic은 서로 다른 처리 성능, 데이터 일관성/정확성을 보장합니다.

따라서 분산 시스템을 다루는 엔지니어는 사용 사례와 성능 요구 사항에 따라 exactly-once, at-least-once, at-most-once 중 적합한 보장 수준을 선택하여 어플리케이션을 개발해야 합니다. 





## References 

- [https://cwiki.apache.org/confluence/display/KAFKA/Idempotent+Producer](https://cwiki.apache.org/confluence/display/KAFKA/Idempotent+Producer)
- [https://www.confluent.io/blog/exactly-once-semantics-are-possible-heres-how-apache-kafka-does-it/](https://www.confluent.io/blog/exactly-once-semantics-are-possible-heres-how-apache-kafka-does-it/)
- [https://www.baeldung.com/kafka-exactly-once](https://www.baeldung.com/kafka-exactly-once)
- [https://gunju-ko.github.io/kafka/2018/03/31/Kafka-Transaction.html](https://gunju-ko.github.io/kafka/2018/03/31/Kafka-Transaction.html)