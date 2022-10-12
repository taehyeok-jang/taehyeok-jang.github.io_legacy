---
layout: post
title: What is Single Sign-On? 
subheading: 
author: taehyeok-jang
categories: [security]
tags: [security, sso, saml, oauth2.0, oidc]

---



## Introduction 

SSO는 한번의 인증으로 여러 application과 service에 안전하게 접근할 수 있게 하는 사용자 인증 방식입니다. 새로운 application을 사용하려고 할 때 자체 인증 시스템을 진행하지 않고 Google, Facebook, Slack을 통하여 간편하게 회원가입 및 로그인한 경험이 있을 것입니다. 이는 해당 application이 Google, Facebook에 사용자 인증 절차를 위임하여 서드파티를 통하여 인증했을 때 application을 사용할 수 있도록 했기 때문입니다. 이처럼 사용자는 SSO를 통하여 수십개의 개별 ID, password를 기억하지 않고도 간편하게 서비스를 이용할 수 있습니다. 

Single sign-on is a user authentication tool that enables users to securely access multiple applications and services using just one set of credentials. Whether your workday relies on Slack, Asana, Google Workspace, or Zoom, SSO provides you with a pop-up widget or login page with just one password that gives you access to every integrated app. Instead of twelve passwords in a day, SSO securely ensures you only need one.



## SSO Types 

SSO 시스템이 구성되는 방식은 크게 두가지입니다. SSO 대상 application에서 사용하는 인증 방식을 SSO agent가 대신해서 수행하는 delegation model과 인증 서버와의 신뢰관계를 기반으로 인증 서버로부터 사용자가 인증한 사실을 전달 받아 요청 시 이를 검사하는 propagation model이 있습니다. 

There are two types of SSO system intergation. One is a delegation model in which the SSO agent performs authentication in a way of a target application. The other is a propagation model. Based on the trust relationship, in which the authentication result is propagated from the authentication server to client and each request is inspected via the authentication server.

 

### Delegation model 

<img src="https://user-images.githubusercontent.com/31732943/195332989-5b9ea428-7781-48e5-82d7-d9e0c4f8bec1.jpg" alt="sso-delegation-model" style="zoom:67%;" />



- Each service delegates authentication to SSO agent. 
- Adopt the delegation model when we cannot alter each service's authentication method. 
- SSO agent stores user credentials (id/pw) of each service, and authenticate users on behalf of services.



### Propagation model 

<img src="https://user-images.githubusercontent.com/31732943/195333009-80fe3c04-5646-45b2-b676-a26625bc53c8.jpg" alt="sso-propgation-model" style="zoom:67%;" />

- Users authenticate via 'authentication service', and retrieve authentication token.
- An authentication token is granted to client via cookie in the web environment. With the support of such a web environment, most SSOs in the web environment adopt this model.
- Then users access to each service with the authentication token. 



## Protocol 

There are a variety of standard protocols to be aware of when identifying and working with SSO.



### SAML (Security Access Markup Language)

SAML is an XML based open standard that encodes text into machine language and enables the exchange of identification information. It has become one of the core standards for SSO and is used to help application providers ensure their authentication requests are appropriate. <u>SAML 2.0 is specifically optimized for use in web applications, which enables information to be transmitted through a web browser</u>. Many enterprise applications adopt SAML as a SSO solution. 

![saml_flow](https://user-images.githubusercontent.com/31732943/195333029-f680598b-3d50-4461-a017-b6512759e7ef.png)



### OAuth 2.0 (Open Authorization 2.0)

OAuth is an open-standard <u>authorization protocol</u> that transfers identification information between apps and encrypts it into machine code. This enables users to grant an application access to their data in another application without them having to manually validate their identity—which is particularly helpful for native apps.

The OAuth 2.0 spec has four important roles:

- **authorization server**: The server that issues the access token. 
- **resource owner**: Normally your application's end user that grants permission to access the resource server with an access token.
- **client**: The application that requests the access token and then passes it to the resource server.
- **resource server**: Accepts the access token and must verify that it's valid. In this case, this is your application.



Here is the abstract protocol flow from [RFC 6749](https://datatracker.ietf.org/doc/html/rfc6749).

<img width="502" alt="oauth_2 0_abstract_flow" src="https://user-images.githubusercontent.com/31732943/195333127-01644e5e-815d-4ad9-a479-1ecca0a7f0cd.png">



There are several grant types such as client credentials, implicit flow. A grant type must be adopted for specific application. OAuth 2.0 standards and many SSO enterprises provide a guidance of how to choose a grant type that fits our application. 





### OIDC (OpenID Connect)

OIDC builts on top of OAuth 2.0 to add information about the user and enable the SSO process, using an additional token called an **ID token**. It allows one login session to be used across multiple applications. For example, it enables a user to log in to a service using their Facebook or Google account rather than entering user credentials. 

Although OpenID Connect is built on top of OAuth 2.0, the [OpenID Connect specification (opens new window)](https://openid.net/connect/) uses slightly different terms for the roles in the flows:

As we discussed above, OAuth 2.0 is a protocol for authorization, not authenticaiton. The access token issued by OAuth 2.0 is only a token that temporarily grants a specific permission and does not contain information about users. <u>Although the user is authenticated to issue an access token, access token must not be used for authentication.</u> 

- **OpenID provider**: The authorization server that issues the ID token. In this case Okta is the OpenID provider.
- **end user**: The end user's information that is contained in the ID token.
- **relying party**: The client application that requests the ID token from Okta.
- **ID token**: The token issued by the OpenID Provider and contains information about the end user in the form of claims.
- **claim**: The claim is a piece of information about the end user.

The high-level flow looks the same for both OpenID Connect and regular OAuth 2.0 flows. <u>The primary difference is that an OpenID Connect flow results in an ID token, in addition to any access or refresh tokens.</u>



### Sum Up 

|                | SAML                                                     | OAuth 2.0                                      | OIDC (OpenID Connect)                                        |
| -------------- | -------------------------------------------------------- | ---------------------------------------------- | ------------------------------------------------------------ |
| Created        | 2001                                                     | 2005                                           | 2006                                                         |
| Format         | XML                                                      | JSON                                           | JSON                                                         |
| Platform       | Web                                                      | Web, Mobile                                    | Web, Mobile                                                  |
| Authorization  | O                                                        | O                                              | X                                                            |
| Authentication | O                                                        | Pseudo-authentication (have vulnerabilities)   | O                                                            |
| Main use cases | SSO for Enterprise internals (not suited for mobile env) | authorize 3rd party app for specific resources | SSO authentication for applications <br />Example. [https://developers.kakao.com/docs/latest/en/kakaologin/common](https://developers.kakao.com/docs/latest/en/kakaologin/common#login-with-oidc) |





## References

- SSO 
  - https://gruuuuu.github.io/security/ssofriends/
  - https://en.wikipedia.org/wiki/OAuth#OpenID_vs._pseudo-authentication_using_OAuth
  - https://oauth.net/articles/authentication/
  - https://www.okta.com/blog/2021/02/single-sign-on-sso/
  - https://openid.net/specs/openid-connect-core-1_0.html

- SAML, OAuth 2.0, OIDC
  - https://oauth.net/2/
  - https://www.okta.com/identity-101/whats-the-difference-between-oauth-openid-connect-and-saml/
  - https://www.okta.com/identity-101/saml-vs-oauth/
  - https://developer.okta.com/docs/concepts/oauth-openid/

