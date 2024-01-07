---
layout: post
title: API Design in Distributed Systems 
subheading: 
author: taehyeok-jang
categories: [distributed-systems]
tags: [api, distributed-systems]
---



이 글은 Stripe Engineering Blog의 [Designing robust and predictable APIs with idempotency](https://stripe.com/blog/idempotency) article과 관련 자료를 읽고 정리한 글입니다.



## Introduction 

> Networks are unreliable. We’ve all experienced trouble connecting to Wi-Fi, or had a phone call drop on us abruptly.
>
> The networks connecting our servers are, on average, more reliable than consumer-level last miles like cellular or home ISPs, but given enough information moving across the wire, they’re still going to fail in exotic ways. Outages, routing problems, and other intermittent failures may be statistically unusual on the whole, but still bound to be happening all the time at some ambient background rate.
>
> To overcome this sort of inherently unreliable environment, it’s important to design APIs and clients that will be robust in the event of failure, and will predictably bring a complex integration to a consistent state despite them. Let’s take a look at a few ways to do that.

network는 unreliable 합니다. celluar network나 home ISP보다는 신뢰할 수 있지만, network 문제는 전체적으로 보면 통계적으로 unusual 하다고 하더라도 여전히 유효한 비율로 발생할 것입니다.

inherently unreliable environment, 즉 본질적으로 unreliable한 환경에서 API와 client들을 설계하는 것은 매우 중요합니다. 이를 위해 특정한 사건의 실패에 robust하고, 실패에도 불구하고 일관성 있는 데이터를 위한 통합 작업을 예측적으로 수행해야 합니다.



## Planning for failure

> Consider a call between any two nodes. There are a variety of failures that can occur:
>
> \- The initial connection could fail as the client tries to connect to a server.
>
> \- The call could fail midway while the server is fulfilling the operation, leaving the work in limbo.
>
> \- The call could succeed, but the connection break before the server can tell its client about it.

network application, 즉 네트워크를 기반으로 하는 인터넷 상의 모든 서비스들은 네트워크 실패에 대비해야 합니다. 기본적으로 network 상의 두 node가 있다고 가정했을 때 위와 같은 실패 가능성이 있습니다. 이와 같이 네트워크는 본질적으로 실패하며 어플리케이션은 이 실패에 대응할 방법을 계획해야 합니다. 

- 서버에 도착하기 전 연결 실패
- 서버 처리 도중 실패 (client abort, timeout 등)
- 서버에서 응답을 내려주는 도중 연결 중단 (infrastructure aborted)



## Guaranteeing “exactly once” semantics

> While the inherently idempotent HTTP semantics around PUT and DELETE are a good fit for many API calls, what if we have an operation that needs to be invoked exactly once and no more? An example might be if we were designing an API endpoint to charge a customer money; accidentally calling it twice would lead to the customer being double-charged, which is very bad.
>
> This is where *idempotency keys* come into play. When performing a request, a client generates a unique ID to identify just that operation and sends it up to the server along with the normal payload. The server receives the ID and correlates it with the state of the request on its end. If the client notices a failure, it retries the request with the same ID, and from there it’s up to the server to figure out what to do with it.

네트워크 실패에 대처하기 위해서 idempotent semantic은 유용합니다. 왜냐하면 클라이언트가 실패를 인지한 상황에서 재시도 요청을 했을 때 여러번 호출하더라도 동일한 결과를 보장하기 때문입니다. 반대로 'increment by 1'과 같은 요청을 보낸다면 네트워크 실패 시에 +1이 될지 혹은 +2, +3가 될지 예측하기 어렵습니다. 

HTTP의 PUT, DELETE method는 이미 idempotent semantic을 내포하고 있지만, POST와 같은 method에서 특정 operation이 정확하게 한번만 일어나야 한다는 것이 필요하다면 어떻게 해야할까요?

여기서 idempontency key를 도입합니다. client에서 unique 한 indempotent key를 생성하여 요청 시 함께 전송하고 서버에서는 이를 고려하여 요청을 처리합니다. 그러면 위 네트워크 실패 시나리오에서 다음과 같이 대처할 수 있습니다.

- 서버에 도착하기 전 연결 실패

클라이언트 재시도 시에 서버는 해당 ID가 포함된 요청이 처음이므로 정상적으로 처리합니다. 

- 서버 처리 도중 실패 

정확한 구현은 어플리케이션에 따라 달라질 수 있지만 ACID 데이터베이스로 처리 도중 실패했다면 성공적으로 rollback이 되었을 것입니다. 따라서 동일한 ID를 가진 요청은 성공적으로 처리 될 것입니다. 

- 서버에서 응답을 내려주는 도중 연결 중단

서버는 해당 요청을 중복 요청으로 인식하고 캐시된 응답을 내려줍니다.



## Being a good distributed citizen

> Safely handling failure is hugely important, but beyond that, it’s also recommended that it be handled in a considerate way. When a client sees that a network operation has failed, there’s a good chance that it’s due to an intermittent failure that will be gone by the next retry. However, there’s also a chance that it’s a more serious problem that’s going to be more tenacious; for example, if the server is in the middle of an incident that’s causing hard downtime. Not only will retries of the operation not go through, but they may contribute to further degradation.
>

네트워크 실패는 잠깐의 문제일 수도 있지만 지속적인 모니터링이 필요한 심각한 장애일 수도 있습니다. 따라서 무작정 재시도를 했다가는 분산 시스템의 네트워크 부하에 영향을 미칠 수도 있습니다.

따라서 재시도를 효율적으로 하기 위해서, TCP/IP congestion control에서의 방법과 마찬가지로 재시도의 주기를 늘려나가는 exponential backoff와 같은 전략을 사용할 수 있습니다. 

또한 서버의 장애가 많은 수의 클라이언트에게 장애를 유발했을 때 thundering herd problem을 유발할 수 있다. 이 문제는 event 발생을 기다리고 있는 process or thread가 있으나 하나의 서버에서만 event handle이 가능할 때를 의미합니다. 리소스에 대해 경합할 것이고 순간적으로 해당 서버에 과부하가 걸리게 합니다. 

이 문제를 해결하기 위해서 jitter 라는 randomness 개념을 도입할 수 있습니다. 재시도를 하려는 클라이언트들이 timeframe 내에서 임의의 시간에 호출하도록 하여 부하를 분산시키는 방법 있습니다. 



## Summary

이 글의 요약입니다.

1. 실패가 consistent하게 처리될 수 있도록 하기. 클라이언트에서 재시도를 하여 데이터를 inconsistent state에서 벗어나게 하기.
2. idempontent한 서버의 설계를 통해 실패 처리가 안전하게 처리될 수 있도록.
3. 실패 처리가 전체 시스템에 responsible한 방법으로 처리될 수 있도록 하기. (exponential backoff and random jitter)



## References

- Stripe Engineering Blog 
  - [https://stripe.com/blog/idempotency](https://stripe.com/blog/idempotency)
  - [http://www.cs.utexas.edu/users/lam/NRL/backoff.html](http://www.cs.utexas.edu/users/lam/NRL/backoff.html)
- Designing Data-Intensive Applications
  - [https://dataintensive.net/](https://dataintensive.net/)
- AWS 
  - [https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/](https://aws.amazon.com/builders-library/making-retries-safe-with-idempotent-APIs/)
  - [https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)