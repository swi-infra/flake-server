#!/bin/bash
set -x

domain=${DOMAIN:-"flake.legato.io"}
data_path=${DATA_PATH:-"./certs"}

# create dummy certs to allow nginx to start

rsa_key_size=4096
if [ ! -e "$data_path/conf/options-ssl-nginx.conf" ] || [ ! -e "$data_path/conf/ssl-dhparams.pem" ]; then
    echo "### Downloading recommended TLS parameters ..."
    mkdir -p "${data_path}/conf"
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot-nginx/certbot_nginx/_internal/tls_configs/options-ssl-nginx.conf > "$data_path/conf/options-ssl-nginx.conf"
    curl -s https://raw.githubusercontent.com/certbot/certbot/master/certbot/certbot/ssl-dhparams.pem > "$data_path/conf/ssl-dhparams.pem"
    echo
fi

if [ -d "${data_path}/conf/live" ]; then
    echo "Found real cert data, exiting"
    exit
fi

echo "Creating dummy certificate for $domain..."
mkdir -p "$data_path/conf/live/$domain"

openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 300 \
    -keyout $data_path/conf/live/$domain/privkey.pem \
    -out $data_path/conf/live/$domain/fullchain.pem \
    -subj "/CN=localhost"

exit
