FROM nginx:latest

# Add dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    nginx-extras \
    iptables \
    iproute2 \
    build-essential \
    libglib2.0-0 \
    libsm6 \
    libxext6 \
    libxrender-dev \
    python3-dev \
    python3-setuptools \
    python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Add init script
ADD docker/10-flake-env.sh /docker-entrypoint.d/

# Add tools
ADD tools /tools/
RUN python3 -m pip install --no-cache-dir -r /tools/host/requirements.txt

# Add nginx conf * public
ADD nginx/conf/nginx.conf /etc/nginx/
ADD nginx/public/ /usr/share/nginx/public
RUN mkdir -p /usr/share/nginx/logs

EXPOSE 80/tcp \
       443/tcp \
       2000-2049/tcp \
       2100-2149/tcp \
       2200-2249/tcp \
       3000-3049/tcp \
       3100-3149/tcp \
       3200-3249/tcp \
       4000-4049/udp \
       4100-4149/udp \
       4200-4249/udp
