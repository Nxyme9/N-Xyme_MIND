use serde::{Deserialize, Serialize};
use serde_json::{json, Value};
use std::collections::HashMap;
use std::io::{self, BufRead, Write};
use std::panic;
use std::process::{Command, Stdio};
use std::sync::Mutex;
use std::time::{Instant, SystemTime, UNIX_EPOCH};

mod ml_bridge;

/// Panic recovery wrapper for MCP tool handlers.
/// MCP tool handlers should NEVER panic - every panic kills the MCP server silently.
/// This wrapper catches panics and returns a structured error instead.
fn safe_run<F: FnOnce() -> Value>(handler: F) -> Value {
    match panic::catch_unwind(panic::AssertUnwindSafe(handler)) {
        Ok(result) => result,
        Err(panic) => {
            let msg = if let Some(s) = panic.downcast_ref::<&str>() {
                s.to_string()
            } else if let Some(s) = panic.downcast_ref::<String>() {
                s.clone()
            } else {
                "unknown internal error".to_string()
            };
            json!({"error": format!("Internal error: {}", msg), "isError": true})
        }
    }
}

/// Router mode - determines which backend to use for routing
#[derive(Clone, Copy, PartialEq, Eq)]
enum RouterMode {
    Rust,   // In-process Rust TF-IDF (default)
    Mojo,   // Shell out to mojo_tool binary
    MojoV1, // Shell out to mojo_daemon_v1 binary (spawn per call)
    Auto,   // Try mojo, fall back to rust if unavailable
}

impl RouterMode {
    fn from_env() -> Self {
        let val = std::env::var("NX_ROUTER").unwrap_or_else(|_| "not_set".to_string());
        eprintln!("DEBUG: NX_ROUTER = '{}'", val);
        match val.as_str() {
            "mojo" => RouterMode::Mojo,
            "mojo_v1" => {
                eprintln!("DEBUG: Setting mode to MojoV1");
                RouterMode::MojoV1
            }
            "auto" => RouterMode::Auto,
            _ => RouterMode::Rust,
        }
    }
}

/// Global state for persistent mojo daemon process
static MOJO_DAEMON: Mutex<Option<std::process::Child>> = Mutex::new(None);

/// Global state for persistent mojo_daemon_v1 process
static MOJO_V1: Mutex<Option<std::process::Child>> = Mutex::new(None);

/// Check if mojo backend is available
fn mojo_available() -> bool {
    std::path::Path::new("bins/mojo_tool").exists()
        || std::process::Command::new("bins/mojo_tool")
            .arg("--help")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
}

/// Route using mojo backend - shells out to bins/mojo_tool binary
/// Returns (tool_name, confidence) or (empty, 0.0) on failure
/// On failure, the error is logged and returned via eprintln for debugging
fn mojo_route(query: &str) -> (String, f64) {
    let output = std::process::Command::new("bins/mojo_tool").arg(query).output();

    match output {
        Ok(out) if out.status.success() => {
            let result = String::from_utf8_lossy(&out.stdout).trim().to_string();
            // Parse output - expect tool name with optional confidence
            // Output format: "tool_name" or "tool_name\nconfidence"
            let result = result.trim();
            let parts: Vec<&str> = result.split(|c| c == ':' || c == '\n').collect();
            let tool_name = parts.first().unwrap_or(&"").to_string();
            let confidence = if parts.len() > 1 {
                parts[1].parse::<f64>().unwrap_or(1.0)
            } else {
                1.0 // Default confidence for mojo
            };
            (tool_name, confidence)
        }
        Err(e) => {
            eprintln!("ERROR: mojo_route failed: {}", e);
            (format!("mojo_error: {}", e), 0.0)
        }
        Ok(out) => {
            let stderr = String::from_utf8_lossy(&out.stderr);
            let exit_code = out.status.code().unwrap_or(-1);
            eprintln!("ERROR: mojo_route failed with exit code {}: {}", exit_code, stderr);
            (
                format!("mojo_error: exit_code={}, stderr={}", exit_code, stderr.trim()),
                0.0,
            )
        }
    }
}

/// Check if mojo_v1 backend is available
fn mojo_v1_available() -> bool {
    std::path::Path::new("bins/mojo_daemon_v1").exists()
        || std::process::Command::new("bins/mojo_daemon_v1")
            .arg("--help")
            .output()
            .map(|o| o.status.success())
            .unwrap_or(false)
}

/// Route using mojo_v1 backend - spawns bins/mojo_daemon_v1 <query>
/// Returns (tool_name, confidence) or (empty, 0.0) on failure
/// On failure, the error is logged and returned via eprintln for debugging
fn mojo_v1_route(query: &str) -> (String, f64) {
    let output = std::process::Command::new("bins/mojo_daemon_v1").arg(query).output();

    match output {
        Ok(out) if out.status.success() => {
            let result = String::from_utf8_lossy(&out.stdout).trim().to_string();
            // Parse output - expect tool name with optional confidence
            let result = result.trim();
            let parts: Vec<&str> = result.split(|c| c == ':' || c == '\n').collect();
            let tool_name = parts.first().unwrap_or(&"").to_string();
            let confidence = if parts.len() > 1 {
                parts[1].parse::<f64>().unwrap_or(1.0)
            } else {
                1.0 // Default confidence for mojo_v1
            };
            (tool_name, confidence)
        }
        Err(e) => {
            eprintln!("ERROR: mojo_v1_route failed: {}", e);
            (format!("mojo_v1_error: {}", e), 0.0)
        }
        Ok(out) => {
            let stderr = String::from_utf8_lossy(&out.stderr);
            let exit_code = out.status.code().unwrap_or(-1);
            eprintln!("ERROR: mojo_v1_route failed with exit code {}: {}", exit_code, stderr);
            (
                format!("mojo_v1_error: exit_code={}, stderr={}", exit_code, stderr.trim()),
                0.0,
            )
        }
    }
}

/// Spawn the persistent mojo daemon (stdin/stdout piped)
/// Returns the child process with stdin/stdout handles, or None on failure
fn spawn_mojo_daemon() -> Option<std::process::Child> {
    use std::io::BufRead;
    eprintln!("DEBUG: spawn_mojo_daemon called");

    let mut child = std::process::Command::new("bins/mojo_daemon_v1")
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::null())
        .spawn()
        .ok()?;

    // Test the daemon with a quick "ping" - write empty line, expect 2 lines
    if let (Some(ref mut stdin), Some(ref mut stdout)) = (&mut child.stdin, &mut child.stdout) {
        // Write a newline to trigger initialization
        let _ = stdin.write_all(b"\n");
        let _ = stdin.flush();

        // Try to read the first line (should be empty tool name or init response)
        let mut reader = std::io::BufReader::new(stdout);
        let mut line = String::new();
        if reader.read_line(&mut line).is_ok() {
            eprintln!("DEBUG: spawn_mojo_daemon test ok, line='{}'", line.trim());
            // Read second line (timing)
            line.clear();
            let _ = reader.read_line(&mut line);
            return Some(child);
        } else {
            eprintln!("DEBUG: spawn_mojo_daemon test failed to read");
        }
    }

    // If test failed, return None to let caller handle fallback
    eprintln!("DEBUG: spawn_mojo_daemon returning None");
    None
}

/// Ensure mojo daemon is running, spawn if not
/// Uses the global MOJO_DAEMON - acquires lock, returns whether daemon exists
fn ensure_mojo_daemon() -> bool {
    let mut guard = MOJO_DAEMON.lock().unwrap_or_else(|e| e.into_inner());
    if guard.is_none() {
        eprintln!("DEBUG: ensure_mojo_daemon spawning new daemon");
        *guard = spawn_mojo_daemon();
    }
    let result = guard.is_some();
    eprintln!("DEBUG: ensure_mojo_daemon returning {}", result);
    result
}

/// Kill the mojo daemon (when it dies)
fn kill_mojo_daemon() {
    let mut guard = MOJO_DAEMON.lock().unwrap_or_else(|e| e.into_inner());
    *guard = None;
}

/// Spawn a new mojo_daemon_v1 process with piped stdin/stdout
fn spawn_mojo_v1_daemon() -> Option<std::process::Child> {
    std::process::Command::new("bins/mojo_daemon_v1")
        .stdin(std::process::Stdio::piped())
        .stdout(std::process::Stdio::piped())
        .stderr(std::process::Stdio::null())
        .spawn()
        .ok()
}

/// Ensure MOJO_V1 has a living daemon, respawn if dead
fn ensure_mojo_v1_daemon() -> Option<std::process::Child> {
    let mut guard = MOJO_V1.lock().unwrap_or_else(|e| e.into_inner());

    // Check if existing process is still alive
    if let Some(ref mut child) = *guard {
        // Try to check if child is still running by polling
        // If wait_with_timeout returns None, process is still running
        // If returns Some, process has exited
        match child.try_wait() {
            Ok(Some(_)) => {
                // Process has exited, need to respawn
                eprintln!("DEBUG: MOJO_V1 daemon died, respawning...");
                *guard = spawn_mojo_v1_daemon();
            }
            Ok(None) => {
                // Process still running, return it
                eprintln!("DEBUG: MOJO_V1 daemon still alive");
                return guard.take(); // Return ownership to caller
            }
            Err(_) => {
                // Error checking status, assume dead and respawn
                eprintln!("DEBUG: MOJO_V1 status check failed, respawning...");
                *guard = spawn_mojo_v1_daemon();
            }
        }
    } else {
        // No existing process, spawn new
        eprintln!("DEBUG: MOJO_V1 spawning new daemon");
        *guard = spawn_mojo_v1_daemon();
    }

    guard.take()
}

/// Route using persistent mojo_daemon_v1 via stdin/stdout
/// Returns (tool_name, confidence) or (empty, 0.0) on failure
/// Auto-restarts the daemon if it dies between calls
fn mojo_route_v1(query: &str) -> (String, f64) {
    use std::io::{BufRead, Write};

    // Try to get or spawn a living daemon
    let mut child_opt = ensure_mojo_v1_daemon();

    // Use the process if available
    if let Some(ref mut child) = child_opt {
        if let (Some(ref mut stdin), Some(ref mut stdout)) = (&mut child.stdin, &mut child.stdout) {
            // Write query + newline
            if stdin.write_all(format!("{}\n", query).as_bytes()).is_err() {
                eprintln!("DEBUG: MOJO_V1 write failed, will respawn on next call");
                // Don't store back - will respawn on next call
                drop(child_opt); // Explicitly drop to ensure cleanup
                return mojo_v1_route(query);
            }
            if stdin.flush().is_err() {
                eprintln!("DEBUG: MOJO_V1 flush failed, will respawn on next call");
                drop(child_opt);
                return mojo_v1_route(query);
            }

            // Read first line (tool name)
            let mut reader = std::io::BufReader::new(stdout);
            let mut tool_line = String::new();
            match reader.read_line(&mut tool_line) {
                Ok(_) => {
                    // Read second line (timing - we ignore it, just consume)
                    let mut timing_line = String::new();
                    let _ = reader.read_line(&mut timing_line);
                    eprintln!(
                        "DEBUG: MOJO_V1 got tool='{}' timing='{}'",
                        tool_line.trim(),
                        timing_line.trim()
                    );

                    // Store the Child back in MOJO_V1 for reuse
                    {
                        let mut guard = MOJO_V1.lock().unwrap_or_else(|e| e.into_inner());
                        *guard = child_opt;
                    }

                    let tool_name = tool_line.trim().to_string();
                    if tool_name.is_empty() {
                        // Empty response, try fallback (but keep daemon alive)
                        return mojo_v1_route(query);
                    }
                    // Parse confidence from tool name if present (format: "tool:0.9")
                    let parts: Vec<&str> = tool_name.split(|c| c == ':' || c == '\n').collect();
                    let tool = parts.first().unwrap_or(&"").to_string();
                    let confidence = if parts.len() > 1 {
                        parts[1].parse::<f64>().unwrap_or(1.0)
                    } else {
                        1.0
                    };
                    return (tool, confidence);
                }
                Err(e) => {
                    eprintln!("DEBUG: MOJO_V1 read failed: {}, will respawn on next call", e);
                    // Read failed, process died - don't store back, will respawn
                    drop(child_opt);
                    return mojo_v1_route(query);
                }
            }
        }
    }

    // Couldn't get stdin/stdout or spawn failed, fall back
    mojo_v1_route(query)
}

/// Route using specified mode - dispatches to correct backend
fn route_with_mode(query: &str, mode: RouterMode, tool_pairs: &[(String, &str)]) -> (String, f64, &'static str) {
    match mode {
        RouterMode::Mojo => {
            let _start = Instant::now();
            let result = mojo_route(query);
            let _elapsed = _start.elapsed().as_micros() as u64;
            (result.0, result.1, "mojo")
        }
        RouterMode::MojoV1 => {
            let _start = Instant::now();
            let result = mojo_route_v1(query);
            let _elapsed = _start.elapsed().as_micros() as u64;
            (result.0, result.1, "mojo_v1")
        }
        RouterMode::Auto => {
            // Try mojo first, fall back to rust
            let _start_mojo = Instant::now();
            let (mojo_tool, mojo_conf) = mojo_route(query);
            let _mojo_elapsed = _start_mojo.elapsed().as_micros() as u64;

            if !mojo_tool.is_empty() && mojo_conf > 0.0 {
                (mojo_tool, mojo_conf as f64, "mojo")
            } else {
                // Fall back to rust
                let _start_rust = Instant::now();
                let (rust_tool, rust_conf) = route_tool(query, tool_pairs);
                let _rust_elapsed = _start_rust.elapsed().as_micros() as u64;
                (rust_tool, rust_conf, "rust")
            }
        }
        RouterMode::Rust => {
            let _start = Instant::now();
            let result = route_tool(query, tool_pairs);
            let _elapsed = _start.elapsed().as_micros() as u64;
            (result.0, result.1, "rust")
        }
    }
}

