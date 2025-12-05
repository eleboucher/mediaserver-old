# Jellyfin

Media server running in Docker Compose, exposed through K3s Traefik.

## Current State
- **Type**: Docker Compose container
- **Access**: https://watch.erwanleboucher.dev
- **Backend**: 192.168.1.40:8096 (Docker host port)
- **Container Port**: 8096

## Migration Options

### Option 1: Keep in Docker Compose (Current - Hybrid Approach)
**Recommended for now** - Simple, working setup.

**Pros:**
- Already configured in docker-compose.yaml
- Easy to manage with existing tools
- No data migration needed

**Cons:**
- Not fully in K3s
- Manual updates

### Option 2: Migrate to K3s Deployment
Deploy as native K3s workload.

**Pros:**
- Full GitOps management
- Automatic updates with Flux
- Better resource management

**Cons:**
- Need to migrate data/config
- More complex PV setup
- Requires node selector for storage

### Option 3: Migrate to Helm Chart
Use community Helm chart (e.g., k8s-at-home).

**Steps to migrate:**
1. Create HelmRepository and HelmRelease
2. Configure persistent storage
3. Migrate existing data
4. Update ingress configuration

**Example:**
```yaml
apiVersion: helm.toolkit.fluxcd.io/v2
kind: HelmRelease
metadata:
  name: jellyfin
  namespace: media
spec:
  chart:
    spec:
      chart: jellyfin
      sourceRef:
        kind: HelmRepository
        name: k8s-at-home
```
