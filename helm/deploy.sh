
helm install metallb metallb/metallb -n metallb-system --create-namespace --set speaker.frr.enabled=false


helm upgrade --install homepage jameswynn/homepage -n default  -f ./helm/homepage/values.yaml


helm install uptime-kuma uptime-kuma/uptime-kuma \
  --namespace default \
  -f ./helm/uptime-kuma/values.yaml
