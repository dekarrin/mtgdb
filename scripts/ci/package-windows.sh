#!/bin/bash

set -ex

mkdir -p "dist/$WINDOWS_RELEASE_NAME"
mv "builds/$WINDOWS_RELEASE_NAME.exe" "dist/$WINDOWS_RELEASE_NAME/mtgdb.exe"
cp -R common-assets/* "dist/$WINDOWS_RELEASE_NAME"
cd dist
echo "Archive Contents:"
ls -la $WINDOWS_RELEASE_NAME
zip "$WINDOWS_RELEASE_NAME.zip" "$WINDOWS_RELEASE_NAME"/* -j
cd ..
mv "dist/$WINDOWS_RELEASE_NAME.zip" archives/
