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

# Some manylinux RPM development packages provide the headers and linker
# symlinks but no pkg-config descriptors. The native MPFR bridge's Rust
# build.rs uses pkg-config to discover them, so create *only missing* site-
# local descriptors after checking the RPM owner and actual system files.
# Do not synthesize a successful probe for missing libraries or override
# an existing descriptor. Debian/Alpine retain their normal package metadata.
if command -v rpm >/dev/null 2>&1; then
    for dep in gmp mpfr; do
        if ! pkg-config --exists "$dep"; then
            if ! rpm -q "${dep}-devel" >/dev/null 2>&1 \
                || [ ! -f "/usr/include/${dep}.h" ] \
                || [ ! -f "/usr/lib64/lib${dep}.so" ]; then
                echo "Error: ${dep} pkg-config metadata and verified RPM headers/libs unavailable."
                exit 1
            fi
            pc_dir=/usr/local/lib/pkgconfig
            mkdir -p "$pc_dir"
            version=$(rpm -q --queryformat '%{VERSION}' "${dep}-devel")
            # Keep the descriptor scoped to the already-installed system RPM.
            # QuPRS pathsum/build.rs separately probes GMP and MPFR.
            cat > "$pc_dir/${dep}.pc" <<EOF
prefix=/usr
exec_prefix=\${prefix}
libdir=/usr/lib64
includedir=/usr/include
Name: ${dep}
Description: ${dep} headers and library installed by system RPM
Version: ${version}
Libs: -L\${libdir} -l${dep}
Cflags: -I\${includedir}
EOF
            echo "Created missing RPM metadata: $pc_dir/${dep}.pc"
        fi
        pkg-config --exists "$dep" || {
            echo "Error: ${dep} metadata still unresolved after installation."
            exit 1
        }
        pkg-config --libs --cflags "$dep"
    done
fi

echo "Successfully installed all system dependencies."