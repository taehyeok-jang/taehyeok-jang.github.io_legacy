---
layout: post
title: (Paper Review) MapReduce - Simplified Data Processing on Large Clusters
subheading: 
author: taehyeok-jang
categories: [distributed-systems]
tags: [paper-review, distributed-systems, map-reduce]
---

## Background

computation은 아마도 컴퓨터가 존재하는 목적 그 자체일 것이다. 컴퓨터가 탄생한 시기와는 달리 현대에는 대량의 데이터를 수집, 저장하는 것이 가능해졌고 이를 적절한 수행시간 내에 처리하기 위해서 여러 컴퓨터에 데이터를 분산시켜서 (parallelism, distributed) 처리하는 방법이 제안되었다. 이중 MapReduce는 2000년대 초 Google에서 개발한 프로그래밍 모델 및 구현으로 수천대의 상용 컴퓨터로 이루어진 cluster에서 대량의 데이터가 병렬, 분산처리 될 수 있도록 하였다. 논문에서도 보여주듯 이 분산처리 computation model은 초기 Google에서 성공적으로 사용되었고 현재에도 대량의 데이터를 처리하는 모든 곳에서 널리 사용되고 있다. MapReduce 이후 Spark와 같은 다양한 분산처리 library들이 특성에 맞게 사용되고 있지만 분산처리 computation model을 위한 MapReduce를 잘 이해하는 것은 필연적으로 도움이 될 것이다. 본 review에서는 논문의 번역 및 요약과 더불어 중간중간 부연 설명을 추가하였다. 세부사항은 생략하였으니 논문을 참조하기를 부탁드린다.

2018년 처음 이 논문을 읽기를 시도했었는데 너무 어려워서 읽지 못하고 포기했던 기억이 있다. 하지만 그동안 알게된 분산 시스템에 대한 기초 지식과 Hadoop MapReduce를 직접 사용해본 경험을 가지고 논문을 다시 읽으니 이전보다 훨씬 더 논문이 잘 읽혔다. (짝짝짝!!!)





## Abstract

MapReduce는 large data set을 process하고 generate하기 위한 programming model과 그에 따른 implementation이다. programmer는 key/value pair를 처리하여 intermediate key/value pairs를 생성하는 map function과 같은 intermediate key들을 merge하는 reduce function을 통해 MapReduce program을 구현한다. paper에서 보여주듯 수많은 real world task들이 map reduce를 통해 표현 가능하다.

함수형으로 작성된 program은 자동으로 병렬처리 되어 상용 machine으로 이루어진 대량의 cluster에서 실행된다. MapReduce의 runtime system은 분산 시스템 환경에서 필요한 여러 실행 세부사항들인 partitioning input data, scheduling the program execution across a set of machines, handling machine failures, and managing the required inter-machine communication들을 수행한다. 이러한 abstraction은 병렬, 분산 시스템의 지식이 없는 programmer도 분산 시스템의 resource를 쉽게 활용할 수 있도록 한다. 



## 1. Introduction 

Google에서는 crawled documents, web request logs 등 대량의 raw data로부터 inverted indices, graph structe of web documents 등 derive data로 처리하기 위한 special-purpose computations들이 작성되었다. 하지만 input data의 크기가 매우 커짐으로써 computation은 필연적으로 수천대의 machine에 분산처리 될 필요가 있었다. 하지만 분산처리 환경에서의 다음과 같은 문제들은 원래 처리해야할 단순한 computation program의 본질을 흐려 complexity를 높였다.

- parallelize a computation 
- distribtue data across a set of machines
- handle machine failures (fault-tolerant)

이러한 complexity를 해결하고자, 분산 시스템에서의 처리를 위한 위의 복잡한 detail은 숨기고 단순한 computation model만을 구현하는 새로운 abstraction을 design 하였다. 이 abstraction은 LISP 및 여러 함수형 언어의 map, reduce primitive로부터 영감을 얻었다. Google은 그들이 기존에 사용하였던 대부분의 computations 들이 map, reduce를 적용하는 것을 포함하는 것을 깨달았다. 또한 이러한 functional model의 사용은 병렬처리와 fault tolerance에 대한 primary mechanism으로서 re-execution을 쉽게 하였다.

