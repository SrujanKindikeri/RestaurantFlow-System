# Recovery Testing Schedule & Procedures

**Purpose:** Ensure backup and recovery systems work as documented, before they are needed.

---

## Testing Schedule

| Test Type | Frequency | Owner | Environment |
|-----------|-----------|-------|-------------|
| Backup checksum verification | Monthly | System Administrator | Staging |
| Database restore drill | Quarterly | System Administrator | Staging (never production) |
| Media restore drill | Quarterly | System Administrator | Staging |
| Full DR exercise | Annual | All stakeholders | Staging |
| Backup staleness check | Automated (hourly) | CentralAlert | Production |
| Disaster recovery health check | Automated (every 15 min) | Backup container cron | Production |

---

## 1. Monthly Backup Verification Test

**Purpose:** Confirm that recent backup files are intact and checksums match.

**Prerequisites:** Access to backup storage, `verify-backup.sh` script.

**Steps:**

```bash
# 1. List recent backups
ls -la /backups/db_*.pgdump.gz.gpg | sort | tail -5

# 2. Verify the most recent database backup
export BACKUP_FILE=/backups/db_restaurantflow_<latest_timestamp>.pgdump.gz.gpg
export BACKUP_ENCRYPTION_KEY=<passphrase>
bash deployment/backup/scripts/verify-backup.sh

# 3. Verify the most recent media backup
export BACKUP_FILE=/backups/media_<latest_timestamp>.tar.gz
bash deployment/backup/scripts/verify-backup.sh

# 4. Check BackupRecord status in Django admin
# Expected: status = VERIFIED, verified_at is populated

# 5. Run the disaster recovery health check
export DB_HOST=localhost DB_PORT=5432 DB_USER=restaurantflow
export BACKUP_LOCAL_DIR=/backups
bash deployment/backup/scripts/disaster-recovery-check.sh
```

**Pass Criteria:**
- [ ] `verify-backup.sh` exits 0 for the most recent DB backup
- [ ] `verify-backup.sh` exits 0 for the most recent media backup
- [ ] `disaster-recovery-check.sh` exits 0
- [ ] `BackupRecord.status = VERIFIED` in admin for tested records
- [ ] No CentralAlerts active for BACKUP_NOT_VERIFIED or BACKUP_STALE

**Fail Criteria:**
- [ ] Any script exits non-zero
- [ ] Checksum mismatch detected
- [ ] No VERIFIED backup found within last 25 hours
- [ ] CentralAlert BACKUP_FAILED or BACKUP_STALE is active

**Record Results:**
```
Date: _______________
Tester: _______________
DB backup verified: Yes / No
Media backup verified: Yes / No
DR health check: Pass / Fail
Issues found: _______________
Actions taken: _______________
```

---

## 2. Quarterly Restore Drill

**Purpose:** Confirm that a database can be fully restored to a non-production environment and passes application health checks.

**Prerequisites:**
- A staging PostgreSQL instance (`restaurantflow_restore_test` database)
- Access to the most recent VERIFIED database backup
- `BACKUP_ENCRYPTION_KEY` and `DB_PASSWORD` available

**Steps:**

```bash
# 1. Create the restore test database (if not exists)
createdb -h staging-host -U restaurantflow restaurantflow_restore_test

# 2. Identify the most recent VERIFIED backup
curl -H "Authorization: Bearer <token>" \
    "https://api.staging.restaurantflow.app/api/backup/records/?backup_type=DATABASE_FULL&status=VERIFIED" \
    | python3 -m json.tool | head -40

# 3. Download backup if on S3
aws s3 cp s3://my-backup-bucket/restaurantflow/backups/db_<timestamp>.pgdump.gz.gpg /tmp/restore_test/

# 4. Verify backup before restoring
export BACKUP_FILE=/tmp/restore_test/db_restaurantflow_<timestamp>.pgdump.gz.gpg
export BACKUP_ENCRYPTION_KEY=<passphrase>
bash deployment/backup/scripts/verify-backup.sh

# 5. Restore to non-production target
export RESTORE_TARGET_DB=restaurantflow_restore_test
export DB_HOST=staging-host DB_PORT=5432
export DB_USER=restaurantflow DB_PASSWORD=<secret>
bash deployment/backup/scripts/restore-database.sh --confirm

# 6. Run application health checks against restored DB
DB_NAME=restaurantflow_restore_test python manage.py check
DB_NAME=restaurantflow_restore_test python manage.py migrate --check

# 7. Spot-check data integrity
psql -h staging-host -U restaurantflow restaurantflow_restore_test << EOF
SELECT COUNT(*) AS order_count FROM orders_order;
SELECT COUNT(*) AS payment_count FROM payments_payment;
SELECT MAX(created_at) AS most_recent_order FROM orders_order;
EOF

# 8. Record restore duration
# Note start and end time; compare against RTO target (4 hours)
```

