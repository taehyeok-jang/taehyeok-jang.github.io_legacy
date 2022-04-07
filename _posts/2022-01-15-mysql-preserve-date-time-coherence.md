---
layout: post
title: MySQL Preserve Date-Time Coherence
subheading: 
author: taehyeok-jang
categories: [database]
tags: [mysql, date, time, timezone]

---



## Introduction 

어플리케이션이 가지고 있는 대부분의 기능은 시간과 관련이 있으므로 데이터 보관을 위한 데이터베이스에서는 시간 데이터의 일관성을 지킬 책임이 있습니다. 시간 데이터는 time instant라고도 표현하며 time zone에 상관 없이 타임라인 상의 동일한 시각을 가리킵니다. 따라서 시간 데이터의 일관성을 유지하는 것은 데이터를 저장하고 조회하는 과정에서 시간 데이터가 여전히 동일한 시각을 가리키도록 하는 것을 의미합니다. 이는 데이터베이스 서버와 클라이언트 간, 요청 클라이언트와 응답 클라이언트 간 time zone이 서로 다른 상황에서도 동일하게 요구됩니다. 

MySQL에서는 시간 데이터의 일관성을 유지하기 위한 여러 설정들을 제공합니다. 사용자는 이 설정들을 통해 여러 시스템 간 시간대의 차이를 고려하여 주어진 시간 데이터를 적절하게 변환하여 저장할 수 있습니다. 이번 글에서는 MySQL에서 시간 데이터를 일관성있게 저장하는 방법에 대해서 알아보겠습니다. 



## Time Zones Went Through 

데이터베이스에 데이터를 저장하기까지 다양한 time zone이 관여합니다. Java 어플리케이션으로부터 MySQL 서버에 이르기까지 관여하는 time zone과 관련된 설정들은 아래와 같습니다.

### Application, Client Time Zone

- Original time zone  

어플리케이션에서 생성되는 데이터의 time zone 입니다. java.util.Date의 경우 default로 JVM time zone이 적용되지만 java.util.Calendar, java.time.OffsetDateTime and java.time.ZonedDateTime 의 경우 명시적으로 time zone을 가지고 있습니다. 

- Client local time zone

어플리케이션 서버의 JVM default time zone 입니다. 기본적으로 호스트의 system time zone과 동일하지만 어플리케이션에서 별도로 설정 가능합니다. 



### MySQL Time Zone

- MySQL TIMESTAMP internal time zone

MySQL에서 시간 데이터를 저장하기 위한 기준 time zone입니다. 특정 time zone의 구분 없이 항상 UTC로 변환하여 저장합니다. 

- MySQL system time zone 

MySQL 서버의 system time zone입니다. 서버를 기동 시 결정하여 `system_time_zone` 이라는 시스템 변수로 사용합니다. 서버를 시작할 때 호스트 머신의 기본 설정을 그대로 상속하며 특정 사용자의 설정이나 시작 스크립트를 통해 수정할 수 있습니다. 

- MySQL current (GLOBAL) time zone 

현재 MySQL 서버가 동작하고 있는 전역 time zone입니다. 초기값은 `SYSTEM`이며 이는 system time zone과 동일한 값을 사용하고 있다는 의미입니다. 전역 time zone은 MySQL 기동 시 `default-time-zone` option이나 my.cnf 파일을 통해 설정할 수 있으며 시스템 권한이 있으면 아래와 같이 쿼리문을 통해 변경할 수 도 있습니다. 

```ini
default-time-zone='timezone' // ex. '+09:00'
```

```sql
SET GLOBAL time_zone = <timezone>;
Ex. 
SET @@global.time_zone = '+00:00';
SET GLOBAL time_zone = '+09:00';
SET GLOBAL time_zone = 'Asia/Seoul';


SELECT @@global.time_zone;
```

- MySQL per-session time zones

MySQL 서버에 연결된 클라이언트 별 session time zone이다. 초기값은 `SYSTEM` 이며 서버 기동 시  `default-time-zone` option을 통해 설정할 수 있습니다. 아래에서 자세히 다루겠지만 클라이언트가 MySQL 서버에 connection을 생성할 때 connection properties을 통해서도 설정 가능합니다.

```sql
SET time_zone = <timezone>;
Ex. 
SET time_zone = 'Europe/Helsinki';
SET time_zone = "+00:00";
SET @@session.time_zone = "+00:00";

SELECT @@session.time_zone;
```



## MySQL Connector/J Connnection Properties (version 8.0~)

MySQL의 공식 JDBC driver인 MySQL Connector/J에서는 클라이언트와 MySQL 서버 간 시간 데이터를 주고 받는 것과 관련된 설정을 제공합니다. 클라이언트에서 connection을 생성할 때 설정이 적용되며, 각 설정들을 잘 조합하여 일관성을 유지하기 위한 적절한 방법을 만들어 낼 수 있습니다.



### connectionTimeZone