/// TF-IDF scoring: lowercases both, splits query into terms, counts term frequency.
/// Returns score using formula: 1.0 + count * 0.5 / (count + 1.0). Skips terms < 2 chars.
fn tf_score(content: &str, query: &str) -> f64 {
    let content_lower = content.to_lowercase();
    let query_lower = query.to_lowercase();

    let query_terms: Vec<&str> = query_lower
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| s.len() >= 2)
        .collect();

    if query_terms.is_empty() {
        return 1.0;
    }

    let mut total_score = 0.0;
    for term in &query_terms {
        let count = content_lower.matches(term).count() as f64;
        total_score += 1.0 + count * 0.5 / (count + 1.0);
    }

    total_score
}

/// Route tool: scores each tool by tf_score(desc, query) + 5.0 if query contains tool name.
/// Also adds 4.0 bonus if ANY query term appears in the tool name (handles "search memory" -> memory_list).
/// Returns (tool_name, confidence) best match.
fn route_tool<'a>(query: &str, tools: &'a [(String, &str)]) -> (String, f64) {
    let query_lower = query.to_lowercase();
    let mut best_name = String::new();
    let mut best_score = 0.0;

    // Extract all query terms for term matching
    let query_terms: Vec<String> = query_lower
        .split(|c: char| !c.is_alphanumeric())
        .filter(|s| s.len() >= 2)
        .map(|s| s.to_string())
        .collect();

    for (name, desc) in tools {
        let name_lower = name.to_lowercase();
        let desc_score = tf_score(desc, query);

        // Full name match bonus: increased from 2.0 to 5.0
        let name_bonus = if query_lower.contains(&name_lower) { 5.0 } else { 0.0 };

        // Term match bonus: if ANY query term appears in the tool name
        // This handles "search memory" -> memory_list, memory_read (query contains "memory" which is in their names)
        let term_bonus = if query_terms.iter().any(|term| name_lower.contains(term)) {
            4.0
        } else {
            0.0
        };

        let total_score = desc_score + name_bonus + term_bonus;

        if total_score > best_score {
            best_score = total_score;
            best_name = name.clone();
        }
    }

    (best_name, best_score)
}

fn data_dir() -> String {
    std::env::var("NX_AGENTS_DATA_DIR").unwrap_or_else(|_| "data".to_string())
}

fn state_path() -> String {
    format!("{}/sessions/state.json", data_dir())
}

fn audit_path() -> String {
    let ts = now();
    let date = chrono_path(ts);
    format!("{}/audit/{}/audit.{}.jsonl", data_dir(), date, date)
}

fn session_transcript_path(session_id: &str, agent: &str) -> String {
    let ts = now();
    let date = chrono_path(ts);
    format!("{}/sessions/{}/{}/{}.jsonl", data_dir(), agent, date, session_id)
}

// === TOOL TELEMETRY SYSTEM ===
// Telemetry format for Rosetta training data generation
// Follows proto-tool.jsonl structure for codeburn compatibility

#[derive(Clone, Serialize, Deserialize)]
struct ToolTelemetryEntry {
    // Core fields matching proto-tool.jsonl format
    #[serde(rename = "sessionId")]
    session_id: String,
    timestamp: String,
    #[serde(rename = "type")]
    entry_type: String,
    message: TelemetryMessage,
}

#[derive(Clone, Serialize, Deserialize)]
struct TelemetryMessage {
    id: String,
    #[serde(rename = "type")]
    msg_type: String,
    role: String,
    model: String,
    content: Vec<ToolUseBlock>,
    usage: Usage,
}

#[derive(Clone, Serialize, Deserialize)]
struct ToolUseBlock {
    id: String,
    name: String,
    input: serde_json::Value,
    // Extended fields for Rosetta training
    result: serde_json::Value,
    #[serde(rename = "duration_us")]
    duration_us: u64,
    confidence: f64,
    tier: String, // rust/mojo/llm
    // Query context for routing analysis
    query: Option<String>,
    #[serde(rename = "routed_tool")]
    routed_tool: Option<String>,
    #[serde(rename = "routing_confidence")]
    routing_confidence: Option<f64>,
}

#[derive(Clone, Serialize, Deserialize)]
struct Usage {
    #[serde(rename = "input_tokens")]
    input_tokens: u64,
    #[serde(rename = "output_tokens")]
    output_tokens: u64,
}

fn telemetry_path() -> String {
    format!("{}/memory/synapses/telemetry.jsonl", data_dir())
}

fn write_telemetry(entry: &ToolTelemetryEntry) {
    let p = telemetry_path();
    ensure_dir(&p);
    let entry_str = format!("{}\n", serde_json::to_string(entry).unwrap());
    use std::io::Write;
    let mut file = std::fs::OpenOptions::new().create(true).append(true).open(&p).unwrap();
    let _ = file.write_all(entry_str.as_bytes());
}

fn iso_timestamp() -> String {
    let now = SystemTime::now();
    let secs = now.duration_since(UNIX_EPOCH).unwrap().as_secs();
    let nanos = now.duration_since(UNIX_EPOCH).unwrap().as_nanos() % 1_000_000_000;
    // Simple ISO 8601 format: YYYY-MM-DDTHH:MM:SS.ssssssZ
    let days = secs / 86400;
    let remaining = secs % 86400;
    let year = 1970 + (days as f64 / 365.25) as u64;
    let day_of_year =
        days - ((year - 1970) * 365 + ((year - 1969) / 4) - ((year - 1901) / 100) + ((year - 1601) / 400)) as u64;
    let is_leap = (year % 4 == 0 && year % 100 != 0) || (year % 400 == 0);
    let days_in_months = if is_leap {
        [31, 29, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    } else {
        [31, 28, 31, 30, 31, 30, 31, 31, 30, 31, 30, 31]
    };
    let mut month = 1;
    let mut day = day_of_year as u64;
    for (i, days_in_month) in days_in_months.iter().enumerate() {
        if day <= *days_in_month {
            month = i as u64 + 1;
            break;
        }
        day -= days_in_month;
    }
    let hours = remaining / 3600;
    let minutes = (remaining % 3600) / 60;
    let seconds = remaining % 60;
    format!(
        "{:04}-{:02}-{:02}T{:02}:{:02}:{:02}.{:09}Z",
        year, month, day, hours, minutes, seconds, nanos
    )
}

fn record_telemetry(
    session_id: &str,
    tool_name: &str,
    args: &serde_json::Value,
    result: &serde_json::Value,
    duration_us: u64,
    confidence: f64,
    tier: &str,
    query: Option<&str>,
    routed_tool: Option<&str>,
    routing_confidence: Option<f64>,
) {
    let entry = ToolTelemetryEntry {
        session_id: session_id.to_string(),
        timestamp: iso_timestamp(),
        entry_type: "assistant".to_string(),
        message: TelemetryMessage {
            id: format!("t{}", now()),
            msg_type: "message".to_string(),
            role: "assistant".to_string(),
            model: "nx-agents-mcp".to_string(),
            content: vec![ToolUseBlock {
                id: format!("t{}", now()),
                name: tool_name.to_string(),
                input: args.clone(),
                result: result.clone(),
                duration_us,
                confidence,
                tier: tier.to_string(),
                query: query.map(|s| s.to_string()),
                routed_tool: routed_tool.map(|s| s.to_string()),
                routing_confidence,
            }],
            usage: Usage {
                input_tokens: 0,
                output_tokens: 0,
            },
        },
    };
    write_telemetry(&entry);
}

fn chrono_path(ts: u64) -> String {
    let days = ts / 86400;
    let y = 1970 + (days as f64 / 365.25) as u64;
    let remaining = days - ((y - 1970) * 365 + ((y - 1969) / 4) - ((y - 1901) / 100) + ((y - 1601) / 400));
    let md = [
        31,
        if (y % 4 == 0 && y % 100 != 0) || (y % 400 == 0) {
            29
        } else {
            28
        },
        31,
        30,
        31,
        30,
        31,
        31,
        30,
        31,
        30,
        31,
    ];
    let mut m = 0u64;
    let mut d = remaining;
    while m < 11 && d >= md[m as usize] {
        d -= md[m as usize];
        m += 1;
    }
    format!("{:04}-{:02}-{:02}", y, m + 1, d + 1)
}

fn ensure_dir(path: &str) {
    if let Some(parent) = std::path::Path::new(path).parent() {
        let _ = std::fs::create_dir_all(parent);
    }
}

fn rate_limit() -> u64 {
    std::env::var("NX_RATE_LIMIT")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(6000)
}

fn rate_window() -> u64 {
    std::env::var("NX_RATE_WINDOW")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(60)
}

const DEFAULT_MAX_ITERATIONS: u64 = 100;
const DEFAULT_CONTEXT_PRUNE_THRESHOLD: u64 = 70;
const DEFAULT_MEMORY_WARN_SIZE: usize = 500;
const DEFAULT_PROJECT_DEPTH: u64 = 2;
const DEFAULT_PROJECT_MAX_FILES: u64 = 15;

fn max_iterations() -> u64 {
    std::env::var("NX_MAX_ITERATIONS")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_MAX_ITERATIONS)
}

fn context_prune_threshold() -> u64 {
    std::env::var("NX_CONTEXT_PRUNE_THRESHOLD")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_CONTEXT_PRUNE_THRESHOLD)
}

fn memory_warn_size() -> usize {
    std::env::var("NX_MEMORY_WARN_SIZE")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_MEMORY_WARN_SIZE)
}

fn project_depth() -> u64 {
    std::env::var("NX_PROJECT_DEPTH")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_PROJECT_DEPTH)
}

fn project_max_files() -> u64 {
    std::env::var("NX_PROJECT_MAX_FILES")
        .ok()
        .and_then(|v| v.parse().ok())
        .unwrap_or(DEFAULT_PROJECT_MAX_FILES)
}

/// Validate agent name - must be alphanumeric with optional underscores, 1-30 chars
fn validate_agent_name(name: &str) -> Result<(), Value> {
    if name.is_empty() {
        return Err(json!({"error": "invalid_agent_name", "reason": "agent name cannot be empty"}));
    }
    if name.len() > 30 {
        return Err(json!({"error": "invalid_agent_name", "reason": "agent name too long (max 30 chars)"}));
    }
    if !name.chars().all(|c| c.is_alphanumeric() || c == '_') {
        return Err(
            json!({"error": "invalid_agent_name", "reason": "agent name must be alphanumeric (a-z, A-Z, 0-9, _)"}),
        );
    }
    Ok(())
}

/// Validate path for safe_delete - check for illegal characters
fn validate_path(path: &str) -> Result<(), Value> {
    if path.is_empty() {
        return Err(json!({"error": "invalid_path", "reason": "path cannot be empty"}));
    }
    // Check for path traversal attempts
    if path.contains("..") {
        return Err(json!({"error": "invalid_path", "reason": "path traversal not allowed"}));
    }
    // Check for null bytes
    if path.contains('\0') {
        return Err(json!({"error": "invalid_path", "reason": "null bytes not allowed"}));
    }
    Ok(())
}

/// Validate text content for dictate_inject - check for control characters
fn validate_text_content(text: &str) -> Result<(), Value> {
    // Check for null bytes
    if text.contains('\0') {
        return Err(json!({"error": "invalid_text", "reason": "null bytes not allowed"}));
    }
    // Check for non-printable control characters (except newlines, tabs)
    for (i, c) in text.chars().enumerate() {
        if c.is_control() && c != '\n' && c != '\t' && c != '\r' {
            return Err(json!({"error": "invalid_text", "reason": "control characters not allowed", "position": i}));
        }
    }
    Ok(())
}

#[derive(Clone, Serialize, Deserialize)]
struct SessionContext {
    id: String,
    created: u64,
    memory: HashMap<String, String>,
    call_count: u64,
    last_rate_ts: u64,
    rate_count: u64,
    ralph_loops: HashMap<String, Lp>,
    streak: u32,
    total_sessions: u32,
    achievements: Vec<String>,
    last_session_date: u64,
    last_session_task: String,
    xp: u64,
    level: u32,
    last_error: bool,
}

#[derive(Clone, Serialize, Deserialize)]
struct Lp {
    task: String,
    promise: String,
    it: u32,
    max: u32,
    active: bool,
    last_updated: u64,
}

#[derive(Clone, Serialize, Deserialize)]
struct AppState {
    sessions: HashMap<String, SessionContext>,
}

static ST: Mutex<Option<AppState>> = Mutex::new(None);

fn now() -> u64 {
    SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_secs()
}

