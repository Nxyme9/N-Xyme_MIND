# Memory System Corruption Runbook

## Symptoms
- Agent reports "memory search failed" or "index corrupted"
- Unified memory returns stale or incorrect results
- `unified-memory_get_memory_stats` shows errors
- Memory write operations fail

## Diagnosis Steps

### 1. Check memory system status
```bash
python3 -c "from src.memory.unified_memory import UnifiedMemory; print('OK')"
```

### 2. Check memory stats
```bash
python3 -c "
from src.memory.unified_memory import UnifiedMemory
um = UnifiedMemory()
stats = um.get_memory_stats()
print(stats)
"
```

### 3. Check SQLite database integrity
```bash
sqlite3 .sisyphus/memory.db "PRAGMA integrity_check;"
sqlite3 .sisyphus/memory.db ".tables"
```

### 4. Check for locked files
```bash
lsof | grep memory.db
```

## Resolution

### Rebuild the memory index:
```bash
# Clear the memory database
rm -f .sisyphus/memory.db

# Rebuild from sources
python3 -c "
from src.memory.unified_memory import UnifiedMemory
um = UnifiedMemory()
# Re-index will happen automatically on first write
print('Memory index cleared. Rebuild on next write.')
"
```

### Re-sync from backup:
```bash
# Check for memory backups
ls -la .sisyphus/backups/memory*

# Restore from backup if available
cp .sisyphus/backups/memory-*.db .sisyphus/memory.db
```

### Clear specific memory types:
```bash
# Clear episodic memory only
python3 -c "
from src.memory.unified_memory import UnifiedMemory
um = UnifiedMemory()
um.clear_memory(scope='episodic')
print('Episodic memory cleared')
"
```

## Prevention
- Regular backups: `bash bin/backup-memory.sh`
- Monitor disk space
- Check memory health: `bash bin/health-l2-vitals.sh`
- Don't interrupt memory writes
