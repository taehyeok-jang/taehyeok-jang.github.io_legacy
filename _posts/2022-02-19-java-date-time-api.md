---
layout: post
title: Java Date Time API 
subheading: 
author: taehyeok-jang
categories: [java]
tags: [java, date, time, timezone]
---

## Introduction 

Java에서 날짜 및 시간과 관련된 작업을 하다보면 Date, Calendar, Instant, ZonedDateTime 등 비슷한 목적의 여러 클래스들이 있어서 헷갈렸던 적이 있을 것입니다. 이는 Java 1.0에서 Date 클래스가 처음 도입된 이후로 여러가지 문제점들이 발견되어 이를 개선하기 위한 클래스들이 새로 생겨났기 때문인데요. Joda Time과 같은 오픈소스 라이브러리가 개발되기도 했지만 Java 8의 java.time 패키지가 도입되면서 Java 기본 패키지에서도 충분한 기능을 제공할 수 있게 되었습니다. 

이번 글에서는 Java의 역사에서 관련 클래스들이 어떻게 발전했는지를 살펴보고, 그리고 나아가 어플리케이션에서 날짜 및 시간의 일관성을 지키기 위한 규칙에 대해서도 간단히 알아보겠습니다.



## A Brief History 

### java.util.Date (Java 1.0)

