#!/usr/bin/env bash
# ==============================================================================
# DigitalQ Labs — Local K3d Cluster Setup
# ==============================================================================
# Idempotent setup script for the local development cluster.
# Safe to re-run: each step checks whether it has already been completed.
#
# Usage:
#   chmod +x setup.sh && ./setup.sh
#
# Prerequisites:
#   - Docker (running)
#   - k3d  >= 5.6.0
#   - kubectl
#   - helm >= 3.12
# ==============================================================================

set -euo pipefail

# ── Colour helpers ────────────────────────────────────────────────────────────
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No colour

info()    { echo -e "${BLUE}[INFO]${NC}  $*"; }
success() { echo -e "${GREEN}[OK]${NC}    $*"; }
warn()    { echo -e "${YELLOW}[WARN]${NC}  $*"; }
error()   { echo -e "${RED}[ERROR]${NC} $*"; exit 1; }

# ── Resolve paths relative to this script ─────────────────────────────────────
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
INFRA_DIR="$(cd "${SCRIPT_DIR}/.." && pwd)"
K3D_CONFIG="${SCRIPT_DIR}/cluster-config.yaml"
K8S_BASE_DIR="${INFRA_DIR}/kubernetes/base"

CLUSTER_NAME="digitalq-dev"
TRAEFIK_NAMESPACE="traefik"
LONGHORN_NAMESPACE="longhorn-system"

# ==============================================================================
# 1. Prerequisite Checks
# ==============================================================================
info "Checking prerequisites…"

command -v docker  >/dev/null 2>&1 || error "docker is not installed. Please install Docker Desktop."
command -v k3d     >/dev/null 2>&1 || error "k3d is not installed. Install via: curl -s https://raw.githubusercontent.com/k3d-io/k3d/main/install.sh | bash"
command -v kubectl >/dev/null 2>&1 || error "kubectl is not installed. Install via: https://kubernetes.io/docs/tasks/tools/"
command -v helm    >/dev/null 2>&1 || error "helm is not installed. Install via: https://helm.sh/docs/intro/install/"

# Verify Docker daemon is running
docker info >/dev/null 2>&1 || error "Docker daemon is not running. Please start Docker Desktop."

success "All prerequisites satisfied."

# ==============================================================================
# 2. Create K3d Cluster (idempotent)
# ==============================================================================
if k3d cluster list 2>/dev/null | grep -q "${CLUSTER_NAME}"; then
    warn "Cluster '${CLUSTER_NAME}' already exists — skipping creation."
else
    info "Creating k3d cluster '${CLUSTER_NAME}' from ${K3D_CONFIG}…"
    k3d cluster create --config "${K3D_CONFIG}"
    success "Cluster '${CLUSTER_NAME}' created."
fi

# Ensure kubeconfig context is set
info "Switching kubectl context to k3d-${CLUSTER_NAME}…"
kubectl config use-context "k3d-${CLUSTER_NAME}"
success "kubectl context set."

# Wait for nodes to be Ready
info "Waiting for nodes to become Ready…"
kubectl wait --for=condition=Ready node --all --timeout=120s
success "All nodes are Ready."

# ==============================================================================
# 3. Install Traefik via Helm (idempotent)
# ==============================================================================
# We install Traefik separately (rather than using K3s's bundled version) so we
# can pin the chart version and add our custom middleware / TLS configuration.

if helm list -n "${TRAEFIK_NAMESPACE}" 2>/dev/null | grep -q traefik; then
    warn "Traefik Helm release already exists — skipping install."
else
    info "Adding Traefik Helm repository…"
    helm repo add traefik https://traefik.github.io/charts 2>/dev/null || true
    helm repo update

    info "Installing Traefik…"
    kubectl create namespace "${TRAEFIK_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

    helm install traefik traefik/traefik \
        --namespace "${TRAEFIK_NAMESPACE}" \
        --set ports.web.port=8000 \
        --set ports.websecure.port=8443 \
        --set service.type=LoadBalancer \
        --set providers.kubernetesIngress.enabled=true \
        --set providers.kubernetesCRD.enabled=true \
        --set providers.kubernetesCRD.allowCrossNamespace=true \
        --set ingressRoute.dashboard.enabled=true \
        --set logs.general.level=INFO \
        --wait --timeout 120s

    success "Traefik installed."
