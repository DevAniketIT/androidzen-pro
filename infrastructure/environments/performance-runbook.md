# Performance Test Environment Runbook

Purpose: High-spec environment for load, stress, and soak tests that mirrors production software versions and configurations but scales up resources.

References
- Config: infrastructure/environments/performance-environment.yaml
- Credentials: infrastructure/credentials/credentials-inventory.yaml
- Data plan: infrastructure/data-management/data-management-plan.yaml

Provisioning
- Create EKS 1.28 with performance and device-lab node groups
- Enable VPA, HPA tuned per config
- Provision RDS (db.r5.2xlarge, 500 GiB gp3, PI enabled) and Redis cluster
- Install Istio 1.19 and NGINX ingress (3 replicas)

Load testing toolchain
- k6, Artillery, JMeter containers with Grafana dashboards
- Synthetic datasets seeded per data plan medium/large scales

Executing tests
- Baseline: 10 min warm-up; capture CPU/mem, p95, error rate
- Stress: ramp to target RPS; sustain 30 min; record saturation points
- Soak: 8-24h stability test; memory leaks, reconnection rate

SLOs and gates
- p95 API < 800ms @ target load
- 5xx < 1% overall
- WebSocket connect success > 99%
- Error budgets tracked per test run

Rollback and cleanup
- kubectl rollout undo ...
- Cleanup old test data as per cleanup policy; archive metrics to S3 30d

Reporting
- Store results in s3://androidzen-test-results/perf/
- Attach Grafana snapshots and JMeter/Artillery/k6 reports

