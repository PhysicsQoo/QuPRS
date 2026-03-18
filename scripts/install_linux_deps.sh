#!/bin/sh
# Exit immediately if a command exits with a non-zero status
set -e

echo "Starting system dependency installation..."
echo "System information:"
cat /etc/os-release || true
uname -a || true

# Determine the package manager and install dependencies
if command -v yum >/dev/null 2>&1; then
    echo "Using yum (RHEL/CentOS/manylinux)..."
    yum install -y gmp-devel mpfr-devel zlib-devel openssl-devel cmake pkgconfig
elif command -v dnf >/dev/null 2>&1; then
    echo "Using dnf (Fedora/AlmaLinux)..."
    dnf install -y gmp-devel mpfr-devel zlib-devel openssl-devel cmake pkgconf
elif command -v microdnf >/dev/null 2>&1; then
    echo "Using microdnf (Oracle Linux/minimal images)..."
    microdnf install -y gmp-devel mpfr-devel zlib-devel openssl-devel cmake pkgconfig
elif command -v apk >/dev/null 2>&1; then
    echo "Using apk (Alpine Linux/musllinux)..."
    apk add gmp-dev mpfr-dev zlib-dev openssl-dev cmake pkgconf
elif command -v apt-get >/dev/null 2>&1; then
    echo "Using apt-get (Debian/Ubuntu)..."
    apt-get update
    apt-get install -y libgmp-dev libmpfr-dev zlib1g-dev libssl-dev cmake pkg-config
else
    echo "Error: Could not find a supported package manager (yum, dnf, microdnf, apk, apt-get)."
    exit 1
fi

echo "Successfully installed all system dependencies."