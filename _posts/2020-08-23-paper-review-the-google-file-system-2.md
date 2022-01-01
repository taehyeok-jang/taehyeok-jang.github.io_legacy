---
layout: post
title: (Paper Review) The Google File System - 2
subheading: 
author: taehyeok-jang
categories: [distributed-systems]
tags: [paper-review, distributed-systems, file-system]
--- 

##  4. Master Operation 

master는 file system과 관련된 모든 system-wide한 동작들을 수행한다.

- all namespace operations of files and directories

- replica placement decision 

- create, re-replicate, rebalance chunks

- reclaim unused storage 

  

### 4.1 Namespace Management and Locking 

여러 master operation은 시간이 상당히 소요된다. 예를 들어 snaphost의 경우 lease를 revoke 시키는 경우 모든 chunkserver에 대해서 lease를 revoke 해야한다. 그러므로, 우리는 적절한 serialization (operation들을 순서대로 처리하는 것) 여러 operation들이 active하게 하고 각 namespace의 region별로 lock을 사용한다. 

전통적인 file system과 다르게 GFS는 per-directory data structure를 사용하지 않으며 file이나 directory에 대한 alias (hard or symbolic links in Unix terms)도 지원하지 않는다. GFS는 full pathname을 metadata에 mapping 하는 lookup table을 통해서 logcial하게 namespace를 나타낸다. prefix compression을 통해서 효과적으로 memory에 저장할 수 있다. namespace tree에 있는 각 node는 관련된 read-write lock을 갖는다. 

각 master operation은 실행되기 전 여러 lock을 획득한다. 보통 /d1/d2/.../dn/leaf에 대해서 operation을 수행하면 dirctory /d1, /d1/d2, ..., /d1/d2/.../dn에 대해서 read lock을 얻고 full pathname /d1/d2/.../dn/leaf에 대해서 write lock을 얻는다. 

GFS locking scheme의 좋은 점은 같은 directory 내부에서 concurrent mutation이 가능하다는 점이다. 예를 들어 한 directory 내에서 여러 파일 생성이 일어날 때 각 mutation은 directory에 대해 read lock을 얻고 file name에 대해 write lock을 얻는다. read lock은 해당 directory가 변경, 삭제되는 것을 막고 write lock은 같은 file name에 대한 시도를 serialize하여 처리한다.

namespace가 여러 node를 가지고 있기 때문에 read-write lock은 lazy하게 할당되며 사용되지 않을 때 한번에 삭제된다. 또한 lock은 deadlock을 방지하기 위해 consistent total order로 획득된다.



### 4.2 Replica Placement 

GFS cluster는 replica factor가 1보다 크게 분산되어있다. 보통 다수의 machine rack에 걸쳐서 수백대의 chunkserver로 이루어져있다. 분산된 chunkserver는 서로 다른 rack으로부터 수백개의 클라이언트로부터 access된다. 서로 다른 rack에 존재하는 두 machine 간 통신은 하나 이상의 network switch를 통하게 되며, rack에 걸쳐이는 bandwidth는 동일한 rack 내부의 machine 간 aggregate bandwidth 보다 작다. scalability, reliability, availability를 위해서 이처럼 multi-level로 replica를 분산시키는 것은 고유의 도전을 의미한다.

chunk replica placemnet policy는 두가지 목적을 수행한다.

- maximize data relibility
- maximize network bandwidth utilization 

이를 위해서 replica를 서로 다른 machine에 대해서만 복제하는 것은 충분하지 않다. 우리는 chunk replica를 rack에 걸쳐서 복제해두어야 한다. 이를 통해서 rack 전체가 실패했을 때도 대처가 가능하고 여러 rack에 걸쳐서 read traffic을 받을 수 있다. write traffic은 여러 rack에 걸쳐서 발생하지만 기꺼이 수용 가능한 tradeoff이다. 



### 4.3 Creation, Re-replication, Rebalancing

chunk replica는 creation, re-replication, rebalancing에 의해 생성된다.

create.

master가 chunk를 create 할 때 빈 replica를 어디에 할당할지 결정한다. 이때 몇가지 factor를 고려한다.

1) 평균 아래의 disk space utilization인 chunkserver. 시간이 지날수록 다른 chunkserver와 utilization이 같아진다.

