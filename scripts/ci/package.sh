#!/bin/bash

set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <os> <arch> <release-name>"
    exit 1
fi

os="${1,,}"
arch="${2,,}"
release="$3"

ext=""
if [ "$os" == "windows" ]; then
    ext=".exe"
fi

echo "Packaging mtgdb$ext for $os/$arch..."

binary_src="$release$ext"
binary_dest="mtgdb$ext"

mkdir -p "dist/$release"
mv "builds/$binary_src" "dist/$release/$binary_dest"
cp -R common-assets/* "dist/$LINUX_RELEASE_NAME"
cd "dist/$LINUX_RELEASE_NAME"
echo "Archive Contents:"
ls -la
tar czf "../$LINUX_RELEASE_NAME.tar.gz" ./*
cd ../..
mv "dist/$LINUX_RELEASE_NAME.tar.gz" archives/