# K3s Migration Guide - Docker Compose to Kubernetes



**Last Updated:** 2025-12-04

**Target Setup:** Hybrid homelab with FluxCD GitOps



---



## Table of Contents



1. [Architecture Overview](#architecture-overview)

2. [Prerequisites](#prerequisites)

3. [Phase 1: FluxCD Bootstrap](#phase-1-fluxcd-bootstrap)

4. [Phase 2: Infrastructure Setup](#phase-2-infrastructure-setup)

5. [Phase 3: Traefik Migration](#phase-3-traefik-migration)

6. [Phase 4: External Secrets with Bitwarden](#phase-4-external-secrets-with-bitwarden)

7. [Phase 5: Storage Configuration](#phase-5-storage-configuration)

8. [Phase 6: Service Migration](#phase-6-service-migration)

9. [Node Affinity Strategy](#node-affinity-strategy)

10. [Migration Examples](#migration-examples)

11. [Troubleshooting](#troubleshooting)



---



## Architecture Overview



### Current State

- **Docker Compose** on 192.168.1.40 (home node) - all services

- **K3s** with MetalLB, cert-manager, AdGuard HA

- Traefik in Docker for internal access

- Cloudflare Tunnel for remote access



### Target State

- **FluxCD** managing all K3s deployments via Git

- **Traefik on K3s** as Ingress Controller

- **External Secrets Operator** pulling from Bitwarden

- **Node Affinity:**

- `home` node: Media stack, Home Assistant, n8n, etc.

- `k3s` node: AdGuard HA, Uptime Kuma

- **Hybrid Approach:**

- Keep VPN stack (Gluetun + qBittorrent) in Docker (for now)

- Migrate everything else to K3s



### Network Flow

```

External → Cloudflare Tunnel → Traefik (K3s) → Services (K3s Pods)

Internal → AdGuard DNS → Traefik (K3s) → Services (K3s Pods)

```



---



## Prerequisites



### K3s Installation Flags

Your K3s should be installed with:

```bash

curl -sfL https://get.k3s.io | sh -s - server \

--disable=traefik \

--disable=servicelb \

--write-kubeconfig-mode=644

```



✅ **You've done this** - good! This gives us full control over Traefik and LoadBalancer.



### Required Tools

```bash

# Install Flux CLI

curl -s https://fluxcd.io/install.sh | sudo bash



# Verify installation

flux --version



# Install kubectl (if not already installed)

curl -LO "https://dl.k8s.io/release/$(curl -L -s https://dl.k8s.io/release/stable.txt)/bin/linux/amd64/kubectl"

sudo install -o root -g root -m 0755 kubectl /usr/local/bin/kubectl



# Install Helm

curl https://raw.githubusercontent.com/helm/helm/main/scripts/get-helm-3 | bash

```



### GitHub Personal Access Token

Create a token at: https://github.com/settings/tokens



Required scopes:

- `repo` (all)

- `write:packages`

- `read:packages`



```bash

export GITHUB_TOKEN=<your-token>

export GITHUB_USER=<your-username>

```



---



## Phase 1: FluxCD Bootstrap



### 1.1 Prepare Repository Structure



Your existing `/opt/yams` directory will be used. Create the structure:



```bash

cd /opt/yams



# Create Flux directory structure

mkdir -p clusters/k3s/{flux-system,infrastructure,apps}

mkdir -p clusters/k3s/apps/{media,automation,system,monitoring}

mkdir -p clusters/k3s/infrastructure/{traefik,metallb,cert-manager,external-secrets}

```



### 1.2 Update .gitignore



**CRITICAL:** Prevent committing secrets and runtime files:



```bash

cat >> .gitignore <<EOF



# K3s/Flux

clusters/k3s/flux-system/gotk-sync.yaml

clusters/k3s/flux-system/gotk-components.yaml



# Runtime data - DO NOT COMMIT

config/qbittorrent/qBittorrent/BT_backup/*.fastresume

config/qbittorrent/qBittorrent/BT_backup/*.torrent

config/**/logs/

config/**/cache/

config/**/backups/



# Secrets - DO NOT COMMIT (use External Secrets instead)

**/*secret*.yaml

**/*-credentials.yaml

.env

EOF

```



### 1.3 Bootstrap Flux



```bash

# Bootstrap Flux to your existing repository

flux bootstrap github \

--owner=$GITHUB_USER \

--repository=yams \

--branch=master \

--path=clusters/k3s \

--personal \

--read-write-key=true



# Output should show:

# ✔ repository cloned

# ✔ components manifests pushed

# ✔ install completed

# ✔ bootstrap finished

```



### 1.4 Verify Flux Installation



```bash

# Check Flux pods

kubectl get pods -n flux-system



# Should see:

# source-controller

# kustomize-controller

# helm-controller

# notification-controller



# Check Flux status

flux get all

```



### 1.5 Configure Flux Sync



Flux will now watch `clusters/k3s/` and apply any YAML you add there.



Default sync interval: 1 minute

Your auto-commit script → Git push → Flux deploys within 60 seconds



---



## Phase 2: Infrastructure Setup



### 2.1 MetalLB (Already Installed)



Create manifest for GitOps:



```bash

cat > clusters/k3s/infrastructure/metallb/namespace.yaml <<EOF

apiVersion: v1

kind: Namespace

metadata:

name: metallb-system

EOF



cat > clusters/k3s/infrastructure/metallb/ipaddresspool.yaml <<EOF

apiVersion: metallb.io/v1beta1

kind: IPAddressPool

metadata:

name: first-pool

namespace: metallb-system

spec:

addresses:

- 192.168.1.53-192.168.1.56

---

apiVersion: metallb.io/v1beta1

kind: L2Advertisement

metadata:

name: l2-advert

namespace: metallb-system

EOF



cat > clusters/k3s/infrastructure/metallb/kustomization.yaml <<EOF

apiVersion: kustomize.config.k8s.io/v1beta1

kind: Kustomization

resources:

- namespace.yaml

- ipaddresspool.yaml

EOF

```



### 2.2 Cert-Manager (Already Installed)



```bash

cat > clusters/k3s/infrastructure/cert-manager/namespace.yaml <<EOF

apiVersion: v1

kind: Namespace

metadata:

name: cert-manager

EOF



cat > clusters/k3s/infrastructure/cert-manager/cloudflare-secret.yaml <<EOF

apiVersion: v1

kind: Secret

metadata:

name: cloudflare-api-token

namespace: cert-manager

type: Opaque

stringData:

api-token: \${CF_DNS_API_TOKEN}

EOF



cat > clusters/k3s/infrastructure/cert-manager/cluster-issuer.yaml <<EOF

apiVersion: cert-manager.io/v1

kind: ClusterIssuer

metadata:

name: letsencrypt-prod

spec:

acme:

email: erwanleboucher@gmail.com

server: https://acme-v02.api.letsencrypt.org/directory

privateKeySecretRef:

name: letsencrypt-prod-key

solvers:

- dns01:

cloudflare:

apiTokenSecretRef:

name: cloudflare-api-token

key: api-token

EOF



cat > clusters/k3s/infrastructure/cert-manager/kustomization.yaml <<EOF

apiVersion: kustomize.config.k8s.io/v1beta1

kind: Kustomization

resources:

- namespace.yaml

- cloudflare-secret.yaml

- cluster-issuer.yaml

EOF

```



**Note:** Move `CF_DNS_API_TOKEN` to External Secrets later.



---



## Phase 3: Traefik Migration



### 3.1 Install Traefik via Helm in K3s



```bash

# Add Traefik repo

helm repo add traefik https://traefik.github.io/charts

helm repo update



# Create values file

cat > clusters/k3s/infrastructure/traefik/values.yaml <<EOF

# Traefik values for K3s

deployment:

replicas: 2 # HA setup



service:

type: LoadBalancer

loadBalancerIP: 192.168.1.52 # Choose from MetalLB pool



ports:

web:

port: 80

redirectTo:

port: websecure

websecure:

port: 443

tls:

enabled: true

certResolver: letsencrypt

dns-over-tls:

port: 853

expose: true



# Enable dashboard (internal only)

ingressRoute:

dashboard:

enabled: true

matchRule: Host(\`traefik.erwanleboucher.dev\`)

entryPoints:

- websecure

tls:

certResolver: letsencrypt



# Certificate resolvers

certificatesResolvers:

letsencrypt:

acme:

email: erwanleboucher@gmail.com

storage: /data/acme.json

dnsChallenge:

provider: cloudflare

resolvers:

- "1.1.1.1:53"

- "1.0.0.1:53"



env:

- name: CF_DNS_API_TOKEN

value: \${CF_DNS_API_TOKEN}



# Persist ACME certificates

persistence:

enabled: true

storageClass: local-path

size: 128Mi



# Providers

providers:

kubernetesCRD:

enabled: true

kubernetesIngress:

enabled: true



# Logs

logs:

general:

level: INFO

access:

enabled: true



# Metrics (optional)

metrics:

prometheus:

enabled: true

EOF

```



### 3.2 Create Traefik HelmRelease for Flux



```bash

cat > clusters/k3s/infrastructure/traefik/helmrelease.yaml <<EOF

apiVersion: v1

kind: Namespace

metadata:

name: traefik

---

apiVersion: source.toolkit.fluxcd.io/v1

kind: HelmRepository

metadata:

name: traefik

namespace: traefik

spec:

interval: 1h

url: https://traefik.github.io/charts

---

apiVersion: helm.toolkit.fluxcd.io/v2

kind: HelmRelease

metadata:

name: traefik

namespace: traefik

spec:

interval: 30m

chart:

spec:

chart: traefik

version: "32.x.x" # Pin to major version

sourceRef:

kind: HelmRepository

name: traefik

namespace: traefik

interval: 12h

valuesFrom:

- kind: ConfigMap

name: traefik-values

---

apiVersion: v1

kind: ConfigMap

metadata:

name: traefik-values

namespace: traefik

data:

values.yaml: |

$(cat clusters/k3s/infrastructure/traefik/values.yaml | sed 's/^/ /')

EOF



cat > clusters/k3s/infrastructure/traefik/kustomization.yaml <<EOF

apiVersion: kustomize.config.k8s.io/v1beta1

kind: Kustomization

resources:

- helmrelease.yaml

EOF

```



### 3.3 Git Commit and Push



```bash

git add clusters/k3s/infrastructure/traefik/

git commit -m "Add Traefik to K3s"

git push



# Flux will deploy within 60 seconds

# Watch deployment:

flux get helmreleases -n traefik

kubectl get pods -n traefik -w

```



### 3.4 Verify Traefik



```bash

# Check LoadBalancer IP

kubectl get svc -n traefik



# Should show EXTERNAL-IP: 192.168.1.52



# Test dashboard (after DNS points to it)

curl -k https://traefik.erwanleboucher.dev

```



### 3.5 Migrate from Docker Traefik



**Update AdGuard DNS:**

- Point `*.erwanleboucher.dev` to `192.168.1.52` (new Traefik K3s IP)



**Stop Docker Traefik:**

```bash

cd /opt/yams

docker compose stop traefik

# Test services - if working, remove from compose

# docker compose rm traefik

```



---







## Phase 5: Storage Configuration



### 5.1 Local Disk Storage (Main Node)



**Config directories:** `/opt/yams/config/`

**Media directory:** `/srv/media` (local)



Use **hostPath** volumes with node affinity:



```yaml

# Example: Jellyfin with hostPath

apiVersion: v1

kind: PersistentVolume

metadata:

name: jellyfin-config

spec:

capacity:

storage: 10Gi

accessModes:

- ReadWriteOnce

persistentVolumeReclaimPolicy: Retain

storageClassName: local-storage

local:

path: /opt/yams/config/jellyfin

nodeAffinity:

required:

nodeSelectorTerms:

- matchExpressions:

- key: kubernetes.io/hostname

operator: In

values:

- home # Main node

---

apiVersion: v1

kind: PersistentVolumeClaim

metadata:

name: jellyfin-config

namespace: media

spec:

accessModes:

- ReadWriteOnce

storageClassName: local-storage

resources:

requests:

storage: 10Gi

```



**Simpler approach - Direct hostPath in Deployment:**

```yaml

volumes:

- name: config

hostPath:

path: /opt/yams/config/jellyfin

type: Directory

- name: media

hostPath:

path: /srv/media

type: Directory

```



### 5.2 SMB Shared Media



For your SMB disk, create an SMB PersistentVolume:



**Install SMB CSI Driver:**

```bash

cat > clusters/k3s/infrastructure/smb-csi/helmrelease.yaml <<EOF

apiVersion: source.toolkit.fluxcd.io/v1

kind: HelmRepository

metadata:

name: csi-driver-smb

namespace: kube-system

spec:

interval: 1h

url: https://raw.githubusercontent.com/kubernetes-csi/csi-driver-smb/master/charts

---

apiVersion: helm.toolkit.fluxcd.io/v2

kind: HelmRelease

metadata:

name: csi-driver-smb

namespace: kube-system

spec:

interval: 30m

chart:

spec:

chart: csi-driver-smb

sourceRef:

kind: HelmRepository

name: csi-driver-smb

interval: 12h

EOF

```



**Create SMB Secret:**

```bash

kubectl create secret generic smb-credentials -n media \

--from-literal=username='smb-user' \

--from-literal=password='smb-password'

```



**Create SMB PV:**

```yaml

apiVersion: v1

kind: PersistentVolume

metadata:

name: smb-media

spec:

capacity:

storage: 100Ti # Adjust

accessModes:

- ReadWriteMany

persistentVolumeReclaimPolicy: Retain

storageClassName: smb

mountOptions:

- dir_mode=0777

- file_mode=0777

- vers=3.0

csi:

driver: smb.csi.k8s.io

volumeHandle: smb-media-share

volumeAttributes:

source: "//192.168.1.x/media" # Your SMB server

nodeStageSecretRef:

name: smb-credentials

namespace: media

---

apiVersion: v1

kind: PersistentVolumeClaim

metadata:

name: smb-media

namespace: media

spec:

accessModes:

- ReadWriteMany

storageClassName: smb

resources:

requests:

storage: 100Ti

```



---



## Phase 6: Service Migration



### 6.1 Create Namespace Structure



```bash

cat > clusters/k3s/apps/media/namespace.yaml <<EOF

apiVersion: v1

kind: Namespace

metadata:

name: media

EOF



cat > clusters/k3s/apps/automation/namespace.yaml <<EOF

apiVersion: v1

kind: Namespace

metadata:

name: automation

EOF



cat > clusters/k3s/apps/system/namespace.yaml <<EOF

apiVersion: v1

kind: Namespace

metadata:

name: system

EOF

```



### 6.2 Migration Priority



**Phase 1 - Simple/Stateless:**

1. Prowlarr

2. Bazarr

3. Jellyseerr

4. Portainer



**Phase 2 - Media Services:**

5. Sonarr

6. Radarr

7. Jellyfin



**Phase 3 - Complex:**

8. Home Assistant

9. n8n + Postgres

10. Ollama + Open WebUI



**Keep in Docker (for now):**

- Gluetun + qBittorrent (VPN networking)

- SABnzbd (via Gluetun)



---



## Node Affinity Strategy



### Node Roles



**home (192.168.1.40):**

- All media services

- Home Assistant

- n8n, Postgres

- Ollama, Open WebUI

- Portainer



**k3s (second node):**

- AdGuard (2 replicas)

- Uptime Kuma



### Enforce with Taints (Optional but Recommended)



**Taint the k3s node:**

```bash

kubectl taint nodes k3s workload=infrastructure:NoSchedule

```



**AdGuard and Uptime Kuma tolerate it:**

```yaml

tolerations:

- key: workload

operator: Equal

value: infrastructure

effect: NoSchedule

nodeSelector:

kubernetes.io/hostname: "k3s"

```



**Everything else pins to home:**

```yaml

nodeSelector:

kubernetes.io/hostname: "home"

```



---



## Migration Examples



### Example 1: Jellyfin (Media Service with GPU)



```yaml

# clusters/k3s/apps/media/jellyfin.yaml

apiVersion: apps/v1

kind: Deployment

metadata:

name: jellyfin

namespace: media

spec:

replicas: 1

selector:

matchLabels:

app: jellyfin

template:

metadata:

labels:

app: jellyfin

spec:

nodeSelector:

kubernetes.io/hostname: "home" # Pin to main node

containers:

- name: jellyfin

image: lscr.io/linuxserver/jellyfin:10.11.4ubu2404-ls10

ports:

- containerPort: 8096

env:

- name: PUID

value: "1000"

- name: PGID

value: "1000"

- name: TZ

value: "Europe/Paris"

resources:

limits:

gpu.intel.com/i915: "1" # Intel GPU

memory: 4Gi

requests:

cpu: 500m

memory: 1Gi

volumeMounts:

- name: config

mountPath: /config

- name: media

mountPath: /data

readOnly: true

volumes:

- name: config

hostPath:

path: /opt/yams/config/jellyfin

type: Directory

- name: media

hostPath:

path: /srv/media

type: Directory

---

apiVersion: v1

kind: Service

metadata:

name: jellyfin

namespace: media

spec:

selector:

app: jellyfin

ports:

- port: 8096

targetPort: 8096

---

apiVersion: networking.k8s.io/v1

kind: Ingress

metadata:

name: jellyfin

namespace: media

annotations:

cert-manager.io/cluster-issuer: letsencrypt-prod

traefik.ingress.kubernetes.io/router.entrypoints: websecure

spec:

ingressClassName: traefik

rules:

- host: watch.erwanleboucher.dev

http:

paths:

- path: /

pathType: Prefix

backend:

service:

name: jellyfin

port:

number: 8096

tls:

- secretName: jellyfin-tls

hosts:

- watch.erwanleboucher.dev

```



### Example 2: Sonarr (Stateful with API Key from Bitwarden)



```yaml

# clusters/k3s/apps/media/sonarr-externalsecret.yaml

apiVersion: external-secrets.io/v1beta1

kind: ExternalSecret

metadata:

name: sonarr-api-key

namespace: media

spec:

refreshInterval: 1h

secretStoreRef:

name: bitwarden

kind: ClusterSecretStore

target:

name: sonarr-secret

data:

- secretKey: api-key

remoteRef:

key: sonarr-api-key

---

# clusters/k3s/apps/media/sonarr.yaml

apiVersion: apps/v1

kind: Deployment

metadata:

name: sonarr

namespace: media

spec:

replicas: 1

selector:

matchLabels:

app: sonarr

template:

metadata:

labels:

app: sonarr

spec:

nodeSelector:

kubernetes.io/hostname: "home"

containers:

- name: sonarr

image: lscr.io/linuxserver/sonarr:4.0.16.2944-ls299

ports:

- containerPort: 8989

env:

- name: PUID

value: "1000"

- name: PGID

value: "1000"

- name: TZ

value: "Europe/Paris"

resources:

limits:

memory: 1Gi

requests:

cpu: 200m

memory: 512Mi

volumeMounts:

- name: config

mountPath: /config

- name: data

mountPath: /data

volumes:

- name: config

hostPath:

path: /opt/yams/config/sonarr

type: Directory

- name: data

hostPath:

path: /srv/media

type: Directory

---

apiVersion: v1

kind: Service

metadata:

name: sonarr

namespace: media

spec:

selector:

app: sonarr

ports:

- port: 8989

targetPort: 8989

---

apiVersion: networking.k8s.io/v1

kind: Ingress

metadata:

name: sonarr

namespace: media

annotations:

cert-manager.io/cluster-issuer: letsencrypt-prod

spec:

ingressClassName: traefik

rules:

- host: sonarr.erwanleboucher.dev

http:

paths:

- path: /

pathType: Prefix

backend:

service:

name: sonarr

port:

number: 8989

tls:

- secretName: sonarr-tls

hosts:

- sonarr.erwanleboucher.dev

```



### Example 3: Home Assistant (Host Network + Privileged)



```yaml

# clusters/k3s/apps/automation/homeassistant.yaml

apiVersion: apps/v1

kind: Deployment

metadata:

name: homeassistant

namespace: automation

spec:

replicas: 1

selector:

matchLabels:

app: homeassistant

template:

metadata:

labels:

app: homeassistant

spec:

hostNetwork: true

nodeSelector:

kubernetes.io/hostname: "home" # Pin to node with USB devices

containers:

- name: homeassistant

image: ghcr.io/home-assistant/home-assistant:2025.11.3

securityContext:

privileged: true

env:

- name: TZ

value: "Europe/Paris"

volumeMounts:

- name: config

mountPath: /config

- name: localtime

mountPath: /etc/localtime

readOnly: true

- name: dbus

mountPath: /run/dbus

readOnly: true

- name: usb

mountPath: /dev/ttyUSB0

volumes:

- name: config

hostPath:

path: /opt/yams/config/homeassistant

type: Directory

- name: localtime

hostPath:

path: /etc/localtime

- name: dbus

hostPath:

path: /run/dbus

- name: usb

hostPath:

path: /dev/ttyUSB0

type: CharDevice

```



### Example 4: AdGuard HA (Multi-Node Replicas)



```yaml

# clusters/k3s/apps/system/adguard.yaml

apiVersion: apps/v1

kind: Deployment

metadata:

name: adguard

namespace: system

spec:

replicas: 2 # HA across both nodes

selector:

matchLabels:

app: adguard

template:

metadata:

labels:

app: adguard

spec:

# No nodeSelector - allow scheduling on both nodes

tolerations:

- key: workload

operator: Equal

value: infrastructure

effect: NoSchedule

affinity:

podAntiAffinity:

requiredDuringSchedulingIgnoredDuringExecution:

- labelSelector:

matchExpressions:

- key: app

operator: In

values:

- adguard

topologyKey: kubernetes.io/hostname # Force different nodes

containers:

- name: adguard

image: adguard/adguardhome:latest

ports:

- containerPort: 53

protocol: UDP

- containerPort: 53

protocol: TCP

- containerPort: 80

- containerPort: 443

- containerPort: 853

volumeMounts:

- name: config

mountPath: /opt/adguardhome/conf

- name: data

mountPath: /opt/adguardhome/work

volumes:

- name: config

persistentVolumeClaim:

claimName: adguard-config

- name: data

persistentVolumeClaim:

claimName: adguard-data

---

apiVersion: v1

kind: Service

metadata:

name: adguard-dns

namespace: system

annotations:

metallb.universe.tf/allow-shared-ip: "adguard-vip"

spec:

type: LoadBalancer

loadBalancerIP: 192.168.1.53

externalTrafficPolicy: Local

selector:

app: adguard

ports:

- name: dns-udp

port: 53

protocol: UDP

- name: dns-tcp

port: 53

protocol: TCP

- name: dns-over-tls

port: 853

protocol: TCP

---

apiVersion: v1

kind: Service

metadata:

name: adguard-web

namespace: system

annotations:

metallb.universe.tf/allow-shared-ip: "adguard-web-vip"

spec:

type: LoadBalancer

loadBalancerIP: 192.168.1.54

selector:

app: adguard

ports:

- name: http

port: 3000

targetPort: 80

```



---



## Troubleshooting



### Flux Not Syncing



```bash

# Check Flux status

flux get all



# Check specific resource

flux get kustomizations

flux get helmreleases -A



# Force reconciliation

flux reconcile kustomization flux-system --with-source



# View logs

kubectl logs -n flux-system -l app=kustomize-controller

kubectl logs -n flux-system -l app=source-controller

```



### External Secrets Not Working



```bash

# Check External Secret status

kubectl get externalsecrets -A

kubectl describe externalsecret <name> -n <namespace>



# Check SecretStore

kubectl get clustersecretstores

kubectl describe clustersecretstore bitwarden



# View operator logs

kubectl logs -n external-secrets-system -l app.kubernetes.io/name=external-secrets

```



### Traefik Not Routing



```bash

# Check Ingress

kubectl get ingress -A

kubectl describe ingress <name> -n <namespace>



# Check Traefik logs

kubectl logs -n traefik -l app.kubernetes.io/name=traefik



# Check IngressRoute (if using Traefik CRD)

kubectl get ingressroute -A



# Test from inside cluster

kubectl run -it --rm debug --image=nicolaka/netshoot -- /bin/bash

curl http://jellyfin.media.svc.cluster.local:8096

```



### Storage Issues



```bash

# Check PVs and PVCs

kubectl get pv

kubectl get pvc -A



# Check if pod can mount

kubectl describe pod <pod-name> -n <namespace>



# Check node storage

df -h /opt/yams/config

df -h /srv/media

```



### DNS Issues



```bash

# Check AdGuard pods

kubectl get pods -n system -l app=adguard



# Check LoadBalancer IP

kubectl get svc -n system adguard-dns



# Test DNS resolution

dig @192.168.1.53 watch.erwanleboucher.dev



# Check CoreDNS

kubectl get pods -n kube-system -l k8s-app=kube-dns

```



---



## Next Steps



1. **Bootstrap FluxCD** - Run Phase 1

2. **Deploy Traefik** - Run Phase 3

3. **Setup External Secrets** - Run Phase 4

4. **Migrate one service** (start with Prowlarr - simplest)

5. **Test end-to-end** (DNS → Traefik → Service)

6. **Migrate remaining services** one by one

7. **Update Homepage** to use K8s service URLs

8. **Decommission Docker Compose** (except VPN stack)



---



## Useful Commands



```bash

# Watch Flux syncing

watch flux get kustomizations



# Check all pods

kubectl get pods -A



# Check services and IPs

kubectl get svc -A



# Check Ingress

kubectl get ingress -A



# Force Flux sync

flux reconcile source git flux-system

flux reconcile kustomization flux-system



# Suspend/Resume Flux (for manual changes)

flux suspend kustomization <name>

flux resume kustomization <name>



# View Traefik dashboard (if enabled)

kubectl port-forward -n traefik svc/traefik 9000:9000

# Open: http://localhost:9000/dashboard/



# Cleanup a stuck deployment

kubectl delete pod <pod> -n <namespace> --grace-period=0 --force

```



---



## References



- [FluxCD Documentation](https://fluxcd.io/flux/)

- [Traefik Kubernetes Docs](https://doc.traefik.io/traefik/providers/kubernetes-ingress/)

- [External Secrets Operator](https://external-secrets.io/)

- [K3s Documentation](https://docs.k3s.io/)

- [MetalLB Configuration](https://metallb.universe.tf/configuration/)



---



**Good luck with your migration! Start small, test thoroughly, and migrate incrementally.**