2) 각 chunkserver에서 최신의 creation이 다수 발생하는 것을 제한한다. 대부분의 application에서append-once-read-only 패턴에 비추어 보았을 때 초기 creation 이후 급격한 대량의 write traffic이 발생할 수 있기 때문이다. 

3) replica는 여러 rack에 걸쳐서 분배되어야 한다.



re-replicate.

master는 가능한 replica의 수가 지정한 replication factor보다 떨어지면 신속하게 re-replicate를 수행한다. re-replicate가 필요한 각 chunk는 여러 factor에 의해 우선순위가 결정된다.

1) replication factor보다 얼마나 모자란지.

2) live file 먼저. delete 예정인 file 보다 자명하게 우선한다.

3) 실행 중인 application에 미치는 실패에 따른 영향도를 최소화하기 위해 client progress를 방해하는 chunk 먼저.

master는 highest prority chunk를 선택한 다음 chunkserver에 명령을 내려서 복제한다.



rebalance. 

master는 주기적으로 replica를 rebalance 한다. master는 현재 replica distribution을 조사한 다음 replica들을 더 나은 disk space, load balancing을 위해 이동시킨다. 이 과정과 더불어서 master는 새로운 chunkserver를 점진적으로 채우며, 새로운 chunk를 급진적으로 받아들여 write traffic이 몰리는 것을 방지한다. 



### 4.4 Garbage Collection 

file을 삭제한 후 GFS는 가능한 물리 저장소를 즉시 회수하지 않는다. file, chunk level 둘 다 regular garbage collection 시에 lazy하게 회수한다. 우리는 이러한 접근이 더 단순하고 신뢰성 있음을 발견하였다.



#### 4.4.1 Mechanism 

file이 application으로부터 삭제될 때 master는 다른 변경처럼 deletion에 대한 log를 남긴다. 하지만 즉시 자원을 회수하는 것이 아니라 file은 단순히 숨김 파일로 변경되며 삭제 예정 timestamp를 가진다 (default 3일이며 설정 가능). master의 regular scan 때 삭제 예정 시간이 지났으면 이 숨김 파일은 master의 metadata에서 삭제된다. 이러한 방법은 효율적으로 chunk로의 링크를 끊는다.

chunk namespace의 regular scan에서 master는 orphaned chunk (file과의 링크가 삭제된 chunk)를 발견하면 master는 해당 chunk에 대한 metadata를 삭제한다. 이후 chunkserver와 주고받는 heartbeat 메시지에서 해당 chunk가 master의 metadata에 존재하지 않는 것을 확인하면 chunkserver는 해당 chunk의 replica를 자유롭게 삭제한다.



#### 4.4.2 Discussion

programming language의 맥락에서 분산 garbage collection은 복잡한 해결책을 요구하는 어려운 문제이지만 GFS에서는 비교적 단순하다. master에 의해서 관리되는 file to chunk mapping을 통해서 모든 chunk에 대한 reference를 확인할 수 있다. 즉, master로부터 확인되지 않은 replica는 garbage다. 

storage 자원 회수에 관한 lazy한 전략은 eager deletion에 비해서 다음과 같은 이점이 있다. 첫째, component의 실패가 빈번한 대규모의 분산 시스템에서는 이 방법이 단순하고 신뢰성있다. master로부터 알려지지 않은 replica를 지우는 이 방법은 동등하고 종속적인 방법을 제공한다. 둘째, storage 자원 회수를 regular background 작업에 merge 시킨다. 그러므로, batch로써 작업이 이루어지고 비용은 amotized 된다. 셋째, 의도적인 지연을 통해서 사고 혹은 비가역적인 삭제를 방지한다. 

경험에 의하면, 이러한 방법의 주요 단점은 storage가 tight하게 사용될 때 사용자에 의한 fine tune을 방해한다는 점이다. 예를 들어 application에서 반복적으로 파일을 생성, 삭제한다면 문제가 될 수 있다. 이러한 문제는 의도적인 삭제에 대한 명시적인 명령을 내릴 수 있도록 하여 해결할 수 있다. 



### 4.5 Stale Replica Detection 

