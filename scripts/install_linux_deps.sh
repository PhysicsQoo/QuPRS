#!/bin/sh
set -e

echo "Detailed system info:"
cat /etc/os-release || true
uname -a || true

if command -v yum >/dev/null 2>&1; then
    echo "Using yum..."
    yum install -y gmp-devel mpfr-devel zlib-devel
elif command -v dnf >/dev/null 2>&1; then
    echo "Using dnf..."
    dnf install -y gmp-devel mpfr-devel zlib-devel
elif command -v microdnf >/dev/null 2>&1; then
    echo "Using microdnf..."
    microdnf install -y gmp-devel mpfr-devel zlib-devel
elif command -v apk >/dev/null 2>&1; then
    echo "Using apk..."
    apk add gmp-dev mpfr-dev zlib-dev
elif command -v apt-get >/dev/null 2>&1; then
    echo "Using apt-get..."
    apt-get update
    apt-get install -y libgmp-dev libmpfr-dev zlib1g-dev
else
    echo "Could not find a supported package manager (yum, dnf, microdnf, apk, apt-get)."
    echo "Listing /bin and /usr/bin:"
    ls /bin /usr/bin
    exit 1
fi
