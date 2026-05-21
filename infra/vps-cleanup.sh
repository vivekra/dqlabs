#!/bin/bash
set -e

echo "=========================================================="
echo " DigitalQ Labs — VPS Full Cleanup Script"
echo "=========================================================="
echo "WARNING: This will destroy your K3s cluster, wipe all PVC"
echo "storage, and tear down the FastAPI & Paymenter containers!"
echo ""
read -p "Are you sure you want to proceed? (y/N): " confirm
if [[ $confirm != [yY] && $confirm != [yY][eE][sS] ]]; then
    echo "Aborting cleanup."
    exit 1
fi

echo ""
echo "1. Tearing down Docker Compose services..."
if [ -f "docker-compose.prod.yml" ]; then
    docker-compose -f docker-compose.prod.yml down -v || echo "Docker-compose down failed, continuing..."
else
    echo "No docker-compose.prod.yml found in current directory. Skipping."
fi

echo "2. Uninstalling K3s cluster and wiping data..."
if [ -f "/usr/local/bin/k3s-uninstall.sh" ]; then
    /usr/local/bin/k3s-uninstall.sh
else
    echo "K3s uninstaller not found. It may already be removed."
fi

echo "3. Removing dangling Docker volumes and networks..."
docker system prune -a -f --volumes

echo "4. (Optional) Uninstalling system packages..."
read -p "Do you also want to UNINSTALL Docker, Helm, jq, and curl from this VPS? (y/N): " pkg_confirm
if [[ $pkg_confirm == [yY] || $pkg_confirm == [yY][eE][sS] ]]; then
    sudo apt-get purge -y docker.io docker-buildx-plugin docker-compose-plugin jq
    sudo apt-get autoremove -y
    sudo rm -rf /usr/local/bin/helm
    echo "Packages removed."
else
    echo "Packages retained."
fi

echo ""
echo "=========================================================="
echo "Cleanup complete! The VPS is now clean."
echo "=========================================================="
