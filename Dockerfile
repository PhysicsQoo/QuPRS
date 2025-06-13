# Copyright 2025 Wei-Jia Huang
#
# SPDX-License-Identifier: MIT

# Use the official Miniconda3 image as the base image
FROM continuumio/miniconda3 AS builder

# Set the working directory inside the container
WORKDIR /app

# 1. Update Conda and upgrade Python to version 3.12 in the base environment
RUN conda update -n base -c defaults conda --yes && \
    conda install -n base -c defaults python=3.12 pip --yes && \
    conda clean --all -f -y

RUN pip install --upgrade pip setuptools wheel

# 2. Install required system libraries
RUN apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libgmpxx4ldbl \
        libmpfr6 \
        libatomic1 && \
    rm -rf /var/lib/apt/lists/*

# Copy Python project files and source code
COPY pyproject.toml MANIFEST.in ./
COPY ./src /app/src

ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}

# 3. Install Python dependencies (including development dependencies)
RUN pip install --no-build-isolation ".[dev]" && \
    rm -rf ~/.cache/pip

FROM builder AS tester

# 4. Copy benchmark, test, and documentation files into the container
COPY ./benchmarks /app/benchmarks
COPY ./test /app/test

# Run tests using pytest
RUN conda run -n base pytest -n auto 

FROM continuumio/miniconda3 AS final
WORKDIR /app

# Repeat environment setup for the final image
RUN conda update -n base -c defaults conda --yes && \
    conda install -n base -c defaults python=3.12 pip --yes && \
    conda clean --all -f -y && \
    apt-get update && \
    apt-get install -y --no-install-recommends \
        build-essential \
        libgmpxx4ldbl \
        libmpfr6 \
        libatomic1 && \
    rm -rf /var/lib/apt/lists/*

RUN pip install --upgrade pip setuptools wheel

COPY pyproject.toml MANIFEST.in ./
COPY ./src /app/src

ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}


# Install the package (without development dependencies)
RUN pip install . && \
    rm -rf ~/.cache/pip

# Copy documentation and license files
COPY README.md LICENSE.md NOTICE.md /app/

# 5. Set license information as a container label
LABEL org.opencontainers.image.licenses="MIT"

# 6. Set the default command to run when the container starts
CMD ["/bin/bash"]