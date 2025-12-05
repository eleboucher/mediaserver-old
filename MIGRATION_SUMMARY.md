# Traefik Migration to K3s - Summary

## What Changed

### ✅ Completed
1. **Removed Docker Traefik** - Traefik no longer runs in Docker Compose
2. **K3s Traefik** - Now handling all HTTP/HTTPS traffic on 192.168.1.52
3. **cert-manager** - Automatically issuing Let's Encrypt certificates via Cloudflare DNS
4. **Service Routing** - All Docker Compose services now route through K3s Traefik

### 🔧 Architecture

**Before:**
```
Internet → Docker Traefik (192.168.1.52) → Docker Services
```

**After:**
```
Internet → K3s Traefik (192.168.1.52) → Docker Services (via Kubernetes Services)
```

### 📁 New Kubernetes Resources

**Location:** `clusters/k3s/apps/`

- **docker-services.yaml** - Kubernetes Services pointing to Docker container IPs
- **docker-ingresses.yaml** - Ingress resources with SSL for all services
- **Wildcard Certificate** - `*.erwanleboucher.dev` (auto-renewed by cert-manager)

### 🌐 Services Migrated

All services now accessible via K3s Traefik with automatic SSL:

| Service | URL | Docker IP |
|---------|-----|-----------|
| Jellyfin | https://watch.erwanleboucher.dev | 172.20.0.7 |
| Sonarr | https://sonarr.erwanleboucher.dev | 172.20.0.13 |
| Radarr | https://radarr.erwanleboucher.dev | 172.20.0.14 |
| Prowlarr | https://prowlarr.erwanleboucher.dev | 172.20.0.17 |
| Bazarr | https://bazarr.erwanleboucher.dev | 172.20.0.16 |
| qBittorrent | https://qbit.erwanleboucher.dev | 172.20.0.18 (Gluetun) |
| Sabnzbd | https://sabnzbd.erwanleboucher.dev | 172.20.0.18 (Gluetun) |
| Portainer | https://portainer.erwanleboucher.dev | 172.20.0.23 |
| Jellyseerr | https://request.erwanleboucher.dev | 172.20.0.25 |
| Autobrr | https://autobrr.erwanleboucher.dev | 172.20.0.24 |
| Beszel | https://monitor.erwanleboucher.dev | 172.20.0.30 |
| N8N | https://n8n.erwanleboucher.dev | 172.20.0.40 |
| Open WebUI | https://ai.erwanleboucher.dev | 172.20.0.51 |
| Wizarr | https://wizarr.erwanleboucher.dev | 172.20.0.5 |
| Profilarr | https://profilarr.erwanleboucher.dev | 172.20.0.4 |

### ⚠️ Important Notes

1. **Docker Labels** - The Traefik labels in docker-compose.yaml are now ignored but harmless
2. **Docker Network** - Services must stay on the `yams_network` (172.20.0.0/24) with fixed IPs
3. **IP Changes** - If a Docker container IP changes, update the Endpoints in `docker-services.yaml`
4. **Backup** - Original docker-compose.yaml saved as `docker-compose.yaml.backup`

### 🔄 Rolling Back

If needed, restore the backup:
```bash
cp docker-compose.yaml.backup docker-compose.yaml
docker-compose up -d traefik
```

### 🚀 Next Steps

1. Monitor certificate issuance: `kubectl get certificates -A`
2. Test all services are accessible
3. (Optional) Remove Traefik labels from docker-compose.yaml services
4. (Optional) Migrate more services fully to K3s as Deployments

### 🎯 Benefits

- ✅ GitOps-managed routing configuration
- ✅ Automatic SSL certificate renewal
- ✅ Single entry point for all services
- ✅ Kubernetes-native ingress management
- ✅ Encrypted secrets with SOPS
