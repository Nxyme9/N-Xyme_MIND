@{
    OrphanThreshold = 5
    StaleThresholdHours = 24
    ActiveThresholdHours = 1
    MaxAgeDays = 7
    HandoffDir = ".sisyphus/handoffs"
    LogDir = ".sisyphus"
    SpawnAgents = @("Sisyphus", "Prometheus")
    ErrorPrefix = "ERROR"
    WarningPrefix = "WARN"
    IndentSize = 4
}
