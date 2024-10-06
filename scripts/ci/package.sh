#!/bin/bash

set -e

if [ "$#" -ne 2 ]; then
    echo "Usage: $0 <os> <release-name>"
    exit 1
fi

os="${1,,}"
release="$2"

ext=""
if [ "$os" == "windows" ]; then
    ext=".exe"
fi

archive_name=""
if [ "$os" == "linux" ]; then
    archive_name="$release.tar.gz"
elif [ "$os" == "windows" ]; then
    archive_name="$release.zip"
else
    echo "Unsupported OS: $os"
    exit 1
fi

function create_archive_linux() {
    tar czvf "$archive_name" -C "$release" .
}

function create_archive_windows() {
    zip "$archive_name" "$release"/* -j
}

function create_archive() {
    if [ "$os" == "linux" ]; then
        create_archive_linux
    elif [ "$os" == "windows" ]; then
        create_archive_windows
    else
        echo "Unsupported OS: $os"
        exit 1
    fi
}

binary_src="$release$ext"
binary_dest="mtgdb$ext"

echo "Packaging mtgdb$ext for $os..."

mkdir -p "dist/$release"
mv "builds/$binary_src" "dist/$release/$binary_dest"
cp -R common-assets/* "dist/$release"
cd dist
echo "Archive Contents:"
ls -la "$release"
create_archive
cd ..
mv "dist/$archive_name" archives/
