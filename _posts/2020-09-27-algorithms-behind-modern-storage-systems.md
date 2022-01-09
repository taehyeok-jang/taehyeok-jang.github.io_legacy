---
layout: post
title: (Paper Review) Algorithms Behind Modern Storage Systems
subheading: 
author: taehyeok-jang
categories: [database]
tags: [paper-review, database, b-tree, lsm-tree]
---



## Introduction 

어플리케이션으로부터 생성되는 데이터 양은 점점 증가하여 이를 저장하기 위한 storage를 확장하는 것은 더욱 도전적인 문제가 되었습니다. 각 데이터베이스 시스템은 성능 상 고유의 trade-off가 있기 때문에 그들의 원리를 잘 이해하고 사용하는 것은 중요합니다. 각 어플리케이션은 read/write 접근 패턴, 요구되는 일관성 수준과 latency 등이 상이하기 때문에 어플리케이션 설계 시 이들의 특성을 잘 이해하고 가장 최적화된 데이터베이스를 선택해야 합니다. 2020년 Stack Overflow Developer Survey에 따르면 주로 사용되는 데이터베이스로 관계형 데이터베이스인 MySQL, PostgreSQL부터 NoSQL의 대표 데이터베이스인 Cassandra 등 아주 다양합니다. 각각의 데이터베이스는 다양한 기능을 지원하지만 이들의 핵심 구동원리에 해당하는 자료구조는 그 디테일을 제외한다면 소수의 몇개로 정해져있습니다. 그러므로 이 자료구조들을 이해한다면 각 데이터베이스의 특성에 대해서도 쉽게 알 수 있을 것입니다. 이번 글에서는 관련된 논문을 읽으면서 (Alex Petrov, 2018) 대부분의 현대 데이터베이스 시스템에서 사용되고 있는 두가지 큰 storage system인 B-Tree, LSM-Tree와 각각의 use case, trade-off를 알아보겠습니다.



## B-Tree

B-Tree는 read optimized 자료구조로서 binary tree의 일반화된 형태입니다. 수많은 변형이 있으며 여러 데이터베이스 (MySQL InnoDB, PostgreSQL)와 파일 시스템(HFS+, HTrees in ext4)에서도 사용되고 있습니다. B-Tree의 개념에 대해서 쉽게 이해하기 위해서 다음의 자료를 참조할 것을 추천합니다. 

