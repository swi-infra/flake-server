# Download custom iperf3
git clone https://github.com/legatoproject/legato-3rdParty-iperf.git --branch master-swi
# Build iperf3
cd legato-3rdParty-iperf && ./configure --prefix=/usr && make && make check && make install; cd ..
# Remove sources
rm -rf legato-3rdParty-iperf
