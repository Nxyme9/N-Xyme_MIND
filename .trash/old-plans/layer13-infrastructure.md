# N-Xyme MIND v1.0 — Layer 13: Infrastructure Implementation Plan

## Context

**Components to implement/enhance**:
1. vpn/rotator.py — ENHANCE existing (429-adaptive + weighted LB)
2. _bmad/ — ENHANCE existing (BMAD workflows + 46 skills)
3. bin/ — ENHANCE existing (CLI tools)
4. tests/ — EXPAND existing (test suite)

**Critical Gaps**:
- Health check endpoints (all services)
- Basic logging (file rotation + aggregation)
- Backup system (config + state export)
- systemd service configurations
- Docker Compose for portable deployment
- Monitoring/alerting integration (Prometheus + Loki)

**Repos to Study**:
- docker/awesome-compose — AI stack templates
- grafana/loki — Log aggregation
- prometheus/prometheus — Metrics collection
- KitOps ModelKit — OCI packaging for AI

---

## 1. Component-by-Component Breakdown

### 1.1 vpn/rotator.py (ENHANCE)

**Add**:
```python
class HealthCheck:
    """Health check for VPN providers."""
    def check_connectivity(self) -> bool
    def check_latency(self) -> float
    def check_bandwidth(self) -> float

class BackupManager:
    """Backup and restore for VPN configs."""
    def backup_configs(self, output_path: Path) -> None
    def restore_configs(self, input_path: Path) -> None
    def export_state(self) -> Dict
    def import_state(self, state: Dict) -> None
```

### 1.2 bin/ (ENHANCE CLI tools)

**Add**:
```python
# bin/nxyme-health
def check_all_services() -> Dict:
    """Check health of all N-Xyme services."""
    ...

# bin/nxyme-backup
def create_backup(output_path: Path) -> None:
    """Create full system backup."""
    ...

def restore_backup(input_path: Path) -> None:
    """Restore from backup."""
    ...

# bin/nxyme-logs
def aggregate_logs(since: str, until: str, level: str) -> None:
    """Aggregate and display logs."""
    ...
```

### 1.3 tests/ (EXPAND)

**Add**:
- `tests/integration/test_health.py` — Health check integration tests
- `tests/integration/test_backup.py` — Backup/restore integration tests
- `tests/integration/test_logging.py` — Logging integration tests
- `tests/smoke/test_startup.py` — Smoke test for startup
- `tests/smoke/test_shutdown.py` — Smoke test for shutdown

### 1.4 Infrastructure Files (NEW)

**Add**:
- `docker-compose.yml` — Docker Compose for portable deployment
- `Dockerfile` — Container image definition
- `systemd/n-xyme.service` — systemd service configuration
- `systemd/n-xyme-vpn.service` — VPN rotator service
- `scripts/backup.sh` — Backup script
- `scripts/restore.sh` — Restore script
- `scripts/health-check.sh` — Health check script
- `logging.conf` — Logging configuration (file rotation)

---

## 2. Dependencies

```
vpn/rotator.py ──► bin/ (CLI tools use rotator)
                 │
tests/ ──────────┤──► All components
                 │
docker-compose ──┤──► All services
                 │
systemd ─────────┤──► All services
```

---

## 3. Implementation Order

| Wave | Task | Depends On |
|------|------|------------|
| 1 | Health check endpoints | None |
| 1 | Logging configuration | None |
| 2 | Backup system | Health checks |
| 2 | CLI tools enhancement | Health checks, logging |
| 3 | systemd services | CLI tools |
| 3 | Docker Compose | All components |
| 4 | Test expansion | All components |

---

## 4. Test Strategy

- **Health checks**: All services respond correctly, degraded state detected
- **Backup/restore**: Full backup created, restored state matches original
- **Logging**: File rotation works, aggregation correct
- **systemd**: Services start/stop correctly, restart on failure
- **Docker Compose**: All services start, health checks pass

---

## 5. Success Criteria

| Component | Criteria |
|-----------|----------|
| Health checks | All services report health, degraded state detected |
| Logging | File rotation works, logs aggregated correctly |
| Backup/restore | Full backup created, restore matches original |
| CLI tools | All commands work, help text accurate |
| systemd | Services start/stop/restart correctly |
| Docker Compose | All services start, health checks pass |
| Tests | 100+ tests passing |