connectionTimeZone은 MySQL Connector/J가 어떻게 session time zone을 결정할지를 정하는 변수이며 클라이언트와 MySQL 서버 간 time zone에 따른 시간 변환을 어떻게 할지를 Connector/J에게 알려줍니다. 이전 설정인 serverTimeZone에서 명칭이 바뀐 것이며 MySQL global 혹은 session time zone과 꼭 같지 않아도 된다는 것을 강조하였습니다. 

- LOCAL (default)

connectionTimeZone을 JVM default time zone과 같게 하겠다는 것을 의미합니다.

- SERVER

Connector/J가 session time zone을 MySQL 서버 설정인 time_zone으로 하겠다는 의미입니다. 

- user-defined time zone

사용자 정의 time zone 설정이 가능하며 time zone 입력은 ZoneId에서 사용되는 syntax 형태를 따라야합니다.

유의해야 할 점은 이 설정만으로 MySQL 서버의 session time zone 설정이 바뀌지는 않으며 변경하려면 forceConnectionTimeZoneToSession 값을 true로 설정해야한다. 마찬가지로 preserveInstants 값이 false이면 시간 데이터의 time zone에 따른 변환이 전혀 이루어지지 않습니다. 



### forceConnectionTimeZoneToSession

forceConnectionTimeZoneToSession은 session time zone을 connectionTimeZone에서 설정한 값으로 설정할지 말지를 결정하는 변수입니다.  

- false (default)

session time zone이 MySQL 서버 상에서 바뀌지 않습니다.

- true

driver는 session time zone 값이 connectionTimeZone으로 설정한 값으로 변경됩니다. 

참고로 이 설정을 connectionTimeZone=SERVER와 함께 사용하면 아무런 효과가 없습니다. MySQL의 time zone은 이미 MySQL 서버 설정으로 되어있기 때문입니다. 



### preserveInstants

preserveInstants은 클라이언트와 MySQL 서버 간 시간 데이터를 주고 받을 때 타임라인 상에서 동일한 시점을 영속적으로 가리키기 위해 시간 변환을 하도록 지시하는 변수입니다. Java의 time instant 기반 변수인 java.sql.Timestamp, java.time.OffsetDateTime 두 클래스에 대해서 1) 저장할 때는 MySQL의 대상 칼럼의 타입이 TIMESTAMP일 때, 2) 조회할 때는 MySQL의 대상 칼럼의 타입이 TIMESTAMP, DATETIME일 때, 클라이언트와 MySQL 서버 간 time zone 차이만큼 시간 변환을 합니다.

- true (default)

Connector/J는 위 connectionTimeZone, forceConnectionTimeZoneToSession 변수를 고려하여 시간 변환을 합니다. 

- false 

시간 변환이 이루어지지 않으며 서버로부터 timestamp는 데이터베이스에 그대로 저장됩니다. 결과적으로 time instant는 실제 값을 유지하지 못하게 됩니다. 



시간 변환을 하지 않을 때 time instant가 어떻게 왜곡되는지 예시를 들어보겠습니다. 

- Time zones: 클라이언트(JVM)는 UTC , server session은 UTC+1. 
- 클라이언트로부터 original timestamp (UTC): `2020-01-01 01:00:00`
- Connector/J에 의해 MySQL 서버로 전송된 timestamp: `2020-01-01 01:00:00` (시간 변환 없음)
- MySQL 서버에 저장된 timestamp: `2020-01-01 00:00:00 UTC` (`2020-01-01 00:00:00 UTC+1` 에서 UTC로 내부 시스템에서 변환)
- MySQL 서버에서 조회할 때 server session (UTC+1)에서의 timestamp: : `2020-01-01 01:00:00`( `2020-01-01 00:00:00` UTC에서 UTC+1로 내부 시스템에서 변환)
- 이전 클라이언트와는 다른 시간대의 (UTC+3) Connector/J로 연결된 클라이언트(JVM)에서의 timestamp: `2020-01-01 01:00:00` (새로운 클라이언트의 time zone과 상관 없이 그대로 반환)

- => time instant의 일관성이 지켜지지 않음. 





## Preserving Time Instants

앞서 언급한대로 MySQL Connector/J의 여러 설정들을 통해 시간 데이터의 일관성을 유지할 수 있습니다. MySQL에서는 시간 데이터를 저장할 때 original time zone을 포함하지 않으며, 그 대신에 session time zone 상에서 적절하게 표시된다고 가정합니다. 이는 시간 데이터를 저장하기 이전에 클라이언트와 MySQL 서버 간 시간 변환이 필요하다는 것을 의미합니다. 어플리케이션이 처한 상황에 맞추어 Connector/J의 설정들을 정하는 몇가지 방법을 알아보겠습니다. 시간 변환이 언제 발생하는지에 초점을 두면 이해하기가 한결 수월합니다. 



### Soution 1. 

<img src="https://user-images.githubusercontent.com/31732943/162183693-cb35327e-cfbd-4f08-9191-d3aa8172aedc.png" alt="mysql_datetime_solution_1" style="zoom:67%;" />

connectionTimeZone=LOCAL&forceConnectionTimeZoneToSession=false

