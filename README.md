# ai-ml-observability-reference-architecture

## What is it?
A reference architecture for AI and ML Observability.

![a picture showing the reference architecture components](./static/reference_architecture.png)

## Why?
![a movie showing the problem statement of why observability is difficult](./static/problem_statement.gif)

Typically, the initial interest in AI/ML observability regards GPU utilization: is it 100%? When it's not, we start to wonder why. 
Investigating why may lead Data Scientists or Machine Learning Engineers into their code rather than infrastructure, 
or SREs to infrastructure when the problem may be code. Additionally, if things fail, it can be very challenging to understand 
why without a view of the entire picture

Creating a reference architecture for AI/ML observability enables all parties to be able to quickly understand how effectively
hardware is being utilized, while also allowing for faster root cause analysis of issues.

This repository contains a helm chart which will deploy an open source observability stack. The components can be configured or swapped, 
but the philosophy remains the same: aggregate the important data to quickly enable diagnoses. Bring your own cluster, deploy the charts, 
and test out the examples or skip ahead to monitoring your own jobs.  


## Getting started

### Prerequisites
A Kubernetes cluster
- Optional components:
  - nvidia device drivers/dcgm (if using)
  - neuron device drivers/neuron-monitor (if using)
  - kuberay (if using)
- Client tools:
  - `kubectl`
  - `kustomize`
  - `helm`

### Installation
`kustomize build --enable-helm | kubectl create -f -`

### Security
The installation above uses the default username and password for Grafana and OpenSearch. To change the usernames and passwords, follow:

#### Grafana
Uncomment and set `adminUser` and `adminPassword` in `prometheus-stack/kustomization.yaml`

#### OpenSearch
- Update `opensearch/admin-credentials-secret.yaml` with base64 encoded username and password
- Update `opensearch/securityconfig-secret.yaml` admin hash with the password hashed using `python -c 'import bcrypt; print(bcrypt.hashpw("admin123".encode("utf-8"), bcrypt.gensalt(12, prefix=b"2a")).decode("utf-8"))'`. Replace `admin123` with your password
- Update `prometheus-stack/data-sources/opensearch.yaml` and update the `basicAuthUser` and `basicAuthPassword`

### Example
To quickstart, we will leverage the AI on EKS base infrastructure blueprint. This blueprint will give us a Kubernetes environment with GPU and Neuron autoscaling to run the example job.

Follow the AI on EKS deployment HERE (LINK HERE)

Now that the cluster is deployed, follow the base installation instructions:
`kustomize build --enable-helm | kubectl create -f -`

Wait for the environment to be fully running. Next, launch a Ray GPU training job:

## Support
Reach out to omrishiv@ for help

## Roadmap

## Contributing
Contributions are always welcome!