chunk replica는 chunkserver가 실패했거나 down 되었을 때 발생한 mutation을 놓쳤을 때 발생한다. up-to-date replica와 stale replica를 구분하기 위해서 master는 각 chunk에 대해서 chunk version number를 관리한다.

master가 chunk에 새로운 lease를 부여할 때 master는 chunk version을 증가시키고 up-to-date replica에 알린다. master와 replica들은 이 새로운 version number를 persistent하게 관리한다. 만약 replica가 stale한 상태라면 verison number는 증가하지 않을 것이다. stale replica가 정상 상태로 돌아와서 master에게 version number를 master에다 알리면, master는 주어진 version number 현재의 것보다 뒤쳐져 있음을 확인하고 해당 replica를 garbage collection 처리될 수 있도록 한다. 



## 5. Fault Tolerance and Diagnosis

자원들을 완전히 신뢰할 수 없다. 이러한 도전을 어떻게 맞닥뜨렸는지와 문제를 분석하기 위한 tool에 대해서 이야기하고자 한다. 



### 5.1 High Availability

GFS cluster 내 수백대의 서버 중에서 일부는 반드시 unavailable한 상태에 이르른다. 우리는 fast recovery와 replication 이 두가지 전략으로 전체 시스템을 highly available 하게 유지하였다.



#### 5.1.1 Fast Recovery 

master와 chunkserver 둘 다 어떻게 종료되었든 이전 상태를 복구하고 시작하는 데 수초 이내가 걸리도록 설계되었다. 사실 상 우리는 정상 종료와 비정상 종료를 구분하지 않는다. client에서는 서버가 재시작할 때 작은 hiccup (지표에 일시적으로 변동이 가해지는 현상)을 겪는다.  



#### 5.1.2 Chunk Replication 

이전에 논의한대로, 각 chunk는 서로 다른 rack에 걸쳐서 설정한 replication factor만큼 복제되어있다. master는 chunkserver가 잘 동작하지 않을 때 존재하는 다른 replica를 복제한다. 현 replication 전략이 잘 동작하고 있지만 우리는 parity, erasure code와 같은 cross-server redundancy의 형태를 더 탐색하는 중이다. 



#### 5.1.3 Master Replication 

master의 상태는 reliability를 위해서 복제되며, operation log와 checkpoint가 여러 machine에 저장된다. 상태에 관한 mutation은 local disk와 master replica에 flush 되었을 때 commit 된다. 만약 master가 실패했을 때 GFS 밖의 monitoring infrastructure에서 이를 탐지하여 새로운 master process를 기동한다. client 단에서는 서로 다른 master에 대해서 DNS로 접근하고 있기 때문에 전혀 변경 사항이 없다. 

더욱이, shadow master는 primary master가 down 되었을 때 파일 시스템에 대한 read-only access를 제공한다. mirror가 아닌 shadow인 이유는 primary에 대해 약간의 지연이 있을 수 있기 때문이다. 하지만 file content가 아닌 metadata에 대한 지연은 application에 대한 영향이 크지 않다. 

shadow master는 자신을 갱신하기 위해 primary master가 받는 operation log를 읽어 순서 그래도 변경사항을 가한다. 또한 primary처럼 chunkserver를 poll 하고 있으며 monitoring 한다. shadow master는 replica의 생성, 삭제로부터 발생하는 primary의 replica placement에 대한 update에 대해서만 primary에 종속적이다. 



### 5.2 Data Integrity

각 chunkserver는 저장된 data의 corruption을 탐지하기 위해 checksum을 사용한다.  GFS cluster에서 corruption은 흔한 일이고, 우리는 이 corruption을 탐지했을 때 복구할 수 있다. 하지만 다른 replica끼리 비교를 통해 corruption을 하는 것은 상당히 비 실용적이다. 따라서 각 chunkserver는 그들 고유의 checksum 유지함으로써 data integrity에 대한 verification을 해야한다. 

chunk는 64KB block으로 이루어져 있다. 각각은 대응하는 32 bit의 checksum이 있고 다른 metadata처럼 memory 및 persistent에 로그와 함께 저장된다. 

