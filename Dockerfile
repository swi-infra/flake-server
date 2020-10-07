FROM nginx:1.19.1

# Set timezone
ENV TZ=Canada/Pacific

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
    git \
    tcpdump \
    cron \
    procps \
    python3-dev \
    python3-setuptools \
    ffmpeg \
    python3-pip && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Add init script
COPY docker/10-flake-env.sh /docker-entrypoint.d/

# Install python dependencies
COPY tools/host/requirements.txt /tools/host/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tools/host/requirements.txt

# Install custom iperf3
COPY tools/bin/get_iperf3.sh /tools/bin/get_iperf3.sh
RUN /tools/bin/get_iperf3.sh

# Add tools
COPY tools /tools/

# Add nginx conf * public
COPY nginx/conf/nginx.conf /etc/nginx/
COPY nginx/public/ /usr/share/nginx/public
RUN mkdir -p /usr/share/nginx/logs

EXPOSE 21/tcp \
       80/tcp \
       443/tcp \
       2000-2049/tcp \
       2100-2149/tcp \
       2200-2249/tcp \
       3000-3049/tcp \
       3100-3149/tcp \
       3200-3249/tcp \
       4000-4049/udp \
       4100-4149/udp \
       4200-4249/udp \
       5000-5049/tcp \
       5100-5149/tcp \
       5200-5249/tcp \
       5000-5049/udp \
       5100-5149/udp \
       5200-5249/udp \
       6000-6049/tcp \
       6100-6149/tcp \
       6200-6249/tcp \
       6000-6049/udp \
       6100-6149/udp \
       6200-6249/udp \
       6050-6099/tcp \
       6150-6199/tcp \
       6250-6299/tcp
