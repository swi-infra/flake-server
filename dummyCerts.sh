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
mkdir -p "$data_path/conf/live/ecdsa_flake"
mkdir -p "$data_path/conf/live/client-auth.httpbin.legato.io"
mkdir -p "$data_path/conf/live/https_certs"
rm -rf "$data_path/../mqtt/certs"
mkdir -p "$data_path/../mqtt/certs/live/mqtt_flake/"

openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 300 \
    -keyout $data_path/conf/live/$domain/privkey.pem \
    -out $data_path/conf/live/$domain/fullchain.pem \
    -subj "/CN=localhost"

openssl ecparam -out $data_path/conf/live/ecdsa_flake/privkey.pem -name secp256r1 -genkey
openssl req -new -key $data_path/conf/live/ecdsa_flake/privkey.pem -x509 -nodes -days 300 \
    -out $data_path/conf/live/ecdsa_flake/fullchain.pem \
    -subj "/CN=localhost"

openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 300 \
    -keyout $data_path/conf/live/client-auth.httpbin.legato.io/privkey.pem \
    -out $data_path/conf/live/client-auth.httpbin.legato.io/fullchain.pem \
    -subj "/CN=localhost"

openssl req -x509 -nodes -newkey rsa:$rsa_key_size -days 300 \
    -keyout $data_path/conf/live/https_certs/privkey.pem \
    -out $data_path/conf/live/https_certs/ca-chain.cert.pem \
    -subj "/CN=localhost"

openssl req -new -x509 -days 300 -extensions v3_ca \
    -keyout $data_path/../mqtt/certs/live/mqtt_flake/ca.key \
    -out $data_path/../mqtt/certs/live/mqtt_flake/ca.crt \
    -subj "/O=MQTT Broker/OU=MQTT Broker" -passout pass:"...."

openssl genrsa -out $data_path/../mqtt/certs/live/mqtt_flake/server.key 2048
openssl req -new -out $data_path/../mqtt/certs/live/mqtt_flake/server.csr \
    -key $data_path/../mqtt/certs/live/mqtt_flake/server.key \
    -subj "/O=MQTT Broker/OU=MQTT Broker/CN=localhost"
openssl x509 -req -in $data_path/../mqtt/certs/live/mqtt_flake/server.csr \
    -CA $data_path/../mqtt/certs/live/mqtt_flake/ca.crt \
    -CAkey $data_path/../mqtt/certs/live/mqtt_flake/ca.key -CAcreateserial \
    -out $data_path/../mqtt/certs/live/mqtt_flake/server.crt -days 300  -passin pass:"...."
openssl rsa -in $data_path/../mqtt/certs/live/mqtt_flake/server.key -out $data_path/../mqtt/certs/live/mqtt_flake/server.key

openssl genrsa -out $data_path/../mqtt/certs/live/mqtt_flake/client.key 2048
openssl req -new -out $data_path/../mqtt/certs/live/mqtt_flake/client.csr \
    -key $data_path/../mqtt/certs/live/mqtt_flake/client.key \
    -subj "/O=MQTT Client/OU=MQTT Client/CN=Thing01"
openssl x509 -req -in $data_path/../mqtt/certs/live/mqtt_flake/client.csr \
    -CA $data_path/../mqtt/certs/live/mqtt_flake/ca.crt \
    -CAkey $data_path/../mqtt/certs/live/mqtt_flake/ca.key -CAcreateserial \
    -out $data_path/../mqtt/certs/live/mqtt_flake/client.crt -days 300  -passin pass:"...."
openssl rsa -in $data_path/../mqtt/certs/live/mqtt_flake/client.key -out $data_path/../mqtt/certs/live/mqtt_flake/client.key

cp -r $data_path/../mqtt/certs/live/mqtt_flake/ $data_path/conf/live/

chown -R 1883:1883 $data_path/../mqtt/certs

exit
