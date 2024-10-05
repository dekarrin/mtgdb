#!/bin/bash

set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <os> <arch>"
    exit 1
fi

os="${1,,}"
arch="${2,,}"

ext=""
if [ "$os" == "windows" ]; then
    ext=".exe"
fi

v="$(cat ./version)"
release="mtgdb-$v-$os-$arch"
echo "RELEASE: $release"
echo "Available dists:"
ls -la ./dist
mv "./dist/mtgdb$ext" "./dist/$release$ext"

# print out env vars
echo "BINARY_PATH=dist/$release$ext" >> "$GITHUB_ENV"
echo "${os^^}_RELEASE_NAME=$release" >> ./$os-build-info.txt
echo "${os^^}_ARTIFACT_NAME=$release$ext" >> ./$os-build-info.txt
cat ./$os-build-info.txt >> "$GITHUB_ENV"