논문에서 주요 contribution은 두가지다.

- a simple and powerful interface, that enables parallization and distribution of large-scale computations
- an implementation of this interface that achieves high performance on large clusters of commodity PCs.



## 2. Programming Model 

MapReduce는 input key/value pairs를 받아서 output key/value pairs를 생성한다. MapReduce library의 사용자는 다음의 두 function을 표현한다. 

Map. 

input pair를 받아서 intermediate key/value pairs를 생성한다. MapReduce library는 같은 intermediate key를 가진 intermediate value들을 group 지어 Reduce function으로 보낸다. 

Reduce. 

intermediate key와 해당 key를 가진 value의 set들을 input으로 받는다. 실제 program 상에는 value의 iterator가 주어져서 memory에 저장하는 것 이상의 value들에 접근할 수 있도록 한다. 주어진 input을 merge 등 추가 처리하여 최종 output을 만들어낸다. 

### 2.1 Example

다음은 대표적인 computation model인 word count의 pseudo code이다. 

```pseudocode
map(String key, String value): 
	// key: document name
	// value: document contents 
	for each word w in value:
		EmitIntermediate(w, "1");

reduce(String key, Iterator values): 
	// key: a word
	// values: a list of counts
	int result = 0;
	for each v in values:
		result += ParseInt(v);
	Emit(AsString(result));
```



### 2.2 Types

위 pseudo code에서는 strinng input, output으로 표현되었지만 개념적으로는 아래와 같은 type으로 표현된다.

```pseudocode
map (k1,v1) → list(k2,v2) 
reduce (k2,list(v2)) → list(v2)
```



### 2.3 More Examples 

다음은 MapReduce computation model로 쉽게 표현될 수 있는 여러 흥미로운 program들이다. 기대보다 더 단순한 형태로 해당 program이 작성될 수 있음에 놀랄 것이다.

Distributed Grep, Count of URL Access, Reverse Web-Link Graph, Term-Vector per Host, Inverted Index, Distribued Sort



## 3. Implementation 

MapReduce interface의 구현은 여러 방안으로 가능하며 가장 적합한 것은 실행 환경에 달려있다. 소규모의 shared-memory machine이나 NUMA multi-processor, 혹은 networked machine으로 이루어진 대량의 cluster 등 다양한 환경에서 구현이 이루어질 수 있다. 논문에서는 Google에서 널리 사용되고 있는 switched Ethernet 내 상용 machine으로 이루어진 cluster를 대상으로한 구현을 다룬다. 환경은 아래와 같다. 처음 논문이 공개된 시기가 2004년이므로 현재 2020년도 보다 hardware 성능이 떨어지지만 서로 다른 성능의 상용 machine을 그대로 활용한다는 점, hardware (CPU, network) 성능이 선형적으로 증가했다는 점에서 크게 다르지 않다. 따라서 여전히 network bandwidth가 귀중한 자원이며 분산 시스템에서의 잠재적 위험성은 유요하다. 

1) Machines are typically dual-processor x86 processors running Linux, with 2-4 GB of memory per machine. 

2) Commodity networking hardware is used – typically either 100 megabits/second or 1 gigabit/second at the machine level, but averaging considerably less in over- all bisection bandwidth.

3) A cluster consists of hundreds or thousands of ma- chines, and therefore machine failures are common.

4) Storage is provided by inexpensive IDE disks at- tached directly to individual machines. A distributed file system [8] developed in-house is used to manage the data stored on these disks. The file system uses replication to provide availability and reliability on top of unreliable hardware.

5) Users submit jobs to a scheduling system. Each job consists of a set of tasks, and is mapped by the scheduler to a set of available machines within a cluster.



### 3.1 Execution Overview 

