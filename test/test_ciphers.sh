#!/usr/bin/env bash

CIPHERS=$(cat <<-END
  ECDHE-RSA-AES128-GCM-SHA256
  ECDHE-ECDSA-AES128-CCM
  ECDHE-ECDSA-AES256-CCM
  ECDHE-ECDSA-AES128-CCM8
  ECDHE-ECDSA-AES256-CCM8
  ECDHE-ECDSA-AES128-GCM-SHA256
  ECDHE-ECDSA-AES256-GCM-SHA384
END
)
CIPHERS=$(echo $CIPHERS)

DELAY=${3:-0.1}
SERVER=${1:?usage: $0 <host:port> [ciphers, default is ${CIPHERS} if all then it will be obtained from openssl] [delay, default is ${DELAY}s]}
if [[ $2 == "all" ]]; then
  CIPHERS=$(openssl ciphers 'ALL:eNULL' | sed -e 's/:/ /g')
fi
MAXLEN=$(openssl ciphers "$CIPHERS" | sed -e 's/:/\n/g' | awk '{ if ( length > L ) { L=length} }END{ print L}')

echo Using $(openssl version).

declare -A TLSMAP=( [tls1_1]=cipher [tls1_2]=cipher)

for tlsver in "${!TLSMAP[@]}"
do
  echo "Using $tlsver"
  ciphers=$(openssl ciphers -$tlsver -s "$CIPHERS" | sed -e 's/:/ /g')
  for cipher in ${ciphers[@]}
  do
    in=$(openssl s_client -$tlsver -${TLSMAP[$tlsver]} "$cipher" -connect $SERVER </dev/null 2>&1)
    if [[ "$in" =~ ":error:" ]] ; then
      result="NO ($(echo -n $in | cut -d':' -f6))"
    else
      if [[ "$in" =~ "Cipher is ${cipher}" || "$in" =~ "Cipher    :" ]] ; then
        result='YES'
      else
        result="UNKNOWN RESPONSE\n$in"
      fi
    fi
    printf 'Testing %-*s ... %s\n' "$MAXLEN" "$cipher" "$result"
    sleep $DELAY
  done
done
