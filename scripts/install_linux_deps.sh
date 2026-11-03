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

# AlmaLinux/RHEL 8 (including some manylinux_2_28 aarch64 images) ships
# gmp-devel and mpfr-devel with headers and link libraries, but without
# their corresponding pkg-config .pc files. The Rust MPFR bridge requires
# both pkg-config probes to succeed. Create metadata ONLY for verified RPM
# development packages when the upstream .pc is genuinely unavailable.
# No library or solver source is replaced.
if command -v rpm >/dev/null 2>&1; then
    for name in gmp mpfr; do
        if ! pkg-config --exists "$name"; then
            header="/usr/include/$name.h"
            library="/usr/lib64/lib$name.so"
            if [ ! -f "$header" ] || [ ! -f "$library" ]; then
                echo "Missing $name headers or link library; cannot generate pkg-config metadata" >&2
                exit 1
            fi
            version="$(rpm -q --queryformat '%{VERSION}' "$name-devel")"
            install -d /usr/local/lib/pkgconfig
            cat > "/usr/local/lib/pkgconfig/$name.pc" <<EOF
prefix=/usr
exec_prefix=\${prefix}
libdir=/usr/lib64
includedir=/usr/include
Name: $name
Description: $name development library installed via RPM
Version: $version
Libs: -L\${libdir} -l$name
Cflags: -I\${includedir}
EOF
            echo "Generated missing RPM-based pkg-config metadata for $name ($version)"
        fi
        pkg-config --exists "$name"
    done
fi

echo "Successfully installed all system dependencies."