# ai-ml-observability-reference-architecture

## What is it?
A reference architecture for AI and ML Observability.

![a picture showing the reference architecture components](./static/reference_architecture.png)

## Why?
![a movie showing the problem statement of why observability is difficult](./static/problem_statement.gif)

Typically, the initial interest in AI/ML observability regards GPU utilization: is it 100%? When it's not, we start to wonder why. 
Investigating why may lead Data Scientists or Machine Learning Engineers into their code rather than infrastructure, 
or SREs to infrastructure when the problem may be code. Additionally, if things fail, it can be very challenging to understand 
why without a view of the entire picture.

Creating a reference architecture for AI/ML observability enables all parties to be able to quickly understand how effectively
hardware is being utilized, while also allowing for faster root cause analysis of issues.

This repository contains a helm chart which will deploy an open source observability stack. The components can be configured or swapped, 
but the philosophy remains the same: aggregate the important data to quickly enable diagnoses. Bring your own cluster, deploy the charts, 
and test out the examples or skip ahead to monitoring your own jobs.  


## Getting started

### Prerequisites
- A Kubernetes cluster

### Installation


## Support
Reach out to omrishiv@ for help

## Roadmap


## Contributing
Contributions are always welcome!