Map function은 여러 machine에 걸쳐 일어나며 input data는 M splits paritioning 만큼 분산된다. 각 input splits은 서로 다른 machine들에서 병렬로 처리된다. Reduce function은 주어진 intermediate key space가 R개로 partitioning 되어 실행된다. 이때 partitioning function은 'hash(key) mod R' 등의 function이 사용된다.

MapReduce operation의 overall flow는 Figure 1에서 나타내고 있다.

1. MapReduce library는 input files를 M pieces (보통 16MB~64MB. GFS의 기본 unit 단위 크기)만큼 분할한다. 그다음 cluster 내 machine들에 구현한 computation program을 실행한다.
2. 이 program들 중 하나는 별도의 기능을 하며 master라고 한다. 다른 program들은 worker라고 부른다. 총 M개의 map task, R개의 reduce task가 있으며 master는 idle worker를 선택하여 task를 할당한다.
3. map task를 할당 받은 workder는 input split으로부터 data를 읽는다. input data로부터 key/value pair를 parse하여 Map function으로 전달한다. Map function에 의해 생성된 intermediate key/value pair는 memory에 buffer 된다.
4. buffer된 key/value pair는 주기적으로 local disk에 저장된다. 이때 partitioning function에 의해 R개의 region으로 분할되어 저장된다. local disk에 저장된 각 buffered pair의 location은 master에 전해지며 master는 reduce task를 수행하는 worker에 이를 전달한다.
5. reduce worker가 master로부터 partitioned intermediate key/value pair에 대한 location 정보를 받으면, RPC를 통해서 map worker에 있는 buffered data를 읽는다. data를 모두 읽으면 intermediate key에 대해 sort를 수행하여 같은 key를 가지고 있는 data는 group 지어지도록 한다. 이는 반드시 필요한 과정인데, 서로다른 key들이 같은 reduce task에 전달될 수 있기 때문이다. sorting 중 data가 memory에 담기 너무 크면 external sort가 수행된다. 
6. reduce worker는 sort 된 intermediate data를 iterate 하면서 key와 그에 대응하는 value set을 Reduce function으로 전달한다. Reduce function의 output은 해당 reduce partition의 최종 output file이 된다. 
7. 모든 map task, reduce task가 완료되면 master는 user program을 깨운다. 

실행을 완료하면 주어진 MapReduce execution의 output은 R개의 output file로 존재한다. 종종 우리는 이 R개의 output file을 그대로 두는데 이는 또다른 MapReduce program의 input data로 바로 활용하거나 다른 distributed application에 사용된다.



### 3.2 Master Data Structures

master는 여러 data structure를 유지한다. 개별 map task, reduce task에 대한 state (idle, in-progress, completed)와 non-idle worker machine의 identity를 저장한다. 또한 master는 각 map task에서 reduce task로 전달되는 intermediate file region에 대한 location 정보(O(M*R))를 저장하는 수로와도 같다. map task가 완료될 때마다 location과 size 정보는 update되며 in-progress 상태의 reduce task에 점진적으로(incrementally) 전달된다. 



### 3.3 Fault Tolerance 

MapReduce library는 수백, 수천대의 machine에서 대량의 data를 처리하기 위해 발명되었으므로 machine failure에 graceful하게 대처하여야 한다. 

machine failures in a distributed system?

분산 시스템에서 machine failure는 드문 현상이 아니다. single machine에서 hardware failure가 일어날 가능성은 낮지만 이를 수천대 운용하는 cluster에서 하루에 하나의 machine 이상에서 failure가 날 가능성은 비교적 높다. 



Worker Faliure

master는 모든 worker에 주기적으로 ping을 날린다. worker가 응답하지 않으면 master는 해당 node를 failed 처리하고 할당된 map task 혹은 reduce task를 완료한 worker에 실패한 task를 re-scheduling하여 재 실행될 수 있도록 한다. 만약 어떤 map task가 worker A에서 수행되다가 worker A가 실패하여 workder B에서 최종 수행되었다면, 이 결과를 read할 reduce task는 master로부터 재실행에 관해 알려지고 worker B로부터 read 해간다.

