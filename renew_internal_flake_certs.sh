#!/bin/bash

if [ -z $1 ];
then
    echo "USAGE: $0 renew"
fi

data_path=$2
domains=$3

function renew {
    local tomorrows_date=$(date -d 1day "+%b-%e-%Y" | sed -e 's/ //g')
    local domain_cert_validity
    local service_status
 
    #downloading latest dummyCerts.sh
    curl http://cgit.central/tools/flake-server.git/plain/dummyCerts.sh?h=refs/heads/internal -o /tmp/dummyCerts.sh && chmod u+x /tmp/dummyCerts.sh

    for domain in ${domains[@]};
    do
        if [ -d $data_path/conf/live/$domain ];
        then
            domain_cert_validity=$(openssl x509 -enddate -noout -in "$data_path/conf/live/$domain/fullchain.pem" | cut -d "=" -f 2 | cut -d " " -f 1,2,4 | sed -e 's/ /-/g')
            if [ $tomorrows_date = $domain_cert_validity ];
            then
                service_status=$(systemctl status flake-filter.service)
                if grep -q 'Active: active' <<< $service_status;
                then
                    echo "Stopping services flake-service, flake-filter and mqtt"
                    systemctl stop flake-filter
                    systemctl stop flake-services
                    systemctl stop mqtt
                fi
                echo "Cleaning expired Certificates!!!..."

                rm -rf $data_path/conf/live
                /tmp/dummyCerts.sh $domain $data_path
            fi
        else
            echo "No certificates being found for domain: $domain on path $data_path"
        fi
    done
}

renew
