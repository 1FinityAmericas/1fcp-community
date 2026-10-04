#!/bin/sh
#########################################################################################################
# JFrog dependency downloader for raw-hosted repositories
#
# Usage:
#   sh get_dependencies.sh <version>
#
# Example:
#   sh get_dependencies.sh 7.5
#
# Downloads all `.tar`, `.tar.gz`, `.tgz` files under /cicada/<version>/...
#########################################################################################################
creds="automation:automation"

if [ "$#" -ne 1 ]; then
  echo "Usage: sh $0 <version>" >&2
  echo "Example: sh $0 7.5 | 7.6"
  exit 1
fi

VERSION="$1"

######################################### Configurable Section #########################################
# JFrog Base URL only
repo_base_url='https://artifactory.fnc.fujitsu.com/artifactory/raw-hosted'
component='rke2-installer'
release="/fcp/images/$VERSION/$component"
#########################################################################################################


#########################################################################################################
# Destination setup
#########################################################################################################
mkdir -p "apps/images" || { echo "Failed to create apps/images"; exit 1; }
cd "apps/images" || exit 1

echo "Fetching dependencies for: $VERSION"
echo "Repository: JFrog"
echo

#########################################################################################################
# Helper: Download files preserving folder structure
#########################################################################################################
download_file() {
  url="$1"
  rel_path=$(echo "$url" | sed -E "s#.*/$component/##")
  mkdir -p "$(dirname "$rel_path")"

  if [ -f "$rel_path" ]; then
    echo "Skipping (exists): $rel_path"
  else
    echo "Downloading: $rel_path"
    curl -u $creds -# -f -L -o "$rel_path" "$url" || echo "❌ Failed to download $url"
  fi
}

#########################################################################################################
# JFrog Recursive Listing
#########################################################################################################
ROOT_PATH="$repo_base_url$release"

fetch_recursive() {
  local base_url="$1"
  local depth="$2"
  [ "$depth" -gt 15 ] && return

  html=$(curl -u $creds -s -L "$base_url/")
  [ -z "$html" ] && return

  echo "$html" | grep -oE 'href="[^"]+"' | sed 's/href="//;s/"//' |
    grep -vE '^\.\./?$' | while read -r item; do
      full_url="$base_url/$item"

      if echo "$item" | grep -qE '/$'; then
        fetch_recursive "${full_url%/}" $((depth + 1))
      else
        if echo "$item" | grep -E -i '\.(tar|tar\.gz|tgz)$' >/dev/null 2>&1; then
          echo "$full_url"
        fi
      fi
    done
}

artifact_list=$(fetch_recursive "$ROOT_PATH" 1 | sort -u)

#########################################################################################################
# Download phase
#########################################################################################################

if [ -z "$artifact_list" ]; then
  echo "No tar/tgz artifacts found for version $VERSION"
  exit 1
fi

echo
echo "Found $(echo "$artifact_list" | wc -l) files to download..."
echo

for url in $artifact_list; do
  download_file "$url"
done

echo
echo "All downloads complete for version $VERSION."

