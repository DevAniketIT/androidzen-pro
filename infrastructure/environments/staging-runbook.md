# Staging Environment Runbook

Purpose: Production-like staging environment for pre-prod validation. Mirrors versions, configs, autoscaling, observability, network policies, and data tier sizes.

References
- Config: infrastructure/environments/staging-environment.yaml
- Credentials: infrastructure/credentials/credentials-inventory.yaml
- Data plan: infrastructure/data-management/data-management-plan.yaml

Change control
- All changes via IaC PRs. No manual changes allowed.
- Approvals: SRE + Security for network/security; DBA for database size/params.

Provisioning steps
1) Prereqs
- Cloud account: AWS us-west-2
- Kubernetes: EKS v1.28 with node pools defined in config
- DNS: staging subdomain delegated
- TLS: Let’s Encrypt staging issuer configured

2) Bootstrap
- Create VPC, subnets, security groups (terraform/module recommended)
- Create EKS cluster + node groups (primary, device-lab)
- Install system add-ons:
  - Ingress controller (nginx)
  - Cert-manager with letsencrypt-staging issuer
  - Metrics-server, Cluster Autoscaler
  - Prometheus, Grafana, Jaeger, Elasticsearch (or vendor-managed equivalents)

3) Data tier
- Provision PostgreSQL 15.4 (RDS) with 100 GiB, single-AZ, backups 7d
- Provision Redis 7 with t3.micro
- Create DB users/roles per credentials inventory; rotate secrets in Vault/ASM

4) App deployment
- Build/push images androidzen/backend and androidzen/frontend to registry
- Apply Kubernetes manifests/helm using staging-environment.yaml values
- Configure Ingress + DNS records

5) Network policies
- Enforce default-deny ingress; allow app->db:5432; app->redis:6379; egress 80/443

6) Observability
- Dashboards imported: API latency, ADB command success, DB connections, Queue depth
- Alerts: healthcheck failed >5m, p95 latency >2s 10m, 5xx rate >1%, DB CPU >80% 15m

Operations
- Health check
  curl -fsS https://staging.androidzen.example.com/api/health || exit 1
- Scale test
  kubectl scale deploy androidzen-backend -n androidzen-staging --replicas=4
- Rollback
  kubectl rollout undo deploy/androidzen-backend -n androidzen-staging

SLA/SLOs
- Health endpoint 99.9% monthly
- p95 API < 500ms under nominal load

Runbooks: incidents
- 5xx spike: check Grafana dashboards, inspect pods logs, recent deploys, DB metrics
- DB connection saturation: raise max_connections cautiously; add connection pooling
- Queue backlog: add replicas; investigate downstream latency

Backups/DR
- Daily RDS snapshots; weekly restore test

Security
- PSP/PodSecurity admission: restricted
- RBAC: least privilege; CI uses a dedicated, namespaced SA