- Time zones: 클라이언트(JVM)와 server session 모두 UTC+1.
- 클라이언트로부터 original timestamp (UTC): `2020-01-01 01:00:00`
- Connector/J에 의해 MySQL 서버로 전송된 timestamp: `2020-01-01 01:00:00` (시간 변환 없음)
- MySQL 서버에 저장된 timestamp: `2020-01-01 00:00:00 UTC` (`2020-01-01 01:00:00 UTC+1` 에서 UTC로 내부 시스템에서 변환)
- MySQL 서버에서 조회할 때 server session (UTC+1)에서의 timestamp: : `2020-01-01 01:00:00`( `2020-01-01 00:00:00` UTC에서 UTC+1로 내부 시스템에서 변환)
- 동일 클라이언트(JVM) (UTC+1)에서의 timestamp: `2020-01-01 01:00:00`

=> 변환 없이 time instant의 일관성이 유지됨. 



### Solution 2.

<img src="https://user-images.githubusercontent.com/31732943/162183738-4dee6ff0-e82b-4051-a4d0-5c0927bdba2c.png" alt="mysql_datetime_solution_2" style="zoom:67%;" />

connectionTimeZone=LOCAL& forceConnectionTimeZoneToSession=true

- Time zones: 클라이언트(JVM)는 UTC+1, server session은 UTC+2 이었으나 Connector/J에 의해 UTC+1로 변경. 
- 클라이언트로부터 original timestamp (UTC+1): `2020-01-01 01:00:00`
- Connector/J에 의해 MySQL 서버로 전송된 timestamp: `2020-01-01 01:00:00` (시간 변환 없음)
- MySQL 서버에 저장된 timestamp: `2020-01-01 00:00:00 UTC` (`2020-01-01 01:00:00 UTC+1` 에서 UTC로 내부 시스템에서 변환)
- MySQL 서버에서 조회할 때 server session (UTC+1)에서의 timestamp: : `2020-01-01 01:00:00`( `2020-01-01 00:00:00` UTC에서 UTC+1로 내부 시스템에서 변환)
- 동일 클라이언트(JVM) (UTC+1)에서의 timestamp: `2020-01-01 01:00:00` (변환 없음)
- Connector/J에 의해 변경된 time zone (UTC+3)의 server session에서 timestamp: `2020-01-01 03:00:00`
- 변경된 클라이언트 (UTC+3) (JVM)에서의 timestamp: `2020-01-01 03:00:00` (변환 없음)



=> Time instant is preserved without conversion by Connector/J, because the session time zone is changed by Connector/J to its JVM's value.



### Solution 3. 

<img src="https://user-images.githubusercontent.com/31732943/162183757-8804eac3-49fa-46cf-8b9e-88284980b937.png" alt="mysql_datetime_solution_3" style="zoom: 67%;" />

preserveInstants=true&connectionTimeZone=<user-defined-time-zone>& forceConnectionTimeZoneToSession=true

이 방법은 Connector/J에 의해 서버의 session time zone 설정을 인식하는 것이 불가능할 때 (CST, CEST 등) 주로 사용됩니다. 

- Time zones: 클라이언트(JVM)는 UTC+2, server session은 CET이었으나 Connector/J에 의해 user-specified `Europe/Berlin` 으로 변경. 
- 클라이언트로부터 original timestamp (UTC+2): `2020-01-01 02:00:00`
- Connector/J에 의해 MySQL 서버로 전송된 timestamp: `2020-01-01 01:00:00` (JVM time zone (UTC+2)과 user-defined time zone (`Europe/Berlin`=UTC+1) 간 변경)
- MySQL 서버에 저장된 timestamp: `2020-01-01 00:00:00 UTC` (`2020-01-01 01:00:00 UTC+1` 에서 UTC로 내부 시스템에서 변환)
- MySQL 서버에서 조회할 때 server session (UTC+1)에서의 timestamp: : `2020-01-01 01:00:00`(UTC에서 `Europe/Berlin` (UTC+1)로 내부 시스템에서 변환)
- 동일 클라이언트(JVM) (UTC+2) 어플리케이션에서의 timestamp: `2020-01-01 02:00:00` (user-defined time zone (UTC+1) and JVM time zone (UTC+2) 간 변환)



=> Time instant is preserved with conversion and with the session time zone being changed by Connector/J according to a user-defined value.





## References

- [https://dev.mysql.com/doc/refman/8.0/en/time-zone-support.html](https://dev.mysql.com/doc/refman/8.0/en/time-zone-support.html)
- [https://dev.mysql.com/doc/connector-j/8.0/en/connector-j-time-instants.html](https://dev.mysql.com/doc/connector-j/8.0/en/connector-j-time-instants.html)
- [https://dev.mysql.com/blog-archive/support-for-date-time-types-in-connector-j-8-0/](https://dev.mysql.com/blog-archive/support-for-date-time-types-in-connector-j-8-0/)
- [https://phoenixnap.com/kb/change-mysql-time-zone](https://phoenixnap.com/kb/change-mysql-time-zone)
- [https://dev.mysql.com/doc/connector-j/8.0/en/connector-j-connp-props-datetime-types-processing.html](https://dev.mysql.com/doc/connector-j/8.0/en/connector-j-connp-props-datetime-types-processing.html)





