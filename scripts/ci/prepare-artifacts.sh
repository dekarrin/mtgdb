#!/bin/bash

set -ex

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <os> <arch>"
    exit 1
fi

os="${1,,}"
arch="${2,,}"

v="$(cat ./version)"
echo "VERSION: $v"
release="mtgdb-$v-$os-$arch"
echo "RELEASE: $release"
mkdir "./dist/$release"
ls -la "./dist"
mv ./dist/mtgdb.exe "./dist/$release.exe"

# print out env vars
echo "BINARY_PATH=\"dist/$release.exe\"" >> "$GITHUB_ENV"
echo "${os^^}_RELEASE_NAME=\"$release\"" >> ./windows-build-info.txt
echo "${os^^}_ARTIFACT_NAME=\"$release.exe\"" >> ./windows-build-info.txt
cat ./windows-build-info.txt >> "$GITHUB_ENV"
