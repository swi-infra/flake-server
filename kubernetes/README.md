Internal Flake Instructions:

Main Resource: https://confluence.sierrawireless.com/display/LEGATO/How+to+configure+Flake+Legato
Getting Started Internal Flake

Tips:
Consult the Conceptual Overview of Internal Flake.
Bringup deployments from the bottom up since the higher deployments depend on
the lower ones running.

1. Bring up FTPD

- Prior to launching, make sure ftpd-secret is present: kubectl get secret
- Prior to launching, edit environtment value PUBLICHOST to 0.0.0.0
- Prior to launching, comment out nodeName value
- After launch, we can record the address of the host/nodeName via Node field:
  kubectl describe pod <pod_name>
- You may choose to use a different host but it will need to correspond with
  the address/name of that host

2. Bring up httpbin
3. Bring up flake-services.yaml

- make sure all the volumes required are present: internal-flake, swifarmkey,
  tls-client-secret, tls-server-secret, nginx-conf
  kubectl get secrets, kubectl get ConfigMaps
- kubectl describe pod <flake-service-pod-name>
- Note down the cluster IP of flake-services to be used for filter (EG: IP: 172.20.9.68)

4. Bring up flake-services-tcp.yaml, flake-services-udp.yaml
5. Bring up filter-deployment.yaml

- make sure all the volumes required are present: filter-nginx-conf, internal-flake
- Environment value "SERVICES HOST" needs the value from flake-services that
  we noted down earlier.
  TODO: Edit filter-deployment.yaml environment value SERVICES HOST such that
  on bring up, we don't need to manually record the value after bringing up
  flake-services

6. Bring up filter-service-tcp.yaml/filter-service-udp.yaml
