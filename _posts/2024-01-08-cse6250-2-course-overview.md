---
layout: post
title: CSE6250 Big Data for Healthcare - 2. Overview
subheading: 
author: taehyeok-jang
categories: [gatech]
tags: [gatech, big-data, machine-learning]
---



## Big Picture 

Systems / Algorithms / Healthcare Applications 

![cse6250_02_01](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/cddf8f6a-611a-4504-b8a8-e646294439b3)

## Healthcare Applications

![cse6250_02_02](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/b5441494-98bf-4541-a9a7-9e780c8e56db)

- Predictive modeling (ex. using historical data to build a model to predict a future outcome) 
- Computational Phenotyping (ex. turning electronic health records into meaningful clinical concepts) 
- Patient similarity (ex. use data to identify groups of patients sharing similar characteristics) 



### Predictive Modeling 

Q.

Try to estimate what percentage of people with Epilepsy in the U.S. responded to treatment? 

- A: ~2 years 
- B: 2~5 year 
- C: 5~ years

A.

32% / 24% / 44% 

Early detection for each group B, C will improve the opportunities of treatment. 



#### Challenges 

What makes predictive modeling difficult? 

- So much data

We have millions of patients, and we want to analyze their diagnosis information, medication information, and so on. So all these data combined together, create a big challenge. 

- So many models 

There are so many models to be built. Predictive modeling is not a single algorithm, but a sequence of computational tasks. But every step in pipeline has many different options. All of those combined give us many pipelines to be evaluated and compared. 

![cse6250_02_03](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/8568b415-6832-418e-b1d6-6242822df86f)



### Computational Phenotyping 

![cse6250_02_04](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/dec6a355-794c-4e58-aa22-e46366dcc22f)

The input of computation phenotyping is the raw patient data that consists of many different sources.

- Demographic information 
- Diagnosis 
- Medication 
- Procedure 
- Lab tests 
- Clinical notes 

Computation phenotyping is the process of turning the raw patient data into medical concepts or phenotypes.



Q. 

In order to extract phenotypes from raw data, what are some of the ‘waste products’ we should deal with? 

A. 

- Missing data
- Duplicates
- Irrelevant
- Redundant



#### Phenotyping Algorithm

![cse6250_02_05](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/c01f9875-9267-4905-a42f-c15fecc7d397)

Let’s take an example of phenotyping algorithm for ‘Type 2 Diabetes’. 

The Input is, EHR (electronic health records of a patient) 



Q. 

Can we just ask whether patient have Type 2 Diabetes diagnoses present in the data? 

A. 

=> NO. 

The electronic health records are very un-reliable (above reasons). Therefore it is not sufficient just checking one source of information. 





### Patient Similarity 

Q.

Which of the following types of reasoning do doctors engage most often?

- Flowchart reasoning 
- Instinct and intuition 
- Comparison to past individual patients 

A. 

=> Comparison to past individual patients (or case-based reasoning) 

Based on our anecdotal experiences, doctor often compared the current patient to the old patient they have seen. 



#### What is Patient Similarity? 

![cse6250_02_06](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/2f2361b1-b32b-4d40-a666-c757f309d359)

Simulating the doctor’ case-based reasoning with computer algorithms. 



When the patient comes in, the doctor does some examination on the patient. Then based on that information, we can do a similarity search through the database. Find those potentially similar patients, then doctor can provide some supervision on that result to find those truly similar patients to the specific clinical context. Then we can group those patients, based on what treatment they are taking, and look at what outcome they are getting. Then recommend the treatment with the best outcome to the current patient. 



## Algorithms 

- Classification 
- Clustering 
- Dimensionality reduction (X -> X’)
- Graph analysis (connect patients to a set of disease they have, then learn what are the most important patients and diseases in the network and also how do they relate?)



## Systems 

![cse6250_02_07](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/2999aea9-45b1-4b16-9b2d-fee7effe9478)
![cse6250_02_08](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/fd8b4f0c-39b3-4695-a780-9d97118bb4bd)

- Hadoop (distributed disk based big data system)
  - Hadoop Pig, Hive, HBase
  - MapReduce, HDFS
  - Core 
- Spark (distributed in-memory based big data system) 
  - Spark SQL 
  - Spark streaming 
  - MLLib (for distributed large scale ML) 
  - GraphX



## Summary 

With Systems / Algorithms / Healthcare Applications all together.

For example, we build ‘a scalable classifier using logistic regression’ on ‘Hadoop’ for ‘predicting heart failure’ 
