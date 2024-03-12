#!/bin/bash

set -e

rm -rf /var/lib/apt/lists/*
sed -i 's/archive.ubuntu.com/ftp.daum.net/g' /etc/apt/sources.list
apt-get update -y