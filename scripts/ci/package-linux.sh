#!/bin/bash

set -ex

mkdir -p "dist/$LINUX_RELEASE_NAME"
mv "builds/$LINUX_RELEASE_NAME" "dist/$LINUX_RELEASE_NAME/mtgdb"
cp -R common-assets/* "dist/$LINUX_RELEASE_NAME"
cd dist
echo "Archive Contents:"
ls -la "$LINUX_RELEASE_NAME"
tar czvf "$LINUX_RELEASE_NAME.tar.gz" -C "$LINUX_RELEASE_NAME" .
cd ..
mv "dist/$LINUX_RELEASE_NAME.tar.gz" archives/
