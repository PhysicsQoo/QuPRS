FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
       python3 libgmp10 libgmpxx4ldbl libmpfr6 libstdc++6 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
ENTRYPOINT ["/usr/bin/python3"]
