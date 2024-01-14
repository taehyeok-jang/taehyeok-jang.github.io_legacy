---
layout: post
title: CSE6250 Big Data for Healthcare - 3. Predictive Modeling 
subheading: 
author: taehyeok-jang
categories: [gatech]
tags: [gatech, big-data, machine-learning]
---



## Intro

A process of modeling historical data for predicting future events. 

For example, use electronic health records to build a model of heart failures. Therefore, the key question is, how do we develop such a predictive model quickly? 



Ex. EHR 

From 2010, EHR become a major data sources of clinical predictive modeling research. 



## Predictive Modeling Pipeline 

![cse6250_03_01](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/690fa3f6-15c6-4b62-9658-d37951e3c7bd)

1. Prediction target 
2. Cohort construction 
3. Feature construction 
4. Feature selection 
5. Predictive model
6. Performance evaluation 

AND iterate! 



## Prediction Target

### Motivations for Early Detection of Heart Failure 

Q.

How many new cases of heart failure occur each year in the US? 

A.

550K 

![cse6250_03_02](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/b1a9059d-d113-4dc8-9a35-fe6a37b80e3f)



Complexity. 

There is no widely-accepted characterizations and definition of heart failure, probably because the complexity of the syndrome. 

It has many potential ideologies, diverse clinical features, and numerous clinical subsets. 



## Cohort Construction

How do we define the study population?

There are two different axes to be considered. 

![cse6250_03_03](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/17ed706f-895b-408d-87df-d04e6c531a82)
![cse6250_03_04](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/5b9a207e-b9d5-44f3-ad4d-820bc063ab49)



### Prospective vs Retrospective 

- Prospective 

Identify the cohort of patients, 

Decide what information to collect and how to collect them,

Start the data collection (from scratch) 



More expensive, takes a longer time



- Retrospective 

Identify the cohort of patients from existing data,

Retrieve all the data about the cohort.



More noises, common on large dataset 



### Study methods

- Cohort Study

We identify all the patients who are exposed to the risk and the matching criteria’s are not involved.  

![cse6250_03_05](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/9245e167-f8ce-4c39-9c90-3ecc734d54aa)



- Case-control study 

We first identify the cases, then try to match them to a set of control patients. 

KEY: to develop match~

![cse6250_03_06](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/7d0e8c11-5c9c-4e50-891b-00e285bd253c)
![cse6250_03_07](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/47115a8e-fc71-4bea-9c30-8b4060b216f5)



## Feature Construction 

The goal of feature construction is to construct all potentially relevant features about patients in order to predict the target outcome. 

![cse6250_03_08](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/e808744f-979c-4dbc-8669-75cf29bfdacf)

- Observation window

We use all the patient information happening this observation window to construct features. 

- Index date 

A date to use to learn predictive model to make a prediction about the target outcome. 

- Prediction window 
- Diagnosis date

the data that the target outcome happens. 

The case patient is diagnosed with heart failure on this date. The control patient does not have. So in theory, we can use any days from control patient as the diagnosis date. But commonly we use the same data of the matching case patient for the corresponding control. 



### Methods to Construct Features

- Count the number of times an event happens

If type 2 diabetes codes happens three times during the observation window, the corresponding feature for type 2 diabetes = 3. 

- Take average of the event value. 

If patient has two HBA1C measures during observation window, we can take the average of this two measurement as a feature for HBA1C. 



The length of prediction window and observation window are two important parameters that goin to impact the model performance. 



Q. 

Which one of these timelines is **the easiest for** modeling?

A. 

Large observation window & Small prediction window 

It is often easier to predict event in the near future (small prediction window). And large observation mean more information to be used to construct features, which is often better since w can model patient better with more data. 



Q. 

Which one of these timelines is **the most useful** model?

A.

Small observation window & Large prediction window. 

It is a quite ideal. In this ideal situation, if we can construct a good model, we want to predict far into future. (Even without much data about patients). However, this setting is often difficult to model, therefore unrealistic. 





### Prediction performance on Different Prediction window 

![cse6250_03_09](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/09146b61-b073-4549-9e37-adf3339058ae)

As another example, we can find that the accuracy of the model drops as we increase the prediction window, because it is easier to predict the near future than things happened far into the future. 

![cse6250_03_10](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/97ca4c2c-fe16-4349-903c-395fa793ded7)

Q. 

Which of these options is the most desirable prediction curve? 

A. 

We can predict accurately for fairly long period of time. While the performance of the other models drop fairly quickly as the prediction window increases. 



### Prediction performance on different observation windows. 

![cse6250_03_11](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/cb7cec6d-7a94-4a98-9aa5-ae3603b27d6b)



Typically, as the observation window increases, the performance improves, because we know more about the patients. 

![cse6250_03_12](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/37416af1-b0ab-4f5a-b050-ed3384a560c6)

Q. 

What is the optimal observation window? 

A. 

630 days

The model performance plateaued after 630 days. It indicates a diminishing return if we go further beyond that point. 



We may choose 900 days, but it’s a trade-off between how long is the observation window and how many patents have that much data. So if we choose 900 days, for patients who do not have enough data up to 900 days, they will be excluded from the study. 







## Feature Selection 

![cse6250_03_13](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/84967f12-b985-461a-aef9-8428b727a217)

The goal of feature selection is to find the truly predictive features to be included in the model. 

We can construct features using patients’ even sequences from raw data in the observation window. We can construct features from all of these events. However, not all events are relevant for predicting a specific target.

![cse6250_03_14](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/7ce0097b-2cfc-4f4d-b9ca-d1331aca9b55)
![cse6250_03_15](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/341dcd37-1f7f-43fb-a05a-1dd8d30b39bb)

In reality, the patient chart is quite complex over 20,000 features from a typical EHR dataset. Not all of this are relevant for predicting a target.

For example, if we want to predict a heart failure, those yellow features are relevant. However, for a different condition such as diabetes, maybe those purple features are relevant. 



## Predictive Model 

![cse6250_03_16](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/1c821c6e-1853-4f1b-be39-1c7f6241d075)

Predictive model is the function that maps the input features of the patient to the output target.

For example, if we know a patient’s past diagnosis, medication, and lab result, if we also know this function, then we can assess how likely the patient will have heart failure. 





## Performance Evaluation 

![cse6250_03_17](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/7f0598ca-386a-402e-b9b6-5385fcb296eb)

Evaluation of predictive models is one of the most crucial steps in the pipeline. 

- Training error is NOT very useful.

We can very easily overfit the training data by using complex model which do not generalize well to future samples.

- Testing error is the KEY metric.

It is a better approximation of the true perfjoamcne of the model on future samples. 



### Cross Validation 

![cse6250_03_18](https://github.com/taehyeok-jang/taehyeok-jang.github.io/assets/31732943/ff973a96-55f2-4a08-8dca-8cfe19b291b6)

The main idea behind the cross-validation, is to iteratively split a dataset into training and validation set. We build the model on the training set, and test the model on the validation set, but do this iteratively many times. Finally the performance matrix are aggregated across these iterations. 



#### 3 common methods for Cross Validation 

- Leave-1-out CV 

Take one example at a time as our validation set, use the remaining set as the training set. 

- K-fold CV

Split the entire dataset into K-folds, we iteratively choose each fold as a validation set, use the remaining folds as a training set to build another model. 

The final performance is the average over these K different models. 

- Randomized CV

Randomly split the dataset into training and testing. 



Randomized vs K-fold? 

Adv.

The proportion of the training and validation set does not depend on the number of folds. 

Disadv.

Some observation may never be selected into the validation set because there’s randomization process, whereas some other examples may be selected more than ones. 