read 요청에 대해서 chunkserver는 응답하기 전 대상 range에 있는 data block에 대한 verification을 수행한다. 만약 checksum이 다르다면 chunkserver는 응답으로 error을 주고 client는 다른 replica로부터 data를 얻는다. 해당 chunkserver는 master에 의해 garbage collection 된다. 

checksum은 성능에 영향을 거의 미치지 않는다. 대부분의 read 요청이 소수의 block에 한정되어있어 verification도 그만큼 이루어진. GFS client는 checksum block boundary에 맞추어 요청을 하기에 overhead를 줄인다. 게다가, checksum lookup 및 comparison은 I/O 없이 발생하고, checksum 계산은 I/O와 overlap 되어 이루어진다. 

checksum 계산은 record append에 최적화되어있다. 마지막 partial checksum block에 대해서 단순히 increment를 시키고, 새로운 checksum block에 대해서는 새로이 계산을 한다.

반대로 write는 대상 range에 있는 기존 block에 대해서 read 및 verification을 하고, write 후 그 block에 대해서 checksum을 계산해서 저장해야 한다. 기존 block에 대한 verification은 반드시 필요한데, 만일 수행하지 않을 경우 corruption 된 data를 overwrite 하기 때문이다.

idle period 시에 chunk server는 scan을 하여 inactive chunk에 대한 verification을 수행한다. 이를 통해서 서버가 모두 valid한 replica만을 들고있다는 가정을 조금 더 완화시킬 수 있다. 



### 5.3 Diagnostic Tools

광범위하고 세부적인 분석 로그는 비용을 거의 발생시키지 않으면서도 문제 격리 (한정적 문제 정의), 디버깅, 성능 분석에 헤아릴 수 없을만큼 중요하다. GFS는 여러 중요한 event와 모든 RPC 요청 및 응답에 로그를 남기고 있다. 이들을 조합해서 모든 상황에 대한 history generation이 가능하다. 로그를 남기는 것은 성능 상에 거의 영향을 주지 않는데, 로그가 sequential 하고 비동기적으로 쓰여지기 때문이다. 



## 6. Measurements

이 section에서는 GFS architecture에 담긴 근본적인 bottleneck을 나타내기 위한 몇몇 micro-benchmark와 google에서 사용되는 실제 cluster에 대한 측정을 다룬다.



### 6.1 Micro-benchmarks

실험을 위한 GFS cluster는 1 master, 2 masters, 16 chunkservers, 16 clients로 구성되어 있다. 모든 machine은 다음과 같은 spec으로 이루어져있다.

- dual 1.4 GHz PIII processors, 2 GB of memory, two 80 GB 5400 rpm disks, and a 100 Mbps full-duplex Ethernet connection to an HP 2524 switch
- All 19 GFS server machines are connected to one switch, and all 16 client machines to the other.The two switches are connected with a 1 Gbps link.



#### 6.1.1-3 Reads, Writes, Record Appends

