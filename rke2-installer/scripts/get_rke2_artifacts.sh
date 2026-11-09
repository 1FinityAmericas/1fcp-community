#!/bin/sh
#########################################################################################################
# RKE2 artifacts downloader script
#
# Usage:
#   sh get_rke2_artifacts.sh
#
# Downloads artifacts required for successful deployment of rke2
#########################################################################################################

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
DEP_HOSTS_FILE="$SCRIPT_DIR/../dep_hosts"

# Check if dep_hosts exists
if [ ! -f "$DEP_HOSTS_FILE" ]; then
  echo "Error: dep_hosts file not found at $DEP_HOSTS_FILE"
  exit 1
fi

# Extract RKE2 version from dep_hosts
RKE2_VERSION=$(grep "^rke2_server_ver=" "$DEP_HOSTS_FILE" | cut -d'=' -f2 | tr -d "'\"")

if [ -z "$RKE2_VERSION" ]; then
  echo "Error: Could not find rke2_server_ver in $DEP_HOSTS_FILE"
  exit 1
fi

######################################### Configurable Section #########################################
# Helm download URL
HELM_BASE_URL="https://get.helm.sh"
RKE2_RELEASES="https://github.com/rancher/rke2/releases/download"
RKE2_INSTALL_SH_BASE="https://raw.githubusercontent.com/rancher/rke2"

# Version variables - Update these as needed
HELM_VERSION="v3.15.1"
KUBEVIP_VERSION="v1.0.3"
AZURECLI_VERSION="2.89.0"

ARCH="amd64"
DEST_DIR="apps/images"

# Container images to pull and save as tar
# Format: image_name|dest_dir|output_file
CONTAINER_IMAGES=(
  "docker.io/plndr/kube-vip:${KUBEVIP_VERSION}|kube-vip|kube-vip-${KUBEVIP_VERSION}.tar"
  "mcr.microsoft.com/azure-cli:${AZURECLI_VERSION}|kube-vip|azure-cli-${AZURECLI_VERSION}.tar"
)

# RKE2 version directory name (remove 'v' prefix, replace '+' with '-', add 'rke2-' prefix)
RKE2_VERSION_DIR="rke2-$(echo "$RKE2_VERSION" | sed 's/^v//; s/+/-/g')"

# Helm artifact
HELM_ARTIFACT="helm-${HELM_VERSION}-linux-${ARCH}.tar.gz"

# RKE2 artifacts from GitHub
RKE2_ARTIFACTS=(
  "rke2-images-calico.linux-${ARCH}.tar.gz"
  "rke2-images-core.linux-${ARCH}.tar.gz"
  "rke2.linux-${ARCH}.tar.gz"
  "sha256sum-${ARCH}.txt"
)

FAILED_DOWNLOADS=""

#########################################################################################################
# Destination setup
#########################################################################################################
mkdir -p "$DEST_DIR" || { echo "Error: Failed to create $DEST_DIR"; exit 1; }
cd "$DEST_DIR" || exit 1

#########################################################################################################
# Helper: Download from raw URL
#########################################################################################################
download_raw() {
  local url="$1"
  local filename="$2"
  
  if [ -f "$filename" ]; then
    return 0
  else
    if curl -s -f -L -o "$filename" "$url"; then
      return 0
    else
      FAILED_DOWNLOADS="${FAILED_DOWNLOADS} ${filename}"
      return 1
    fi
  fi
}

#########################################################################################################
# Helper: Pull and save container image as tar
#########################################################################################################
pull_and_save_image() {
  local image="$1"
  local dest_dir="$2"
  local output_file="$3"
  
  mkdir -p "$dest_dir"
  
  if [ -f "$dest_dir/$output_file" ]; then
    return 0
  else
    if podman pull -q "$image" > /dev/null 2>&1; then
      if podman save -q -o "$dest_dir/$output_file" "$image" > /dev/null 2>&1; then
        podman rmi "$image" > /dev/null 2>&1
        return 0
      else
        FAILED_DOWNLOADS="${FAILED_DOWNLOADS} ${dest_dir}/${output_file}"
        podman rmi "$image" > /dev/null 2>&1
        return 1
      fi
    else
      FAILED_DOWNLOADS="${FAILED_DOWNLOADS} ${dest_dir}/${output_file}"
      return 1
    fi
  fi
}

#########################################################################################################
# Download phase - Helm from get.helm.sh
#########################################################################################################

echo "Downloading Helm..."
mkdir -p "helm"
download_raw "${HELM_BASE_URL}/${HELM_ARTIFACT}" "helm/${HELM_ARTIFACT}"

#########################################################################################################
# Download phase - Container images (kube-vip, azure-cli)
#########################################################################################################

echo "Downloading kube-vip and azure-cli images..."
for image_info in "${CONTAINER_IMAGES[@]}"; do
  IFS='|' read -r image_name dest_dir output_file <<< "$image_info"
  pull_and_save_image "$image_name" "$dest_dir" "$output_file"
done

#########################################################################################################
# Download phase - RKE2 artifacts from GitHub
#########################################################################################################

echo "Downloading RKE2 tars..."
for artifact in "${RKE2_ARTIFACTS[@]}"; do
  encoded_version=$(echo "$RKE2_VERSION" | sed 's/+/%2B/g')
  url="${RKE2_RELEASES}/${encoded_version}/${artifact}"

  if [ -f "$artifact" ]; then
    continue
  else
    if curl -s -f -L -o "$artifact" "$url"; then
      :
    else
      FAILED_DOWNLOADS="${FAILED_DOWNLOADS} ${artifact}"
    fi
  fi
done

#########################################################################################################
# Download install.sh from version-specific RKE2 source
#########################################################################################################

RKE2_INSTALL_SH_URL="${RKE2_INSTALL_SH_BASE}/${RKE2_VERSION}/install.sh"
download_raw "$RKE2_INSTALL_SH_URL" "install.sh"

#########################################################################################################
# Consolidate RKE2 artifacts into single tar under version directory
#########################################################################################################

if [ -z "$FAILED_DOWNLOADS" ]; then
  mkdir -p "$RKE2_VERSION_DIR/rke2-artifacts"
  cp "${RKE2_ARTIFACTS[@]}" "$RKE2_VERSION_DIR/rke2-artifacts/"
  cp "install.sh" "$RKE2_VERSION_DIR/rke2-artifacts/install.sh"
  tar -cf "$RKE2_VERSION_DIR/rke2-artifacts.tar" -C "$RKE2_VERSION_DIR" rke2-artifacts
  rm -rf "$RKE2_VERSION_DIR/rke2-artifacts"
  rm -f "${RKE2_ARTIFACTS[@]}"
  rm -f "install.sh"
  echo "Download complete"
else
  echo "Failed downloads:${FAILED_DOWNLOADS}"
fi
