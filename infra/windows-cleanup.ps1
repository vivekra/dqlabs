# PowerShell Cleanup Script for DigitalQ Labs (Windows)
# ----------------------------------------------------------

param(
    [switch]$SkipDockerCompose,   
    [switch]$SkipK3d,            
    [switch]$UninstallPackages   
)

function Ask-YesNo($message) {
    $answer = Read-Host "$message [y/N]"
    return $answer -match '^(y|yes)$'
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " DigitalQ Labs - Windows Full Cleanup Script" -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan

# Fixed: Using single quotes ensures PowerShell treats the parentheses as a basic text string
$promptMessage = 'This will destroy all local resources (containers, k3d cluster, Helm releases). Proceed?'
if (-not (Ask-YesNo $promptMessage)) {
    Write-Host "Aborting cleanup." -ForegroundColor Yellow
    exit 0
}

# 1. Docker-Compose services
if (-not $SkipDockerCompose) {
    Write-Host "Stopping Docker-Compose services..." -ForegroundColor Green
    
    if (Test-Path "..\apps\web\docker-compose.yml") {
        docker-compose -f ..\apps\web\docker-compose.yml down -v
    }
    
    if (Test-Path "..\apps\orchestrator\docker-compose.yml") {
        docker-compose -f ..\apps\orchestrator\docker-compose.yml down -v
    }
    
    if (Test-Path "docker-compose.yml") {
        docker-compose -f docker-compose.yml down -v
    }
    
    docker network rm dqlabs_network 2>$null | Out-Null
}

# 2. Remove all Helm releases
Write-Host "Removing Helm releases..." -ForegroundColor Green
$releases = helm list -A -q 2>$null
if ($releases) {
    foreach ($rel in $releases) {
        $ns = (helm list -A | Where-Object { $_ -match $rel } | Select-Object -First 1).Split()
        Write-Host "Uninstalling $rel from namespace $ns" -ForegroundColor Magenta
        helm uninstall $rel -n $ns
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Failed to uninstall $rel" -ForegroundColor Yellow
        }
    }
}
else {
    Write-Host "No Helm releases found." -ForegroundColor Yellow
}

# 3. Delete k3d cluster
if (-not $SkipK3d) {
    if (Get-Command k3d -ErrorAction SilentlyContinue) {
        Write-Host "Deleting any existing k3d clusters..." -ForegroundColor Green
        k3d cluster list -o json | ConvertFrom-Json | ForEach-Object {
            $clusterName = $_.name
            Write-Host "Removing cluster $clusterName" -ForegroundColor Magenta
            k3d cluster delete $clusterName
            if ($LASTEXITCODE -ne 0) {
                Write-Host "Failed to delete $clusterName" -ForegroundColor Yellow
            }
        }
    }
    else {
        Write-Host "k3d is not installed - skipping cluster deletion." -ForegroundColor Yellow
    }
}

# 4. Prune Docker system
Write-Host "Pruning Docker system..." -ForegroundColor Green
docker system prune -a -f --volumes

# 5. Optional: Uninstall packages
if ($UninstallPackages) {
    Write-Host "Uninstalling Docker Desktop, k3d, and Helm..." -ForegroundColor Red
    if (Get-Command winget -ErrorAction SilentlyContinue) {
        winget uninstall "Docker Desktop" -e
        if ($LASTEXITCODE -ne 0) {
            Write-Host "Docker Desktop not found or already removed." -ForegroundColor Yellow
        }
    }
    if (Get-Command k3d -ErrorAction SilentlyContinue) {
        $k3dPath = (Get-Command k3d).Source
        Remove-Item $k3dPath -Force -ErrorAction SilentlyContinue
        Write-Host "k3d binary removed." -ForegroundColor Magenta
    }
    if (Get-Command helm -ErrorAction SilentlyContinue) {
        $helmPath = (Get-Command helm).Source
        Remove-Item $helmPath -Force -ErrorAction SilentlyContinue
        Write-Host "Helm binary removed." -ForegroundColor Magenta
    }
}

Write-Host "==========================================================" -ForegroundColor Cyan
Write-Host " Cleanup complete! Your Windows environment is now clean. " -ForegroundColor Cyan
Write-Host "==========================================================" -ForegroundColor Cyan
