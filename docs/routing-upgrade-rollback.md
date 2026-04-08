# Routing Upgrade Rollback Procedures

This document describes how to rollback each component of the routing upgrade system to its previous stable state.

## 1. Disable Semantic Classifier (Fallback to Keyword Routing)

**File:** `config/routing.json`

```json
{
  "semantic_classifier": {
    "enabled": false
  },
  "keyword_fallback": {
    "enabled": true
  }
}
```

**Verification:**
```bash
curl -s http://localhost:8080/health | jq '.routing.mode'
# Expected: "keyword"
```

## 2. Disable Vector Q-Learning (Fallback to Hash-Based Routing)

**File:** `config/routing.json`

```json
{
  "q_learning": {
    "vector_enabled": false,
    "hash_based_fallback": true
  }
}
```

**Database:**
```sql
UPDATE routing_config 
SET active_strategy = 'hash_based' 
WHERE component = 'q_learning';
```

**Verification:**
```bash
curl -s http://localhost:8080/health | jq '.routing.strategy'
# Expected: "hash_based"
```

## 3. Disable Meta-Learning (MAML/EWC)

**File:** `config/routing.json`

```json
{
  "meta_learning": {
    "maml_enabled": false,
    "ewc_enabled": false,
    "warm_start": true
  }
}
```

**Reset weights:**
```bash
python3 bin/routing-dashboard.py --reset-weights
```

**Verification:**
```bash
python3 bin/routing-dashboard.py --status | grep meta_learning
# Expected: "disabled"
```

## 4. Revert Database Schema Changes

**Backup exists:** `backups/routing_db_pre_upgrade.sql`

```bash
# Stop service
systemctl stop routing-service

# Restore from backup
psql -U routing_user -d routing_db < backups/routing_db_pre_upgrade.sql

# Verify schema
psql -U routing_user -d routing_db -c "\d routing_config"
```

**Manual rollback SQL (if backup unavailable):**
```sql
-- Drop new columns
ALTER TABLE routing_outcomes DROP COLUMN IF EXISTS embedding_vector;
ALTER TABLE agent_performance DROP COLUMN IF EXISTS meta_weights;

-- Restore old constraints
ALTER TABLE routing_outcomes ADD CONSTRAINT old_pk PRIMARY KEY (task_id, timestamp);
```

## 5. Health Check for Downgrade Verification

```bash
#!/bin/bash
echo "=== Routing Downgrade Health Check ==="

# 1. Service health
curl -s http://localhost:8080/health | jq -e '.status == "healthy"'

# 2. Routing mode
MODE=$(curl -s http://localhost:8080/health | jq -r '.routing.mode')
[ "$MODE" = "keyword" ] || [ "$MODE" = "hash_based" ]

# 3. Q-Learning disabled
QL=$(curl -s http://localhost:8080/health | jq -r '.routing.q_learning')
[ "$QL" = "false" ]

# 4. Meta-learning disabled
ML=$(curl -s http://localhost:8080/health | jq -r '.meta_learning')
[ "$ML" = "false" ]

# 5. Database schema
psql -U routing_user -d routing_db -c "SELECT 1 FROM routing_config LIMIT 1"

echo "=== All checks passed ==="
```

**Run health check:**
```bash
chmod +x bin/routing-health-check.sh
./bin/routing-health-check.sh
```

## Rollback Quick Reference

| Component | Config Key | Rollback Command |
|-----------|-----------|------------------|
| Semantic Classifier | `semantic_classifier.enabled` | Set to `false` |
| Vector Q-Learning | `q_learning.vector_enabled` | Set to `false` |
| Meta-Learning (MAML) | `meta_learning.maml_enabled` | Set to `false` |
| Meta-Learning (EWC) | `meta_learning.ewc_enabled` | Set to `false` |
| Database | `routing_config` | Restore from backup |
