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
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    libgmp-dev \
    libmpfr-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy Python project files and source code
# COPY pyproject.toml MANIFEST.in ./
# COPY ./src /app/src
COPY . .

RUN git submodule update --init --recursive

RUN pip install wheel && \
    pip wheel . --wheel-dir /wheels

# Set environment variables
ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}


FROM builder AS tester

# 4. Copy benchmark, test, and documentation files into the container
COPY ./benchmarks /app/benchmarks
COPY ./test /app/test

# Run tests using pytest
RUN pip install --no-index --find-links=/wheels "QuPRS[dev]"
RUN conda run -n base pytest -n auto 

FROM continuumio/miniconda3 AS final
WORKDIR /app

# Repeat environment setup for the final image
RUN conda update -n base -c defaults conda --yes && \
    conda install -n base -c defaults python=3.12 pip --yes && \
    conda clean --all -f -y && \
    apt-get update && apt-get install -y --no-install-recommends \
    libgmp10 \
    libmpfr6 \
    && rm -rf /var/lib/apt/lists/*



ARG SETUPTOOLS_SCM_PRETEND_VERSION
ENV SETUPTOOLS_SCM_PRETEND_VERSION=${SETUPTOOLS_SCM_PRETEND_VERSION}


# Install the package (without development dependencies)
COPY --from=builder /wheels /wheels

RUN pip install --no-index --find-links=/wheels QuPRS && \
    rm -rf /wheels ~/.cache/pip

# Copy documentation and license files
COPY README.md LICENSE.md NOTICE.md /app/

# 5. Set license information as a container label
LABEL org.opencontainers.image.licenses="MIT"

# 6. Set the default command to run when the container starts
CMD ["/bin/bash"]