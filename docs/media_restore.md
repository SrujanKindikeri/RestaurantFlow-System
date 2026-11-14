# Media Files Restore Procedure

---

## When to Restore Media Files

Restore media files when:
- Accidental deletion of files in `backend/mediafiles/`
- Storage volume corruption
- Migration to a new server
- Disaster recovery: application container data lost
- Ransomware: restoring from a clean backup to a fresh volume

Do NOT restore media files:
- As a first response to application errors (diagnose the cause first)
- Over a volume that still contains valid, newer files without comparing contents first

---

## Pre-Restore Checklist

Before starting a restore:

- [ ] Identify the correct backup file (use `BackupRecord` list in Django admin or `/api/backup/records/`)
- [ ] Verify the backup file integrity: `bash verify-backup.sh` (or check `BackupRecord.status = VERIFIED`)
- [ ] Confirm the target directory is correct and is NOT the live production directory (unless intentional)
- [ ] Confirm you have sufficient disk space at the target (`df -h <target_dir>`)
- [ ] Notify all operators that media may be temporarily unavailable
- [ ] Take a snapshot/note of the current media file count for post-restore verification

---

## Step-by-Step Restore

### 1. Identify the backup to restore

```bash
# List recent media backups via the API
curl -H "Authorization: Bearer <token>" \
    https://api.restaurantflow.app/api/backup/records/?backup_type=MEDIA

# Or list files directly in the backup container
ls -la /backups/media_*.tar.gz | sort | tail -10
```

### 2. Verify the backup before restoring

```bash
export BACKUP_FILE=/backups/media_20250115T030000Z.tar.gz

# Check checksum
bash deployment/backup/scripts/verify-backup.sh
# Expected output: "Backup verification PASSED"
```

### 3. Choose a restore target (non-production first)

```bash
# For testing: restore to a staging directory
export RESTORE_TARGET_DIR=/staging/mediafiles

# For production: restore to the live media directory
# (only after verifying the backup in staging first)
export RESTORE_TARGET_DIR=/app/backend/mediafiles
```

### 4. Run the restore

```bash
export BACKUP_FILE=/backups/media_20250115T030000Z.tar.gz
export RESTORE_TARGET_DIR=/staging/mediafiles

bash deployment/backup/scripts/restore-media.sh --confirm
```

**PowerShell:**
```powershell
$env:BACKUP_FILE = "C:\backups\media_20250115T030000Z.tar.gz"
$env:RESTORE_TARGET_DIR = "C:\staging\mediafiles"
.\deployment\backup\scripts\restore-media.ps1 -Confirm
```

---

## Post-Restore Verification

### File count check

```bash
# Count files in restored directory
find /staging/mediafiles -type f | wc -l

# Compare against Django database count
python manage.py shell -c "
from django.db import connection
with connection.cursor() as cur:
    cur.execute(\"SELECT COUNT(*) FROM menu_menuitem WHERE image != ''\")
    print('DB records with images:', cur.fetchone()[0])
"
```

### Spot-check individual files

```bash
# Pick a few known file paths from the database and verify they exist
ls -la /staging/mediafiles/menu/items/
ls -la /staging/mediafiles/organizations/logos/
```

### Application serve check

If restoring to the live directory:
1. Restart the application container: `docker restart restaurantflow_app`
2. Load a page that serves a media file (e.g., menu item with an image)
3. Confirm the image loads (HTTP 200 from `/media/...`)

---

## Handling Partial Media Loss

If only a subset of files was lost (e.g., accidental deletion of a subdirectory):

1. Restore the full media backup to a temporary directory: `RESTORE_TARGET_DIR=/tmp/media_restore`
2. Copy only the missing files from the restored directory to production:
   ```bash
   rsync -av /tmp/media_restore/mediafiles/menu/items/ /app/backend/mediafiles/menu/items/
   ```
3. Verify the specific files are now accessible
4. Remove the temporary restore directory: `rm -rf /tmp/media_restore`

This approach avoids overwriting newer files that were not affected by the loss.
