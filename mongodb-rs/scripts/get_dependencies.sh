#!/bin/sh
#########################################################################################################
# Dependency downloader for raw-hosted repositories (Nexus or JFrog)
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
COMPONENT="mongodb-rs"

######################################### Configurable Section #########################################
# === Set your repository info here ===
# Nexus Example: http://nexus.fnc.fujitsu.com/nexus
# JFrog Example: https://artifactory.fnc.fujitsu.com/artifactory/raw-hosted
#repo_base_url='http://nexus.fnc.fujitsu.com/nexus'
repo_base_url='https://artifactory.fnc.fujitsu.com/artifactory/raw-hosted'
fcp_release="/fcp/images/$VERSION"
#########################################################################################################

# Detect repository type
if echo "$repo_base_url" | grep -qi "artifactory"; then
  repo_type='jfrog'
elif echo "$repo_base_url" | grep -qi "nexus"; then
  repo_type='nexus'
else
  echo "Unable to detect repository type from URL: $repo_base_url"
  exit 1
fi

# Destination
mkdir -p "apps/images" || exit 1
cd "apps/images" || exit 1

echo "Component : $COMPONENT"
echo "Version   : $VERSION"
echo "Repo Type : $repo_type"
echo

#########################################################################################################
download_file() {
  url="$1"
  rel_path=$(echo "$url" | sed -E "s#.*/$COMPONENT/#$COMPONENT/#")
  mkdir -p "$(dirname "$rel_path")"
  echo "Downloading: $rel_path"
  curl -# -f -L -o "$rel_path" "$url" || echo "❌ Failed: $url"
}
#########################################################################################################

if [ "$repo_type" = "jfrog" ]; then

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

else
  REPO="raw-hosted"
  API="$repo_base_url/service/rest/v1/assets?repository=$REPO"
  SEARCH="fcp/$VERSION/$COMPONENT"

  artifact_list=""
  token=""

  while :; do
    URL="$API"
    [ -n "$token" ] && URL="$URL&continuationToken=$token"

    resp=$(curl -s "$URL")

    urls=$(echo "$resp" | grep -oE '"downloadUrl" *: *"[^"]+"' \
           | awk -F '"' '{print $4}' | grep "$SEARCH")

    [ -n "$urls" ] && artifact_list="$artifact_list"$'\n'"$urls"

    token=$(echo "$resp" | grep -oE '"continuationToken" *: *"[^"]+"' \
            | awk -F '"' '{print $4}')

    [ "$token" = "null" ] || [ -z "$token" ] && break
  done

  artifact_list=$(echo "$artifact_list" | sed '/^\s*$/d' | sort -u)
fi

#########################################################################################################

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