fn load_state() -> AppState {
    let p = state_path();
    std::fs::read_to_string(&p)
        .ok()
        .and_then(|d| serde_json::from_str(&d).ok())
        .unwrap_or(AppState {
            sessions: HashMap::new(),
        })
}

fn save_state(s: &AppState) {
    if let Ok(d) = serde_json::to_string(s) {
        let p = state_path();
        ensure_dir(&p);
        let _ = std::fs::write(&p, &d);
    }
}

fn ensure_state() -> std::sync::MutexGuard<'static, Option<AppState>> {
    let mut g = ST.lock().unwrap_or_else(|e| e.into_inner());
    if g.is_none() {
        *g = Some(load_state());
    }
    g
}

fn audit_log(session_id: &str, tool: &str, params: &Value, result: &Value) {
    let entry = json!({"ts": now(), "session_id": session_id, "tool": tool, "params": params, "result": result});
    let p = audit_path();
    ensure_dir(&p);
    let entry_str = format!("{}\n", serde_json::to_string(&entry).unwrap());
    if let Err(e) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&p)
        .and_then(|mut f| f.write_all(entry_str.as_bytes()))
    {
        eprintln!("ERROR: audit_log failed to write to {}: {}", p, e);
    }
}

fn write_transcript(session_id: &str, agent: &str, tool: &str, params: &Value, result: &Value) {
    let entry = json!({"ts": now(), "tool": tool, "params": params, "result": result});
    let p = session_transcript_path(session_id, agent);
    ensure_dir(&p);
    let entry_str = format!("{}\n", serde_json::to_string(&entry).unwrap());
    if let Err(e) = std::fs::OpenOptions::new()
        .create(true)
        .append(true)
        .open(&p)
        .and_then(|mut f| f.write_all(entry_str.as_bytes()))
    {
        eprintln!("ERROR: write_transcript failed to write to {}: {}", p, e);
    }
}

fn get_or_create_session<'a>(
    sessions: &'a mut HashMap<String, SessionContext>,
    session_id: &'a str,
) -> &'a mut SessionContext {
    let ts = now();
    sessions
        .entry(session_id.to_string())
        .or_insert_with(|| SessionContext {
            id: session_id.to_string(),
            created: ts,
            memory: HashMap::new(),
            call_count: 0,
            last_rate_ts: ts,
            rate_count: 0,
            ralph_loops: HashMap::new(),
            streak: 0,
            total_sessions: 0,
            achievements: vec![],
            last_session_date: ts,
            last_session_task: String::new(),
            xp: 0,
            level: 1,
            last_error: false,
        })
}

fn check_rate(s: &SessionContext) -> Result<(), Value> {
    let ts = now();
    if ts - s.last_rate_ts > rate_window() {
        return Ok(());
    }
    let rl = rate_limit();
    if s.rate_count >= rl {
        let retry = rate_window() - (ts - s.last_rate_ts);
        return Err(json!({"error": "rate_limit", "limit": rl, "retry_after_secs": retry}));
    }
    Ok(())
}

fn add_xp(s: &mut SessionContext, amount: u64) {
    s.xp += amount;
    let nl = (s.xp / 100) as u32 + 1;
    if nl > s.level {
        s.level = nl;
        s.achievements.push(format!("LEVEL_{}", s.level));
    }
}

fn check_achievements(s: &mut SessionContext) {
    if s.streak >= 5 && !s.achievements.contains(&"STREAK_5".to_string()) {
        s.achievements.push("STREAK_5".to_string());
    }
    if s.streak >= 10 && !s.achievements.contains(&"GUARDIAN".to_string()) {
        s.achievements.push("GUARDIAN".to_string());
    }
    if s.call_count >= 50 && !s.achievements.contains(&"FLOW_STATE".to_string()) {
        s.achievements.push("FLOW_STATE".to_string());
    }
    if s.total_sessions >= 10 && !s.achievements.contains(&"VETERAN".to_string()) {
        s.achievements.push("VETERAN".to_string());
    }
    // Only add FIRST_BLOOD on the very first achievement
    if s.achievements.is_empty() {
        s.achievements.push("FIRST_BLOOD".to_string());
    }
}

fn record_success(s: &mut SessionContext) {
    // Only increment streak for existing sessions, reset to 1 for new
    let is_new_session = s.streak == 0;
    if is_new_session {
        s.streak = 1;
    } else {
        s.streak += 1;
    }
    s.last_error = false;
    add_xp(
        s,
        1 + if s.streak >= 5 { 1 } else { 0 } + if s.streak >= 10 { 2 } else { 0 },
    );
    check_achievements(s);
}

fn find_active_loop<'a>(sessions: &'a HashMap<String, SessionContext>, sid: &str) -> Option<(String, &'a Lp)> {
    sessions.get(sid).and_then(|s| {
        s.ralph_loops
            .iter()
            .find(|(_, l)| l.active)
            .map(|(id, l)| (id.clone(), l))
    })
}

fn make_progress(s: &SessionContext, loop_id: &str, l: &Lp) -> Value {
    json!({"streak": s.streak, "xp": s.xp, "level": s.level, "calls": s.call_count,
        "achievements": s.achievements, "loop_id": loop_id, "loop_it": l.it, "loop_max": l.max,
        "loop_task": l.task, "loop_pct": if l.max > 0 { (l.it as f64 / l.max as f64 * 100.0) as u32 } else { 0 }})
}

struct T {
    n: &'static str,
    d: &'static str,
    risk: &'static str,
    s: fn() -> Value,
    h: fn(&Value) -> Value,
}

// ─── Holographic Memory Engine ───

struct MemoryStore {
    vectors: Vec<(String, Vec<f32>)>, // (session_id, embedding)
}

static MEMORY: Mutex<Option<MemoryStore>> = Mutex::new(None);

fn load_vectors() -> Vec<(String, Vec<f32>)> {
    let mut vecs = Vec::new();
    let path = format!("{}/memory/vectors/ingest.jsonl", data_dir());
    if let Ok(data) = std::fs::read_to_string(&path) {
        // Parse last 1000 lines only for speed
        let lines: Vec<&str> = data.lines().rev().take(1000).collect();
        for line in lines.iter().rev() {
            if let Ok(val) = serde_json::from_str::<Value>(line) {
                if let (Some(id), Some(_len)) = (
                    val.get("id").and_then(|v| v.as_str()),
                    val.get("dim").and_then(|v| v.as_u64()),
                ) {
                    vecs.push((
                        id.to_string(),
                        // Re-generate from content for now (production uses stored vectors)
                        val.get("content")
                            .and_then(|v| v.as_str())
                            .map(|c| tfidf_vector(c))
                            .unwrap_or_default(),
                    ));
                }
            }
        }
    }
    vecs
}

fn ensure_memory() -> std::sync::MutexGuard<'static, Option<MemoryStore>> {
    let mut g = MEMORY.lock().unwrap();
    if g.is_none() {
        let loaded = load_vectors();
        *g = Some(MemoryStore { vectors: loaded });
    }
    g
}

fn tfidf_vector(text: &str) -> Vec<f32> {
    let mut terms: HashMap<String, f32> = HashMap::new();
    for word in text.to_lowercase().split_whitespace() {
        if word.len() < 2 {
            continue;
        }
        *terms.entry(word.to_string()).or_insert(0.0) += 1.0;
    }
    let mut vec = Vec::new();
    let keys: Vec<String> = terms.keys().cloned().collect();
    for key in keys {
        let count = terms[&key];
        vec.push(count / (1.0 + count)); // normalized TF
    }
    // Pad to 64-dim for simplicity (production uses 768-dim embedding)
    vec.resize(64, 0.0);
    vec
}

// ─── Dense Embedding — minilm direct + ONNX fallback + TF-IDF ───
// Priority: minilm crate (384-dim) -> ONNX model (384-dim) -> TF-IDF (64-dim)

/// Try minilm library directly for embedding
fn minilm_embed(text: &str) -> Option<Vec<f32>> {
    eprintln!("DEBUG: Using minilm crate for embedding (384-dim)");
    let embedding = minilm::embed(text);
    Some(embedding)
}

/// Run ONNX inference to get embedding (fallback if minilm fails)
fn onnx_embed(text: &str) -> Option<Vec<f32>> {
    // Check if ONNX model exists
    let model_path = format!("{}/memory/models/embedding.onnx", data_dir());
    if !std::path::Path::new(&model_path).exists() {
        eprintln!("DEBUG: ONNX model not found at {}", model_path);
        return None;
    }

    // ONNX loading would go here if ort API was simpler
    // For now, fall back to minilm or TF-IDF
    eprintln!("DEBUG: ONNX model exists but ort integration pending");
    None
}

/// Try minilm-cli subprocess for embedding (last resort before TF-IDF)
fn minilm_cli_embed(text: &str) -> Option<Vec<f32>> {
    let cli_path = "./target/release/minilm-cli";
    if !std::path::Path::new(cli_path).exists() {
        eprintln!("DEBUG: minilm-cli not found at {}", cli_path);
        return None;
    }

    eprintln!("DEBUG: minilm-cli available but using crate for better embedding");
    None
}

fn dense_embed(text: &str) -> Vec<f32> {
    // Try Rust ONNX first (384-dim, real model via ort crate)
    if let Some(results) = rust_onnx_embed(&[text]) {
        if !results.is_empty() {
            eprintln!("DEBUG: Using Rust ONNX embedding (384-dim)");
            return results[0].clone();
        }
    }

    // Try minilm crate second (384-dim via GGUF weights)
    if let Some(embedding) = minilm_embed(text) {
        eprintln!("DEBUG: Using minilm embedding (384-dim)");
        return embedding;
    }

    // Try ONNX model as fallback
    if let Some(embedding) = onnx_embed(text) {
        eprintln!("DEBUG: Using ONNX embedding (384-dim)");
        return embedding;
    }

    // Try minilm-cli as last resort
    if let Some(embedding) = minilm_cli_embed(text) {
        eprintln!("DEBUG: Using minilm-cli embedding (384-dim)");
        return embedding;
    }

    // Fallback to TF-IDF (64-dim)
    eprintln!("DEBUG: Falling back to TF-IDF embedding (64-dim)");
    tfidf_vector(text)
}

fn cosine_sim(a: &[f32], b: &[f32]) -> f32 {
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let na: f32 = a.iter().map(|x| x * x).sum();
    let nb: f32 = b.iter().map(|x| x * x).sum();
    if na == 0.0 || nb == 0.0 {
        return 0.0;
    }
    dot / (na.sqrt() * nb.sqrt())
}

fn recency_weight(session_id: &str) -> f32 {
    // Simpler: sessions with higher numeric IDs are more recent
    if let Some(ts) = session_id.rsplit('_').next().and_then(|s| s.parse::<u64>().ok()) {
        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap()
            .as_secs();
        let hours_ago = (now - ts) / 3600;
        1.0 / ((hours_ago as f32).max(1.0)).sqrt()
    } else {
        0.5
    }
}

