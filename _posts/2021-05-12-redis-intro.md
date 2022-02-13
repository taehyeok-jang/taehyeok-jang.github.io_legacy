---
layout: post
title: Redis Introduction 
subheading: 
author: taehyeok-jang
categories: [database]
tags: [database, cache]
---

이 글은 2019년 11월 21일 우아한형제들 테크 세미나에서 강대명님께서 발표하신 자료를 바탕으로 추가적으로 정리한 글입니다. 

[[우아한테크세미나] 191121 우아한레디스 by 강대명님](https://www.youtube.com/watch?v=mPB2CZiAkKM)



## Introduction 

- Redis는 In-memory data structure storage이며 Remote Dictionary Server의 줄임말
- Open source under a BSD 3-clause licensed
  - 코드를 임의로 수정하거나 공개하지 않아도 상관 없으며 사용 유무만을 밝히면 된다
  - 단, Redis Enterprise는 수정 시 소스 코드를 공개해야 함 
- Supported data structures 
  - Strings, set, sorted-set, hashes, list 
  - hyperloglog, bitmap, geospatial index 
  - streams
- Only 1 commiter (Salvatore Sanfilippo)



### Use Cases 

- Remote data structure 
  - 여러 어플리케이션 서버에서 데이터를 공유하고 싶을 때 
- 한대에서만 필요하다면 전역변수를 쓰면 되지 않나? 
  - Redis 자체가 atomic을 보장해준다 (single thread)
- 주로 쓰이는 사례들 
  - 인증토큰 등을 저장 (strings or hash)
  - Ranking board (sorted set)
  - API limiter
  - Job queue (list)



### Why Collections? 

- 개발의 편의성 
- 개발의 난이도 

참고로 Memcached는 collection 지원 안함. 



#### 개발의 편의성 

Ex. 랭킹 서버를 직접 구현한다면? 

- 가장 간단한 방법
  - DB에 유저의 score를 저장하고 score로 order by
  - 개수가 많아지면 결국 디스크를 사용하므로 문제가 발생할 수 있음. 
- In-memory를 활용한 랭킹 서버 구현이 필요함. Redis의 sorted set을 이용하면 랭킹을 구현할 수 있음 
  - 추가적으로 replication도 가능 
  - 다만 해당 솔루션의 한계에 종속될 수 있음 
    - 랭킹에 저장해야 할 id가 1개당 100 byte라고 하면 
      - 10명 -> 1KB
      - 10K명 -> 1MB
      - 10M명 -> 1GB
      - 10G명 -> 1TB 



#### 개발의 난이도 

Ex. 친구 리스트 관리를 key/value 형태로 저장한다면?

현재 사용자 123의 key는 'friends:123', 현재 친구 A만 존재함

어떤 문제가 발생할 수 있을까요? 

- Tx1

1. 친구 리스트 friends:123을 읽는다 
2. Friends:123의 끝에 친구 B를 추가한다 
3. 해당 값을 friends:123에 저장한다  

- Tx2. 

1. 친구 리스트 friends:123을 읽는다 
2. Friends:123의 끝에 친구 C를 추가한다 
3. 해당 값을 friends:123에 저장한다

  

아래 두 상황에서는 race condition 및 context switching이 발생하여 데이터의 최종 상태가 올바르지 않다. 



Normal case. 

|      | Tx1 (Add friend B)    | Tx2 (Add friend C)    | Result |
| ---- | --------------------- | --------------------- | ------ |
| 1    | Read from friends:123 |                       | A      |
| 2    | Add friend B          |                       | A      |
| 3    | Write to friends:123  |                       | A, B   |
| 4    |                       | Read from friends:123 | A, B   |
| 5    |                       | Add friend C          | A, B   |
| 6    |                       | Write to friends:123  | A, C   |



Race condition. 

|      | Tx1 (Add friend B)    | Tx2 (Add friend C)    | Result |
| ---- | --------------------- | --------------------- | ------ |
| 1    | Read from friends:123 |                       | A      |
| 2    |                       | Read from friends:123 | A      |
| 3    | Add friend B          |                       | A      |
| 4    |                       | Add friend C          | A      |
| 5    | Write to friends:123  |                       | A, B   |
| 6    |                       | Write to friends:123  | A, C   |



Race condition + Context switching. 

|      | Tx1 (Add friend B)    | Tx2 (Add friend C)    | Result |
| ---- | --------------------- | --------------------- | ------ |
| 1    | Read from friends:123 |                       | A      |
| 2    |                       | Read from friends:123 | A      |
| 3    | Add friend B          |                       | A      |
| 4    |                       | Add friend C          | A      |
| 5    |                       | Write to friends:123  | A, C   |
| 6    | Write to friends:123  |                       | A, B   |



=> Redis의 경우는 atomic한 collection을 지원하기 때문에 위와 같은 문제를 피할 수 있다.

외부의 collection을 잘 이용하는 것으로 개발 시간을 단축시키고, 비즈니스 이외의 문제를 신경쓰지 않도록 하기 때문에 collection이 중요. 





## Cache

### Why Cache?

계산 결과를 저장하여 다음에 요청이 들어올 때 활용하여 성능을 향상시키기 위함. 

파레토 법칙.
20%의 사용자가 80%의 트래픽을 차지. 



### Cache Strategy - Look Aside 

read-through 

### Cache Strategy - Write Back 

1. Web server 는 모든 데이터를 cache에만 저장 
2. Cache에 특정 시간 동안 데이터를 저장
3. Cache에 있는 데이터를 DB에 저장 
4. DB에 저장된 데이터를 삭제



Pros.
DB insert query를 배치로 처리함으로써 횟수를 절감하여 성능을 올릴 수 있음. 
disk RAID controller에도 cache가 있는데, 배터리가 나가서 충전하는 시간에 cache가 동작 안하고 있을 때 성능이 저하.

Cons. 
cache에 있는 데이터가 사라질 수 있음. 
따라서 로깅 등의 목적이나 극단적으로 write heavy한 작업에 대안으로서 사용한다. 


## Redis Collections 
- Strings
- List 
- Set 
- Sorted Set 
- Hash 

주의.
어떤 collection을 선택하는지에 따라 서비스 성능이 비약적으로 개선/악화될 수 있다. 

### Strings
Main point.
key를 어떤 것으로 잡을 것인가? 

- set, get
- mset, mget (multi-)

### List 
- Lpush, Rpush
- Lpop, Rpop


### Set 
데이터의 존재 유무를 확인.
- 기본 사용법 
  - sadd <key> <value>
    - value가 이미 있으면 추가되지 않는다
  - Members <key> 
    - 모든 value를 돌려준다
  - sismember <key> <value>
    - value가 존재하면 1, 없으면 0. 

follow 관계 구현에 사용되기도 함. 


### Sorted Sets 

랭킹에 따라서 순서가 바뀌길 바랄 때. strings와 더불어 가장 빈번하게 사용되는 collection. 

score는 integer가 아닌 floating point. 

- 기본 사용법 
  - zadd <key> <score> <value> 
    - value가 이미 key에 있으면 해당 score로 변경된다 
  - zrange <key> <start index> <end index>
    - 해당 index 범위 값을 모두 돌려준다 
    - Zrange testkey 0-1. 모든 범위를 가져옴. 

- 사용자 랭킹 보드로 사용할 수 있음.
- Sorted Sets의 score는 double 타입이기 때문에 값이 정확하지 않을 수 있다. 
- 컴퓨터에서는 실수가 표현할 수 없는 정수값들이 존재. 



- 정렬이 필요한 값이 필요하다면?
  - select * from rank order by score limit 50, 20;
    - zrange rank 50 70 
  - elect * from rank order by score desc limit 50, 20;
    - zrevrange rank 50 70 
- score 기준으로 추출하고 싶으면? 
  - select * from rank where score >= 70 and score <100;
    - zrangebyscore rank 70 100 
  - select * from rank where score > 70;
    - zrangebyscore rank (70 +inf



### Hash 

key 밑에 subkey가 존재. 즉 key/value 내에 key/value를 가진다. 

- 기본 사용법 
  - hmset <key> <subkey1> <value1> <subkey2> <value2> 
  - hgetall <key>
    - 해당 key의 모든 subkey와 value를 가져옴 
  - hget <key> <subkey>
  - hmget <key> <subkey1> <subkey2> <subkey3> ... <subkeyN> 



### 주의사항 

- 하나의 collection에 너무 많은 아이템을 적재하면 좋지 않다 
  - 10K개 이하 몇천개 수준으로 유지하는게 좋다
- expire는 collection의 item 개별로 적용되는 것이 아니라 전체 collection에 대해서만 적용된다
  - 해당 10K개의 아이템을 가진 collection에 expire가 걸려있으면 그 시간 이후에는 10K개의 아이템이 모두 삭제된다. 



## Redis Maintenance 

- 메모리 관리를 잘하자
- O(n) 관련 명령어는 주의하자 
- Replication 
- 권장 설정 팁



### 메모리 관리를 잘하자

- Redis는 in-memory data structrure이기 때문에 메모리 관리가 정말 중요하다. 
- Physical memory 이상을 사용하면 문제가 발생한다 
  - swap이 없으면 OOM 등으로 서버가 바로 죽는다
  - swap이 있으면 swap 사용으로 해당 메모리 page 접근 시 마다 느려진다
- maxmemory를 설정하더라도 이보다 더 사용할 가능성이 크다 
  - maxmemory는 Redis 내 총 저장 용량에 관련된 threshold. 
  - maxmemory를 넘어가면 Redis가 알아서 특정 key를 random하게 지우거나 expire 시킴. 
  - 메모리 관리는 JMalloc에 의존함. JMalloc의 특성 상 Redis는 현재 사용 중인 정확한 메모리 용량을 알 수 없음. (메모리 파편화도 관련이 있음)
  - Redis는 메모리 파편화가 발생할 수 있으며 4.x 대부터 메모리 파편화를 줄이도록 JMalloc에 힌트를 주는 기능이 들어갔으나 버전에 따라서 다르게 동작할 수 있음.
  - 3.x 버전의 경우 실제 used memory는 2GB로 계측이 되지만 10GB의 RSS를 사용하는 경우가 자주 발생 
- 다양한 사이즈를 가지는 데이터 보다는 유사한 크기의 데이터를 가지는 경우가 유리. 
- RSS 값을 모니터링 해야함 
  - 여러 시스템에서 현재 메모리 상에서 swap이 발생하고 있다는 것을 모를 때가 많다 
- 큰 메모리를 사용하는 인스턴스 하나보다는 적은 메모리를 사용하는 인스턴스 여러개가 안전하다.
  - 24 GB 1 instance => 8GB 3 instance 
  - master slave 클러스터에서 사용 중에 필연적으로 fork를 하게된다. write가 heavy한 클러스터의 경우 최대 메모리를 2배까지 사용할 수 있음. copy on write로 동작하므로 한 인스턴스를 전체 copy 복사할 수 있음. 



### 메모리가 부족할 때는?

- Cache is Cash!
  - 조금 더 메모리 용량이 큰 장비로 migration 
  - 메모리 용량을 넉넉하지 않게 쓰면 migration 중에 문제가 발생할 수도 있으므로 메모리 용량의 60~70%가 되었을 때 migration 준비를 해야한다. 
- 있는 데이터 줄이기 
  - 데이터를 일정 수준에서만 사용하도록 특정 데이터를 줄임 
  - 다만 이미 swap을 사용 중이라면 프로세스를 재시작해야 함. 



### 메모리를 줄이기 위한 설정

- 기본적으로 collection들은 다음과 같은 자료구조를 사용
  - Hash -> HashTable을 하나 더 사용
  - Sorted Set -> SkipList와 HashTable을 이용
  - Set -> HashTable 사용
  - 해당 자료구조들은 메모리를 많이 사용한다 
- ZipList를 이용하자



### ZipList 구조 

- In-memory 특성 상, 적은 개수라면 선형 탐색을 하더라도 빠르다 
- List, Hash, Sorted Sets 등을 ZipList로 대체해서 처리를 하는 설정이 존재 
  - https://redis.com/ebook/part-2-core-concepts/01chapter-9-reducing-memory-use/9-1-short-structures/9-1-1-the-ziplist-representation/



### O(n) 관련 명령어는 주의하자 

- Redis는 single threaded
  - 단순한 get/set의 경우, 초당 10만 TPS 이상 처리 가능 (CPU 처리 성능에 영향을 받음)
  - Redis가 동시에 여러개의 명령을 처리할 수 있을까? => 한번에 하나의 명령만 수행 가능 
  - 따라서 긴 시간이 필요한 명령을 수행하면 그 뒤에 명령들이 줄줄이 지연되게 된다. 
- 대표적인 O(n) 명령어들
  - keys,
  - flushall, flushdb 
  - delete collections 
  - get all collections 


### 대표적인 실수 사례 

- key가 백만개 이상인데 확인을 위해 keys 명령을 사용하는 경우 
  - 모니터링 스크립트가 일초에 한번씩 keys를 호출하는 사례가 있었음 
- 아이템이 몇만개 든 hash, sorted set, set에서 모든 데이터를 가져오는 경우 
- 예전에 Spring Security OAuth RedisTokenStore 

### 어떻게 개선할 것인가? 

- keys는 scan 명령을 사용하는 것으로 하나의 긴 명령을 짧은 여러번의 명령으로 바꿀 수 있다. 
  - scan <cursor> 
- collection의 모든 item을 가져와야 할 때?
  - collection의 일부만 가져오거나 
    - sorted set 
  - 큰 collection을 작은 여러개의 collection으로 나누어 저장 
    - UserRanks -> UserRank1, UserRank2, UserRank3, ...
    - 하나 당 몇천개 내로 저장하는 것이 좋다 
- Spring Security OAuth RedisTokenStore 이슈 
  - Access token의 저장을 List (O(n)) 자료구조를 통해서 이루어짐 
    - 검색, 삭제 시에 모든 item을 찾아봐야함. 1M 개가 넘어가면 전체 성능에 영향을 미친다
  - 현재는 Set (O(1))을 이용해서 검색, 삭제를 하도록 수정되었음. 



### Redis.conf 권장 설정 팁

- maxclient 설정 50K. 이왕이면 높게 
  - maxclient 만큼만 네트워크로 접속 가능 
  - maxclient를 넘어서 접속이 안되는 경우가 있음 
- RDB/AOF off (성능, 안정성)
- 특정 commands disable 
  - keys 
  - AWS의 ElasticCache는 이미 지원하고 있음 
- 전체 장애의 90% 이상이 keys와 save 설정을 사용해서 발생 
- 적절한 ziplist 설정 



## Redis Replication 

A 서버의 데이터를 B 서버에 지속적으로 동기화하고 있는 것. 

- Async replication 
  - Replication lag이 발생할 수 있다 
- 'replicaof' (>= 5.0.0) or 'slaveof' 명령으로 설정 가능 
  - 'replicaof' <hostname> <port>
- DBMS의 row replication이 아니라 statement (query) replication가 유사 



### replication 설정 과정 

1. Secondary에 replicaof or slaveof 명령으 ㄹ전달 
2. Secondary는 Primary에 sync명령 전달 
3. Primary는 현재 메모리 상태를 저장하기 위해 fork (이것이 모든 문제의 근원)
4. fork한 프로세서는 현재 메모리 정보를 disk에 dump (이 과정 생략 가능)
5. 해당 정보를 secondary에 전달 
6. Fork 이후의 데이터를 secondary에 계속 전달 



### replicaiton 시 주의할 점 

- Replication 과정에서 fork가 발생하므로 메모리 부족이 발생할 수 있다 
- Redis-cli --rdb 명령은 현재 상태의 메모리 스냅샷을 가져오므로 같은 문제를 발생시킴 
- AWS나 클라우드의 Redis는 조금 다르게 구현되어서 해당 부분이 조금 더 안정적. 대신 속도가 느리다고 알려져 있음. 
- 많은 대수의 Redis 서버가 Replica를 두고 있다면 
  - 네트워크 이슈나 사람의 작업으로 동시에 replication이 재시도 되도록 하면 문제가 발생할 수 있음 
  - ex. 같은 네트워크 안에서 30GB를 사용하는 Redis master 100대 정도가 replication을 동시에 시작하면 어떤 일이 벌어질까? => rollout 필요 



## Redis 데이터 분산 

- 데이터의 특성에 따라서 선택할 수 있는 방법이 달라진다 
  - cache일 때는 우아한 Redis
  - persistent 해야하면 안 우아한 Redis (위험을 무릅쓰는 길)

- Application 

  - consistent hashing 
  - sharding 

  

### Consistent hashing 

consistent hashing (twemproxy를 통해 쉽게 사용 가능)

- 서버가 추가되어도 기존의 분산된 데이터는 그대로 분산되도록 하는 처리가 필요함. 즉, 기존 데이터는 rebalancing 이 발생하지 않아야 함. Consistent hashing을 통해서 서버 추가/삭제 시 영향 범위는 해당 서버로 한정된다. 
- hash 값을 계산하여 자기보다 크면서 가장 가까운 값. 큰 값이 없으면 circular list 방식으로 탐색. 

### Sharding 

- 데이터를 어떻게 나눌 것인가? 데이터를 어떻게 찾을 것인가? 

- Range 
  - Ex. 1~10000, 10001~20000, 20001~30000
  - Cons.
    - 서비스 상황에 따라서 서버 간 부하 불균형이 극명하게 발생한다. 

- Modular 
  - N%K로 부하 분산 
  - Range보다 데이터를 균등하게 분배할 가능성이 높다 
  - Cons 
    - 서버 한대가 추가될 때 재분배 양이 많아지므로 1대씩이 아니라 2배씩 늘려야 함. 
- Indexed 
  - 인덱스 서버를 따로 두어 부하 분산 
  - Cons
    - 인덱스 서버가 SPOF 



## Redis Cluster 

- [ ] TODO 



## Redis Failover 

- Coordinator 기반
- VIP/DNS 기반 


### Coordinator 기반 

- Zookeeper, etcd, consul 등의 coordinator 사용
- Coordinator 기반으로 설정을 관리한다면 동일한 방식으로 관리가 가능 
- 해당 기능을 이용하도록 개발이 필요하다. 


### VIP/DNS 기반 

- 클라이언트에 추가적인 구현이 필요없다 
- VIP 기반은 외부로 서비스를 제공해야 하는 서비스 업자에 유리 (예를 들어 클라우드 업체). 벤더의 DNS caching 전략을 모르기 때문에. 
- DNS 기반은 DNS cache TTL을 잘 관리해야 함
  - 사용하는 언어별 DNS 캐싱 정책을 잘 알아야 함. (Ex. Java는 30초 동안 DNS 캐싱)
  - 툴에 따라서 한번 가져온 DNS 정보를 다시 호출하지 않는 경우도 존재 
  - AWS 내부에서는 DNS 기반. 
  - DNS를 바꾸는 것이 더 쉽기는 함. 


## 결론

- 기본적으로 Redis는 매우 좋은 캐시 저장소 
- 그러나 메모리를 타이트하게 쓰는 경우, 관리하기가 어렵다
  - 32GB 장비라면 24GB 이상 사용할 시 장비 증설을 고려하는 것이 좋음 
  - write가 heavy 할 때는 migration도 매우 주의해야 함 
- client-output-buffer-limit 설정이 필요 



### Redis as Cache 

- Redis를 cache로 사용할 때는 문제가 적게 발생 
  - Redis가 불능일 때 DB에 부하가 어느 정도 증가하는지 확인 필요 
  - Consistent hashing 도 실제 부하를 아주 균등하게 나누지는 않음. Adaptvie consistent hashing 을 이용해볼 수도 있음 



### Redis as Pesistent Storage

- Redis를 persistent storage로 사용할 경우 
  - 반드시 primary/secondary 구조로 구성이 필요함 
  - 메모리를 절대로 타이트하게 사용하면 안된다 
    - 정기적인 migration이 필요 
    - 가능하면 자동화 툴을 만들어서 이용
  - RDB/AOF가 필요하다면 secondary에서만 구동 


## Further Readings 

- Redis persistence (RDB, AOF)
- Redis pub/sub 
- Redis Stream 
- Probabilistic Data Structure - Hyperloglog
- Redis module 



## References 

- https://redis.io
- Consistent hashing 
  - https://charsyam.wordpress.com/2011/11/25/memcached-에서의-consistent-hashing/
  - https://smallake.kr/?p=17730
  - https://charsyam.wordpress.com/2016/10/02/입-개발-consistent-hashing-에-대한-기초/




