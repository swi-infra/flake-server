#!/bin/bash

source /tools/bin/flake_env

# Build iperf3
cd /legato-3rdParty-iperf && ./configure && make && make check && make install; cd /

server configure
