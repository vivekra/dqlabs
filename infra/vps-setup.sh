#!/bin/bash
set -e

# Configuration
INGRESS_DOMAIN=${INGRESS_DOMAIN:-"127.0.0.1.nip.io"}

echo "Setting up VPS for DigitalQ Labs..."
echo "INGRESS_DOMAIN is set to $INGRESS_DOMAIN"

# Update and install dependencies
sudo apt-get update
sudo apt-get install -y docker.io docker-buildx-plugin docker-compose-plugin curl jq

# Create the shared external network for modular docker-compose files
echo "Creating dqlabs_network..."
sudo docker network create dqlabs_network || echo "dqlabs_network already exists."


# Install K3s (disabling default traefik to install it via helm)
echo "Installing K3s..."
curl -sfL https://get.k3s.io | INSTALL_K3S_EXEC="--disable traefik" sh -

# Wait for k3s to be ready
echo "Waiting for k3s to be ready..."
sleep 15
sudo chmod 644 /etc/rancher/k3s/k3s.yaml

# Install Helm
echo "Installing Helm..."
curl -fsSL -o get_helm.sh https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3
chmod 700 get_helm.sh
./get_helm.sh
rm get_helm.sh

export KUBECONFIG=/etc/rancher/k3s/k3s.yaml

# Install Traefik via Helm
echo "Installing Traefik..."
helm repo add traefik https://helm.traefik.io/traefik
helm repo update
helm install traefik traefik/traefik -n kube-system

echo "VPS setup complete!"
echo "Please configure your DNS to point $INGRESS_DOMAIN to this server's IP address."