MapReduce는 다수의 workder failure에도 resilient하다. 만약 network maintenance 등으로 수분동안 수십대의 machine이 사용 불가능하더라도 master는 단순히 re-scheduling 후 재실행하여 'eventually complete' 될 수 있도록 한다. 



Master Failure 

master data strcuture에 대해 주기적인 checkpoint를 write하여 master가 실패했을 때 last checkpoint로부터 재수행하는 것이 가능하다. 하지만 single master에서 실패는 unlikely 하므로 현재의 구현은 MapReduce computation을 abort 시킨다. client는 이를 확인하여 언제든지 재시도 할 수 있다.



Semantics in the Presence of Failures 

user가 구현한 map function, reduce function이 deterministic하다면 MapReduce의 분산 실행은 single machine에서의 non-faulting sequential execution과 같은 결과를 생성한다.

Google의 MapReduce는 이러한 성질을 위해 map, reduce task의 atomic commit에 의존한다. 각 in-progress task는 output을 private temporary file에 쓴다. map task는 R개의 file을, reduce task는 1개의 file을 생성한다. map task가 완료되면 worker는 master에게 R개의 temporary file의 이름을 알려주고, 만약 같은 이름의 file이 담긴 message를 이미 받았으면 무시하고 아니면 master data structure에다가 write 한다. reduce task가 완료되면 reduce worker는 temporary output file에 filnal output file를 atomic하게 rename한다. 이 atomic rename operation은 최종적으로 파일 시스템에 해당 reduce task가 올바르게 한번 수행될 수 있도록 한다. 

만약 map, reduce task가 non-determinitic 하더라도 우리는 weaker, but still reasonable한 결과를 보장할 것이다. 하지만 map task M, reduce task R1, R2가 있는 상황을 가정하자. e(Ri)를 commit된 (exactly executed once) execution으로 정의한다면 여기서 weaker semantics이 발생하는데, e(R1)과 e(R2) 각각은 map task M의 서로 다른 non-deterministic한 결과를 읽기 때문이다.



### 3.4 Locality

Google의 MapReduce의 구현에서 performance 상 매우 중요한 attribute이다.

computing environment에서 network bandwidth는 매우 희소한 자원이므로, input data가 computing cluster를 이루는 machine들의 local disk에 저장된 것을 활용하였다. 즉, MapReduce는 각 input file들의 location 정보를 고려하여 특정 map task가 input data의 replica가 있는 machine 상에서 실행될 수 있도록 하였다. 이것이 실패하더라도 replica의 주변 (ex. 같은 network switch)에서 수행되도록 하였다. 결과적으로 대부분의 input data가 local read 하였고 network bandwidth를 소모하지 않았다. 



### 3.5 Task Granularity 

위에서 map phase를 M 조각으로, reduce phase를 R 조각으로 세분하였다. 이상적으로 M, R은 worker machine 수보다 아주 크게 잡아야 한다. 각 worker가 여러 다른 task를 수행하게 하는 것은 dynamic load balancing에 유리하고 worker가 실패했을 때 recovery 속도도 높인다. 

M, R을 얼마나 크게 잡아야할지에 대한 practical bound는 존재한다. master는 O(M+R)의 scheduling을 정해야 하고 위에서 언급했듯이 O(M*R)만큼의 state, location 정보를 유지해야 한다. (memory에 저장되는 절대적 크기는 크지 않다)

R은 R개의 output file을 생성하는 것을 의미하므로 구현하는 사용자에 의해서 정해진다. M은 실용적으로 input data의 크기가 16MB~64MB가 되도록 정하여 locality를 극대화하도록 한다. Google에서 수행한 실험에서는 2000대의 machine 환경에서 M = 200K, R = 5K로 종종 수행하였다.



### 3.6 Backup Tasks 

