# ==============================================================================
# DigitalQ Labs — Local Dev Cluster Setup (PowerShell)
# ==============================================================================
# Idempotent setup script for Windows developers.
# Safe to re-run: each step checks whether it has already been completed.
#
# Usage:
#   .\dev-cluster-setup.ps1
#
# Prerequisites:
#   - Docker Desktop (running)
#   - k3d  >= 5.6.0
#   - kubectl
#   - helm >= 3.12
# ==============================================================================

#Requires -Version 5.1

param(
    [switch]$SkipHelm,        # Skip Helm chart installations
    [switch]$SkipManifests,   # Skip applying base manifests
    [switch]$Destroy          # Tear down the cluster instead
)

$ErrorActionPreference = "Stop"

# ── Configuration ─────────────────────────────────────────────────────────────
$ClusterName = "digitalq-dev"
$TraefikNamespace = "traefik"
$LonghornNamespace = "longhorn-system"

# Resolve paths relative to this script
$ScriptDir = Split-Path -Parent $MyInvocation.MyCommand.Path
$InfraDir = Split-Path -Parent $ScriptDir
$K3dConfig = Join-Path $InfraDir "k3d\cluster-config.yaml"
$K8sBaseDir = Join-Path $InfraDir "kubernetes\base"

# ── Helper Functions ──────────────────────────────────────────────────────────
function Write-Info { param([string]$Message) Write-Host "[INFO]  $Message" -ForegroundColor Blue }
function Write-Success { param([string]$Message) Write-Host "[OK]    $Message" -ForegroundColor Green }
function Write-Warn { param([string]$Message) Write-Host "[WARN]  $Message" -ForegroundColor Yellow }
function Write-Err { param([string]$Message) Write-Host "[ERROR] $Message" -ForegroundColor Red; exit 1 }

function Test-Command {
    param([string]$Command)
    return [bool](Get-Command $Command -ErrorAction SilentlyContinue)
}

# ==============================================================================
# Handle -Destroy flag
# ==============================================================================
if ($Destroy) {
    Write-Info "Destroying cluster '$ClusterName'..."
    & k3d cluster delete $ClusterName 2>$null
    Write-Success "Cluster '$ClusterName' destroyed."
    exit 0
}

# ==============================================================================
# 1. Prerequisite Checks
# ==============================================================================
Write-Info "Checking prerequisites..."

$prerequisites = @(
    @{ Name = "docker"; Url = "https://docs.docker.com/desktop/install/windows-install/" },
    @{ Name = "k3d"; Url = "https://k3d.io/#installation" },
    @{ Name = "kubectl"; Url = "https://kubernetes.io/docs/tasks/tools/install-kubectl-windows/" },
    @{ Name = "helm"; Url = "https://helm.sh/docs/intro/install/" }
)

$missing = @()
foreach ($prereq in $prerequisites) {
    if (Test-Command $prereq.Name) {
        Write-Success "$($prereq.Name) found."
    }
    else {
        $missing += $prereq
    }
}

if ($missing.Count -gt 0) {
    Write-Host ""
    Write-Err ("Missing prerequisites:`n" + (
            ($missing | ForEach-Object { "  - $($_.Name): $($_.Url)" }) -join "`n"
        ))
}

# Verify Docker daemon is running
$dockerCheck = docker info --format '{{.ID}}' 2> $null
if ($LASTEXITCODE -ne 0 -or [string]::IsNullOrEmpty($dockerCheck)) {
    Write-Err "Docker daemon is not running. Please start Docker Desktop."
    exit 1 
}
else {
    Write-Success "Docker daemon is running."
}

Write-Success "All prerequisites satisfied."

Write-Info "Creating docker network dqlabs_network..."
docker network create dqlabs_network 2>$null | Out-Null
Write-Success "Docker network dqlabs_network ready."

# ==============================================================================
# 2. Create K3d Cluster (idempotent)
# ==============================================================================
$existingClusters = & k3d cluster list -o json 2>$null | ConvertFrom-Json
$clusterExists = $existingClusters | Where-Object { $_.name -eq $ClusterName }

