# Copyright 2025 Wei-Jia Huang
# SPDX-License-Identifier: MIT

# =================================================================
# Planner Stage: Prepare Rust dependency cache for cargo-chef
# =================================================================
FROM python:3.12-slim AS planner
WORKDIR /app

# Install rustup, cargo-chef, and required certificates
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl ca-certificates build-essential\
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install cargo-chef

COPY . .
WORKDIR /app/rust
RUN cargo chef prepare --recipe-path /app/recipe.json

# =================================================================
# Builder Stage: Build the Python wheel
# =================================================================
FROM python:3.12-slim AS builder
WORKDIR /app

# Install build dependencies, C headers, and Rust toolchain
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential git cmake libgmp-dev libmpfr-dev zlib1g-dev curl ca-certificates \
    pkg-config libssl-dev \
    && rm -rf /var/lib/apt/lists/* \
    && curl --proto '=https' --tlsv1.2 -sSf https://sh.rustup.rs | sh -s -- -y
ENV PATH="/root/.cargo/bin:${PATH}"
RUN cargo install cargo-chef

# Utilize Docker layer caching to build Rust dependencies
COPY --from=planner /app/recipe.json /app/recipe.json

WORKDIR /app/rust
RUN cargo chef cook --release --recipe-path /app/recipe.json

WORKDIR /app
# Copy the rest of the source code and initialize git submodules
COPY . .
RUN git submodule update --init --recursive

ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}

# Build the Release wheel for the project (excluding dev dependencies)
RUN pip install --no-cache-dir maturin && \
    maturin build --release --out /wheels

# =================================================================
# Tester Stage: Verify the build in a clean runtime environment
# =================================================================
FROM python:3.12-slim AS tester
WORKDIR /app

# Install ONLY the required runtime system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    zlib1g libssl3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Copy built wheels and test files from the builder stage
COPY --from=builder /wheels /wheels
COPY . /app

# Install the built wheel along with development dependencies for testing
RUN pip install --no-cache-dir --find-links=/wheels "QuPRS[dev]"
RUN pytest /app/test -n auto

# =================================================================
# Final Stage: Minimal production-ready image
# =================================================================
FROM python:3.12-slim AS final
WORKDIR /app

# Install ONLY the required runtime system libraries
RUN apt-get update && apt-get install -y --no-install-recommends \
    zlib1g libssl3 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
    
ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}

# Install the package (without development dependencies)
COPY --from=builder /wheels /wheels
RUN pip install --no-cache-dir --find-links=/wheels QuPRS && \
    rm -rf /wheels

# Copy documentation and license files
COPY README.md LICENSE.md NOTICE.md /app/

# Set license information as a container label
LABEL org.opencontainers.image.licenses="MIT"

# Set the default command to run when the container starts
CMD ["/bin/bash"]