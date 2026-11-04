FROM ubuntu:24.04
ARG DEBIAN_FRONTEND=noninteractive
RUN apt-get update -qq \
    && apt-get install -y --no-install-recommends \
       python3-minimal libgmp10 libmpfr6 libstdc++6 ca-certificates \
    && rm -rf /var/lib/apt/lists/*
COPY driver.py /opt/qoo156/driver.py
ENV PYTHONDONTWRITEBYTECODE=1
USER 65534:65534
ENTRYPOINT ["python3", "/opt/qoo156/driver.py"]
