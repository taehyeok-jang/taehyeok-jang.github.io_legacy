---
layout: post
title: MapReduce - Performance Tunings
subheading: 
author: taehyeok-jang
categories: [distributed-systems]
tags: [paper-review, distributed-systems, map-reduce]
---



## Introduction 

[(Paper Review) MapReduce - Simplified Data Processing on Large Clusters](https://taehyeok-jang.github.io/distributed-systems/2020/08/09/paper-review-map-reduce.html)

이전에 업로드한 위 글을 통해서 Google의 MapReduce에 대해서 알아보았습니다. Google에서는 MapReduce를 오픈소스로 공개하지 않았기 때문에 대용량 data processing이 필요한 회사들은 Hadoop ecosystem에 있는 MapReduce framework를 사용했습니다. 

이번 글에서는 MapReduce 작업을 수행할 때 성능 및 정합성 측면에서 고려하는 요소를 살펴보고자 합니다.



## Speculative Execution 

```
/**
 * Turn speculative execution on or off for this job. 
 * 
 * @param speculativeExecution <code>true</code> if speculative execution 
 *                             should be turned on, else <code>false</code>.
 */
public void setSpeculativeExecution(boolean speculativeExecution) {
  ensureState(JobState.DEFINE);
  conf.setSpeculativeExecution(speculativeExecution);
}
```

MapReduce job class의 설정으로 speculative execution 옵션이 있습니다. 이 옵션은 MapReduce 수행 도중 특정 worker node에서 task 수행이 지연되고 있으면 해당 task와 동일한 backup task를 실행시키는 것을 허용합니다. 

Google MapReduce 논문의 목차 3.6에서 해당 내용을 기술하고 있습니다. 



> ### 3.6 Backup Tasks
>
> MapReduce의 수행시간을 길게하는 원인 중 하나로 **straggler가 있다.** straggler는 소수의 map task 혹은 reduce task를 수행하는 데 비정상적으로 긴 시간을 소요하는 machine을 의미한다. straggler는 여러 이유에서 발생한다. bad disk, scheduling으로 인한 CPU, memory, disk, network bandwidth 등 자원의 경합이 될 수 있다. 최근에 발견한 bug로는 processor cache를 disable 시키는 initialization code도 있었다.
>
> 이러한 straggler로 인한 문제를 완화하기 위해서 **general mechanism**을 도입하였다. MapReduce operation이 수행 완료에 가까워지면 master는 남아있는 in-progress task에 대한 backup execution을 schedule 한다. 그러면 그 task는 primary 혹은 backup execution에서 완료하게 된다. 논문에서는 이 mechanism을 tune 하여 수 percent의 추가 자원을 사용하면서 수행 완료시간을 상당히 줄이는 결과를 얻었다.



논문에서는 speculative execution을 활성화시킴으로써 부분 실패에 대한 작업 지연을 미리 예방하여 성능 향상에 기여한다고 이야기하고 있습니다. 

하지만, 언제나 speculative execution을 활성화시키는 것만이 능사는 아닙니다. 이는 MapReduce 작업의 실행 환경과 대상이 되는 application의 특성에 따라 달라질 수 있습니다. 

Enterprise Hadoop cluster 환경에서는 다수의 MapReduce 작업이 한 cluster 내에서 실행됩니다. 각 MapReduce 작업 별 적당한 throughput과 예상 수행완료 시점을 정하기 위해서는 적정 수준 parallelism이 필요하며 map task, reduce task의 개수를 통해 parallelism을 정한다. 하지만 backup task가 실행되면 추가적인 병렬처리가 발생하게 되며 이에 따라 더 많은 resource, network를 사용하게 된다. 조금 더 예측 가능한 리소스 관리가 요구되는 환경이라면 speculative execution을 off 해야합니다. 

또한 application의 특성에 따라 달라질 수 있습니다. MapReduce 작업을 통해 application에 read/write를 수행하기도 하는데 만약 application에서 write에 대해 exactly-once semantic을 요구한다면 speculative execution을 반드시 off 해야합니다. 만약 처리 지연 혹은 부분 실패에 따른 backup task가 생성되었는데 일정 기간 이후 원래 task가 처리되고 backup task 또한 처리된다면 중복 쓰기가 발생하기 때문입니다.



## Table Scan 

MapReduce 를 활용한 작업 중에서는 저장소에 있는 데이터를 읽어서 연산을 하는 경우도 있을 것입니다. 이때 대량의 데이터를 scan하는 경우 저장소가 감당하지 못할 부하가 발생할 수도 있기 때문에 이와 관련된 제어는 반드시 필요합니다. 이번 글에서는 Hadoop HBase를 예로 들겠지만 scan caching 및 batch와 관련된 제어는 다른 데이터베이스에도 동일한 원리를 가지고 최적화 할 수 있을 것이라 기대합니다.



### Block Cache

[https://hbase.apache.org/1.1/apidocs/org/apache/hadoop/hbase/client/Scan.html](https://hbase.apache.org/1.1/apidocs/org/apache/hadoop/hbase/client/Scan.html)

```
- getCacheBlocks
public boolean getCacheBlocks()

Get whether blocks should be cached for this Scan.

- setCacheBlocks
public Scan setCacheBlocks(boolean cacheBlocks)

Set whether blocks should be cached for this Scan.
This is true by default. When true, default settings of the table and family are used (this will never override caching blocks if the block cache is disabled for that family or entirely).
```

HBase의 scan 설정 중에는 각 region server 별로 cache block을 제어하는 옵션이 있습니다. 기본적으로는 true로 되어있어 어플리케이션 수행 중 빈번하게 read/write 되는 데이터에 효율적으로 접근할 수 있도록 합니다. 

하지만 MapReduce 작업을 위해서는 해당 설정을 비활성화하는 것이 더 효율적일 수 있습니다. MapReduce 작업에서 full scan을 수행하여 저장소 내 전체 데이터 읽는 상황인데, cache block이 적용되어 있으면 page fault가 과도하게 발생하여 오히려 성능 저하를 초래할 수 있습니다. 



### Caching vs Batch 

HBase scan의 경우 한 row 당 한번에 RPC call이 발생합니다. 이러한 방식은 크기가 작은 cell을 처리할 때 비효율적인데 클러스터 내에서 빈번한 network transfer은 네트워크 부하로 이어지기 때문입니다. 따라서 한번의 RPC call을 통해 여러 row를 반환하는 것이 더 효율적일 수 있다. 

HBase에서는 한번의 RPC을 통해 반환할 row, column 개수를 제어할 수 있습니다. 

[https://hbase.apache.org/1.1/apidocs/org/apache/hadoop/hbase/client/Scan.html](https://hbase.apache.org/1.1/apidocs/org/apache/hadoop/hbase/client/Scan.html)

``` 
- setCaching
public Scan setCaching(int caching)

Set the number of rows for caching that will be passed to scanners. If not set, the Configuration setting HConstants.HBASE_CLIENT_SCANNER_CACHING will apply. Higher caching values will enable faster scanners but will use more memory.

- setBatch
public Scan setBatch(int batch)

Set the maximum number of values to return for each call to next(). Callers should be aware that invoking this method with any value is equivalent to calling setAllowPartialResults(boolean) with a value of true; partial results may be returned if this method is called. Use setMaxResultSize(long)} to limit the size of a Scan's Results instead.
```



높은 cache ratio는 신속한 scan을 제공하지만 메모리를 더 사용하므로 주의해야 합니다. 대량의 rows를 scan 해야하는 상황이라면 최악의 경우 클라이언트 프로세스의 maximum heap 크기 초과로 인해 OutOfMemoryException 가 발생할 수도 있습니다.

HBase에서는 이에 대한 답으로서 batching을 도입하였습니다. Batching은 스캔 작업에서 한 번에 가져올 column의 수를 지정하는 데 사용됩니다. 각 row는 여러 column으로 구성되어 있으므로 이 설정은 각 Result instance에 포함될 column 수를 제어합니다. 더 많은 column을 한 번에 가져오면 scan 작업의 효율성이 향상될 수 있습니다.

scanner의 caching과 batching size의 조합은 scan 명령어로 발생할 RPC call의 수를 결정합니다. [HBase: The Definitive Guide](https://www.oreilly.com/library/view/hbase-the-definitive/9781449314682/) 의 3장에 예시를 인용합니다. 주어진 테이블은 각각 10개의 column을 가진 2개의 column family, 총 10개의 row로 이루어져 있습니다. 즉 row 당 20개의 column, 그리고 총 200개의 cell로 이루어진 테이블입니다. 

```java
// Example 3-20. Using caching and batch parameters for scans
private static void scan(int caching, int batch) throws IOException {
    Logger log = Logger.getLogger("org.apache.hadoop");
    final int[] counters = {0, 0};
    Appender appender = new AppenderSkeleton() {
        @Override
        protected void append(LoggingEvent event) {
            String msg = event.getMessage().toString();
            if (msg != null && msg.contains("Call: next")) {
                counters[0]++;
            }
        }

        @Override
        public void close() {
        }

        @Override
        public boolean requiresLayout() {
            return false;
        }
    };
    log.removeAllAppenders();
    log.setAdditivity(false);
    log.addAppender(appender);
    log.setLevel(Level.DEBUG);
    Scan scan = new Scan();
    scan.setCaching(caching);
    scan.setBatch(batch);
    ResultScanner scanner = table.getScanner(scan);
    for (Result result : scanner) {
        counters[1]++;
    }
    scanner.close();
    System.out.println("Caching: " + caching + ", Batch: " + batch +
            ", Results: " + counters[1] + ", RPCs: " + counters[0]);
}
```



아래의 표는 caching과 batching size의 조합에 따른 RPC call의 횟수입니다. caching/batch 각각 1로 설정했을 때 cell의 개수만큼 RPC call이 발생하였고, 5/100, 5/20, 10/10 조합일 때 최적의 성능을 보이고 있습니다. 따라서 MapReduce application에서는 테이블 스키마, data의 저장 패턴 등을 고려하여 caching과 batching size의 조합을 잘 찾는다면 최적의 성능을 얻을 수 있을 것입니다.



![scan-batch](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/749fcd79-ed81-44ef-800c-4c7b2c037f3a)





## References

- Apache HBase 
  - [https://hbase.apache.org/1.1/apidocs/org/apache/hadoop/hbase/client/Scan.html](https://hbase.apache.org/1.1/apidocs/org/apache/hadoop/hbase/client/Scan.html)
  - [HBase: The Definitive Guide](https://www.oreilly.com/library/view/hbase-the-definitive/9781449314682/)
