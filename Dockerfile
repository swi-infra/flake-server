FROM nginx:1.22.1-bullseye

ARG DEV_BUILD
RUN if [ "${DEV_BUILD}" = "1" ]; then echo "Building in dev mode..."; fi

# Set timezone
ENV TZ=Canada/Pacific

# Add dependencies
RUN apt-get update && \
    apt-get install --no-install-recommends -y \
    nginx-extras \
    logrotate \
    gzip \
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
    apt-get install --upgrade -y openssl --no-install-recommends && \
    apt-get clean && \
    rm -rf /var/lib/apt/lists/*

# Add init script
COPY docker/10-flake-env.sh /docker-entrypoint.d/

# Install python dependencies
RUN python3 -m pip install --upgrade pip
COPY tools/host/requirements.txt /tools/host/requirements.txt
RUN python3 -m pip install --no-cache-dir -r /tools/host/requirements.txt

# Install custom iperf3
COPY tools/bin/get_iperf3.sh /tools/bin/get_iperf3.sh
RUN /tools/bin/get_iperf3.sh

# Add tools
COPY tools /tools/

# Add nginx conf * public
COPY nginx/conf/nginx.conf /etc/nginx/
COPY nginx/conf/nginx_logrotate.conf /etc/logrotate.d/nginx
COPY nginx/public/ /usr/share/nginx/public
RUN mkdir -p /usr/share/nginx/logs
RUN if [ "${DEV_BUILD}" = "1" ]; then \
    sed -i "s/proxy_pass http:\/\/httpbin:80;/set $upstream http:\/\/httpbin:80;\nproxy_pass $upstream;/g" /etc/nginx/nginx.conf; \
fi

EXPOSE 21/tcp \
       80/tcp \
       443/tcp \
       8443/tcp \
       1883-1884/tcp \
       8883-8884/tcp \
       6300-6301/tcp \
       2000-2003/tcp \
       2100-2103/tcp \
       2200-2203/tcp \
       3000-3003/tcp \
       3100-3103/tcp \
       3200-3203/tcp \
       4000-4003/udp \
       4100-4103/udp \
       4200-4203/udp \
       5000-5299/tcp \
       5000-5299/udp \
       6000-6003/tcp \
       6100-6103/tcp \
       6200-6203/tcp \
       6000-6003/udp \
       6100-6103/udp \
       6200-6203/udp \
       6050-6053/tcp \
       6150-6153/tcp \
       6250-6253/tcp \
       6060-6063/tcp \
       6160-6163/tcp \
       6260-6263/tcp \
       6070-6073/tcp \
       6170-6173/tcp \
       6270-6273/tcp \
       6080-6083/tcp \
       6180-6183/tcp \
       6280-6283/tcp \
       7000-7003/udp \
       7100-7103/udp \
       7200-7203/udp \
       7050-7053/udp \
       7150-7153/udp \
       7250-7253/udp