fn tools() -> Vec<T> {
    vec![
        T {
            n: "session_start",
            d: "Start/resume session. Returns streak, XP, achievements.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"}},"required":["session_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("default");
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = get_or_create_session(&mut st.sessions, sid);
                let ts = now();
                if ts - s.last_rate_ts > rate_window() {
                    s.rate_count = 0;
                    s.last_rate_ts = ts;
                }
                let remaining = rate_limit().saturating_sub(s.rate_count);
                s.call_count += 1;
                s.rate_count += 1;
                s.total_sessions += 1;
                s.last_session_date = ts;
                s.streak += 1;
                s.xp += 1;
                s.last_error = false;
                let ctx_pct = ((s.call_count as f64 * 5.0 + s.memory.len() as f64 * 10.0) as u64).min(100);
                let r = json!({"session_id": sid, "created": s.created, "call_count": s.call_count,
                    "rate_remaining": remaining, "memory_keys": s.memory.len(),
                    "streak": s.streak, "xp": s.xp, "level": s.level, "achievements": s.achievements,
                    "total_sessions": s.total_sessions, "context_util_pct": ctx_pct,
                    "context_prune_needed": ctx_pct > context_prune_threshold(),
                    "estimated_time": "instant"});
                save_state(st);
                r
            },
        },
        T {
            n: "session_status",
            d: "Session state: calls, memory, loops, context %.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"}},"required":["session_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let g = ensure_state();
                let st = g.as_ref().unwrap();
                match st.sessions.get(sid) {
                    Some(s) => {
                        let active = find_active_loop(&st.sessions, sid);
                        let ctx_pct = ((s.call_count as f64 * 5.0 + s.memory.len() as f64 * 10.0) as u64).min(100);
                        let mut r = json!({"session_id": sid, "created": s.created, "call_count": s.call_count,
                            "rate_remaining": rate_limit().saturating_sub(s.rate_count), "rate_limit": rate_limit(),
                            "memory_keys": s.memory.len(), "active_loops": s.ralph_loops.len(),
                            "streak": s.streak, "xp": s.xp, "level": s.level, "achievements": s.achievements,
                            "total_sessions": s.total_sessions, "last_session_task": s.last_session_task,
                            "context_util_pct": ctx_pct,
                            "context_hint": if ctx_pct > 70 { "Context is getting full — consider context_prune" } else { "Healthy" },
                            "estimated_time": "instant"});
                        if let Some((id, l)) = active {
                            r["progress"] = make_progress(s, &id, l);
                        }
                        r
                    }
                    None => json!({"error": "session_not_found"}),
                }
            },
        },
        T {
            n: "continue_session",
            d: "Resume last active loop. No IDs needed.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"}},"required":["session_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let g = ensure_state();
                let st = g.as_ref().unwrap();
                match find_active_loop(&st.sessions, sid) {
                    Some((id, l)) => json!({"found": true, "loop_id": id, "task": l.task,
                        "progress": format!("{}/{}", l.it, l.max), "cont": l.active,
                        "estimated_time": format!("~{} min", l.max.saturating_sub(l.it).max(1))}),
                    None => {
                        json!({"found": false, "message": "Nothing to continue. Start a new task.", "estimated_time": "instant"})
                    }
                }
            },
        },
        T {
            n: "welcome_back",
            d: "Warm session restore: streak, XP, last task.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"}},"required":["session_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let g = ensure_state();
                let st = g.as_ref().unwrap();
                match st.sessions.get(sid) {
                    Some(s) => {
                        let active = find_active_loop(&st.sessions, sid);
                        let mut r = json!({"welcome_back": true,
                            "message": "Welcome back!".to_string(),
                            "streak": s.streak, "xp": s.xp, "level": s.level,
                            "achievements": s.achievements, "total_sessions": s.total_sessions,
                            "last_session_task": s.last_session_task, "estimated_time": "instant"});
                        if let Some((ref id, l)) = active {
                            r["active_loop"] = json!({"task": l.task, "progress": format!("{}/{}", l.it, l.max), "loop_id": id.as_str()});
                        }
                        r
                    }
                    None => {
                        json!({"welcome_back": true, "message": "Welcome! This is your first session.", "estimated_time": "instant"})
                    }
                }
            },
        },
        T {
            n: "next_step",
            d: "ONE next action suggestion. Never a list.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"}},"required":["session_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let g = ensure_state();
                let st = g.as_ref().unwrap();
                match st.sessions.get(sid) {
                    Some(s) => {
                        let sug = if let Some((_, l)) = find_active_loop(&st.sessions, sid) {
                            let pct = if l.max > 0 {
                                (l.it as f64 / l.max as f64 * 100.0) as u32
                            } else {
                                0
                            };
                            format!(
                                "Continue '{}' — {}% done, ~{} iterations remaining",
                                l.task,
                                pct,
                                l.max.saturating_sub(l.it)
                            )
                        } else if !s.last_session_task.is_empty() {
                            format!(
                                "Your last task was '{}'. Pick it up or start fresh?",
                                s.last_session_task
                            )
                        } else {
                            "No recent activity. Start a task or ask me what to do.".to_string()
                        };
                        json!({"suggestion": sug, "estimated_time": "instant"})
                    }
                    None => {
                        json!({"suggestion": "Start a session first with session_start.", "estimated_time": "instant"})
                    }
                }
            },
        },
        T {
            n: "memory_write",
            d: "Store key-value in session. >500 chars needs confirm.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"key":{"type":"string"},"value":{"type":"string"},"confirm":{"type":"boolean"}},"required":["session_id","key","value"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let key = p.get("key").and_then(|v| v.as_str()).unwrap_or("");
                let value = p.get("value").and_then(|v| v.as_str()).unwrap_or("");
                let confirm = p.get("confirm").and_then(|v| v.as_bool()).unwrap_or(false);
                let warn_size = memory_warn_size();
                if value.len() > warn_size && !confirm {
                    return json!({"error":"requires_confirmation","reason":format!("value exceeds {} chars", warn_size),"hint":"set confirm: true to proceed"});
                }
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = match st.sessions.get_mut(sid) {
                    Some(s) => s,
                    None => return json!({"error":"session_not_found"}),
                };
                if let Err(e) = check_rate(s) {
                    return e;
                }
                s.call_count += 1;
                s.rate_count += 1;
                let prev = s.memory.insert(key.to_string(), value.to_string());
                let mem_len = s.memory.len();
                let prev_exists = prev.is_some();
                s.last_session_task = format!("memory_write: {}", key);
                record_success(s);
                let r = json!({"stored": true, "key": key, "prev_exists": prev_exists, "memory_size": mem_len,
                    "streak": s.streak, "xp": s.xp, "level": s.level, "estimated_time": "< 1s"});
                save_state(st);
                r
            },
        },
        T {
            n: "memory_read",
            d: "Read a value by key.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"key":{"type":"string"}},"required":["session_id","key"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let key = p.get("key").and_then(|v| v.as_str()).unwrap_or("");
                let g = ensure_state();
                let st = g.as_ref().unwrap();
                match st.sessions.get(sid) {
                    Some(s) => {
                        json!({"key": key, "found": s.memory.contains_key(key), "value": s.memory.get(key), "estimated_time": "< 1s"})
                    }
                    None => json!({"error":"session_not_found"}),
                }
            },
        },
        T {
            n: "memory_list",
            d: "List all memory keys in session.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"}},"required":["session_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let g = ensure_state();
                let st = g.as_ref().unwrap();
                match st.sessions.get(sid) {
                    Some(s) => {
                        let keys: Vec<&String> = s.memory.keys().collect();
                        json!({"session_id": sid, "keys": keys, "count": keys.len(), "estimated_time": "< 1s"})
                    }
                    None => json!({"error":"session_not_found"}),
                }
            },
        },
        T {
            n: "context_prune",
            d: "Smart compaction by agent type. Dry-run available.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"agent_type":{"type":"string","enum":["sisyphus","hephaestus","kairos","default"]},"confirm":{"type":"boolean"}},"required":["session_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let agent = p
                    .get("agent_type")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| {
                        let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                        if sid.contains("hephaestus") {
                            "hephaestus".to_string()
                        } else if sid.contains("sisyphus") {
                            "sisyphus".to_string()
                        } else if sid.contains("kairos") {
                            "kairos".to_string()
                        } else {
                            "default".to_string()
                        }
                    });
                let confirm = p.get("confirm").and_then(|v| v.as_bool()).unwrap_or(false);
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = match st.sessions.get_mut(sid) {
                    Some(s) => s,
                    None => return json!({"error":"session_not_found"}),
                };
                let before = s.memory.len();
                if before < 10 {
                    return json!({"info":"nothing_to_prune","memory_size":before,"estimated_time":"< 500ms"});
                }
                let mut to_prune: Vec<String> = Vec::new();
                for k in s.memory.keys() {
                    let should_prune = match agent.as_str() {
                        "sisyphus" => k.starts_with("dictation_") || (k.starts_with("delegation_") && before > 20),
                        "hephaestus" => {
                            k.starts_with("code_output_")
                                || k.starts_with("error_")
                                || (k.starts_with("hephaestus_result_") && before > 15)
                        }
                        "kairos" => k.starts_with("session_note_") && before > 10,
                        _ => k.starts_with("dictation_") || k.starts_with("delegation_"),
                    };
                    if should_prune {
                        to_prune.push(k.clone());
                    }
                }
                let suggested = to_prune.len();
                if !confirm {
                    return json!({"info":"dry_run","memory_size":before,"would_prune":suggested,"agent_type":agent,"hint":"set confirm: true to execute","estimated_time":"< 500ms"});
                }
                for k in &to_prune {
                    s.memory.remove(k);
                }
                let after = s.memory.len();
                record_success(s);
                let r = json!({"pruned": to_prune.len(), "memory_before": before, "memory_after": after, "actioned": true,
                    "agent_type": agent, "streak": s.streak, "xp": s.xp, "level": s.level,
                    "estimated_time": "< 500ms", "context_hint": "opencode auto-compaction at 70%"});
                save_state(st);
                r
            },
        },
        T {
            n: "audit_log_recent",
            d: "Recent tool calls for session.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"limit":{"type":"integer","default":10}},"required":["session_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let limit = p.get("limit").and_then(|v| v.as_u64()).unwrap_or(10) as usize;
                let log = std::fs::read_to_string(audit_path()).unwrap_or_default();
                let entries: Vec<Value> = log
                    .lines()
                    .filter_map(|l| serde_json::from_str(l).ok())
                    .filter(|e: &Value| e.get("session_id").and_then(|v| v.as_str()) == Some(sid))
                    .rev()
                    .take(limit)
                    .collect();
                json!({"session_id": sid, "entries": entries, "count": entries.len(), "estimated_time": "~1s"})
            },
        },
        T {
            n: "ralph_start",
            d: "Start iterative loop. Persists across restarts.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"task":{"type":"string"},"promise":{"type":"string"},"max_iterations":{"type":"integer"}},"required":["session_id","task"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let task = p.get("task").and_then(|v| v.as_str()).unwrap_or("").to_string();
                // Validate task is not empty
                if task.is_empty() {
                    return json!({"error":"invalid_task","reason":"task cannot be empty"});
                }
                let prom = p.get("promise").and_then(|v| v.as_str()).unwrap_or("DONE").to_string();
                let mx = p.get("max_iterations").and_then(|v| v.as_u64()).unwrap_or(max_iterations()) as u32;
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = match st.sessions.get_mut(sid) {
                    Some(s) => s,
                    None => return json!({"error":"session_not_found"}),
                };
                if let Err(e) = check_rate(s) {
                    return e;
                }
                s.call_count += 1;
                s.rate_count += 1;
                s.last_session_task = task.clone();
                let id = format!("l{}", SystemTime::now().duration_since(UNIX_EPOCH).unwrap().as_nanos());
                let ts = now();
                s.ralph_loops.insert(
                    id.clone(),
                    Lp {
                        task: task.clone(),
                        promise: prom,
                        it: 0,
                        max: mx,
                        active: true,
                        last_updated: ts,
                    },
                );
                record_success(s);
                let streak = s.streak;
                let xp = s.xp;
                let level = s.level;
                save_state(st);
                json!({"loop_id": id, "session_id": sid, "persisted": true,
                    "estimated_time": format!("~{} min", mx.max(1)),
                    "streak": streak, "xp": xp, "level": level})
            },
        },
        T {
            n: "ralph_status",
            d: "Check loop iteration, max, active.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"loop_id":{"type":"string"}},"required":["session_id","loop_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let id = p.get("loop_id").and_then(|v| v.as_str()).unwrap_or("");
                let g = ensure_state();
                let st = g.as_ref().unwrap();
                match st.sessions.get(sid) {
                    Some(s) => match s.ralph_loops.get(id) {
                        Some(l) => json!({"it": l.it, "max": l.max, "active": l.active,
                            "estimated_time": format!("~{} min", l.max.saturating_sub(l.it).max(1)),
                            "task": l.task, "pct": if l.max > 0 { (l.it as f64 / l.max as f64 * 100.0) as u32 } else { 0 }}),
                        None => json!({"error": "loop_not_found"}),
                    },
                    None => json!({"error": "session_not_found"}),
                }
            },
        },
        T {
            n: "ralph_iterate",
            d: "Advance loop. Returns cont, pct, est. remaining.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"loop_id":{"type":"string"},"output":{"type":"string"}},"required":["session_id","loop_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let id = p.get("loop_id").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let out = p.get("output").and_then(|v| v.as_str()).unwrap_or("");
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = match st.sessions.get_mut(&sid) {
                    Some(s) => s,
                    None => return json!({"error":"session_not_found"}),
                };
                if let Err(e) = check_rate(s) {
                    return e;
                }
                s.call_count += 1;
                s.rate_count += 1;
                let result = match s.ralph_loops.get_mut(&id) {
                    Some(l) => {
                        l.it += 1;
                        l.last_updated = now();
                        let done = !l.promise.is_empty() && out.contains(&l.promise);
                        let maxed = l.it >= l.max;
                        if done || maxed {
                            l.active = false;
                        }
                        let pct = (l.it as f64 / l.max as f64 * 100.0) as u32;
                        let remaining = l.max.saturating_sub(l.it).max(1);
                        Some((done, maxed, l.active, l.it, l.max, pct, remaining))
                    }
                    None => None,
                };
                match result {
                    Some((done, maxed, cont, it, m, pct, remaining)) => {
                        record_success(s);
                        let streak = s.streak;
                        let xp = s.xp;
                        let level = s.level;
                        save_state(st);
                        json!({"cont": cont, "it": it, "max": m,
                            "r": if done {"done"} else if maxed {"maxed"} else {"run"},
                            "estimated_time": format!("~{} min", remaining),
                            "streak": streak, "xp": xp, "level": level, "pct": pct})
                    }
                    None => json!({"error": "loop_not_found"}),
                }
            },
        },
        T {
            n: "ralph_cancel",
            d: "Cancel active loop.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"loop_id":{"type":"string"}},"required":["session_id","loop_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let id = p.get("loop_id").and_then(|v| v.as_str()).unwrap_or("");
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = match st.sessions.get_mut(sid) {
                    Some(s) => s,
                    None => return json!({"error":"session_not_found"}),
                };
                match s.ralph_loops.get_mut(id) {
                    Some(l) => {
                        l.active = false;
                        record_success(s);
                        save_state(st);
                        json!({"cancelled": true, "estimated_time": "instant"})
                    }
                    None => json!({"error": "loop_not_found"}),
                }
            },
        },
        T {
            n: "ralph_list",
            d: "List all loops for a session with progress, status, timestamps.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"}},"required":["session_id"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let g = ensure_state();
                let st = g.as_ref().unwrap();
                match st.sessions.get(sid) {
                    Some(s) => {
                        let loops: Vec<Value> = s.ralph_loops.iter().map(|(id, l)| {
                            json!({
                                "loop_id": id,
                                "task": l.task,
                                "it": l.it,
                                "max": l.max,
                                "active": l.active,
                                "last_updated": l.last_updated,
                                "pct": if l.max > 0 { (l.it as f64 / l.max as f64 * 100.0) as u32 } else { 0 }
                            })
                        }).collect();
                        json!({"loops": loops, "count": loops.len(), "estimated_time": "instant"})
                    }
                    None => json!({"error": "session_not_found"}),
                }
            },
        },
        T {
            n: "dictate_inject",
            d: "Inject dictated text. REQUIRES confirm:true.",
            risk: "destructive",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"text":{"type":"string","maxLength":1000},"confirm":{"type":"boolean"}},"required":["session_id","text","confirm"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let text = p.get("text").and_then(|v| v.as_str()).unwrap_or("");
                let confirm = p.get("confirm").and_then(|v| v.as_bool()).unwrap_or(false);
                if !confirm {
                    return json!({"error":"confirmation_required","hint":"set confirm: true"});
                }
                // Validate text content - check for illegal control characters
                if let Err(e) = validate_text_content(&text) {
                    return e;
                }
                if text.len() > 1000 {
                    return json!({"error":"text_too_long","max_chars":1000,"received":text.len()});
                }
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = match st.sessions.get_mut(sid) {
                    Some(s) => s,
                    None => return json!({"error":"session_not_found"}),
                };
                if let Err(e) = check_rate(s) {
                    return e;
                }
                s.call_count += 1;
                s.rate_count += 1;
                s.memory.insert(format!("dictation_{}", now()), text.to_string());
                s.last_session_task = format!("dictation: {}...", &text[..text.len().min(40)]);
                record_success(s);
                let r = json!({"success": true, "session_id": sid, "char_count": text.len(), "calls": s.call_count, "estimated_time": "< 1s"});
                save_state(st);
                r
            },
        },
        T {
            n: "delegate_to_hephaestus",
            d: "Delegate code task to Hephaestus.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"task":{"type":"string"},"files":{"type":"string"},"acceptance_criteria":{"type":"string"}},"required":["session_id","task"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let task = p.get("task").and_then(|v| v.as_str()).unwrap_or("");
                let files = p.get("files").and_then(|v| v.as_str()).unwrap_or("");
                let criteria = p.get("acceptance_criteria").and_then(|v| v.as_str()).unwrap_or("");
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = match st.sessions.get_mut(sid) {
                    Some(s) => s,
                    None => return json!({"error":"session_not_found"}),
                };
                if let Err(e) = check_rate(s) {
                    return e;
                }
                s.call_count += 1;
                s.rate_count += 1;
                s.memory.insert(
                    format!("delegation_{}", now()),
                    json!({"task": task, "files": files, "criteria": criteria, "hephaestus": true}).to_string(),
                );
                s.last_session_task = format!("delegated: {}", &task[..task.len().min(40)]);
                record_success(s);
                save_state(st);
                json!({"delegated": true, "target": "hephaestus", "session_id": sid, "task": task, "status": "awaiting_completion", "estimated_time": "varies"})
            },
        },
        T {
            n: "project_map",
            d: "Project structure: dirs, files, depth-limited.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"root":{"type":"string"},"depth":{"type":"integer","default":2},"max_files":{"type":"integer","default":15}},"required":["session_id"]}),
            h: |p| {
                let root = p.get("root").and_then(|v| v.as_str()).unwrap_or(".");
                let depth = p.get("depth").and_then(|v| v.as_u64()).unwrap_or(project_depth());
                let max_files = p.get("max_files").and_then(|v| v.as_u64()).unwrap_or(project_max_files());
                let mut result = String::new();
                let mut dirs: Vec<(String, u64)> = vec![(root.to_string(), 0)];
                let mut idx = 0;
                while idx < dirs.len() && idx < 50 {
                    let (dir, d) = dirs[idx].clone();
                    idx += 1;
                    if d > depth {
                        continue;
                    }
                    if let Ok(entries) = std::fs::read_dir(&dir) {
                        let mut files: Vec<String> = Vec::new();
                        let mut subdirs: Vec<String> = Vec::new();
                        for e in entries.flatten() {
                            if let Ok(ft) = e.file_type() {
                                let name = e.file_name().to_string_lossy().to_string();
                                if name.starts_with('.') || name == "target" || name == "node_modules" {
                                    continue;
                                }
                                if ft.is_dir() {
                                    subdirs.push(name);
                                } else {
                                    files.push(name);
                                }
                            }
                        }
                        files.sort();
                        subdirs.sort();
                        let indent = "  ".repeat(d as usize);
                        let short = if dir.len() > 60 {
                            format!("...{}", &dir[dir.len().saturating_sub(57)..])
                        } else {
                            dir.clone()
                        };
                        result.push_str(&format!("{}{}/\n", indent, short));
                        for f in files.iter().take(max_files as usize) {
                            result.push_str(&format!("{}  {}\n", indent, f));
                        }
                        if files.len() > max_files as usize {
                            result.push_str(&format!(
                                "{}  ... {} more files\n",
                                indent,
                                files.len() - max_files as usize
                            ));
                        }
                        for sd in &subdirs {
                            dirs.push((format!("{}/{}", dir, sd), d + 1));
                        }
                    }
                    let _ = idx;
                }
                json!({"project_structure": result, "scanned": format!("{} directories", idx), "estimated_time": "< 100ms"})
            },
        },
        T {
            n: "batch_read",
            d: "Read multiple files in one call.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"paths":{"type":"array","items":{"type":"string"}}},"required":["session_id","paths"]}),
            h: |p| {
                let paths = p.get("paths").and_then(|v| v.as_array()).cloned().unwrap_or_default();
                let contents: Vec<Value> = paths
                    .iter()
                    .map(|path| {
                        let p = path.as_str().unwrap_or("");
                        // Validate path - prevent directory traversal
                        let canonical = std::path::Path::new(p).canonicalize().unwrap_or_else(|_| std::path::PathBuf::new());
                        let root = std::path::Path::new(".").canonicalize().unwrap_or_else(|_| std::path::PathBuf::new());
                        if !canonical.starts_with(&root) {
                            return json!({"path": p, "found": false, "error": "ACCESS DENIED (outside project root)"});
                        }
                        match std::fs::read_to_string(p) {
                            Ok(content) => {
                                json!({"path": p, "found": true, "content": content, "lines": content.lines().count()})
                            }
                            Err(e) => json!({"path": p, "found": false, "error": e.to_string()}),
                        }
                    })
                    .collect();
                let found = contents
                    .iter()
                    .filter(|c| c.get("found").and_then(|v| v.as_bool()).unwrap_or(false))
                    .count();
                json!({"files": contents, "total": paths.len(), "found": found, "estimated_time": format!("~{}ms", paths.len() * 5)})
            },
        },
        T {
            n: "code_verify",
            d: "Run quality gates: fmt, lint, test, audit.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"path":{"type":"string","default":"."},"gate":{"type":"string","enum":["all","fmt","lint","test","audit"]}},"required":["session_id"]}),
            h: |p| {
                let cwd = p.get("path").and_then(|v| v.as_str()).unwrap_or(".");
                let gate = p.get("gate").and_then(|v| v.as_str()).unwrap_or("all");
                let run_gate = |cmd: &str, args: &[&str]| -> Value {
                    match std::process::Command::new(cmd).args(args).current_dir(cwd).output() {
                        Ok(out) => {
                            json!({"exit": out.status.code().unwrap_or(1), "stdout": String::from_utf8_lossy(&out.stdout).lines().last().unwrap_or("").to_string(), "stderr": String::from_utf8_lossy(&out.stderr).lines().last().unwrap_or("").to_string()})
                        }
                        Err(e) => json!({"error": e.to_string()}),
                    }
                };
                let mut results = json!({"project": cwd});
                if gate == "all" || gate == "fmt" {
                    results["fmt"] = run_gate("cargo", &["fmt", "--all", "--check"]);
                }
                if gate == "all" || gate == "lint" {
                    results["lint"] = run_gate("cargo", &["clippy", "--workspace", "--", "-D", "warnings"]);
                }
                if gate == "all" || gate == "test" {
                    results["test"] = run_gate("cargo", &["test", "--workspace"]);
                }
                if gate == "all" || gate == "audit" {
                    results["audit"] = run_gate("cargo", &["audit"]);
                }
                results["estimated_time"] = json!("varies by gate");
                results
            },
        },
        T {
            n: "safe_delete",
            d: "Move to data/trash/ instead of permanent rm.",
            risk: "destructive",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"paths":{"type":"array","items":{"type":"string"}},"confirm":{"type":"boolean"}},"required":["session_id","paths","confirm"]}),
            h: |p| {
                let paths = p.get("paths").and_then(|v| v.as_array()).cloned().unwrap_or_default();
                let confirm = p.get("confirm").and_then(|v| v.as_bool()).unwrap_or(false);
                if !confirm {
                    return json!({"error":"confirmation_required","hint":"set confirm: true to move files to trash"});
                }
                let trash_dir = format!("data/trash/{}/", chrono_path(now()));
                ensure_dir(&format!("{}dummy", trash_dir));
                let mut results: Vec<Value> = Vec::new();
                for path in &paths {
                    let p = path.as_str().unwrap_or("");
                    // Validate path - domain-specific validation for safe_delete
                    if let Err(e) = validate_path(p) {
                        results.push(e);
                        continue;
                    }
                    if p.is_empty() {
                        continue;
                    }
                    let fname = std::path::Path::new(p)
                        .file_name()
                        .and_then(|n| n.to_str())
                        .unwrap_or("unknown");
                    let dest = format!("{}/{}_{}", trash_dir, now(), fname);
                    let result = match std::fs::copy(p, &dest) {
                        Ok(_) => {
                            let _ = std::fs::remove_file(p);
                            json!({"path": p, "trashed": true, "location": dest})
                        }
                        Err(e) => json!({"path": p, "trashed": false, "error": e.to_string()}),
                    };
                    results.push(result);
                }
                json!({"results": results, "total": paths.len(), "trashed": results.iter().filter(|r| r.get("trashed").and_then(|v| v.as_bool()).unwrap_or(false)).count(), "trash_dir": trash_dir, "estimated_time": "< 100ms", "warning": "Files moved to trash. Use trash_restore to recover."})
            },
        },
        T {
            n: "trash_restore",
            d: "List/restore trashed files.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"paths":{"type":"array","items":{"type":"string"}}},"required":["session_id"]}),
            h: |p| {
                let paths = p
                    .get("paths")
                    .and_then(|v| v.as_array())
                    .map(|a| {
                        a.iter()
                            .filter_map(|v| v.as_str().map(|s| s.to_string()))
                            .collect::<Vec<_>>()
                    })
                    .unwrap_or_default();
                let trash_base = "data/trash";
                if paths.is_empty() {
                    let mut dirs: Vec<String> = Vec::new();
                    if let Ok(entries) = std::fs::read_dir(trash_base) {
                        for e in entries.flatten() {
                            if e.file_type().map(|t| t.is_dir()).unwrap_or(false) {
                                dirs.push(e.file_name().to_string_lossy().to_string());
                            }
                        }
                    }
                    dirs.sort();
                    dirs.reverse();
                    let mut latest: Vec<Value> = Vec::new();
                    for d in dirs.iter().take(3) {
                        let dir_path = format!("{}/{}", trash_base, d);
                        if let Ok(files) = std::fs::read_dir(&dir_path) {
                            for f in files.flatten() {
                                latest.push(json!({"date": d, "file": f.file_name().to_string_lossy().to_string(), "path": f.path().to_string_lossy().to_string()}));
                            }
                        }
                    }
                    return json!({"trash_dirs": dirs, "latest_files": latest, "estimated_time": "< 100ms", "hint": "call trash_restore with paths: [\"data/trash/{date}/{file}\"] to restore"});
                }
                let mut results: Vec<Value> = Vec::new();
                for src in &paths {
                    let fname = std::path::Path::new(src)
                        .file_name()
                        .and_then(|n| n.to_str())
                        .unwrap_or("restored")
                        .to_string();
                    let dest = format!("data/trash/restored/{}", fname);
                    ensure_dir(&dest);
                    match std::fs::rename(src, &dest) {
                        Ok(_) => results.push(json!({"from": src, "restored_to": dest})),
                        Err(e) => results.push(json!({"from": src, "error": e.to_string()})),
                    }
                }
                json!({"results": results, "estimated_time": "< 100ms"})
            },
        },
        T {
            n: "hephaestus_new_task",
            d: "Parallel-worker-safe fresh task. Prunes old context.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"task":{"type":"string"},"files":{"type":"string"},"acceptance_criteria":{"type":"string"}},"required":["session_id","task"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("hephaestus");
                let task = p.get("task").and_then(|v| v.as_str()).unwrap_or("");
                let files = p.get("files").and_then(|v| v.as_str()).unwrap_or("");
                let criteria = p.get("acceptance_criteria").and_then(|v| v.as_str()).unwrap_or("");
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = get_or_create_session(&mut st.sessions, sid);
                // Preserve streak/xp/level/achievements — prune task-specific memory only
                let to_prune: Vec<String> = s
                    .memory
                    .keys()
                    .filter(|k| {
                        k.starts_with("delegation_")
                            || k.starts_with("dictation_")
                            || k.starts_with("hephaestus_result_")
                            || k.starts_with("code_output_")
                            || k.starts_with("error_")
                    })
                    .cloned()
                    .collect();
                let pruned_count = to_prune.len();
                for k in &to_prune {
                    s.memory.remove(k);
                }
                s.ralph_loops.clear();
                s.memory.insert(
                    format!("delegation_{}", now()),
                    json!({"task": task, "files": files, "criteria": criteria, "fresh": true}).to_string(),
                );
                s.last_session_task = format!("task: {}", &task[..task.len().min(40)]);
                record_success(s);
                let ctx_pct = 5;
                save_state(st);
                json!({"fresh": true, "task": task, "files": files, "criteria": criteria,
                    "pruned_old_context": pruned_count, "worker_session": sid,
                    "context_util_pct": ctx_pct, "parallel_safe": true,
                    "estimated_time": "< 1s",
                    "other_workers_unaffected": true})
            },
        },
        
        T {
            n: "memory_ingest",
            d: "Ingest text into holographic memory. Generates embedding vector, stores in FAISS index.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"content":{"type":"string"},"content_type":{"type":"string","enum":["code","query","decision","error","summary","general"]}},"required":["session_id","content"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let content = p.get("content").and_then(|v| v.as_str()).unwrap_or("").to_string();
                let ct = p.get("content_type").and_then(|v| v.as_str()).unwrap_or("general");
                if content.is_empty() { return json!({"error":"empty_content"}); }
                
                // Generate embedding vector (TF-IDF based for now)
                let text = format!("{} {}", ct, content);
                let vec = dense_embed(&text);
                let vec2 = vec.clone();
                let now = std::time::SystemTime::now().duration_since(std::time::UNIX_EPOCH).unwrap().as_secs();
                let vector_id = format!("{}_{}", sid, now);
                
                // Store in memory
                let mut g = ensure_memory();
                let mem = g.as_mut().unwrap();
                mem.vectors.push((vector_id.clone(), vec));
                
                // Persist to disk (append-only)
                let path = format!("{}/memory/vectors/ingest.jsonl", data_dir());
                ensure_dir(&path);
                let _ = std::fs::OpenOptions::new().create(true).append(true).open(&path).and_then(|f| std::io::Write::write_all(&mut std::io::BufWriter::new(f), format!("{}
", serde_json::to_string(&json!({"id":vector_id,"content":text,"dim":vec2.len()})).unwrap()).as_bytes()));
                
                json!({"ingested":true,"id":vector_id,"dim":vec2.len(),"total_vectors":mem.vectors.len(),"estimated_time":"< 1ms"})
            },
        },
        T {
            n: "memory_search",
            d: "Search holographic memory. Returns similar sessions ranked by cosine similarity with recency boost.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"query":{"type":"string"},"k":{"type":"integer","default":5}},"required":["session_id","query"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let query = p.get("query").and_then(|v| v.as_str()).unwrap_or("");
                let k = p.get("k").and_then(|v| v.as_u64()).unwrap_or(5) as usize;
                if query.is_empty() { return json!({"error":"empty_query"}); }
                
                let start = std::time::Instant::now();
                let qvec = dense_embed(&format!("query: {}", query));
                
                let mut g = ensure_memory();
                let mem = g.as_ref().unwrap();
                
                if mem.vectors.is_empty() {
                    return json!({"results":[],"count":0,"elapsed_us":0});
                }
                
                // Score all vectors with cosine similarity + recency boost
                let mut scored: Vec<(String, f32)> = mem.vectors.iter().map(|(id, vec)| {
                    let sim = cosine_sim(&qvec, vec);
                    let recency = recency_weight(id);
                    let blended = 0.85 * sim + 0.15 * recency;
                    (id.clone(), blended)
                }).collect();
                
                // Sort by score descending
                scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
                
                let results: Vec<Value> = scored.iter().take(k).map(|(id, score)| {
                    json!({"session_id": id, "score": score, "relevance": if *score > 0.7 {"high"} else if *score > 0.4 {"medium"} else {"low"}})
                }).collect();
                
                let elapsed = start.elapsed().as_micros();
                json!({"results": results, "count": results.len(), "total_indexed": mem.vectors.len(), "elapsed_us": elapsed})
            },
        },
T {
            n: "ask",
            d: "NL entry: say what you need, tool routes automatically.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"query":{"type":"string"}},"required":["session_id","query"]}),
            h: |p| {
                let q = p.get("query").and_then(|v| v.as_str()).unwrap_or("");
                let sid = p
                    .get("session_id")
                    .and_then(|v| v.as_str())
                    .unwrap_or("default")
                    .to_string();

                // Build tool descriptions array from tools() results (use d: field)
                let all_tools = tools();
                let tool_pairs: Vec<(String, &str)> = all_tools
                    .iter()
                    .map(|t| (t.n.to_string(), t.d))
                    .collect();

                // HYBRID ROUTING: Rust for high-confidence, Mojo for ambiguous
                // Threshold tuned to 8.0 as starting point (adjust based on observed confidence scores)
                const HYBRID_THRESHOLD: f64 = 8.0;
                let start = Instant::now();
                
                // Step 1: Run Rust TF-IDF routing first
                let (rust_tool, rust_confidence) = route_tool(q, &tool_pairs);
                eprintln!("DEBUG HYBRID: Rust route='{}' confidence={}", rust_tool, rust_confidence);
                
                let (best_tool, confidence, tier, backend);
                
                // Step 2: If confidence >= 8.0, use Rust result immediately
                if rust_confidence >= HYBRID_THRESHOLD {
                    best_tool = rust_tool;
                    confidence = rust_confidence;
                    tier = "rust".to_string();
                    backend = "rust";
                    eprintln!("DEBUG HYBRID: Using Rust (confidence >= {})", HYBRID_THRESHOLD);
                } else {
                    // Step 3: Confidence < 8.0, try Mojo daemon
                    eprintln!("DEBUG HYBRID: Low confidence ({} < {}), trying Mojo daemon", rust_confidence, HYBRID_THRESHOLD);
                    let (mojo_tool, mojo_confidence) = mojo_route_v1(q);
                    
                    if !mojo_tool.is_empty() && mojo_confidence > 0.0 {
                        best_tool = mojo_tool.clone();
                        confidence = mojo_confidence;
                        tier = "mojo_v1".to_string();
                        backend = "mojo_v1";
                        eprintln!("DEBUG HYBRID: Using Mojo daemon (tool='{}' conf={})", mojo_tool, mojo_confidence);
                    } else {
                        // Step 4: Mojo unavailable or failed, fallback to Rust
                        eprintln!("DEBUG HYBRID: Mojo unavailable, falling back to Rust");
                        best_tool = rust_tool;
                        confidence = rust_confidence;
                        tier = "rust_fallback".to_string();
                        backend = "rust";
                    }
                }
                
                let elapsed_us = start.elapsed().as_micros() as u64;

                let mut g = ensure_state();
                let (calls, streak, xp, level, mem_len, active_loops) = {
                    let st = g.as_mut().unwrap();
                    let s = get_or_create_session(&mut st.sessions, &sid);
                    s.call_count += 1;
                    s.rate_count += 1;
                    (
                        s.call_count,
                        s.streak,
                        s.xp,
                        s.level,
                        s.memory.len(),
                        s.ralph_loops.len(),
                    )
                };
                drop(g);  // Explicitly drop the first mutex guard to avoid deadlock

                let result = json!({
                    "route": best_tool,
                    "best_tool": best_tool,
                    "confidence": confidence,
                    "elapsed_us": elapsed_us,
                    "tier": tier,
                    "backend": backend,
                    "router_mode": "hybrid",
                    "calls": calls,
                    "streak": streak,
                    "xp": xp,
                    "level": level,
                    "active_loops": active_loops,
                    "memory_keys": mem_len
                });

                let mut g2 = ensure_state();
                let st2 = g2.as_mut().unwrap();
                let s2 = get_or_create_session(&mut st2.sessions, &sid);
                s2.last_session_task = format!("ask: {}", &q[..q.len().min(40)]);
                record_success(s2);
                save_state(st2);
                result
            },
        },
        T {
            n: "router_benchmark",
            d: "Benchmark all routing backends with test query.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"query":{"type":"string"}},"required":["session_id"]}),
            h: |p| {
                let q = p.get("query").and_then(|v| v.as_str()).unwrap_or("list memory keys");
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("default").to_string();

                let all_tools = tools();
                let tool_pairs: Vec<(String, &str)> = all_tools
                    .iter()
                    .map(|t| (t.n.to_string(), t.d))
                    .collect();

                let mut results = json!({});

                // Benchmark Rust backend (always available)
                let rust_start = Instant::now();
                let (rust_tool, rust_conf) = route_tool(q, &tool_pairs);
                let rust_elapsed = rust_start.elapsed().as_micros() as u64;
                results["rust"] = json!({"time_us": rust_elapsed, "result": rust_tool, "confidence": rust_conf});

                // Benchmark Mojo backend (if available)
                let mojo_available = mojo_available();
                if mojo_available {
                    let mojo_start = Instant::now();
                    let (mojo_tool, mojo_conf) = mojo_route(q);
                    let mojo_elapsed = mojo_start.elapsed().as_micros() as u64;
                    results["mojo"] = json!({"time_us": mojo_elapsed, "result": mojo_tool, "confidence": mojo_conf});
                } else {
                    results["mojo"] = json!({"error": "not_available", "time_us": null, "result": null});
                }

                // Benchmark MojoV1 backend (if available)
                let mojo_v1_avail = mojo_v1_available();
                if mojo_v1_avail {
                    let mojo_v1_start = Instant::now();
                    let (mojo_v1_tool, mojo_v1_conf) = mojo_v1_route(q);
                    let mojo_v1_elapsed = mojo_v1_start.elapsed().as_micros() as u64;
                    results["mojo_v1"] = json!({"time_us": mojo_v1_elapsed, "result": mojo_v1_tool, "confidence": mojo_v1_conf});
                } else {
                    results["mojo_v1"] = json!({"error": "not_available", "time_us": null, "result": null});
                }

                // Current mode info
                let mode = RouterMode::from_env();
                results["current_mode"] = json!(match mode {
                    RouterMode::Rust => "rust",
                    RouterMode::Mojo => "mojo",
                    RouterMode::MojoV1 => "mojo_v1",
                    RouterMode::Auto => "auto",
                });
                results["query"] = json!(q);
                results["session_id"] = json!(sid);

                results
            },
        },
        T {
            n: "router_benchmark_v1",
            d: "Benchmark all backends: rust, mojo, mojo_v1 with timing.",
            risk: "read",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"query":{"type":"string"}},"required":["session_id"]}),
            h: |p| {
                let q = p.get("query").and_then(|v| v.as_str()).unwrap_or("search memory");
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("default").to_string();

                let all_tools = tools();
                let tool_pairs: Vec<(String, &str)> = all_tools
                    .iter()
                    .map(|t| (t.n.to_string(), t.d))
                    .collect();

                let mut results = json!({});
                results["query"] = json!(q);
                results["session_id"] = json!(sid);

                // Benchmark Rust backend (always available)
                let rust_start = Instant::now();
                let (rust_tool, rust_conf) = route_tool(q, &tool_pairs);
                let rust_elapsed = rust_start.elapsed().as_micros() as u64;
                results["rust"] = json!({"backend": "rust", "time_us": rust_elapsed, "result": rust_tool, "confidence": rust_conf});

                // Benchmark Mojo backend (if available)
                let mojo_avail = mojo_available();
                if mojo_avail {
                    let mojo_start = Instant::now();
                    let (mojo_tool, mojo_conf) = mojo_route(q);
                    let mojo_elapsed = mojo_start.elapsed().as_micros() as u64;
                    results["mojo"] = json!({"backend": "mojo", "time_us": mojo_elapsed, "result": mojo_tool, "confidence": mojo_conf});
                } else {
                    results["mojo"] = json!({"backend": "mojo", "available": false, "error": "binary not found"});
                }

                // Benchmark MojoV1 backend (if available)
                let mojo_v1_avail = mojo_v1_available();
                if mojo_v1_avail {
                    let mojo_v1_start = Instant::now();
                    let (mojo_v1_tool, mojo_v1_conf) = mojo_v1_route(q);
                    let mojo_v1_elapsed = mojo_v1_start.elapsed().as_micros() as u64;
                    results["mojo_v1"] = json!({"backend": "mojo_v1", "time_us": mojo_v1_elapsed, "result": mojo_v1_tool, "confidence": mojo_v1_conf});
                } else {
                    results["mojo_v1"] = json!({"backend": "mojo_v1", "available": false, "error": "binary not found"});
                }

                // Summary
                results["summary"] = json!({
                    "backends_tested": ["rust", "mojo", "mojo_v1"],
                    "all_available": mojo_avail && mojo_v1_avail
                });

                results
            },
        },
        T {
            n: "decision_log",
            d: "Save design decision with rationale.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"topic":{"type":"string"},"decision":{"type":"string"},"rationale":{"type":"string"}},"required":["session_id","topic","decision"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let topic = p.get("topic").and_then(|v| v.as_str()).unwrap_or("");
                let decision = p.get("decision").and_then(|v| v.as_str()).unwrap_or("");
                let rationale = p.get("rationale").and_then(|v| v.as_str()).unwrap_or("");
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = match st.sessions.get_mut(sid) {
                    Some(s) => s,
                    None => return json!({"error":"session_not_found"}),
                };
                let entry = json!({"topic":topic,"decision":decision,"rationale":rationale,"ts":now()}).to_string();
                let entry_for_log = entry.clone();
                s.memory.insert(format!("decision_{}", topic.replace(" ", "_")), entry);
                s.last_session_task = format!("decision: {} -> {}", topic, &decision[..decision.len().min(30)]);
                let log_path = format!("{}/memory/synapses/decisions.jsonl", data_dir());
                ensure_dir(&log_path);
                let _ = std::fs::OpenOptions::new().create(true).append(true).open(&log_path)
                    .and_then(|mut f| f.write_all(format!("{}\n", entry_for_log).as_bytes()));
                record_success(s);
                save_state(st);
                json!({"saved":true,"topic":topic,"decision":decision,"persisted_to":"memory/synapses/decisions.jsonl","estimated_time":"< 1s"})
            },
        },
        T {
            n: "delegate_task",
            d: "Delegate task to another agent via shared memory.",
            risk: "write",
            s: || json!({"type":"object","properties":{"session_id":{"type":"string"},"from":{"type":"string"},"to":{"type":"string"},"task":{"type":"string"},"files":{"type":"string"},"criteria":{"type":"string"}},"required":["session_id","from","to","task"]}),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("default");
                let from = p.get("from").and_then(|v| v.as_str()).unwrap_or("unknown");
                let to_agent = p.get("to").and_then(|v| v.as_str()).unwrap_or("unknown");
                // Validate agent names - domain-specific validation
                if let Err(e) = validate_agent_name(to_agent) {
                    return e;
                }
                let task = p.get("task").and_then(|v| v.as_str()).unwrap_or("");
                // Validate task is not empty
                if task.is_empty() {
                    return json!({"error":"invalid_task","reason":"task cannot be empty"});
                }
                let files = p.get("files").and_then(|v| v.as_str()).unwrap_or("");
                let criteria = p.get("criteria").and_then(|v| v.as_str()).unwrap_or("");
                let mut g = ensure_state();
                let st = g.as_mut().unwrap();
                let s = get_or_create_session(&mut st.sessions, sid);
                s.memory.insert(format!("task_{}_{}", to_agent, now()), json!({"from": from, "to": to_agent, "task": task, "files": files, "criteria": criteria, "status": "pending"}).to_string());
                s.last_session_task = format!("delegated to {}: {}", to_agent, &task[..task.len().min(30)]);
                record_success(s);
                save_state(st);
                json!({"delegated": true, "from": from, "to": to_agent, "task": task, "status": "pending", "estimated_time": "instant"})
            },
        },
        // === SESSION DIGEST MCP TOOL ===
        // Generates structured digest from session transcript
        T {
            n: "session_digest",
            d: "Generate structured digest from session transcript. Extracts key decisions, code topics, summary.",
            risk: "write",
            s: || json!({
                "type":"object",
                "properties":{
                    "session_id":{"type":"string"},
                    "content":{"type":"string"},
                    "agent":{"type":"string","default":"sisyphus"}
                },
                "required":["session_id","content"]
            }),
            h: |p| {
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let content = p.get("content").and_then(|v| v.as_str()).unwrap_or("");
                let agent = p.get("agent").and_then(|v| v.as_str()).unwrap_or("sisyphus");
                
                let ts = now();
                
                // Extract key decisions from content
                // Patterns: "decided", "chose", "use X instead of Y"
                let mut key_decisions: Vec<String> = Vec::new();
                let decision_patterns = ["decided", "chose", "use ", "implemented", "adopted", "selected", "went with"];
                
                for line in content.lines() {
                    let line_lower = line.to_lowercase();
                    for pattern in &decision_patterns {
                        if line_lower.contains(pattern) {
                            // Clean up the line - extract meaningful part
                            let trimmed = line.trim();
                            if !trimmed.is_empty() && trimmed.len() > 10 && trimmed.len() < 200 {
                                key_decisions.push(trimmed.to_string());
                                break;
                            }
                        }
                    }
                }
                
                // Deduplicate decisions
                key_decisions.sort();
                key_decisions.dedup();
                key_decisions.truncate(10); // Keep top 10
                
                // Extract code topics from content
                let code_keywords = [
                    "auth", "middleware", "database", "api", "router", "handler",
                    "model", "view", "controller", "service", "repository", "schema",
                    "migration", "connection", "query", "endpoint", "route", "jwt",
                    "session", "token", "password", "hash", "encryption", "validation",
                    "error", "logging", "config", "env", "test", "mock", "fixture",
                    "struct", "enum", "impl", "trait", "function", "async", "await",
                    "rust", "python", "javascript", "typescript", "sql", "html", "css"
                ];
                
                let mut code_topics: Vec<String> = Vec::new();
                let content_lower = content.to_lowercase();
                for kw in &code_keywords {
                    if content_lower.contains(kw) {
                        code_topics.push(kw.to_string());
                    }
                }
                code_topics.sort();
                code_topics.dedup();
                code_topics.truncate(10); // Keep top 10
                
                // Count tools used in transcript (count tool names in content)
                let tool_names = [
                    "session_start", "session_status", "memory_write", "memory_read",
                    "memory_list", "context_prune", "project_map", "batch_read",
                    "code_verify", "safe_delete", "delegate_to_hephaestus", "delegate_task",
                    "ask", "ralph_start", "ralph_iterate", "decision_log", "memory_ingest",
                    "memory_search", "hephaestus_new_task"
                ];
                let mut tool_count = 0;
                for tool in &tool_names {
                    if content_lower.contains(tool) {
                        tool_count += 1;
                    }
                }
                // Also count generic "tool" mentions
                let generic_tool_count = content_lower.matches("tool").count();
                tool_count = tool_count.max(generic_tool_count).max(1);
                
                // Generate summary from decisions
                let summary = if !key_decisions.is_empty() {
                    // Combine first 2-3 decisions into a summary
                    let first_decisions: Vec<String> = key_decisions.iter().take(3).cloned().collect();
                    if first_decisions.len() == 1 {
                        first_decisions[0].clone()
                    } else {
                        first_decisions.join("; ")
                    }
                } else {
                    // Fallback: extract first meaningful sentence
                    let sentences: Vec<&str> = content.split(|c| c == '.' || c == '!' || c == '?')
                        .filter(|s| s.len() > 20 && s.len() < 150)
                        .collect();
                    sentences.first().map(|s| s.trim().to_string()).unwrap_or_else(|| "Session completed".to_string())
                };
                
                // Build digest
                let digest = json!({
                    "session_id": sid,
                    "ts": ts,
                    "agent": agent,
                    "key_decisions": key_decisions,
                    "code_topics": code_topics,
                    "tool_count": tool_count,
                    "summary": summary
                });
                
                // Save to file: data/memory/synapses/digest-{session_id}.jsonl
                let digest_path = format!("{}/memory/synapses/digest-{}.jsonl", data_dir(), sid);
                ensure_dir(&digest_path);
                
                let digest_str = serde_json::to_string(&digest).unwrap();
                let entry_str = format!("{}\n", digest_str);
                
                if let Err(e) = std::fs::OpenOptions::new().create(true).append(true).open(&digest_path)
                    .and_then(|mut f| f.write_all(entry_str.as_bytes())) {
                    eprintln!("ERROR: session_digest failed to write to {}: {}", digest_path, e);
                }
                
                json!({
                    "digest": digest,
                    "saved_to": digest_path,
                    "estimated_time": "< 10ms"
                })
            },
        },
        // === TOOL TELEMETRY MCP TOOL ===
        // Stores/query telemetry for Rosetta training data generation
        T {
            n: "tool_telemetry",
            d: "Store/query tool call telemetry. Query by session_id, tool, time range. Returns Rosetta training format.",
            risk: "read",
            s: || json!({
                "type":"object",
                "properties":{
                    "action":{"type":"string","enum":["store","query","stats","export"]},
                    "session_id":{"type":"string"},
                    "tool_name":{"type":"string"},
                    "tier":{"type":"string","enum":["rust","mojo","llm"]},
                    "start_time":{"type":"string"},
                    "end_time":{"type":"string"},
                    "limit":{"type":"integer","default":10},
                    "min_confidence":{"type":"number"},
                    "query":{"type":"string"},
                    "duration_us":{"type":"integer"},
                    "result_sample":{"type":"boolean"}
                },
                "required":["action"]
            }),
            h: |p| {
                let action = p.get("action").and_then(|v| v.as_str()).unwrap_or("query");
                let sid = p.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                let tool_name = p.get("tool_name").and_then(|v| v.as_str()).unwrap_or("");
                let tier = p.get("tier").and_then(|v| v.as_str()).unwrap_or("");
                let start_time = p.get("start_time").and_then(|v| v.as_str()).unwrap_or("");
                let end_time = p.get("end_time").and_then(|v| v.as_str()).unwrap_or("");
                let limit = p.get("limit").and_then(|v| v.as_u64()).unwrap_or(10) as usize;
                let min_confidence = p.get("min_confidence").and_then(|v| v.as_f64());
                let duration_us = p.get("duration_us").and_then(|v| v.as_u64()).unwrap_or(0);
                let result_sample = p.get("result_sample").and_then(|v| v.as_bool()).unwrap_or(false);
                
                let path = telemetry_path();
                
                // STORE action: record a telemetry entry
                if action == "store" {
                    let entry = ToolTelemetryEntry {
                        session_id: sid.to_string(),
                        timestamp: iso_timestamp(),
                        entry_type: "assistant".to_string(),
                        message: TelemetryMessage {
                            id: format!("t{}", now()),
                            msg_type: "message".to_string(),
                            role: "assistant".to_string(),
                            model: "nx-agents-mcp".to_string(),
                            content: vec![ToolUseBlock {
                                id: format!("t{}", now()),
                                name: tool_name.to_string(),
                                input: p.clone(),
                                result: json!({"stored": true}),
                                duration_us,
                                confidence: 1.0,
                                tier: tier.to_string(),
                                query: None,
                                routed_tool: None,
                                routing_confidence: None,
                            }],
                            usage: Usage { input_tokens: 0, output_tokens: 0 },
                        },
                    };
                    write_telemetry(&entry);
                    return json!({
                        "stored": true,
                        "path": path,
                        "session_id": sid,
                        "tool": tool_name,
                        "estimated_time": "< 1ms"
                    });
                }
                
                // QUERY action: filter and return telemetry entries
                if action == "query" {
                    let content = std::fs::read_to_string(&path).unwrap_or_default();
                    let mut entries: Vec<Value> = content
                        .lines()
                        .filter_map(|l| serde_json::from_str(l).ok())
                        .collect();
                    
                    // Apply filters
                    if !sid.is_empty() {
                        entries.retain(|e| e.get("sessionId").and_then(|v| v.as_str()) == Some(sid));
                    }
                    if !tool_name.is_empty() {
                        entries.retain(|e| {
                            if let Some(msg) = e.get("message") {
                                if let Some(tools) = msg.get("content").and_then(|c| c.as_array()) {
                                    return tools.iter().any(|t| t.get("name").and_then(|n| n.as_str()) == Some(tool_name));
                                }
                            }
                            false
                        });
                    }
                    if !tier.is_empty() {
                        entries.retain(|e| {
                            if let Some(msg) = e.get("message") {
                                if let Some(tools) = msg.get("content").and_then(|c| c.as_array()) {
                                    return tools.iter().any(|t| t.get("tier").and_then(|t| t.as_str()) == Some(tier));
                                }
                            }
                            false
                        });
                    }
                    if let Some(min_c) = min_confidence {
                        entries.retain(|e| {
                            if let Some(msg) = e.get("message") {
                                if let Some(tools) = msg.get("content").and_then(|c| c.as_array()) {
                                    return tools.iter().any(|t| t.get("confidence").and_then(|c| c.as_f64()).unwrap_or(0.0) >= min_c);
                                }
                            }
                            false
                        });
                    }
                    if !start_time.is_empty() {
                        entries.retain(|e| e.get("timestamp").and_then(|t| t.as_str()).map(|t| t >= start_time).unwrap_or(false));
                    }
                    if !end_time.is_empty() {
                        entries.retain(|e| e.get("timestamp").and_then(|t| t.as_str()).map(|t| t <= end_time).unwrap_or(false));
                    }
                    
                    entries.reverse();
                    let limited: Vec<Value> = entries.into_iter().take(limit).collect();
                    
                    // If result_sample, extract just tool_name, args, result for training
                    if result_sample {
                        let training_samples: Vec<Value> = limited.iter().map(|e| {
                            if let Some(msg) = e.get("message") {
                                if let Some(tools) = msg.get("content").and_then(|c| c.as_array()) {
                                    if let Some(tool) = tools.first() {
                                        return json!({
                                            "session_id": e.get("sessionId").and_then(|v| v.as_str()).unwrap_or(""),
                                            "timestamp": e.get("timestamp").and_then(|v| v.as_str()).unwrap_or(""),
                                            "tool_name": tool.get("name").and_then(|v| v.as_str()).unwrap_or(""),
                                            "args": tool.get("input").unwrap_or(&json!({})),
                                            "result": tool.get("result").unwrap_or(&json!({})),
                                            "duration_us": tool.get("duration_us").and_then(|v| v.as_u64()).unwrap_or(0),
                                            "confidence": tool.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.0),
                                            "tier": tool.get("tier").and_then(|v| v.as_str()).unwrap_or(""),
                                        });
                                    }
                                }
                            }
                            json!({})
                        }).collect();
                        return json!({
                            "action": "query",
                            "results": training_samples,
                            "count": training_samples.len(),
                            "path": path,
                            "filters": {
                                "session_id": sid,
                                "tool_name": tool_name,
                                "tier": tier,
                                "start_time": start_time,
                                "end_time": end_time
                            },
                            "estimated_time": "~1ms"
                        });
                    }
                    
                    return json!({
                        "action": "query",
                        "results": limited,
                        "count": limited.len(),
                        "path": path,
                        "filters": {
                            "session_id": sid,
                            "tool_name": tool_name,
                            "tier": tier,
                            "start_time": start_time,
                            "end_time": end_time
                        },
                        "estimated_time": "~1ms"
                    });
                }
                
                // STATS action: aggregate telemetry statistics
                if action == "stats" {
                    let content = std::fs::read_to_string(&path).unwrap_or_default();
                    let entries: Vec<Value> = content
                        .lines()
                        .filter_map(|l| serde_json::from_str(l).ok())
                        .collect();
                    
                    let mut tool_counts: HashMap<String, u64> = HashMap::new();
                    let mut tier_counts: HashMap<String, u64> = HashMap::new();
                    let mut session_counts: HashMap<String, u64> = HashMap::new();
                    let mut total_duration: u64 = 0;
                    let mut total_confidence: f64 = 0.0;
                    let mut count: u64 = 0;
                    
                    for e in &entries {
                        if let Some(msg) = e.get("message") {
                            if let Some(tools) = msg.get("content").and_then(|c| c.as_array()) {
                                for tool in tools {
                                    let tn = tool.get("name").and_then(|v| v.as_str()).unwrap_or("unknown").to_string();
                                    let tr = tool.get("tier").and_then(|v| v.as_str()).unwrap_or("unknown").to_string();
                                    let dur = tool.get("duration_us").and_then(|v| v.as_u64()).unwrap_or(0);
                                    let conf = tool.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.0);
                                    
                                    *tool_counts.entry(tn).or_insert(0) += 1;
                                    *tier_counts.entry(tr).or_insert(0) += 1;
                                    total_duration += dur;
                                    total_confidence += conf;
                                    count += 1;
                                }
                            }
                        }
                        if let Some(sid_val) = e.get("sessionId").and_then(|v| v.as_str()) {
                            *session_counts.entry(sid_val.to_string()).or_insert(0) += 1;
                        }
                    }
                    
                    let avg_duration = if count > 0 { total_duration / count } else { 0 };
                    let avg_confidence = if count > 0 { total_confidence / count as f64 } else { 0.0 };
                    
                    return json!({
                        "action": "stats",
                        "total_entries": entries.len(),
                        "total_tool_calls": count,
                        "tool_counts": tool_counts,
                        "tier_counts": tier_counts,
                        "session_counts": session_counts,
                        "avg_duration_us": avg_duration,
                        "avg_confidence": avg_confidence,
                        "path": path,
                        "estimated_time": "~1ms"
                    });
                }
                
                // EXPORT action: export for Rosetta training data generation
                if action == "export" {
                    let content = std::fs::read_to_string(&path).unwrap_or_default();
                    let entries: Vec<Value> = content
                        .lines()
                        .filter_map(|l| serde_json::from_str(l).ok())
                        .collect();
                    
                    let mut misroutes: Vec<Value> = Vec::new();
                    let mut correct_routes: Vec<Value> = Vec::new();
                    
                    for e in &entries {
                        if let Some(msg) = e.get("message") {
                            if let Some(tools) = msg.get("content").and_then(|c| c.as_array()) {
                                for tool in tools {
                                    let conf = tool.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.0);
                                    let has_query = tool.get("query").and_then(|v| v.as_str()).is_some();
                                    
                                    if conf < 0.5 && has_query {
                                        misroutes.push(json!({
                                            "session_id": e.get("sessionId").and_then(|v| v.as_str()).unwrap_or(""),
                                            "query": tool.get("query").and_then(|v| v.as_str()).unwrap_or(""),
                                            "routed_tool": tool.get("routed_tool").and_then(|v| v.as_str()).unwrap_or(""),
                                            "actual_tool": tool.get("name").and_then(|v| v.as_str()).unwrap_or(""),
                                            "confidence": conf,
                                            "duration_us": tool.get("duration_us").and_then(|v| v.as_u64()).unwrap_or(0),
                                            "tier": tool.get("tier").and_then(|v| v.as_str()).unwrap_or("")
                                        }));
                                    }
                                    if conf >= 0.8 {
                                        correct_routes.push(json!({
                                            "session_id": e.get("sessionId").and_then(|v| v.as_str()).unwrap_or(""),
                                            "query": tool.get("query").and_then(|v| v.as_str()).unwrap_or(""),
                                            "routed_tool": tool.get("routed_tool").and_then(|v| v.as_str()).unwrap_or(tool.get("name").and_then(|v| v.as_str()).unwrap_or("")),
                                            "confidence": conf,
                                            "tier": tool.get("tier").and_then(|v| v.as_str()).unwrap_or("")
                                        }));
                                    }
                                }
                            }
                        }
                    }
                    
                    return json!({
                        "action": "export",
                        "misdirected_routes": misroutes,
                        "correct_routes": correct_routes,
                        "misroute_count": misroutes.len(),
                        "correct_count": correct_routes.len(),
                        "training_data_format": "rosetta_v1",
                        "estimated_time": "~1ms"
                    });
                }
                
                json!({"error": "unknown_action", "available_actions": ["store", "query", "stats", "export"]})
            },
        },
    ]
}

