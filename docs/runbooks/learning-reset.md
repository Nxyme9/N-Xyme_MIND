# Learning Engine Reset Runbook

## Symptoms
- Agent routing decisions seem degraded
- Q-table shows inconsistent weights
- Learning stats show NaN or invalid values
- `learning-engine_status` returns errors

## Diagnosis Steps

### 1. Check learning engine status
```bash
python3 -c "
from src.learning.engine import LearningEngine
le = LearningEngine()
status = le.get_status()
print(status)
"
```

### 2. Check Q-table integrity
```bash
python3 -c "
import json
with open('.sisyphus/q_table.json') as f:
    data = json.load(f)
    print('Q-table valid:', type(data))
    print('Entries:', len(data))
"
```

### 3. Check for corrupted entries
```bash
python3 -c "
import json
with open('.sisyphus/q_table.json') as f:
    data = json.load(f)
    for k, v in data.items():
        if v.get('q_value') in [None, 'NaN', 'nan']:
            print(f'Corrupted: {k}')
"
```

### 4. Check learning stats
```bash
python3 -c "
from src.learning.engine import LearningEngine
le = LearningEngine()
stats = le.get_learning_stats()
print(stats)
"
```

## Resolution

### Clear Q-table:
```bash
# Backup current Q-table
cp .sisyphus/q_table.json .sisyphus/q_table.backup.json

# Clear Q-table (will rebuild from scratch)
echo '{}' > .sisyphus/q_table.json
```

### Reset learning weights:
```bash
# Reset to default weights
python3 -c "
from src.learning.engine import LearningEngine
le = LearningEngine()
le.reset_weights()
print('Learning weights reset to defaults')
"
```

### Full learning engine reset:
```bash
# Remove learning data
rm -f .sisyphus/q_table.json
rm -f .sisyphus/learning.db

# Restart to rebuild
pkill -f "learning" || true
python3 -m src.learning.engine &
```

## Prevention
- Monitor learning stats: `learning-engine_status`
- Regular Q-table backups
- Check for NaN values in logs
- Review routing decisions periodically
