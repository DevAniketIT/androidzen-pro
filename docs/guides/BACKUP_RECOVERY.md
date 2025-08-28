# Backup and Recovery Documentation

## Table of Contents
1. [Database Backup Strategies](#database-backup-strategies)
2. [File Storage Backup Procedures](#file-storage-backup-procedures)
3. [Disaster Recovery Runbook](#disaster-recovery-runbook)
4. [RTO/RPO Targets](#rtorpo-targets)
5. [Backup Verification Procedures](#backup-verification-procedures)
6. [Recovery Testing Schedule](#recovery-testing-schedule)

## Database Backup Strategies

### 1. Production Database Backup

#### Primary Backup Strategy
- **Type**: Automated continuous backup with point-in-time recovery
- **Frequency**: Full backup daily at 2:00 AM UTC, incremental backups every 15 minutes
- **Retention Policy**: 
  - Daily backups: 30 days
  - Weekly backups: 12 weeks
  - Monthly backups: 12 months
  - Yearly backups: 7 years

#### Backup Methods

##### Hot Backups (Online)
```bash
# PostgreSQL streaming replication
pg_basebackup -h primary-db -D /backup/postgres/hot -U replicator -v -P -W

# MongoDB replica set backup
mongodump --host replica-set/primary:27017,secondary:27017 --out /backup/mongodb/hot/$(date +%Y%m%d)
```

##### Cold Backups (Offline)
```bash
# Weekly cold backup during maintenance window
systemctl stop androidzen-api
pg_dump -h localhost -U admin androidzen_prod > /backup/postgres/cold/androidzen_$(date +%Y%m%d).sql
systemctl start androidzen-api
```

### 2. Development Database Backup
- **Frequency**: Daily at 1:00 AM local time
- **Retention**: 7 days
- **Method**: Logical dump for easy restoration and sharing

### 3. Backup Locations
- **Primary**: AWS S3 with versioning enabled
- **Secondary**: Google Cloud Storage (cross-cloud redundancy)
- **Local**: On-site NAS for quick recovery (7 days retention)

### 4. Backup Encryption
- All backups encrypted using AES-256
- Encryption keys managed through AWS KMS
- Regular key rotation every 90 days

## File Storage Backup Procedures

### 1. User-Generated Content

#### Application Files
- **Path**: `/app/storage/uploads/`
- **Backup Method**: Rsync to multiple locations
- **Schedule**: Hourly incremental, daily full
- **Retention**: 90 days

```bash
# Hourly incremental backup
rsync -avz --delete /app/storage/uploads/ s3://androidzen-backups/uploads/$(date +%Y%m%d)/

# Daily full backup verification
rsync -avz --checksum /app/storage/uploads/ /backup/local/uploads/$(date +%Y%m%d)/
```

#### User Profile Images
- **CDN Integration**: CloudFront with S3 origin
- **Backup**: Automatic S3 cross-region replication
- **Versioning**: Enabled for accidental deletion protection

### 2. Application Code and Configuration

#### Source Code
- **Primary**: Git repositories on GitHub
- **Backup**: GitLab mirror (automated sync)
- **Local**: Daily clone to backup servers

#### Configuration Files
```bash
# Configuration backup script
#!/bin/bash
CONFIG_BACKUP_PATH="/backup/config/$(date +%Y%m%d)"
mkdir -p $CONFIG_BACKUP_PATH

# Application configs
cp -r /app/config/ $CONFIG_BACKUP_PATH/app/
cp -r /etc/nginx/ $CONFIG_BACKUP_PATH/nginx/
cp -r /etc/ssl/ $CONFIG_BACKUP_PATH/ssl/

# Environment variables (encrypted)
gpg --cipher-algo AES256 --compress-algo 2 --symmetric --output $CONFIG_BACKUP_PATH/.env.gpg /app/.env
```

### 3. Log Files
- **Retention**: 30 days local, 1 year archived
- **Compression**: gzip for files older than 7 days
- **Backup**: AWS CloudWatch Logs integration

## Disaster Recovery Runbook

### 1. Incident Classification

#### Severity Levels
- **P1 (Critical)**: Complete service outage, data loss risk
- **P2 (High)**: Partial outage, performance degradation
- **P3 (Medium)**: Non-critical component failure
- **P4 (Low)**: Monitoring alerts, no user impact

### 2. Emergency Contacts

| Role | Primary | Secondary | Escalation |
|------|---------|-----------|------------|
| On-Call Engineer | +1-XXX-XXX-XXXX | +1-XXX-XXX-XXXX | DevOps Lead |
| Database Admin | +1-XXX-XXX-XXXX | +1-XXX-XXX-XXXX | CTO |
| Infrastructure Lead | +1-XXX-XXX-XXXX | +1-XXX-XXX-XXXX | Engineering Manager |

### 3. Recovery Procedures

#### Database Recovery

##### Point-in-Time Recovery
```bash
# Stop application services
systemctl stop androidzen-api androidzen-worker

# Restore database from backup
pg_restore -h localhost -U admin -d androidzen_prod /backup/postgres/androidzen_20240101.dump

# Apply WAL files for point-in-time recovery
pg_waldump /backup/wal/000000010000000000000001 | psql -d androidzen_prod

# Start services
systemctl start androidzen-api androidzen-worker
```

##### Full Database Replacement
```bash
# Create new database
createdb -h localhost -U admin androidzen_prod_new

# Restore from latest backup
pg_restore -h localhost -U admin -d androidzen_prod_new /backup/postgres/latest.dump

# Update connection strings and restart
sed -i 's/androidzen_prod/androidzen_prod_new/g' /app/config/database.conf
systemctl restart androidzen-api
```

#### Application Recovery

##### Code Deployment Rollback
```bash
# Rollback to previous stable version
kubectl set image deployment/androidzen-api api=androidzen/api:stable
kubectl set image deployment/androidzen-worker worker=androidzen/worker:stable

# Verify rollback
kubectl rollout status deployment/androidzen-api
kubectl rollout status deployment/androidzen-worker
```

##### Configuration Recovery
```bash
# Restore configuration from backup
cp /backup/config/latest/app/* /app/config/
cp /backup/config/latest/nginx/* /etc/nginx/

# Decrypt and restore environment variables
gpg --decrypt /backup/config/latest/.env.gpg > /app/.env

# Restart services
systemctl restart nginx androidzen-api
```

#### Infrastructure Recovery

##### Server Replacement
1. **Provision new server** using infrastructure as code
2. **Restore application code** from Git repository
3. **Restore database** from latest backup
4. **Restore file storage** from S3/backup location
5. **Update DNS records** to point to new server
6. **Verify functionality** using health checks

##### Network Recovery
1. **Identify network issues** using monitoring tools
2. **Switch to backup network provider** if needed
3. **Update firewall rules** for new network configuration
4. **Test connectivity** from all critical paths

### 4. Communication Plan

#### Internal Communication
- **Slack**: #incident-response channel
- **Email**: engineering-alerts@androidzen.pro
- **Phone**: Conference bridge for P1 incidents

#### External Communication
- **Status Page**: status.androidzen.pro updates
- **Social Media**: Twitter @AndroidZenPro
- **Email**: Customer notification for prolonged outages

## RTO/RPO Targets

### Recovery Time Objectives (RTO)

| Component | P1 Incidents | P2 Incidents | P3 Incidents |
|-----------|-------------|-------------|-------------|
| API Service | 15 minutes | 1 hour | 4 hours |
| Database | 30 minutes | 2 hours | 8 hours |
| File Storage | 45 minutes | 2 hours | 12 hours |
| User Authentication | 10 minutes | 30 minutes | 2 hours |
| Background Jobs | 1 hour | 4 hours | 24 hours |
| Monitoring/Alerts | 2 hours | 8 hours | 48 hours |

### Recovery Point Objectives (RPO)

| Data Type | Maximum Data Loss | Backup Frequency |
|-----------|------------------|------------------|
| User Data | 15 minutes | Continuous replication |
| Transactions | 5 minutes | Real-time sync |
| User Files | 1 hour | Hourly incremental |
| Configuration | 24 hours | Daily backup |
| Logs/Analytics | 1 hour | Real-time streaming |
| System Metrics | 5 minutes | Continuous collection |

### Service Level Agreements

#### Availability Targets
- **Production**: 99.9% uptime (8.77 hours downtime/year)
- **Staging**: 99.0% uptime (87.7 hours downtime/year)
- **Development**: 95.0% uptime (438 hours downtime/year)

#### Performance Targets
- **API Response Time**: < 200ms (95th percentile)
- **Database Query Time**: < 100ms (95th percentile)
- **File Upload Time**: < 5 seconds for 10MB files

## Backup Verification Procedures

### 1. Automated Verification

#### Database Backup Verification
```bash
#!/bin/bash
# Daily backup verification script

BACKUP_FILE="/backup/postgres/$(date +%Y%m%d).dump"
TEST_DB="androidzen_test_restore"

# Create test database
createdb $TEST_DB

# Restore backup to test database
pg_restore -d $TEST_DB $BACKUP_FILE

# Run verification queries
RECORD_COUNT=$(psql -d $TEST_DB -t -c "SELECT COUNT(*) FROM users;")
INTEGRITY_CHECK=$(psql -d $TEST_DB -t -c "SELECT COUNT(*) FROM pg_stat_user_tables WHERE schemaname='public';")

# Cleanup
dropdb $TEST_DB

# Report results
echo "Backup verification completed: $RECORD_COUNT user records found"
if [ $INTEGRITY_CHECK -gt 0 ]; then
    echo "✅ Backup verification PASSED"
    exit 0
else
    echo "❌ Backup verification FAILED"
    exit 1
fi
```

#### File Storage Verification
```bash
#!/bin/bash
# File storage integrity check

STORAGE_PATH="/app/storage/uploads"
BACKUP_PATH="/backup/uploads/$(date +%Y%m%d)"

# Generate checksums
find $STORAGE_PATH -type f -exec md5sum {} \; > /tmp/storage_checksums.txt
find $BACKUP_PATH -type f -exec md5sum {} \; > /tmp/backup_checksums.txt

# Compare checksums
if diff /tmp/storage_checksums.txt /tmp/backup_checksums.txt > /dev/null; then
    echo "✅ File storage backup verification PASSED"
else
    echo "❌ File storage backup verification FAILED"
    diff /tmp/storage_checksums.txt /tmp/backup_checksums.txt
fi
```

### 2. Manual Verification

#### Weekly Backup Spot Checks
- **Database**: Restore random table and verify data integrity
- **Files**: Download random files and verify accessibility
- **Configuration**: Test configuration restoration on staging environment

#### Monthly Deep Verification
- **Full restore test** on isolated environment
- **Cross-region backup** accessibility verification
- **Encryption key rotation** and backup re-encryption test

### 3. Monitoring and Alerting

#### Backup Success/Failure Alerts
```yaml
# Prometheus alert rules
groups:
  - name: backup.alerts
    rules:
      - alert: BackupFailed
        expr: backup_success{job="backup"} == 0
        for: 5m
        labels:
          severity: critical
        annotations:
          summary: "Backup failed for {{ $labels.backup_type }}"
          
      - alert: BackupSizeAnomaly
        expr: backup_size_bytes < backup_size_bytes offset 7d * 0.8
        for: 10m
        labels:
          severity: warning
        annotations:
          summary: "Backup size significantly smaller than expected"
```

#### Verification Alerts
- Failed backup restoration tests
- Checksum mismatches in file storage
- Missing backup files beyond retention policy
- Encryption key access failures

## Recovery Testing Schedule

### 1. Testing Calendar

#### Daily Tests (Automated)
- **Backup verification**: Database and file integrity checks
- **Health checks**: All backup storage locations
- **Monitoring alerts**: Backup pipeline status

#### Weekly Tests
- **Partial restore**: Single table/collection restoration
- **File recovery**: Random file set restoration
- **Configuration restore**: Staging environment config update

#### Monthly Tests
- **Database point-in-time recovery**: Restore to specific timestamp
- **Cross-region failover**: Switch to backup cloud provider
- **Network failure simulation**: Test backup access during network issues

#### Quarterly Tests (Game Days)
- **Full disaster recovery drill**: Complete system restoration
- **Multi-component failure**: Simulate database + storage failure
- **Extended outage scenario**: Test backup systems under prolonged load

### 2. Testing Procedures

#### Game Day Scenario 1: Database Corruption
```markdown
**Scenario**: Primary database corrupted, needs restoration from backup

**Steps**:
1. Simulate database corruption in staging
2. Execute database recovery procedures
3. Verify data integrity and completeness
4. Measure RTO against targets
5. Document lessons learned

**Success Criteria**:
- RTO < 30 minutes
- RPO < 15 minutes
- Zero data corruption in restored database
```

#### Game Day Scenario 2: Multi-Zone Failure
```markdown
**Scenario**: Primary AWS region unavailable, failover to secondary region

**Steps**:
1. Disable primary region access
2. Activate disaster recovery procedures
3. Route traffic to backup region
4. Restore services from backups
5. Verify full functionality

**Success Criteria**:
- RTO < 1 hour
- All critical services operational
- User data accessible and consistent
```

#### Game Day Scenario 3: Ransomware Attack
```markdown
**Scenario**: File storage encrypted by ransomware, need clean restoration

**Steps**:
1. Isolate affected systems
2. Identify clean backup point before infection
3. Restore files from verified clean backups
4. Implement additional security measures
5. Verify system integrity

**Success Criteria**:
- Complete file restoration from clean backups
- No re-infection after restoration
- Security measures prevent similar attacks
```

### 3. Testing Documentation

#### Test Reports Template
```markdown
# Recovery Test Report

**Date**: YYYY-MM-DD
**Test Type**: [Daily/Weekly/Monthly/Quarterly]
**Scenario**: [Description]

## Execution Summary
- **Start Time**: HH:MM UTC
- **End Time**: HH:MM UTC
- **Duration**: X minutes
- **Outcome**: [PASS/FAIL/PARTIAL]

## Metrics
- **RTO Achieved**: X minutes (Target: Y minutes)
- **RPO Achieved**: X minutes (Target: Y minutes)
- **Data Integrity**: [PASS/FAIL]
- **Service Availability**: X%

## Issues Identified
1. Issue description
2. Root cause
3. Impact assessment
4. Remediation steps

## Improvements
- Process improvements
- Tool enhancements
- Documentation updates
- Training needs

## Sign-off
- **Test Lead**: [Name]
- **Operations Lead**: [Name]
- **Date**: YYYY-MM-DD
```

### 4. Continuous Improvement

#### Quarterly Reviews
- Analyze test results and trends
- Update RTO/RPO targets based on business needs
- Review and update recovery procedures
- Plan infrastructure improvements

#### Annual DR Planning
- Full disaster recovery plan review
- Backup strategy optimization
- Cost analysis and budget planning
- Team training and capability assessment

---

## Emergency Contacts and Resources

### Key Personnel
- **CTO**: [Name] - [Phone] - [Email]
- **DevOps Lead**: [Name] - [Phone] - [Email]
- **Database Administrator**: [Name] - [Phone] - [Email]
- **Infrastructure Lead**: [Name] - [Phone] - [Email]

### External Vendors
- **AWS Support**: Enterprise Support Case
- **Database Vendor**: Premium Support
- **Backup Software**: 24/7 Support Line

### Important URLs
- Status Page: https://status.androidzen.pro
- Monitoring Dashboard: https://monitoring.androidzen.pro
- Backup Management: https://backup.androidzen.pro
- Documentation: https://docs.androidzen.pro

---

*Last Updated: [Current Date]*
*Next Review Date: [Quarterly Review Date]*
*Document Owner: Infrastructure Team*
