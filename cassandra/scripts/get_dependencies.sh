#!/bin/sh
#########################################################################################################
# Dependency downloader for raw-hosted repositories (JFrog)
#
# Usage:
#   sh scripts/get_dependencies.sh <version>
#
# Example:
#   sh scripts/get_dependencies.sh 2.0
#########################################################################################################

if [ "$#" -ne 1 ]; then
  echo "Usage: sh $0 <version>" >&2
  exit 1
fi

VERSION="$1"
COMPONENT="cassandra"

######################################### Configurable Section #########################################
repo_base_url='https://artifactory.fnc.fujitsu.com/artifactory/raw-hosted'
fcp_release="/fcp/images/$VERSION"

#########################################################################################################

mkdir -p "apps/images" || exit 1
cd "apps/images" || exit 1

echo "Component : $COMPONENT"
echo "Version   : $VERSION"
echo "Repo Type : $repo_type"
echo

#########################################################################################################
# Helper: Download preserving directory structure below fcp/<version>/<component>/
#########################################################################################################
download_file() {
  url="$1"
  rel_path=$(echo "$url" | sed -E "s#.*/$COMPONENT/#$COMPONENT/#")
  mkdir -p "$(dirname "$rel_path")"
  echo "Downloading: $rel_path"
  curl -# -f -L -o "$rel_path" "$url" || echo "❌ Failed: $url"
}

#########################################################################################################
# JFrog (HTML folder crawl)
#########################################################################################################
ROOT="$repo_base_url$fcp_release/$COMPONENT"

fetch_recursive() {
  local base="$1"
  local depth="$2"

  [ "$depth" -gt 15 ] && return

  html=$(curl -s -L "$base/")
  [ -z "$html" ] && return

  echo "$html" | grep -oE 'href="[^"]+"' | sed 's/href="//;s/"//' \
    | grep -vE '^\.\./?$' | while read -r item; do
        full="$base/$item"
        if echo "$item" | grep -qE '/$'; then
          fetch_recursive "${full%/}" $((depth + 1))
        else
          echo "$full"
        fi
      done
}
artifact_list=$(fetch_recursive "$ROOT" 1 | sort -u)

if [ -z "$artifact_list" ]; then
  echo "No artifacts found under fcp/$VERSION/$COMPONENT"
  exit 1
fi

echo "Found $(echo "$artifact_list" | wc -l) files"
echo

for url in $artifact_list; do
  download_file "$url"
done

echo
echo "Download complete."

