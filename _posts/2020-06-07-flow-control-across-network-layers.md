---
layout: post
title: Flow Control across Network Layers
subheading: 
author: taehyeok-jang
categories: [network]
tags: [network, reactive]
---



## Introduction 

reactive stream 구현을 사용하여 네트워크 애플리케이션을 개발한다고 가정해보겠습니다. 그리고 우리는 HTTP/2를 사용합니다. 

reactive stream은 back-pressure이라고 하는 스트림 처리를 위한 흐름 제어를 제공합니다. reactive stream의 subscriber는 연결된 publisher에게 가용성을 요구하여 스트리밍된 데이터의 크기를 제어합니다. 그러나 네트워크 계층 내 application layer의 HTTP/2와 transport layer인 TCP에도 각각 흐름 제어 메커니즘이 존재합니다. 

따라서 스트리밍 데이터를 end system으로 보내려고 할 때 세 단계의 흐름 제어가 작동하게 됩니다. 이번 글에서는 세 단계의 흐름 제어를 가장 낮은 단계에서부터 순차적으로 살펴보겠습니다.



## TCP Layer 

TCP가 흐름 제어를 제공한다는 것은 잘 알려져 있습니다. 클라이언트에서는 한 번에 수신할 수 있는 TCP segment 수를 제어할 수 있는 방법을 제공합니다. 클라이언트는 연결된 end system에 대한 TCP 헤더에서 사용 가능한 창(크기)을 확인합니다.

![tcp_congestion_control](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/a92b360a-2a28-4636-9213-c84b077e37bf)

TCP 연결을 위한 3-way handshake 동안, 양쪽은 시스템 default 설정으로 자신의 rwnd 크기 (received window size)를 초기화합니다. 만약 한 쪽이 부하를 감당할 수 없는 경우, 더 window size를 알릴 수 있습니다. window size가 0이면, receiver 측에서 어플리케이션 buffer를 비울 때까지 더 이상 데이터를 보낼 수 없음을 의미합니다. 이 작업 흐름은 모든 TCP connection의 지속되는 동안 계속되며, 각 ACK는 각 측의 최신 rwnd 값을 전달하여, 양쪽이 모두 데이터 흐름 속도를 sender와 receiver의 용량 및 처리 속도에 동적으로 조절할 수 있게 합니다.

sender는 rwnd보다 작은 양의 데이터를 전송합니다.

```
var = (LastByteSent - LastByteAcked) < rwnd 
```

receiver는 지속적으로 TCP 헤더 내 window size를 가리키는 rwnd를 포함하여 receiver에서 가능한 buffer size를 알립니다. 

```
rwnd = RcvBuffer - (LastByteRcvd - LastByteRead)
```



## HTTP/2

![fig7_1_alt](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/d997c815-2f95-48c0-856f-688e927718cc)


HTTP/2는 application layer의 효율성을 극대화하기 위해 설계된 프로토콜입니다. 이전 버전인 HTTP/1.1과 달리, HTTP/2는 하나의 TCP connection을 통해 여러 개의 스트림을 동시에 다룰 수 있는 'multiplexing' 기능을 제공합니다. 즉, 여러 요청과 응답을 동시에 교환할 수 있어, 네트워크 지연을 줄이고 성능을 향상시킬 수 있습니다.

flow control은 이러한 환경에서 데이터 전송을 조절하는 중요한 메커니즘입니다. HTTP/2 stream의 각 수신자는 자신의 처리 속도에 맞추어 받을 수 있는 데이터의 양을 조절할 수 있습니다. 

HTTP/2의 flow control은'credit-based 시스템을 사용합니다. 이는 수신자가 초기에 어느 정도의 데이터를 받을 수 있는지 정하는 credit을 발행하고, 데이터를 받을 때마다 해당 credit이 감소하며, 필요에 따라 WINDOW_UPDATE 프레임을 통해 credit을 다시 증가시키는 방식으로 작동합니다. 이를 통해 데이터 송수신의 속도를 동적으로 조절할 수 있습니다.

또한, HTTP/2의 flow control은 hop-by-hop 기반이라는 점에서 end-to-end 방식과 구별됩니다. 즉, 각 네트워크 노드(중간 서버)는 독립적으로 flow control을 적용하여, 자신의 리소스 상황과 정책에 따라 데이터 전송을 조절할 수 있습니다. 이는 전체 네트워크의 성능과 안정성을 높이는 데 기여합니다.



<img src="https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/43174293-f4ff-49a6-b0da-e7f6eb097e10" alt="http2_flow_control_01" style="zoom:67%;" />





## Reactive Stream

![bp buffer2 v3](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/95bca026-205c-44bf-a79d-2502c1a86386)

Reactive Stream의 Back-pressure는 subscriber가 publisher로부터 받는 데이터의 수용을 제어하는 메커니즘입니다. subscriber와 publisher가 네트워크상에서 분리되어 있다면, 그들의 처리량은 서로 달라야 합니다. 만약 subscriber가 publisher보다 낮은 속도로 수락된 데이터를 처리한다면, subscriber 측에 남은 데이터는 계속 쌓이게 됩니다. 이는 저장소 overflow를 초래하고 이는 치명적인 하드웨어 실패로 이어질 수도 있습니다. subscriber는 콜백에서 다음에 발행될 데이터의 크기를 요청함으로써 자신의 acceptance rate을 제어합니다.

Reacitve Stream의 여러 구현체는 다양한 종류의 back-pressure 전략을 지원합니다. 다양한 네트워크 상황에 절대적인 전략은 없으며, 어떻게 동작하기를 원하는지에 따라 애플리케이션은 back-pressure 상황을 처리할 수 있습니다. 



## References

- Overall
  - [https://www.pearson.com/us/higher-education/product/Kurose-Computer-Networking-A-Top-Down-Approach-7th-Edition/9780133594140.html#resources](https://www.pearson.com/us/higher-education/product/Kurose-Computer-Networking-A-Top-Down-Approach-7th-Edition/9780133594140.html#resources)
- TCP Layer
  - [TCP: Flow Control and Window Size](https://www.youtube.com/watch?app=desktop&v=4l2_BCr-bhw)
- HTTP/2
  - https://livebook.manning.com/book/http2-in-action/chapter-7/61
  - [https://web.dev/articles/performance-http2](https://web.dev/articles/performance-http2)
  - [https://datatracker.ietf.org/doc/html/rfc7540](https://datatracker.ietf.org/doc/html/rfc7540)
  - [https://medium.com/coderscorner/http-2-flow-control-77e54f7fd518](https://medium.com/coderscorner/http-2-flow-control-77e54f7fd518)
  - [https://www.slideshare.net/Enbac29/http2-standard-for-video-streaming](https://www.slideshare.net/Enbac29/http2-standard-for-video-streaming)
  - [https://developers.google.com/web/fundamentals/performance/http2](https://developers.google.com/web/fundamentals/performance/http2)
  - [https://http2.github.io/http2-spec/](https://http2.github.io/http2-spec/)
- Reactive Stream
  - [https://github.com/ReactiveX/RxJava/wiki/Backpressure](https://github.com/ReactiveX/RxJava/wiki/Backpressure)
  - [http://reactivex.io/RxJava/2.x/javadoc/io/reactivex/BackpressureStrategy.html](http://reactivex.io/RxJava/2.x/javadoc/io/reactivex/BackpressureStrategy.html)