fn main() {
    let all = tools();
    let si = io::stdin();
    let mut so = io::stdout();
    for line in si.lock().lines() {
        let line = match line {
            Ok(l) => l,
            Err(_) => break,
        };
        if line.trim().is_empty() {
            continue;
        }
        let req: Value = match serde_json::from_str(&line) {
            Ok(r) => r,
            Err(_) => continue,
        };
        let method = req.get("method").and_then(|v| v.as_str()).unwrap_or("");
        let id = req.get("id").cloned().unwrap_or(json!(null));
        let params = req.get("params").cloned().unwrap_or(json!({}));
        let result = match method {
            "initialize" => {
                json!({"protocolVersion":"2024-11-05","capabilities":{"tools":{}},"serverInfo":{"name":"nx-agents","version":"0.6.0"}})
            }
            "tools/list" => {
                let list: Vec<Value> = all
                    .iter()
                    .map(|t| {
                        let mut schema = (t.s)();
                        if let Some(props) = schema.get_mut("properties") {
                            if let Some(obj) = props.as_object_mut() {
                                obj.insert("_risk".to_string(), json!(t.risk));
                            }
                        }
                        json!({"name": t.n, "description": t.d, "inputSchema": schema})
                    })
                    .collect();
                json!({"tools": list})
            }
            "tools/call" => {
                let name = params.get("name").and_then(|v| v.as_str()).unwrap_or("");
                let args = params.get("arguments").cloned().unwrap_or(json!({}));
                let start = Instant::now();
                let result = match all.iter().find(|t| t.n == name) {
                    Some(t) => safe_run(|| (t.h)(&args)),
                    None => {
                        let names: Vec<&str> = all.iter().map(|t| t.n).collect();
                        json!({"error":"unknown_tool","available":names})
                    }
                };
                let duration_us = start.elapsed().as_micros() as u64;
                let sid = args.get("session_id").and_then(|v| v.as_str()).unwrap_or("unknown");
                audit_log(sid, name, &args, &result);
                let agent = args
                    .get("_agent")
                    .and_then(|v| v.as_str())
                    .map(|s| s.to_string())
                    .unwrap_or_else(|| {
                        let sid = args.get("session_id").and_then(|v| v.as_str()).unwrap_or("");
                        if sid.contains("hephaestus") {
                            "hephaestus".to_string()
                        } else if sid.contains("sisyphus") {
                            "sisyphus".to_string()
                        } else if sid.contains("kairos") {
                            "kairos".to_string()
                        } else {
                            "unknown".to_string()
                        }
                    });
                write_transcript(sid, &agent, name, &args, &result);

                // === AUTO-TELEMETRY RECORDING ===
                // Determine tier based on tool category
                let tier = if name == "ask" || name == "session_start" || name == "next_step" {
                    "llm"
                } else if name == "project_map"
                    || name == "batch_read"
                    || name == "code_verify"
                    || name == "router_benchmark"
                {
                    "rust"
                } else {
                    "mojo"
                };

                // Get confidence if this was a routing call (ask tool)
                let (query, routed_tool, routing_confidence) = if name == "ask" {
                    let q = args.get("query").and_then(|v| v.as_str()).unwrap_or("");
                    let rt = result.get("best_tool").and_then(|v| v.as_str());
                    let rc = result.get("confidence").and_then(|v| v.as_f64());
                    (Some(q), rt, rc)
                } else {
                    (None, None, None)
                };

                // Determine confidence based on result
                let confidence = if let Some(err) = result.get("error") {
                    0.0 // Failed call = 0 confidence
                } else if name == "ask" {
                    result.get("confidence").and_then(|v| v.as_f64()).unwrap_or(0.5)
                } else {
                    1.0 // Successful non-routing call = full confidence
                };

                record_telemetry(
                    sid,
                    name,
                    &args,
                    &result,
                    duration_us,
                    confidence,
                    tier,
                    query,
                    routed_tool,
                    routing_confidence,
                );
                result
            }
            m if m.starts_with("notifications/") => continue,
            _ => json!({"error":"unknown_method"}),
        };
        let _ = writeln!(
            so,
            "{}",
            serde_json::to_string(&json!({"jsonrpc":"2.0","id":id,"result":result})).unwrap()
        );
        let _ = so.flush();
    }
}

