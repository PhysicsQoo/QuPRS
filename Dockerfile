# Copyright 2025 Wei-Jia Huang
#
# SPDX-License-Identifier: MIT

# Use the official Miniconda3 image as the base
FROM continuumio/miniconda3

# Set the working directory
WORKDIR /app

# 1. Update Conda and upgrade Python in the base environment to 3.12
# Combine conda update, python upgrade, and pip installation in a single RUN command
# Leverage Docker cache and clean up to reduce image size
RUN conda update -n base -c defaults conda --yes && \
    conda install -n base -c defaults python=3.12 pip --yes && \
    conda clean --all -f -y

# 2. Install Python packages
# All packages are installed in the base environment
RUN pip install git+https://github.com/PhysicsQoo/QuPRS.git && \
    pip install tqdm psutil pytest pytest-xdist && \
    # Clean up pip cache to reduce image size
    rm -rf ~/.cache/pip && \
    rm -rf ./dist

# 3. Copy test, benchmarking, and documentation files
COPY ./benchmarks/Feymann /app/benchmarks/Feymann
COPY ./benchmarks/MQTBench /app/benchmarks/MQTBench
COPY ./test /app/test
COPY README.md /app/README.md
COPY LICENSE.md /app/LICENSE.md
COPY NOTICE.md /app/NOTICE.md

# 4. Set license information
LABEL org.opencontainers.image.licenses="MIT"

# 5. Set the default command when the container starts
CMD ["/bin/bash"]
