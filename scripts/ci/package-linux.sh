#!/bin/bash

set -ex

echo wd: $(pwd)

mkdir -p "dist/$LINUX_RELEASE_NAME"
echo "DEBUG Archive Pre Move Contents"
ls -la "dist/$LINUX_RELEASE_NAME"
echo 'DEBUG "file builds/$LINUX_RELEASE_NAME"'
file "builds/$LINUX_RELEASE_NAME"
echo 'DEBUG "file dist/$LINUX_RELEASE_NAME/mtgdb"'
file "dist/$LINUX_RELEASE_NAME/mtgdb" || echo "File Not Found; Expected"
mv "builds/$LINUX_RELEASE_NAME" "dist/$LINUX_RELEASE_NAME/mtgdb"
echo "Archive Contents IMMEDIATE MOVE:"
ls -la "dist/$LINUX_RELEASE_NAME"
echo 'DEBUG "file dist/$LINUX_RELEASE_NAME/mtgdb"'
file "dist/$LINUX_RELEASE_NAME/mtgdb"
cp -R common-assets/* "dist/$LINUX_RELEASE_NAME"
cd "dist/$LINUX_RELEASE_NAME"
echo "Archive Contents:"
ls -la
tar czf "../$LINUX_RELEASE_NAME.tar.gz" ./*
cd ../..
mv "dist/$LINUX_RELEASE_NAME.tar.gz" archives/