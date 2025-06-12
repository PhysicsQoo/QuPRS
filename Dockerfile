# Copyright 2025 Wei-Jia Huang
#
# SPDX-License-Identifier: MIT

# Use the official Miniconda3 image as the base image
FROM continuumio/miniconda3

# Set the working directory inside the container
WORKDIR /app
COPY . .

# 1. Update Conda and upgrade Python in the base environment to version 3.12
# Combine conda update, Python upgrade, and pip installation in a single RUN command
# Clean up to reduce image size
RUN conda update -n base -c defaults conda --yes && \
    conda install -n base -c defaults python=3.12 pip --yes && \
    conda clean --all -f -y

# 2. Install required system libraries
RUN apt update && \
    apt install -y --no-install-recommends \
        libgmpxx4ldbl \
        libmpfr6 \
        libatomic1 && \
    rm -rf /var/lib/apt/lists/*

# 3. Install Python packages in the base environment
RUN pip install .[dev] && \
    # Remove pip cache to reduce image size
    rm -rf ~/.cache/pip && \
    rm -rf ./dist

# 4. Copy benchmark, test, and documentation files into the container
COPY ./benchmarks/Feymann /app/benchmarks/Feymann
COPY ./benchmarks/MQTBench /app/benchmarks/MQTBench
COPY ./test /app/test
COPY README.md /app/README.md
COPY LICENSE.md /app/LICENSE.md
COPY NOTICE.md /app/NOTICE.md

RUN conda run -n base pytest -n auto 

# 5. Set license information as a container label
LABEL org.opencontainers.image.licenses="MIT"



# 6. Set the default command to run when the container starts
CMD ["/bin/bash"]