[https://docs.oracle.com/javase/8/docs/api/java/util/Date.html](https://docs.oracle.com/javase/8/docs/api/java/util/Date.html)

가장 먼저 출시된 클래스는 Java 1.0의 java.util.Date 클래스입니다. 공식 문서의 정의대로 이 클래스는 단순 날짜가 아니라 특정한 시간을 millisecond 단위로 나타냅니다. Date 클래스는 기본적인 사용 방법과 유효성 측면에서 여러 문제가 있었습니다. 

첫번째로, 연도는 1900년부터 시작되었고 월은 0부터 시작하여 직관적인 사용이 어려웠습니다. 예를 들어 2020년 06월 10일을 나타내기 위해서는 아래와 같이 Date 인스턴스를 생성해야 합니다. 

```java
Date date = new Date(120, 5, 10);
```



두번째로, 입력된 날짜에 대한 유효성 검증이 제대로 지원되지 않았습니다. 아래의 예시처럼 생성자에 2020년 05월 31일을 입력하면 아무런 예외나 경고 메시지 없이 2020년 06월 01일로 Date 인스턴스가 생성됩니다. 

```java
Date date1 = new Date(120, 5, 31);
Date date2 = new Date(120, 6, 1);

assertEquals(date1, date2);
```



### java.util.Calendar (Java 1.1)

Java 1.1에서 java.util.Calendar 클래스가 도입되면서 Date 클래스와 관련된 몇가지 문제점들이 개선되었지만 여전히 여러 문제점들이 있었습니다.

월이 여전히 0부터 시작합니다. Caldenar 클래스에서 `Calendar.JULY` 와 같은 상수들을 지원했지만 정수를 그대로 사용할 수 있는 이상 잘못 사용될 가능성은 여전히 존재합니다. 

두번째로, Date와 마찬가지로 Calendar 클래스 또한 mutable이어서 set method로 값을 변경할 수 있습니다. 이 클래스들의 인스턴스가 여러 객체에서 공유되거나 여러 스레드에서 동시접근한다면 예상하지 못한 문제가 발생할 수 있습니다.

Time zone을 관리하기가 어렵습니다. TimeZone 인스턴스 생성 시 `Asia/Seoul` 이 아니라 실수로 `Seoul/Asia` 를 입력하면 아무런 예외가 발생하지 않으면서 Time zone은 `GMT` 로 생성됩니다. 이는 잠재적인 오류의 가능성을 가지고 있습니다.

```java
TimeZone zone = TimeZone.getTimeZone("Seoul/Asia");
Calendar calendar = Calendar.getInstance(zone); 

assertEquals(calendar.getTimeZone(), "GMT");
```



### java.time (Java 8, JSR 310)

Java 8에서 JSR 310 표준을 통합하여 java.time 패키지를 도입했습니다. 이 패키지는 기존 클래스들의 문제들을 해결하고 날짜와 시간을 관리하기 위한 기능을 제공합니다.

1. 충분히 효율적인 API를 제공합니다. 
2. Date, Time, Instant, TimeZone을 위한 표준을 지원합니다.
3. 객체 간 공유 및 스레드 안정성을 위해 immutable로 구현하였습니다.

[https://docs.oracle.com/javase/8/docs/api/java/time/package-summary.html](https://docs.oracle.com/javase/8/docs/api/java/time/package-summary.html)

아래는 java.time 패키지 내 일부 클래스들입니다. 타임라인 상에서 특정 순간을 나타내기 위한 Instant 클래스, time zone 없이 날짜, 시간을 표기하기 위한 LocalDate, LocalTime, LocalDateTime 클래스가 있습니다. 그리고 time zone을 offset이나 id로 (ZoneOffset, ZoneId) 나타낼 수 있으며 OffsetDateTime, ZonedDateTime 클래스를 통해서 특정 지역에서 날짜와 시간과 관련된 완전한 정보를 표현할 수 있습니다. 모든 클래스는 날짜와 시간과 관련된 국제 표준인 [ISO-8601](https://en.wikipedia.org/wiki/ISO_8601)을 따르고 있습니다.

| Class                                                        | Description                                                  |
| :----------------------------------------------------------- | :----------------------------------------------------------- |
| [Instant](https://docs.oracle.com/javase/8/docs/api/java/time/Instant.html) | An instantaneous point on the time-line.                     |
| [LocalDate](https://docs.oracle.com/javase/8/docs/api/java/time/LocalDate.html) | A date without a time-zone in the ISO-8601 calendar system, such as `2007-12-03`. |
| [LocalDateTime](https://docs.oracle.com/javase/8/docs/api/java/time/LocalDateTime.html) | A date-time without a time-zone in the ISO-8601 calendar system, such as `2007-12-03T10:15:30`. |
| [LocalTime](https://docs.oracle.com/javase/8/docs/api/java/time/LocalTime.html) | A time without a time-zone in the ISO-8601 calendar system, such as `10:15:30`. |
| [OffsetDateTime](https://docs.oracle.com/javase/8/docs/api/java/time/OffsetDateTime.html) | A date-time with an offset from UTC/Greenwich in the ISO-8601 calendar system, such as `2007-12-03T10:15:30+01:00`. |
| [OffsetTime](https://docs.oracle.com/javase/8/docs/api/java/time/OffsetTime.html) | A time with an offset from UTC/Greenwich in the ISO-8601 calendar system, such as `10:15:30+01:00`. |
| [ZonedDateTime](https://docs.oracle.com/javase/8/docs/api/java/time/ZonedDateTime.html) | A date-time with a time-zone in the ISO-8601 calendar system, such as `2007-12-03T10:15:30+01:00 Europe/Paris`. |
| [ZoneId](https://docs.oracle.com/javase/8/docs/api/java/time/ZoneId.html) | A time-zone ID, such as `Europe/Paris`.                      |
| [ZoneOffset](https://docs.oracle.com/javase/8/docs/api/java/time/ZoneOffset.html) | A time-zone offset from Greenwich/UTC, such as `+02:00`.     |



## Date, Time APIs

Java에서 날짜, 시간과 관련하여 여러 유용한 API들을 소개합니다. 레거시를 포함하는 시스템에서는 관련된 여러 클래스들이 섞여서 사용되고 있을텐데요. 하위 호환을 반드시 지원해야 하는 경우가 아니라면 java.time 패키지에 있는 클래스들로 변환하여 날짜와 시간을 명확하게 표현하는 것을 권장합니다. 



### Current Date, Time 

- Date

```java
new Date();
```



- LocalDate, LocalDateTime 

```java
LocalDate.now();
LocalTime.now();
LocalDateTime.now();
```



### Convert between Old & New 

- Date -> ZonedDateTime

```java
// zoneId = ZoneId.systemDefault();
public static ZonedDateTime convert(@Nonnull Date date, ZoneId zoneId) {
  return date.toInstant().atZone(zoneId);
}
```



- ZonedDateTime -> Date 

```java
public static Date convert(ZonedDateTime zonedDateTime) {
  return Date.from(zonedDateTime.toInstant());
}
```



### Formatting 

- Date -> String 

```java
SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd'T'HH:mm:ss.SSS'Z'", Locale.getDefault());

public String dateToISOString(@Nonnull Date date) {
    return DATE_FORMAT.format(date);
}
```

- String -> Date 

```java
SimpleDateFormat DATE_FORMAT = new SimpleDateFormat("yyyy-MM-dd", Locale.getDefault());

public Date dateFromString(String dateStr) { // "2022-01-01"
	return DATE_FORMAT.parse(dateStr); 
}
```



#### java.time.DateTimeFormatter

Java 8의 DateTimeFormatter 클래스에서는 format과 관련된 풍부한 기능을 제공합니다. `DateTimeFormatter.ofPattern` 를 통해 직접 format을 설정할 수도 있고 이미 제공되는 여러 format을 활용할 수도 있습니다. 

```java
DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss")

DateTimeFormatter.BASIC_ISO_DATE; //  '20111203'
DateTimeFormatter.ISO_DATE; // '2011-12-03' or '2011-12-03+01:00'
DateTimeFormatter.ISO_LOCAL_DATE; //  '2011-12-03'
DateTimeFormatter.ISO_LOCAL_TIME; //  '10:15' or '10:15:30'
DateTimeFormatter.ISO_LOCAL_DATE_TIME; //  '2011-12-03T10:15:30'
DateTimeFormatter.ISO_OFFSET_DATE_TIME; // '2011-12-03T10:15:30+01:00'
DateTimeFormatter.ISO_ZONED_DATE_TIME; // '2011-12-03T10:15:30+01:00[Europe/Paris]'
```



- LocalDate, LocalDateTime -> String

```java
<LocalDate>.format(DateTimeFormatter.BASIC_ISO_DATE);
<LocalDateTime>.format(DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
```



- String -> LocalDate, LocalDateTime 

```java
LocalDate.parse("1995-05-09");
LocalDate.parse("20191224", DateTimeFormatter.BASIC_ISO_DATE); 

LocalDateTime.parse("2019-12-25T10:15:30");
LocalDateTime.parse("2019-12-25 12:30:00", DateTimeFormatter.ofPattern("yyyy-MM-dd HH:mm:ss"));
```



- ZonedDateTime -> String

```java
<ZonedDateTime>.format(DateTimeFormatter.ISO_ZONED_DATE_TIME); // ex. 2022-03-12T17:26:05.840250+09:00[Asia/Seoul]
<ZonedDateTime>.format(DateTimeFormatter.ISO_OFFSET_DATE_TIME); // ex. 2022-03-12T17:26:05.840250+09:00
```



- String -> ZonedDateTime 

```java
String input = "2022-03-12T17:26:05.840250+09:00[Asia/Seoul]"
ZonedDateTime.parse(input);
```





## Preserve Date, Time Consistency in Application  

어플리케이션이 가지고 있는 대부분의 기능은 시간과 관련이 있습니다. 예를 들어 Uber의 배차 시스템에서 고객에게 드라이버를 매칭하기 위해서는 고객이 언제 배차 요청을 했는지, 드라이버들 중에서 후보 드라이버는 얼만큼 대기하고 있었는지, 기대 소요시간은 얼마인지 등 여러 시간 데이터들을 가지고 배차 시스템이 동작합니다. 

하나의 어플리케이션은 다수의 웹 서버, 어플리케이션 서버, 데이터베이스 등 다양한 시스템이 긴밀하게 연결되어있는데요. 어플리케이션에 제대로 동작하려면 이들 시스템 간에 시간 데이터를 주고 받거나 영속적으로 저장할 때 시간 데이터의 일관성을 지키는 것이 매우 중요합니다. 그렇지 않으면 시간 역전 등의 문제로 인해 예측 및 분석하기가 어려운 장애가 발생할 수 있습니다. 일관성을 지키기 위해서는 다음의 두가지 규칙을 지켜야 합니다.



- 시간 데이터를 주고 받을 때 표준을 통해 주고 받습니다. (ISO-8601)
- 시간 데이터를 저장할 때 요청 서버와 데이터베이스의 시간대 차이를 고려하여 시간을 변환하여 저장합니다.



### ISO-8601 

ISO-8601은 date, time 관련 데이터들을 주고 받기 위한 국제 표준입니다. 잘 정의된 명확한 포맷을 통해서 날짜 및 시간 데이터를 주고 받을 때 잘못 해석되는 것을 방지하기 위한 표준이며 1988년에 처음 도입된 이후로 몇번의 개정이 있었습니다. 

날짜, 주, 일, 등 시간을 나타내는 표준이 각각 존재하지만, 특정 지역에서의 시간대를 포함하여 시간을 표현하기 위해서 ISO-8601에서는 아래 포맷을 사용합니다. 시간에 관한 전체 정보를 모든 시스템이 동의하는 표준으로 주고 받으므로 직렬화, 역직렬화 중에도 데이터가 손실되거나 왜곡될 일 없이 일관성을 유지할 수 있습니다. 

```
yyyy-MM-dd'T'HH:mm:ss'Z' (UTC)
yyyy-MM-dd'T'HH:mm:ss+HH:ss (offset)
```



### Database

서버들 간에 시간 데이터의 일관성을 지키기 위해서 ISO-8601 포맷으로 주고 받는 것 이상으로, 데이터베이스는  시간 데이터를 저장하고 이후에 서버의 요청으로부터 응답을 내려줄 때도 일관성을 지킬 책임이 있습니다.

MySQL에서는 요청 서버와 데이터베이스 서버의 시간대, 그리고 사용자 정의 시간대를 고려하여 시간을 변환하여 저장하기 위한 설정을 제공합니다. MySQL에서 시간 데이터를 어떻게 저장하는지에 대해서는 아래 글에서 추가적으로 알아보겠습니다.

(더보기)



## References

- [https://medium.com/javarevisited/the-evolution-of-the-java-date-time-api-bfdc61375ddb](https://medium.com/javarevisited/the-evolution-of-the-java-date-time-api-bfdc61375ddb)
- [https://docs.oracle.com/javase/8/docs/api/java/time/package-summary.html](https://docs.oracle.com/javase/8/docs/api/java/time/package-summary.html)
- [Naver D2 - Java의 날짜와 시간 API](https://d2.naver.com/helloworld/645609)
- [https://en.wikipedia.org/wiki/ISO_8601](https://en.wikipedia.org/wiki/ISO_8601)

