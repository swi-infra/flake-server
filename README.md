# Flake Legato

Flake is a testing server with the purpose of emulating poor network conditions.
It relies on software to emulate poor network conditions, by introducing delays and loss of packets in the link between a client (DUT) and the services it provides (HTTP/HTTPS/UDP/iperf).

## Concept

Flake comes with a set of services:

- _HTTP/HTTPS file server_: simple file server that provide files of different types (audio, video, text, ...)
- _HTTP/HTTPS httpbin.org_: an instance of <https://httpbin.org/> , which is a simple REST service
- _iperf3_: instances of the famous bandwidth measurement tool
- _TCP/UDP echo server_: server that sends back to the client any received data

Each service is exposed over multiple ports, with each port emulating a different condition.

_Example_:

- https, 0ms delay, 5% packet loss, binary file, 30MB
  <https://flake.legato.io:3006/binary/data_30MB.bin>
- http, 200ms delay, 0.5% packet loss, video file, 15MB
  <http://flake.legato.io:2202/video/data_15MB.avi>
- udp, 100ms delay, 2.5% packet loss, audio file, 10MB
  flake.legato.io:4105
  udp packet data:
  `audio/data_10MB.wav`
- iperf, 100ms delay, 2.5% packet loss
  `iperf -c flake.legato.io -p 5105`

## Emulated conditions

### Packet loss

Packet loss is seen when one or more packets fail to reach their destination.
By introducing packet loss to a network test, we can see how the product responds to it.
Packet loss can produce network disruptions and losses of connectivity.
It is important to test these situations to ensure that if a given product is on a poor network it is still able to have successful communication.

### Packet delay

Packet delay is the amount of time that the packet is held up before routing to the destination.
Packet delay is naturally introduced in processing delay, which occures when the packet is being routed through the network layers and when routing to and from the user through the network.
Using Flake Legato we can emulate extended packet delay to see how a product reacts to it.
Packet delay can produce network disruptions and connectivity losses.

It is important to test these situations to ensure that if a given product is on a poor network it is still able to have successful communication.

## Deploy

### Getting started

To get a local dev environment:

- Install `docker-compose` (<https://docs.docker.com/compose/>)
- Run

  ```sh
  ./dummyCerts.sh
  sudo docker build -t root/nginx-xtra . --build-arg DEV_BUILD=1
  sudo docker-compose up
  ```

This should make the services available locally, on the ports exposed by your machine.
It will refuse to start if there is conflicting ports (80, 443, ...) already exposed by your machine.

#### Implementation

##### Microservices

The architecture relies on 3 Docker containers:

- `services`: provides a nginx server that services some HTML/javascript, and few generated sample files. Generation occurs during services init.
- `httpbin`: uses the official Docker image from https://httpbin.org/ to service an instance of that service. nginx server from the `services` container uses `proxy_pass` to forward relevant traffic to that container.
- `filter`: containers that acts as a MITM (man in the middle) and modifies the traffic, by delaying it and randomly dropping packets using `tc` ( <https://man7.org/linux/man-pages/man8/tc.8.html> )

##### Port structure

The service includes a JavaScript generator that helps to generate links, but the overall structure is:

| Protocol | Port |
| -------- | ---- |
| HTTP     | 2xxx |
| HTTPS    | 3xxx |
| UDP      | 4xxx |
| iperf    | 5xxx |
| echo     | 6xxx |

| Delay | Port |
| ----- | ---- |
| 0ms   | x0xx |
| 100ms | x1xx |
| 200ms | x2xx |

| Loss  | Port |
| ----- | ---- |
| 0%    | xx00 |
| 0.25% | xx01 |
| 0.5%  | xx02 |
| 1%    | xx03 |
| 1.5%  | xx04 |
| 2.5%  | xx05 |
| 5%    | xx06 |
| 10%   | xx07 |
| 15%   | xx08 |
| 25%   | xx09 |
| 50%   | xx10 |

##### Logging

There is logging available at flake.legato.io/logs

- `pcap`: packet capture logs are available in two locations. The `services` container pcaps are in pcap/ and the `filter` container pcaps are available in filter/pcap/.
  (control script logs at pcap_manager.log and in pcap_listener/ as well as filter/pcap_manager.log and in filter/pcap_listener/)
- `nginx`: nginx logs can be found at access.log, error.log, http.access.log.
- `iperf`: iperf logs can be found at iperf3.log.
  (control script logs at iperf_manager.log)
- `udp server`: udp server logs can be found at udp_server.log.
- `echo server`: echo server logs can be found at echo_servers.log.