https://www.cs.princeton.edu/courses/archive/fall06/cos226/lectures/balanced.pdf
[![img](https://1.bp.blogspot.com/-am75dhLjeK8/X3E2XYlDv5I/AAAAAAAADoo/RF1sD1P8Waw4j8oP2N2G4Oh-qr2d1txiQCLcBGAsYHQ/w400-h195/b-tree.png)](https://1.bp.blogspot.com/-am75dhLjeK8/X3E2XYlDv5I/AAAAAAAADoo/RF1sD1P8Waw4j8oP2N2G4Oh-qr2d1txiQCLcBGAsYHQ/s1572/b-tree.png)

위 자료는 프린스턴 대학의 알고리즘 강의 중 일부입니다. binary tree부터 시작해서 balanced tree인 red-black tree, 그리고 이들 자료구조가 일반화된 형태인 2-3-4 tree, B-Tree를 다루고 있습니다. B-Tree는 node 당 지정된 개수의 link를 가진 balanced tree라고 이해하면 되겠습니다. B-Tree의 성질은 다음과 같습니다.

- Sorted
- Self-balancing. insertion 시에 overflow 혹은 deletion 시에 일정 수준의 occupancy가 떨어지는 것을 확인하여 node 분할 혹은 합병을 합니다
- Guarantee of logarithmic lookup time
- Mutable



## LSM-Tree

LSM-Tree (log-structured merge tree)는 write optimized 된 immutable, disk-resident 한 자료구조입니다. read 보다 write가 더 빈번한 시스템에서 우수한 성능을 가집니다. 현재 LSM-Tree가 더 인기를 얻고 있는는 것은 디스크 성능을 저하시키는 random insert, update, delete를 없앴기 때문입니다. 

### Anatomy of LSM-Tree

sequential write를 허용하기 위해서, 즉 write를 sequential하게 만들기 위해서 LSM-Tree는 write, update를 memory-resident table에 batch 형태로 저장합니다. 여기에 사용하는 자료구조는 binary search tree나 skip list 등을 사용합니다. batch 크기가 다 차면 이때 한번에 disk로 저장(flush)합니다. 데이터를 retrieve 하는 것은 모든 disk-resident 부분과 in-memory table을 찾아보아야 하며 결과를 돌려주기 전에 merge를 수행합니다. [![img](https://1.bp.blogspot.com/-slWHSy63a3c/X3E2yPKWICI/AAAAAAAADow/0lghKH0dZLwzP5fM3O7eJq4ojtOL59aywCLcBGAsYHQ/w640-h180/lsm-tree-01.png)](https://1.bp.blogspot.com/-slWHSy63a3c/X3E2yPKWICI/AAAAAAAADow/0lghKH0dZLwzP5fM3O7eJq4ojtOL59aywCLcBGAsYHQ/s1430/lsm-tree-01.png)



### SSTable (Sorted String Table)

현대 여러 LSM-Tree의 구현은 disk-resident table로서 SSTable을 사용하고 있으며, 그 이유로는 단순함 (read/write, search가 쉽다)과 병합 성질 (병합 중 SSTable scan과 병합된 결과의 write가 sequential 하다)이 있습니다. SSTable은 disk-resisdent ordered immutable 자료구조입니다. 구조적으로 data block과 index block으로 나누어져 있어 주로 sparse index 형태의 index block에 먼저 접근하여 data block으로 접근합니다. data block의 모든 value는 insert, update, delete가 수행된 시점의 timestamp를 가집니다.

SSTable은 다음과 같은 성질을 가집니다.

- point query는 primary index를 찾음으로써 매우 빠르게 수행됩니다
- scan은 data block으로부터 key/value가 순차적으로 read되기 때문에 효율적으로 이루어질 수 있습니다

SSTable은 memory-resident table이 flush에 의해 disk에 쓰이기 전 일종의 snapshot이라고 할 수 있습니다. 

[![img](https://1.bp.blogspot.com/-JqlWhSQoZ2g/X3E286XVbRI/AAAAAAAADo0/mBbIQtwGGT4WshAJ8WZ_yjdectyOWxvggCLcBGAsYHQ/w640-h308/lsm-tree-02.png)](https://1.bp.blogspot.com/-JqlWhSQoZ2g/X3E286XVbRI/AAAAAAAADo0/mBbIQtwGGT4WshAJ8WZ_yjdectyOWxvggCLcBGAsYHQ/s1292/lsm-tree-02.png)



### Lookups

SSTable의 데이터를 retrieve 하는 과정을 살펴보겠습니다.

- search all SSTables on disk
- check the memory-resident table
- merge their contents together before running the result

검색된 data는 여러 SSTable에 있을 수 있기 때문에 read 중에 merge step을 포함하여 이들을 합칩니다. merge step은 update, delete에 대한 결과를 보장하기 위해서도 필요합니다. LSM-Tree에서 delete는 tombstone이라 불리는 placeholder를 insert 하는 것이고 insert는 더 큰 timestamp의 record힙니다. read 동안 record는 delete에 의해 shadow 되어 return 되지 않거나 더 큰 timestamp로 update 된 record를 return 합니다. 아래는 merge step이 서로 다른 SSTable의 데이터를 통합(reconcile)하는 과정을 보여줍니다. 

![img](https://1.bp.blogspot.com/-9smBt85IgaM/X3E3FnlSnCI/AAAAAAAADo8/8h49TprKMgcd8tUFN0LWvw5r6nVodfShgCLcBGAsYHQ/w640-h262/lsm-tree-03.png)



### Bloom Filter

[![img](https://1.bp.blogspot.com/-bDvX0S_d3Go/X3E3PEb-BRI/AAAAAAAADpA/fY2bgZN3R0IW3A_B_42QYp2y-hpvsXBOACLcBGAsYHQ/w640-h104/lsm-tree-04.png)](https://1.bp.blogspot.com/-bDvX0S_d3Go/X3E3PEb-BRI/AAAAAAAADpA/fY2bgZN3R0IW3A_B_42QYp2y-hpvsXBOACLcBGAsYHQ/s1252/lsm-tree-04.png)



read 시에 검색 대상이 되는 SSTable의 개수를 줄이고 모든 SSTable에 대해서 주어진 key를 가지고 있는지 확인하는 것을 피하기 위해 여러 storage system은 Bloom filter라는 자료구조를 사용합니다. Bloom filter는 주어진 element가 set에 속하는지 아닌지 판단하기 위해 사용하는 확률적 자료구조이며 다음의 명제 두가지를 제공합니다.

- might be in an SSTable (probabily produce false positive)
- is definitely not in an SSTable (definitely not produce false negative)

따라서 LSM-Tree에서는 이 Bloom filter가 제공하는 정보를 기반으로 search 하지 않아도 되는 SSTable은 건너뛸 수 있습니다. Bloom filter의 세부 동작은 어떤 hash function을 몇개 사용하는지, filter는 몇 bit 인지, 총 몇개의 element가 insert 되는지에 따라 결정됩니다. 더 큰 filter를 사용할수록 false positive, 즉 might be in an SSTable 케이스의 확률은 줄어들지만 space complexity가 증가하는 trade-off가 있습니다. Bloom filter에 대해서 직관적으로 이해하기 위해서 아래 링크에서 직접 시도해보기를 추천합니다. 

https://llimllib.github.io/bloomfilter-tutorial/



### LSM-Tree Maintenance

[![img](https://1.bp.blogspot.com/-XnwOTWcyxnU/X3E3h_UK2bI/AAAAAAAADpM/qZ_HrH8IYUQUqLCnjLJblyjltcYbXpkUwCLcBGAsYHQ/w640-h322/LSM_Tree.png)](https://1.bp.blogspot.com/-XnwOTWcyxnU/X3E3h_UK2bI/AAAAAAAADpM/qZ_HrH8IYUQUqLCnjLJblyjltcYbXpkUwCLcBGAsYHQ/s1395/LSM_Tree.png)



각 SSTable은 key를 기준으로 sort 되어있기 때문에 이 과정은 merge sort 처럼 동작하여 매우 효율적입니다. 

- 여러 SSTable로부터 sequential 하게 read 됩니다
- 병합 결과 SSTable 또한 sequential 하게 write 됩니다
- merge sort는 memory에 모두 적재할 수 없는 큰 파일에서도 잘 동작합니다
- stable sort 이므로 기존 record의 순서를 보존합니다

compaction이 완료되면 기존의 SSTable은 버리고 새로운 SSTable로 대체합니다. 일부 데이터베이스 시스템에서는 같은 크기의 table들을 같은 level 로 group 지어서 각 level 별로 충분한 table이 생성되면 그 상위 level의 table로 compaction이 이루어지도록 합니다. 



## Atomicity and Durability

B-Tree와 LSM-Tree에서 모두 I/O operation의 수를 줄이고 sequential하게 이루어지도록 하기 위해 실제 update를 하기 전 memory에 operation을 batch로 처리합니다. 이는 시스템에 장애가 발생했을 때 data integrity가 보장되지 않을 수 있으며 atomicity, durability 를 확신할 수 없다는 것을 암시합니다.

이 문제를 해결하기 위해서 대부분의 현대 데이터베이스 시스템에서는 WAL (write-ahead log)를 사용합니다. WAL의 핵심 아이디어는 모든 상태 변화를 disk 상의 append-only log로 남기는 것입니다. 이는 장애 상황에서도 WAL을 replay하여 이전의 상태를 재현 가능하다는 것을 의미합니다. 

B-Tree에서 WAL은 반드시 로그를 남긴 뒤에만 데이터 파일에 변경 사항을 적용하는 것으로 사용합니다. 비교적 작은 크기의 WAL을 남기며 data page에 적용되지 않은 변경 사항을 WAL을 통해 재현 가능합니다. LSM-Tree에서는 WAL이 memtable에는 적용되었으나 disk에 완전히 flush 되지 않은 변경사항을 저장하기 위해 사용됩니다. memtable이 flush 되어 새로운 read가 새로 생성된 SSTable에서 이루어지는 시점부터 해당 segment는 제거됩니다. 



## Summary

B-Tree와 LSM-Tree의 가장 큰 차이는 read/write 중 어떤 것에 최적화되었고 이 최적화에 의한 암시가 무엇인지다. 이 둘의 성질을 비교하면 아래와 같습니다.

B-Tree.

- mutable 
- read-optimized
- write는 연쇄적인 (cascaded) node split을 발생시킬 수 있으며 이는 write operation을 더 무겁게 합니다
- byte adressing이 불가능한 page environment (block storage)에 최적화 되어있습니다
- 빈번한 update에 의한 fragmentation이 발생할 수 있으며 추가적인 maintenance와 block rewrite를 요구합니다. 하지만 LSM-Tree의 maintenance 보다 가볍습니다

- concurrent access는 reader/writer isolation을 요구하며 lock, latch의 chain을 포함합니다

LSM-Tree. 

- immutable. disk에 한번 write 되면 절대 update 되지 않습니다. immutable에서 오는 장점 중 하나는 flush 된 table에 대해서 concurrent access가 가능하다는 점입니다
- write-optimized
- read는 여러 source (SSTable)을 거쳐야 하며 merge process를 거칠 수 있습니다
- buffered write가 disk에 flush 되어야 하므로 maintenance/compaction이 요구됩니다



## References

- Alex Petrov, 2018. Algorithms Behind Modern Storage Systems: Different uses for read-optimized B-trees and write-optimized LSM-trees. Queue; (https://dl.acm.org/doi/10.1145/3212477.3220266)
- [Stack Overflow Developer Survey, 2020](https://insights.stackoverflow.com/survey/2020#technology-databases-all-respondents4)

- B-Tree
  - https://en.wikipedia.org/wiki/B-tree
  - https://www.cs.princeton.edu/courses/archive/fall06/cos226/lectures/balanced.pdf
  - https://docs.microsoft.com/en-us/sql/relational-databases/indexes/clustered-and-nonclustered-indexes-described?view=sql-server-ver15
  - https://www.tutorialspoint.com/difference-between-clustered-index-and-non-clustered-index-in-sql-server

- LSM-Tree 
  - https://en.wikipedia.org/wiki/Log-structured_merge-tree
  - https://yetanotherdevblog.com/lsm/
  - https://medium.com/swlh/log-structured-merge-trees-9c8e2bea89e8

- Bloom filter
  - https://en.wikipedia.org/wiki/Bloom_filter
  - https://llimllib.github.io/bloomfilter-tutorial/
  - https://yetanotherdevblog.com/bloom-filters/