MapReduce의 수행시간을 길게하는 원인 중 하나로 straggler가 있다. straggler는 소수의 map task 혹은 reduce task를 수행하는 데 비정상적으로 긴 시간을 소요하는 machine을 의미한다. straggler는 여러 이유에서 발생한다. bad disk, scheduling으로 인한 CPU, memory, disk, network bandwidth 등 자원의 경합이 될 수 있다. 최근에 발견한 bug로는 processor cache를 disable 시키는 initialization code도 있었다.

이러한 straggler로 인한 문제를 완화하기 위해서 general mechanism을 도입하였다. MapReduce operation이 수행 완료에 가까워지면 master는 남아있는 in-progress task에 대한 backup execution을 schedule 한다. 그러면 그 task는 primary 혹은 backup execution에서 완료하게 된다. 논문에서는 이 mechanism을 tune 하여 수 percent의 추가 자원을 사용하면서 수행 완료시간을 상당히 줄이는 결과를 얻었다.



## 4. Refinements 

논문 참조. 



## 5. Performance 



### 5.1 Cluster Configuration 

약 1800개 machine으로 이루어진 cluster에서 MapReduce program을 수행하였다. 각 machine은 2GHz Intel Xeon Processor (with hyper treadin enabled)를 가지며 4GB memory, 2개의 160GB IDE disk, gigabit Ethernet link로 구성되었다. machine들은 2-level tree-shaped switched network에 arrange 되어 root로부터 도합 약 100-200Gbps의 bandwidth를 가진다. 모든 machine은 같은 hosting facility (IDC)에 있어 임의의 machine 간 RTT는 1ms 이내이다.

### 5.2 Grep