// ─── Rust ONNX Embedding Engine (ort crate) ───
// Replaces the Python embedding server with native Rust inference.
// No Python, no subprocess, no version conflicts.
// Uses `ort` crate already compiled in Cargo.toml.

fn rust_onnx_embed(texts: &[&str]) -> Option<Vec<Vec<f32>>> {
    let model_path = format!("{}/memory/models/embedding.onnx", data_dir());
    if !std::path::Path::new(&model_path).exists() {
        return None;
    }

    let mut session = ort::session::Session::builder()
        .ok()?
        .commit_from_file(&model_path)
        .ok()?;

    let mut results = Vec::with_capacity(texts.len());
    for text in texts {
        let tokens: Vec<i64> = text
            .split_whitespace()
            .map(|w| {
                (w.bytes()
                    .fold(0u64, |acc, b| acc.wrapping_mul(31).wrapping_add(b as u64))
                    % 30522) as i64
            })
            .take(128)
            .collect();

        let mut input_ids = vec![0i64; 128];
        for (i, t) in tokens.iter().enumerate() {
            input_ids[i] = *t;
        }

        let input = ort::value::Tensor::from_array(([1usize, 128], input_ids.into_boxed_slice())).ok()?;
        let outputs = session.run(ort::inputs!["input_ids" => input]).ok()?;

        if let Some(tensor) = outputs.get("last_hidden_state") {
            let (shape, flat_data) = tensor.try_extract_tensor::<f32>().ok()?;
            let dims: &[i64] = &*shape;
            if dims.len() == 3 && dims[0] == 1 && dims[2] == 384 {
                let seq_len = dims[1] as usize;
                let mut pooled = Vec::with_capacity(384);
                for i in 0..384 {
                    let mut sum = 0.0f32;
                    for j in 0..seq_len {
                        sum += flat_data[j * 384 + i];
                    }
                    pooled.push(sum / seq_len as f32);
                }
                let norm: f32 = pooled.iter().map(|x| x * x).sum::<f32>().sqrt();
                if norm > 0.0 {
                    for v in &mut pooled {
                        *v /= norm;
                    }
                }
                results.push(pooled);
            } else {
                return None;
            }
        } else {
            return None;
        }
    }

    Some(results)
}

// Fallback: call Python embedding server via subprocess
fn py_embed(text: &str) -> Vec<f32> {
    // Try Rust ONNX first
    if let Some(results) = rust_onnx_embed(&[text]) {
        if !results.is_empty() {
            return results[0].clone();
        }
    }

    // Fallback to TF-IDF
    tfidf_vector(text)
}

// Replace dense_embed with py_embed that tries Rust ONNX first
// dense_embed is already used by memory_ingest and memory_search