if ($clusterExists) {
    Write-Warn "Cluster '$ClusterName' already exists - skipping creation."
}
else {
    Write-Info "Creating k3d cluster '$ClusterName' from $K3dConfig..."

    if (-not (Test-Path $K3dConfig)) {
        Write-Err "Cluster config not found at: $K3dConfig"
    }

    & k3d cluster create --config $K3dConfig
    if ($LASTEXITCODE -ne 0) { Write-Err "Failed to create cluster." }

    Write-Success "Cluster '$ClusterName' created."
}

# Switch kubectl context
Write-Info "Switching kubectl context to k3d-$ClusterName..."
& kubectl config use-context "k3d-$ClusterName"
if ($LASTEXITCODE -ne 0) { Write-Err "Failed to switch kubectl context." }
Write-Success "kubectl context set."

# Wait for nodes
Write-Info "Waiting for nodes to become Ready..."
& kubectl wait --for=condition=Ready node --all --timeout=120s
if ($LASTEXITCODE -ne 0) { Write-Err "Nodes did not become Ready within 120s." }
Write-Success "All nodes are Ready."

# ==============================================================================
# 3. Install Traefik via Helm (idempotent)
# ==============================================================================
if (-not $SkipHelm) {
    $traefikRelease = & helm list -n $TraefikNamespace -o json 2>$null | ConvertFrom-Json
    $traefikExists = $traefikRelease | Where-Object { $_.name -eq "traefik" }

    if ($traefikExists) {
        Write-Warn "Traefik Helm release already exists - skipping install."
    }
    else {
        Write-Info "Adding Traefik Helm repository..."
        & helm repo add traefik https://traefik.github.io/charts 2>$null
        & helm repo update

        Write-Info "Installing Traefik..."
        # Create namespace idempotently
        & kubectl create namespace $TraefikNamespace --dry-run=client -o yaml | kubectl apply -f -

        & helm install traefik traefik/traefik `
            --namespace $TraefikNamespace `
            --set ports.web.port=8000 `
            --set ports.websecure.port=8443 `
            --set service.type=LoadBalancer `
            --set providers.kubernetesIngress.enabled=true `
            --set providers.kubernetesCRD.enabled=true `
            --set providers.kubernetesCRD.allowCrossNamespace=true `
            --set ingressRoute.dashboard.enabled=true `
            --set logs.general.level=INFO `
            --wait --timeout 120s

        if ($LASTEXITCODE -ne 0) { Write-Err "Failed to install Traefik." }
        Write-Success "Traefik installed."
    }
} # FIXED: Added this missing closing bracket for the SkipHelm block


# ==============================================================================
# 5. Apply Base Kubernetes Manifests
# ==============================================================================
if (-not $SkipManifests) {
    Write-Info "Applying base Kubernetes manifests from $K8sBaseDir..."

    $kustomizePath = Join-Path $K8sBaseDir "kustomization.yaml"
    if (Test-Path $kustomizePath) {
        & kubectl apply -k $K8sBaseDir
    }
    else {
        # Fallback: apply individual YAML files
        Get-ChildItem -Path $K8sBaseDir -Filter "*.yaml" | ForEach-Object {
            & kubectl apply -f $_.FullName
        }
    }

    if ($LASTEXITCODE -ne 0) { Write-Err "Failed to apply base manifests." }
    Write-Success "Base manifests applied."
}

# ==============================================================================
# 6. Label Worker Nodes
# ==============================================================================
Write-Info "Labelling worker nodes..."

$agentNodes = & kubectl get nodes -o json | ConvertFrom-Json
$agents = $agentNodes.items | Where-Object { $_.metadata.name -match "agent" }

foreach ($agent in $agents) {
    $nodeName = $agent.metadata.name
    & kubectl label node $nodeName "digitalq.io/role=workspace" --overwrite
    Write-Success "Labelled $nodeName with digitalq.io/role=workspace"
}

# ==============================================================================
# 7. Configure kubeconfig
# ==============================================================================
Write-Info "Verifying kubeconfig..."

$currentContext = & kubectl config current-context
if ($currentContext -eq "k3d-$ClusterName") {
    Write-Success "kubeconfig is correctly set to k3d-$ClusterName." # FIXED: Terminated string correctly
}