[![img](https://1.bp.blogspot.com/-beYCO6WhGYI/XzAjZGpC-6I/AAAAAAAADhw/gxZ5N0NXw1YndRg8tJ6ABXBHBx7La-TAwCLcBGAsYHQ/w328-h209/MapReduce-Fig2.png)](https://1.bp.blogspot.com/-beYCO6WhGYI/XzAjZGpC-6I/AAAAAAAADhw/gxZ5N0NXw1YndRg8tJ6ABXBHBx7La-TAwCLcBGAsYHQ/s860/MapReduce-Fig2.png)

grep program은 10^10 100-byte records를 scan하며 비교적 rare한 세글자의 pattern을 search한다. input split은 약 64MB로 분할되었고 (M = 15K) ouput은 하나의 file에 저장된다 (R = 1). 

Figure 2는 시간에 따른 computation의 progress를 나타낸다. 점점 더 많은 machine에서 MapReduce computation을 할당 받을 수록 rate는 점진적으로 증가하다가 1764 workers가 할당 받았을 때 peak를 찍는다. map task가 완료되면 rate는 줄어들기 시작한다. 전체 수행시간은 약 150초가 소요되었다. 이 수행시간에는 startup overhead가 존재한다. overhead에는 propagation of the program to all worker machines, delays interacting with GPS to open the set of 1000 input files, get the inforamation needed for the locality optimization이 포함된다. 

### 5.3 Sort 

[![img](https://1.bp.blogspot.com/-CTWBB2Re91U/XzAjihjZW5I/AAAAAAAADh0/x507g1NquzIMnTgPqUJ4tk4SoKI3-KgmwCLcBGAsYHQ/s640/MapReduce-Fig3.png)](https://1.bp.blogspot.com/-CTWBB2Re91U/XzAjihjZW5I/AAAAAAAADh0/x507g1NquzIMnTgPqUJ4tk4SoKI3-KgmwCLcBGAsYHQ/s1222/MapReduce-Fig3.png)

sort program은 10^10 100-byte records (=~ 1TB)를 sort 한다. 이 program은 TeraSort benchmark를 따라서 구현되었다. 

sorting program은 50 line이 안되는 user code로 이루어져 있으며 3 line의 Map function은 textline으로부터 10-byte의 sorting key를 추출하여 key와 value를 intermediate key/value pair로 보낸다. Reduce function은 built-in Identity function을 사용하며 intermediate key/value pair를 그대로 output key/value pair로 보낸다. 최종 output은 2-way replicated GFS file로 저장된다. 

input data는 64MB 크기로 (M = 15000) 분할된다. sorted output은 4000개의 file에 (R = 4000) 저장된다. partitioning function은 R piece중 하나로 분리하기 위해 key의 초기 몇 byte를 사용한다.

Figure 3은 sort program의 execution에 대한 progress를 나타낸다. 위의 graph는 input이 read되는 input rate를 나타낸다. 중간의 graph는 shuffle rate, data가 map task로부터 reduce task로 network 상에서 이동하는 rate를 나타낸다. 아래의 graph는 reduce task에서 sorted data가 최종 output file로 write 되는 rate를 나타낸다. 

주목해야 할 몇가지가 있는데, input rate가 shuffle rate와 output rate 보다 비약적으로 높다는 점인데 이는 locality optimization에 따른 결과이다. 제한된 network bandwidth  환경에서 local disk에서 대부분의 data read가 일어났기 때문이다. shuffle rate는 output rate보다 높은데 이는 output phase는 sorted data의 2개의 copy를 write 하기 때문이다. GFS에서 data의 availability, reliability를 위해 서로 다른 machine에 data를 저장하기 때문에 network 상의 data transfer가 발생하여 network bandwidth를 상당 부분 차지한다. 

### 5.4 Effects of Backup Tasks

Figure 3의 (b)에서 backup task가 disable 된 program의 execution을 보여준다. execution flow는 (a)와 거의 같지만, 소수의 task에서 지연이 발생하여 전체 수행시간은 1283 secs가 되어 44%의 지연이 발생하였다.

### 5.5 Machine Failures 

Figure 3의 (c)은 의도적으로 1746 workers 중 200개를 죽이는 program의 execution을 나타낸다. cluster의 scheduler는 즉시 새로운 process를 수행한다. worker의 kill은 일시적으로 input rate를 음의 값에 이르게 하지만 map task의 re-execution은 매우 신속하게 일어나 전체 computation은 993 secs만에 끝나 총 5%의 지연만을 발생시켰다. 



## 6. Experience

MapReduce library의 초기 버전은 2003년 2월에 작성되었고 locality optimization, dynamic load balancing 등의 비약적인 개선은 2003년 8월에 이루어졌다. 당시 MapReduce library가 Google에서 다루는 아주 다양한 문제들에 적용될 수 있음을 확인하였다

- large-scale machine learning problems
- clustering problems for the Google News and Froogle products
- extraction of data used to produce reports of popular queries (e.g. Google Zeitgeist)
- extractionofpropertiesofwebpagesfornewexperiments and products (e.g. extraction of geographi- cal locations from a large corpus of web pages for localized search)
- large-scale graph computations



## 7. Related Work 

아래 MapReduce의 key idea나 implementation은 다양한 논문으로부터 왔다. 자세한 것은 논문을 참조하기를 바란다.

- a programming model to abstractize parallelization 
- locality optimization 
- backup task mechanism 
- in-house cluster management system 
- a programming model where processes communicate with each other by sending data over distributed queues 



## 8. Conclusion

MapReduce programming model은 Google에서 여러 목적을 위해 성공적으로 사용되었다. 연구는 다음과 같은 이유로 성공에 기여하였다.

- model is easy to use, even for programmers without experience with parallel and distributed systems
- a large variety of problems are easily expressible 
- an implementation of MapReduce that scales to large clusters of machines 

그리고 연구로부터 다음을 배웠다.

- restricting the programming modle makes it easy to parallelize and distribute computations and to make such computations fault-tolerant. 
- network bandwidth is a scarce resource. the locality optimization and writing a single copy of an intermediate data to local disk saves network bandwidth.
- redundant execution can be used to reduce the impact of slow machines, and to handle machine failures and data loss.



## References

- Jeffrey Dean, & Sanjay Ghemawat (2004). MapReduce: Simplified Data Processing on Large Clusters. In *OSDI'04: Sixth Symposium on Operating System Design and Implementation* (pp. 137–150).