**Media Restore Drill:**

```bash
export BACKUP_FILE=/backups/media_<timestamp>.tar.gz
export RESTORE_TARGET_DIR=/staging/mediafiles_restore_test
bash deployment/backup/scripts/restore-media.sh --confirm

# Verify file count
find /staging/mediafiles_restore_test -type f | wc -l
# Compare against expected count from database
```

**Pass Criteria:**
- [ ] Backup file verifies (checksum match)
- [ ] `restore-database.sh` exits 0
- [ ] `python manage.py check` passes against restored DB
- [ ] Data is present and consistent (order counts match expectations)
- [ ] Restore duration within RTO target (4 hours)
- [ ] Media file count matches database records

**Fail Criteria:**
- [ ] Restore fails or exits non-zero
- [ ] `manage.py check` fails (schema mismatch)
- [ ] Data integrity errors found
- [ ] Restore duration exceeds RTO target

**Record Results:**
```
Date: _______________
Tester: _______________
Backup file: _______________
Backup age at restore: _______________
Restore start time: _______________
Restore end time: _______________
Restore duration (minutes): _______________
RTO target met: Yes / No
Order count in restored DB: _______________
Data integrity check: Pass / Fail
Issues found: _______________
Actions taken: _______________
Next test date: _______________
```

---

## 3. Annual Full DR Exercise

**Purpose:** Test the complete disaster recovery process from scratch, as if the production environment is completely lost.

**Scope:**
- Provision a new server from scratch
- Deploy the full application stack
- Restore database and media from backup
- Verify all services are operational
- Measure actual RTO

**Steps:**

1. **Announce maintenance window** (1 day in advance)
2. **Provision a clean server** via cloud provider
3. **Deploy infrastructure** (Docker, docker-compose, monitoring)
4. **Restore database** (Scenario 1, Case B in `disaster_recovery_runbook.md`)
5. **Restore media files** (`media_restore.md`)
6. **Restore configuration** (from latest config backup)
7. **Start application** and run health checks
8. **Test end-to-end**: create an order, process a payment, check kitchen display
9. **Measure actual RTO** from "declared disaster" to "application fully functional"
10. **Debrief** within 24 hours: what went wrong, what took longer than expected

**Pass Criteria:**
- [ ] Application responds to `/health/ready/` within RTO target (4 hours)
- [ ] New order can be created, assigned to kitchen, marked complete
- [ ] Payment can be processed
- [ ] Admin dashboard accessible
- [ ] No data integrity errors
- [ ] All CentralAlerts resolved

**Record Results:**
```
Date: _______________
Exercise type: Full DR
Time disaster declared: _______________
Time application functional: _______________
Total RTO: _______________
RTO target met: Yes / No
Issues encountered: _______________
Follow-up items: _______________
```

---

## Responsibilities

| Role | Responsibility |
|------|---------------|
| System Administrator | Execute all backup verification and restore drills |
| Operations Manager | Approve test schedule, review results |
| Development Lead | Update procedures when application changes affect restore steps |
| All staff | Participate in annual DR exercise |

---

## Reporting Failed Tests

When any test fails:
1. Create a CentralIssue with category `SYSTEM`, severity `HIGH`
2. Document the failure in this document's results section
3. Assign to System Administrator for root cause analysis
4. Fix the issue before the next scheduled test
5. Run an unscheduled verification after the fix

Failures must not be silently ignored. The backup system is only reliable if tests are taken seriously.
