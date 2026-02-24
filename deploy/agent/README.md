# AI/ML Optimization Agent

An AI agent for analyzing AI/ML workloads and providing optimization recommendations. It connects to the observability stack via MCP servers to access Prometheus metrics, OpenSearch logs, and Kubernetes resources.

## Prerequisites

- The observability stack deployed (see the [root README](../../README.md))
- MCP servers deployed (uncomment `- mcp` in `deploy/kustomization.yaml` or `--set mcp.enabled=true` with Helm)
- AWS credentials configured for Amazon Bedrock (the agent uses Claude via Bedrock) — see [Bedrock Authentication](#bedrock-authentication) below

## Bedrock Authentication

The agent calls Claude via Amazon Bedrock, which requires AWS credentials. How you provide them depends on where the agent runs.

### Running locally

Use any standard AWS credential method — environment variables, `~/.aws/credentials`, or SSO:

```bash
export AWS_ACCESS_KEY_ID=...
export AWS_SECRET_ACCESS_KEY=...
export AWS_REGION=us-east-1
```

Or if using AWS SSO / IAM Identity Center:

```bash
aws sso login --profile your-profile
export AWS_PROFILE=your-profile
```

The IAM identity needs the `bedrock:InvokeModelWithResponseStream` permission for the model used by the agent (`us.anthropic.claude-opus-4-5-20251101-v1:0`).

### Running on EKS (recommended)

When deploying the agent to an EKS cluster, use **EKS Pod Identity** to grant Bedrock access without managing static credentials. This associates an IAM role directly with the agent's Kubernetes ServiceAccount.

The EKS Pod Identity Agent (installed as a cluster add-on) injects the credentials automatically. No environment variables needed.

For full setup details, see the [EKS Pod Identity documentation](https://docs.aws.amazon.com/eks/latest/userguide/pod-identities.html).

## Architecture

```
┌────────────────┐     ┌────────────────┐     ┌─────────────────────┐
│   Streamlit    │     │   Agent API    │     │    MCP Servers      │
│    (8501)      │────▶│    (8080)      │────▶│                     │
│                │     │                │     │  prometheus  (8080) │
│   ConfigMap    │     │   Container    │     │  kubernetes  (8080) │
│                │     │                │     │  opensearch  (9900) │
└────────────────┘     └────────────────┘     └─────────────────────┘
  python:3.13-slim       custom image
  + app.py mounted       (Dockerfile)
```

The Streamlit UI and agent are separate containers. The Streamlit app (`app.py`) is deployed as a ConfigMap mounted into a generic Python container. The agent is a custom image built from the Dockerfile in this directory. Both connect over HTTP within the cluster.

## MCP Server Service URLs

Once deployed, the MCP servers are available at these in-cluster addresses:

| Server | Kubernetes Service URL |
|--------|------------------------|
| Prometheus | `http://prometheus-mcp.monitoring.svc.cluster.local:8080/sse` |
| Kubernetes | `http://kubernetes-mcp-server.monitoring.svc.cluster.local:8080/sse` |
| OpenSearch | `http://opensearch-mcp-server.monitoring.svc.cluster.local:9900/sse` |

## Usage

There are three ways to run the agent, depending on where you want each component to run.

---

### Option 1: Run everything locally (port-forward MCP servers)

Use this for local development. Port-forward the MCP servers from the cluster to your machine, then run the agent and Streamlit locally.

**1. Port-forward the MCP servers:**

```bash
# Each in a separate terminal (or background them)
kubectl port-forward -n monitoring svc/prometheus-mcp 8001:8080
kubectl port-forward -n monitoring svc/kubernetes-mcp-server 8002:8080
kubectl port-forward -n monitoring svc/opensearch-mcp-server 8003:9900
```

**2. Install dependencies:**

```bash
# Agent dependencies
pip install -r requirements.txt

# Streamlit dependencies (separate from agent)
pip install streamlit requests
```

**3. Start the agent:**

```bash
export MCP_SERVERS="prometheus=http://localhost:8001/sse,kubernetes=http://localhost:8002/sse,opensearch=http://localhost:8003/sse"
python agent.py
```

**4. Start the Streamlit UI:**

```bash
# In a new terminal
streamlit run app.py
```

The agent API is at `http://localhost:8080` and the UI is at `http://localhost:8501`.

---

### Option 2: Deploy agent on cluster, interact via curl

Build and deploy the agent as a container on the cluster. It connects directly to the MCP servers via their Kubernetes service URLs. Port-forward the agent to send requests from your machine.

**1. Build and push the agent container:**

```bash
docker build -t <your-registry>/ai-ml-agent:latest .
docker push <your-registry>/ai-ml-agent:latest
```

**2. Deploy to the cluster:**

```bash
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-ml-agent
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-ml-agent
  template:
    metadata:
      labels:
        app: ai-ml-agent
    spec:
      containers:
        - name: agent
          image: <your-registry>/ai-ml-agent:latest
          ports:
            - containerPort: 8080
          env:
            - name: MCP_SERVERS
              value: "prometheus=http://prometheus-mcp.monitoring.svc.cluster.local:8080/sse,kubernetes=http://kubernetes-mcp-server.monitoring.svc.cluster.local:8080/sse,opensearch=http://opensearch-mcp-server.monitoring.svc.cluster.local:9900/sse"
---
apiVersion: v1
kind: Service
metadata:
  name: ai-ml-agent
  namespace: monitoring
spec:
  selector:
    app: ai-ml-agent
  ports:
    - port: 8080
      targetPort: 8080
EOF
```

**3. Port-forward and send requests:**

```bash
kubectl port-forward -n monitoring svc/ai-ml-agent 8080:8080
```

```bash
curl -X POST http://localhost:8080/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "Analyze GPU usage for training jobs"}' \
  --no-buffer
```

---

### Option 3: Deploy agent and Streamlit on cluster

Deploy both the agent and Streamlit on the cluster. The Streamlit app is packaged as a ConfigMap and mounted into a generic Python container — no custom image build needed for the UI. Port-forward only Streamlit to access it.

**1. Build and push the agent container:**

```bash
docker build -t <your-registry>/ai-ml-agent:latest .
docker push <your-registry>/ai-ml-agent:latest
```

**2. Create the Streamlit ConfigMap from `app.py`:**

```bash
kubectl create configmap streamlit-app --from-file=app.py -n monitoring
```

**3. Deploy agent and Streamlit:**

```bash
kubectl apply -f - <<EOF
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-ml-agent
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-ml-agent
  template:
    metadata:
      labels:
        app: ai-ml-agent
    spec:
      containers:
        - name: agent
          image: <your-registry>/ai-ml-agent:latest
          ports:
            - containerPort: 8080
          env:
            - name: MCP_SERVERS
              value: "prometheus=http://prometheus-mcp.monitoring.svc.cluster.local:8080/sse,kubernetes=http://kubernetes-mcp-server.monitoring.svc.cluster.local:8080/sse,opensearch=http://opensearch-mcp-server.monitoring.svc.cluster.local:9900/sse"
---
apiVersion: v1
kind: Service
metadata:
  name: ai-ml-agent
  namespace: monitoring
spec:
  selector:
    app: ai-ml-agent
  ports:
    - port: 8080
      targetPort: 8080
---
apiVersion: apps/v1
kind: Deployment
metadata:
  name: ai-ml-agent-ui
  namespace: monitoring
spec:
  replicas: 1
  selector:
    matchLabels:
      app: ai-ml-agent-ui
  template:
    metadata:
      labels:
        app: ai-ml-agent-ui
    spec:
      containers:
        - name: streamlit
          image: python:3.13-slim
          command: ["/bin/bash", "-c"]
          args:
            - pip install streamlit requests && streamlit run /app/app.py --server.port=8501 --server.address=0.0.0.0
          ports:
            - containerPort: 8501
          env:
            - name: AGENT_URL
              value: "http://ai-ml-agent.monitoring.svc.cluster.local:8080"
          volumeMounts:
            - name: app-code
              mountPath: /app
      volumes:
        - name: app-code
          configMap:
            name: streamlit-app
---
apiVersion: v1
kind: Service
metadata:
  name: ai-ml-agent-ui
  namespace: monitoring
spec:
  selector:
    app: ai-ml-agent-ui
  ports:
    - port: 8501
      targetPort: 8501
EOF
```

**4. Port-forward the Streamlit UI:**

```bash
kubectl port-forward -n monitoring svc/ai-ml-agent-ui 8501:8501
```

Open `http://localhost:8501` in your browser.

To update the Streamlit app after editing `app.py`:

```bash
kubectl create configmap streamlit-app --from-file=app.py -n monitoring --dry-run=client -o yaml | kubectl apply -f -
kubectl rollout restart deployment/ai-ml-agent-ui -n monitoring
```

## API Reference

### POST /prompt

Submit a prompt and receive a streaming SSE response.

```bash
curl -X POST http://localhost:8080/prompt \
  -H "Content-Type: application/json" \
  -d '{"prompt": "What are the most expensive workloads running right now?"}' \
  --no-buffer
```

Response is a stream of Server-Sent Events:
```
data: {"type": "text", "content": "Let me check..."}
data: {"type": "tool", "name": "query_prometheus", "input": {...}}
data: {"type": "text", "content": " the metrics show..."}
data: {"type": "done"}
```

Event types:
| Type | Description |
|------|-------------|
| `text` | Agent response text chunk |
| `tool` | MCP tool invocation (name and input) |
| `result` | Tool result |
| `done` | Stream complete |
| `error` | Error occurred |

### GET /health

```bash
curl http://localhost:8080/health
```

Returns agent status, model, and configured MCP servers:
```json
{"status": "healthy", "model": "us.anthropic.claude-opus-4-5-20251101-v1:0", "mcp_servers": ["prometheus", "kubernetes", "opensearch"]}
```

## Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_SERVERS` | Comma-separated `name=url` pairs for MCP servers | `""` |
| `MODEL_ID` | Bedrock model ID for the agent | `us.anthropic.claude-opus-4-5-20251101-v1:0` |
| `AGENT_URL` | Agent API URL (used by Streamlit) | `http://localhost:8080` |