fi

# ==============================================================================
# 4. Install Longhorn Storage via Helm (idempotent)
# ==============================================================================
# Longhorn provides distributed block storage with snapshots and backups,
# matching what we use in production for workspace PVCs.

if helm list -n "${LONGHORN_NAMESPACE}" 2>/dev/null | grep -q longhorn; then
    warn "Longhorn Helm release already exists — skipping install."
else
    info "Adding Longhorn Helm repository…"
    helm repo add longhorn https://charts.longhorn.io 2>/dev/null || true
    helm repo update

    info "Installing Longhorn (this may take a few minutes)…"
    kubectl create namespace "${LONGHORN_NAMESPACE}" --dry-run=client -o yaml | kubectl apply -f -

    helm install longhorn longhorn/longhorn \
        --namespace "${LONGHORN_NAMESPACE}" \
        --set defaultSettings.defaultDataPath=/var/lib/rancher/k3s/storage \
        --set defaultSettings.defaultReplicaCount=2 \
        --set persistence.defaultClassReplicaCount=2 \
        --wait --timeout 300s

    success "Longhorn installed."
fi

# ==============================================================================
# 5. Apply Base Kubernetes Manifests
# ==============================================================================
info "Applying base Kubernetes manifests from ${K8S_BASE_DIR}…"

if [ -f "${K8S_BASE_DIR}/kustomization.yaml" ]; then
    kubectl apply -k "${K8S_BASE_DIR}"
else
    # Fallback: apply individual files if kustomize config is missing
    for manifest in "${K8S_BASE_DIR}"/*.yaml; do
        kubectl apply -f "${manifest}"
    done
fi

success "Base manifests applied."

# ==============================================================================
# 6. Label Worker Nodes
# ==============================================================================
# Label agent nodes so the orchestrator can schedule workspace pods onto them.
info "Labelling worker nodes…"

AGENT_NODES=$(kubectl get nodes -l 'node-role.kubernetes.io/master!=' -o name 2>/dev/null || true)
if [ -z "${AGENT_NODES}" ]; then
    # k3s doesn't always set the master label; fall back to selecting agents by name
    AGENT_NODES=$(kubectl get nodes -o name | grep -i agent || true)
fi

for node in ${AGENT_NODES}; do
    kubectl label "${node}" digitalq.io/role=workspace --overwrite
    success "Labelled ${node} with digitalq.io/role=workspace"
done

# ==============================================================================
# 7. Print Connection Info
# ==============================================================================
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo -e "${GREEN} DigitalQ Labs — Local Cluster Ready${NC}"
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
echo ""
echo -e "  Cluster name :  ${BLUE}${CLUSTER_NAME}${NC}"
echo -e "  K8s context  :  ${BLUE}k3d-${CLUSTER_NAME}${NC}"
echo -e "  API server   :  ${BLUE}https://localhost:6443${NC}"
echo -e "  HTTP ingress :  ${BLUE}http://localhost:80${NC}"
echo -e "  HTTPS ingress:  ${BLUE}https://localhost:443${NC}"
echo -e "  Registry     :  ${BLUE}localhost:5111${NC}"
echo ""
echo -e "  Traefik      :  ${BLUE}kubectl -n ${TRAEFIK_NAMESPACE} get svc${NC}"
echo -e "  Longhorn UI  :  ${BLUE}kubectl -n ${LONGHORN_NAMESPACE} port-forward svc/longhorn-frontend 9000:80${NC}"
echo ""
echo -e "  Namespaces   :"
kubectl get namespaces --no-headers | awk '{printf "    - %s\n", $1}'
echo ""
echo -e "${GREEN}════════════════════════════════════════════════════════════════${NC}"
