# Combined Setup Guide

Complete setup guide for deploying the Agentic SRE system with demo workloads on a local KIND cluster.

## Prerequisites

- Docker Desktop or Docker Engine running
- `kind` (Kubernetes in Docker)
- `kubectl` CLI tool

## 1) Create KIND Cluster

```bash
kind create cluster --name agentic-sre --config kind/kind-config.yaml
kubectl config use-context kind-agentic-sre
```

## 2) Install Required Components

### Install metrics-server (required)
```bash
kubectl apply -f https://github.com/kubernetes-sigs/metrics-server/releases/latest/download/components.yaml
kubectl -n kube-system rollout status deployment/metrics-server
```

### Optional: Install lightweight Prometheus
```bash
kubectl apply -f https://raw.githubusercontent.com/prometheus-operator/prometheus-operator/main/bundle.yaml
```

## 3) Build and Load Images

### Build core service images
```bash
docker build -t agentic-sre-api:latest -f Dockerfile.api .
docker build -t agentic-sre-ui:latest -f Dockerfile.ui .
```

### Build demo application images
```bash
docker build -t demo-app-a:latest demo-apps/app-a
docker build -t demo-app-b:latest demo-apps/app-b
```

### Load all images into KIND
```bash
kind load docker-image agentic-sre-api:latest --name agentic-sre
kind load docker-image agentic-sre-ui:latest --name agentic-sre
kind load docker-image demo-app-a:latest --name agentic-sre
kind load docker-image demo-app-b:latest --name agentic-sre
```

## 4) Deploy Core Services

```bash
kubectl apply -f k8s/namespace.yaml
kubectl apply -f k8s/rbac-readonly.yaml
kubectl apply -f k8s/configmap.yaml
kubectl apply -f k8s/secret.yaml
kubectl apply -f k8s/redis-deployment.yaml
kubectl apply -f k8s/redis-service.yaml
kubectl apply -f k8s/api-deployment.yaml
kubectl apply -f k8s/api-service.yaml
kubectl apply -f k8s/ui-deployment.yaml
kubectl apply -f k8s/ui-service.yaml
```

## 5) Deploy Demo Workloads

### Create demo namespaces and applications
```bash
kubectl apply -f k8s/demo/namespaces.yaml
kubectl apply -f k8s/demo/app-a.yaml
kubectl apply -f k8s/demo/app-b.yaml
```

## 6) Configure Demo Attacker Credentials

The demo attacker has scoped write permissions only to demo namespaces for safe incident simulation.

### Create service account and RBAC
```bash
kubectl apply -f k8s/demo/rbac-demo-attacker.yaml
```

### Generate and store token
```bash
kubectl -n agentic-sre create token demo-attacker > /tmp/demo-attacker.token
```

### Mount token into API deployment
```bash
kubectl -n agentic-sre create secret generic demo-attacker-token \
  --from-file=token=/tmp/demo-attacker.token

kubectl -n agentic-sre patch deployment agentic-sre-api \
  --type='json' \
  -p='[
    {"op":"add","path":"/spec/template/spec/volumes/-","value":{"name":"demo-attacker-token","secret":{"secretName":"demo-attacker-token"}}},
    {"op":"add","path":"/spec/template/spec/containers/0/volumeMounts/-","value":{"name":"demo-attacker-token","mountPath":"/var/run/demo-attacker","readOnly":true}},
    {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"DEMO_ATTACKER_TOKEN_PATH","value":"/var/run/demo-attacker/token"}}
  ]'
```

## 7) Verify Installation

### Check core services
```bash
kubectl get pods -n agentic-sre
```

### Check demo workloads
```bash
kubectl get pods -n ns-a
kubectl get pods -n ns-b
```

### Test API endpoints
```bash
# Health check
curl http://localhost:30080/healthz

# Inject demo incident
curl -X POST http://localhost:30080/demo/inject \
  -H "Content-Type: application/json" \
  -d '{"incident_type": "crashloop", "namespace": "default", "severity": "high"}'
```

### Access UI
```bash
open http://localhost:30081
```

The UI Dashboard should display:
- Core service health status
- Demo workload status (ns-a, ns-b)
- Incident management interface

## Cleanup

To remove the entire setup:

```bash
kind delete cluster --name agentic-sre
rm /tmp/demo-attacker.token
```

## Troubleshooting

### Pods not starting
```bash
kubectl describe pod <pod-name> -n <namespace>
kubectl logs <pod-name> -n <namespace>
```

### Images not loading
Ensure Docker is running and images are built before loading into KIND.

### Port conflicts
If ports 30080 or 30081 are in use, modify the NodePort values in the service YAML files.
