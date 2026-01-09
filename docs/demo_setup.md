# Demo Setup (KIND)

This addendum walks through setting up the demo workloads and the scoped demo attacker credentials on a local KIND cluster.

## Prerequisites

- Docker Desktop or Docker Engine running
- `kind`, `kubectl`
- The API + UI images built locally (see `setup.md`)

## 1) Create/Use the KIND cluster

```bash
kind create cluster --name agentic-sre --config kind/kind-config.yaml
kubectl config use-context kind-agentic-sre
```

## 2) Deploy core services

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

## 3) Load demo app images into KIND

```bash
docker build -t demo-app-a:latest demo-apps/app-a
docker build -t demo-app-b:latest demo-apps/app-b
kind load docker-image demo-app-a:latest --name agentic-sre
kind load docker-image demo-app-b:latest --name agentic-sre
```

## 4) Deploy demo namespaces and workloads

```bash
kubectl apply -f k8s/demo/namespaces.yaml
kubectl apply -f k8s/demo/app-a.yaml
kubectl apply -f k8s/demo/app-b.yaml
```

## 5) Create demo attacker token (scoped, write only to demo namespaces)

```bash
kubectl apply -f k8s/demo/rbac-demo-attacker.yaml
kubectl -n agentic-sre create token demo-attacker > /tmp/demo-attacker.token
```

## 6) Mount demo attacker token into the API

Create a token secret and update the API deployment to mount it (minimal patch):

```bash
kubectl -n agentic-sre create secret generic demo-attacker-token --from-file=token=/tmp/demo-attacker.token
kubectl -n agentic-sre patch deployment agentic-sre-api \
  --type='json' \
  -p='[
    {"op":"add","path":"/spec/template/spec/volumes/-","value":{"name":"demo-attacker-token","secret":{"secretName":"demo-attacker-token"}}},
    {"op":"add","path":"/spec/template/spec/containers/0/volumeMounts/-","value":{"name":"demo-attacker-token","mountPath":"/var/run/demo-attacker","readOnly":true}},
    {"op":"add","path":"/spec/template/spec/containers/0/env/-","value":{"name":"DEMO_ATTACKER_TOKEN_PATH","value":"/var/run/demo-attacker/token"}}
  ]'
```

## 7) Validate demo workloads

```bash
kubectl get pods -n ns-a
kubectl get pods -n ns-b
```

Once pods are ready, the UI Demo Workloads panel should display health status.
