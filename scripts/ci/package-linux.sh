#!/bin/bash

set -ex

mkdir -p "dist/$LINUX_RELEASE_NAME"
mv "builds/$LINUX_RELEASE_NAME" "dist/$LINUX_RELEASE_NAME/mtgdb"
cp -R common-assets/* "dist/$LINUX_RELEASE_NAME"
cd "dist/$LINUX_RELEASE_NAME"
echo "Archive Contents:"
ls -la
tar czf "../$LINUX_RELEASE_NAME.tar.gz" ./*
cd ../..
mv "dist/$LINUX_RELEASE_NAME.tar.gz" archives/
