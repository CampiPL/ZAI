#!/usr/bin/env bash
# Install Docker Engine and Compose from Docker's official Ubuntu repository.
# Usage: sudo bash scripts/install-docker-ubuntu.sh "$(id -un)"
set -euo pipefail

if [[ ${EUID} -ne 0 ]]; then
  echo 'Uruchom przez sudo lub systemowe okno pkexec.' >&2
  exit 1
fi
target_user=${1:?Podaj nazwę użytkownika, który będzie uruchamiał Docker}
id "$target_user" >/dev/null
source /etc/os-release
[[ ${ID} == ubuntu ]] || { echo 'Ten skrypt obsługuje Ubuntu.' >&2; exit 1; }

apt-get update
apt-get install -y ca-certificates curl
install -m 0755 -d /etc/apt/keyrings
curl -fsSL https://download.docker.com/linux/ubuntu/gpg -o /etc/apt/keyrings/docker.asc
chmod a+r /etc/apt/keyrings/docker.asc
cat > /etc/apt/sources.list.d/docker.sources <<EOF
Types: deb
URIs: https://download.docker.com/linux/ubuntu
Suites: ${UBUNTU_CODENAME:-$VERSION_CODENAME}
Components: stable
Architectures: $(dpkg --print-architecture)
Signed-By: /etc/apt/keyrings/docker.asc
EOF
apt-get update
apt-get install -y docker-ce docker-ce-cli containerd.io docker-buildx-plugin docker-compose-plugin
systemctl enable --now docker
usermod -aG docker "$target_user"
docker version
docker compose version
echo 'Docker gotowy. Nowe terminale po ponownym zalogowaniu odziedziczą grupę docker.'
