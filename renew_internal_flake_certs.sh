#!/bin/bash

set -xe

if [ -z $1 ];
then
    echo "USAGE: $0 renew"
fi

data_path=$2
domains=$3

function renew {
    local todays_date=$(date "+%b-%e-%Y" | sed -e 's/ //g')
    local domain_cert_validity

    if [ -d $data_path/conf/live/$domain ];
    then
        domain_cert_validity=$(openssl x509 -enddate -noout -in "$data_path/conf/live/$domain/fullchain.pem" | cut -d "=" -f 2 | cut -d " " -f 1,3,5 | sed -e 's/ /-/g')
        if [ $todays_date \> $domain_cert_validity ];
        then
            echo "Cleaning expired Certificates!!!..."
            rm -rf $data_path/conf/live
            $data_path/dummyCerts.sh $domain $data_path
        fi
    fi
}