[![img](https://1.bp.blogspot.com/-WxfATF-aCfQ/X0XUMZtfDLI/AAAAAAAADjc/D4sAcHAY2R8NJjpIdJDk8ZG940ZmwLk-wCLcBGAsYHQ/s640/GFS-Fig3.png)](https://1.bp.blogspot.com/-WxfATF-aCfQ/X0XUMZtfDLI/AAAAAAAADjc/D4sAcHAY2R8NJjpIdJDk8ZG940ZmwLk-wCLcBGAsYHQ/s2254/GFS-Fig3.png)

figure 3은 위 cluster에 대한 aggregate read, write, record append rate를 나타낸다. 기본적으로 ideal peak는 1Gbps link에 의해 125 MB/s에서 saturate되며 client에서는 100 Mbps network interface에 의해 12.5 MB/s에서 saturate 된다.

read.

실제 실험에서는 한 client 연결 시 이론적인 성능의 80%를, client 수가 늘어나면서 추가적으로 80%에서 75%더 감소하였다. 이는 여러 client가 같은 chunkserver에서 동시에 read를 하기 때문이다.

write. 

write는 67 MB/s에서 saturate 되는데, 기본적으로 chunk 하나 당 16개 chunkserver 중 3개씩 write해야하기 때문이다. 실제 성능은 조금 더 작게 증가한다. 이는 동시 write 뿐만아니라 replication factor에서 기인한다.

record append.

성능은 client 수에 상관없이 대상 마지막 chunk를 들고 있는 chunkserver의  network bandwidth에 의해 한정된다. client 수가 늘어날수록 congestion과 network trasfer rate 변수에 영향을 받아 성능이 조금씩 saturate 되었다.

실제 cluster에서는 N clients가 M shared file에 접근하는 형태가 될 것이다. 대량의 cluster에서는 위 congestion이 크게 문제가 되지 않는데, client는 chunkserver가 다른 file로 busy 할 때 다른 file에 먼저 쓸 수 있기 때문이다. 



### 6.2 Real World Clusters

google에서 실제 사용되는 두 cluster 조사 결과이다. cluster A는 연구개발 용으로, cluster B는 실제 production 용으로 사용되었으며 둘은 각기 다른 spec을 가지며 다른 접근 패턴을 보인다. 

[![img](https://1.bp.blogspot.com/-so1NAthwBJg/X0XUWe3OGMI/AAAAAAAADjg/C_geCKM3RxcB3N8Fzgp1lpAZKIU9UBbbwCLcBGAsYHQ/s640/GFS-Tab2.png)](https://1.bp.blogspot.com/-so1NAthwBJg/X0XUWe3OGMI/AAAAAAAADjg/C_geCKM3RxcB3N8Fzgp1lpAZKIU9UBbbwCLcBGAsYHQ/s952/GFS-Tab2.png)

6.2.1 Storage

두 cluster는 수백 chunkserver로 이루어진 storage로 사용되었으며 replication factor가 3임을 고려했을 때 실제 데이터 저장률은 used disk space의 1/3이 될 것이다.

6.2.2 Metadata

chunkserver의 metadata 용량은 64KB data block가지는 checksum이 대부분이며 chunk version number 또한 포함된다.

master의 metadata 용량은 훨씬 적은데 이는 우리가 초기 논의했던 master의 memory 이슈가 전체 system capacity에 영향을 미치지 않을 것이라는 주장과 일치하는 결과를 보여준다.

각 chunkserve와 master는 50~100MB 크기의 metadata를 가지고 있어 recovery가 신속하다. 다만, master의 경우 온전히 동작하려면 30~60초가 걸리는데, chunk location정보를 모두 취합해야 하기 때문이다.

6.2.3-5 Read and Write Rates, Master Load, Recovery Time 

[![img](https://1.bp.blogspot.com/-NEy1WoZ_RDo/X0XUekwtFjI/AAAAAAAADjo/oyzUI5UygXEKi4O1xPjDCNXXhXtzuCtsgCLcBGAsYHQ/s640/GFS-Tab3.png)](https://1.bp.blogspot.com/-NEy1WoZ_RDo/X0XUekwtFjI/AAAAAAAADjo/oyzUI5UygXEKi4O1xPjDCNXXhXtzuCtsgCLcBGAsYHQ/s1092/GFS-Tab3.png)



### 6.3 Workload Breakdown

이 section에서는 두 cluster에 대한 workload 분석을 하려고 한다. cluster X는 연구개발용이며 cluster Y는 production의 data processsing 용이다.



#### 6.3.1 Methodology and Caveats

결과는 client로 비롯된 request만을 포함하였다. I/O에 관한 통계는 GFS 서버에 로깅된 실제 RPC 요청을 바탕으로 heuristic하게 reconstruct 되었다.

논문을 통해서 workload에 대한 지나친 일반화를 조심하였으면 한다. google에서는 GFS와 application 모두 완전히 통제하고 있다. application은 GFS에 맞게 설계되었으며 역으로 GFS도 application을 위해 설계되었다. 



#### 6.3.2 Chunkserver Workload

[![img](https://1.bp.blogspot.com/-3vPoGjEdwEE/X0XUldO-peI/AAAAAAAADjs/qEUT50oKAeUSmlecOUPzsEPAA39qMj9lgCLcBGAsYHQ/s640/GFS-Tab4.png)](https://1.bp.blogspot.com/-3vPoGjEdwEE/X0XUldO-peI/AAAAAAAADjs/qEUT50oKAeUSmlecOUPzsEPAA39qMj9lgCLcBGAsYHQ/s1044/GFS-Tab4.png)

[![img](https://1.bp.blogspot.com/-6GzP4GF1HXs/X0XUoWwwZ7I/AAAAAAAADj0/6t7vJsYQOEM0nCTK1XoGFJ58XPv-bDrfACLcBGAsYHQ/s640/GFS-Tab5.png)](https://1.bp.blogspot.com/-6GzP4GF1HXs/X0XUoWwwZ7I/AAAAAAAADj0/6t7vJsYQOEM0nCTK1XoGFJ58XPv-bDrfACLcBGAsYHQ/s1038/GFS-Tab5.png)

table 4는 size 별 operation 분포를 보여준다. 

read의 경우 64KB 이하는 큰 파일에서 작은 부분을 찾기 위한 seek-intensive 한 작업이며 512KB 이상은 긴 sequential read이다. cluster Y는 상당한 비율로 read의 결과 0을 retrun 하는데, 이는 producer-consumer queue에서 consumer가 producer 보다 overpace 된 상황으로부터 온다. X는 data analysis 목적으로 사용되어 short-lived data를 read 하기 때문이 그 비율이 적다.

write의 경우 256KB 이상은 writer의 buffering으로부터 온다. 작은 data를 buffer 한 경우는 checkpoint, syschronize 할 때나 혹은 정말로 작은 data를 write 할 때이다.

table 5는 operation의 size 별 data transfer 비율이다. 대부분의 data transfer는 큰 size에서 발생하며 read의 경우 소량의 random seek이 큰 비율을 차지하고 있다.

6.3.3 Appends and Writes 

record append는 production system에서 무겁게 사용되었다. cluster X의 경우 write 대비 record append는 108:1의 비율이며 byte transfer로는 8:1이다. cluster Y의 경우 각각 3.7:1, 2.5:1이다. 기대한대로 record append의 비율이 압도적으로 dominate 하였다. 또한 대부분의 overwrite는 client retry에서 발생하였다.

#### 6.3.4 Master Workload 

[![img](https://1.bp.blogspot.com/-INIR8ovIKKo/X0XUvRO4L9I/AAAAAAAADj8/T5vXPToMBfQras1FpTzgKZWIoRFRdOpIACLcBGAsYHQ/s640/GFS-Tab6.png)](https://1.bp.blogspot.com/-INIR8ovIKKo/X0XUvRO4L9I/AAAAAAAADj8/T5vXPToMBfQras1FpTzgKZWIoRFRdOpIACLcBGAsYHQ/s1004/GFS-Tab6.png)

master의 workload 중 대부분의 요청은 chunk locations에 대한 request (FindLocation)고 lease holder information에 대한 request (FindLeaseHolder)였다. 



## 7. Experiences

GFS를 디자인하고 배포하는 과정에서 opeational, technical 한 다양한 이슈들을 겪었다. 

먼저 GFS는 backend file system으로 인식되었으나 다양한 용처가 생기면서 permission, quota 등에 대한 근본적인 필요성이 제기되었다.

맞닥뜨린 가장 큰 문제들은 disk와 linux로부터 왔다. 자세한 내용은 논문을 참조하기를 바란다. 



## 8. Related Work

GFS가 채택한 설계는 여러 연구와 관련이 있다. 자세한 내용은 논문을 참조하기를 바란다. 

- location independent namespace

- a set of disks distributed in networks, rather than RAID

- do not provide any caching

- centralized server, rather than relying on distributed algorithms for consistency and management 

- delivering aggregate performance to a large number of clients 

- atomic record appends

  

## 9. Conclusions 

 GFS는 성공적으로 google의 storage 수요를 충족시켰으며 다양한 분야에서 storage platform에서 사용되고 있다. GFS는 전체 web scale의 문제들을 혁신하고 뛰어넘게 하기 위한 중요한 tool로 자리 잡았다. 



## References

- Sanjay Ghemawat, Howard Gobioff, & Shun-Tak Leung (2003). The Google File System. In *Proceedings of the 19th ACM Symposium on Operating Systems Principles* (pp. 20–43).

- https://www.cs.princeton.edu/courses/archive/fall18/cos418/docs/p8-consistency.pdf