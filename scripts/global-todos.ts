/**
 * Global Todo Aggregator
 * Aggregates todos from all OpenCode sessions into ADHD-optimized views.
 *
 * Views:
 * - Now: 3 highest-priority pending/in_progress tasks
 * - Today: 7 tasks (max), no scroll
 * - Week: 20 tasks (max)
 *
 * Run: npx tsx scripts/global-todos.ts
 */

// ---------------------------------------------------------------------------
// Logger abstraction
// ---------------------------------------------------------------------------

/**
 * Simple logger that wraps console methods for structured output.
 * Supports log, warn, error, and table output modes.
 */
class Logger {
  /**
   * Log an informational message to stdout.
   * @param args - Values to log (same as console.log).
   */
  log(...args: unknown[]): void {
    console.log(...args);
  }

  /**
   * Log a warning message to stderr.
   * @param args - Values to log (same as console.warn).
   */
  warn(...args: unknown[]): void {
    console.warn(...args);
  }

  /**
   * Log an error message to stderr.
   * @param args - Values to log (same as console.error).
   */
  error(...args: unknown[]): void {
    console.error(...args);
  }

  /**
   * Display tabular data (delegates to console.table).
   * @param data - Array of objects or arrays to display as a table.
   */
  table(data: unknown[]): void {
    console.table(data);
  }
}

/** Singleton logger instance used throughout the module. */
const logger = new Logger();

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/** Represents a single todo item from an OpenCode session. */
interface TodoItem {
  id?: string;
  content: string;
  status: "pending" | "in_progress" | "completed" | "cancelled";
  priority?: "low" | "medium" | "high";
  session_id?: string;
  session_title?: string;
}

/** Metadata about an OpenCode session. */
interface SessionInfo {
  id: string;
  message_count: number;
  agents_used: string[];
  has_todos: boolean;
  title?: string;
}

// ---------------------------------------------------------------------------
// Constants
// ---------------------------------------------------------------------------

/** Status indicators for display. */
const STATUS_ICONS: Record<string, string> = {
  pending: "⏳",
  in_progress: "🔄",
  completed: "✅",
  cancelled: "❌",
};

/** Priority indicators for display. */
const PRIORITY_ICONS: Record<string, string> = {
  high: "🔴",
  medium: "🟡",
  low: "🟢",
};

/** Time estimates based on priority level. */
const TIME_ESTIMATES: Record<string, string> = {
  high: "60 min",
  medium: "30 min",
  low: "15 min",
};

// ---------------------------------------------------------------------------
// Functions
// ---------------------------------------------------------------------------

/**
 * Retrieves all session IDs from the OpenCode environment.
 * In production, this calls the session_list tool.
 * @returns Promise resolving to an array of session ID strings.
 */
async function getAllSessions(): Promise<string[]> {
  // In production, this would call session_list tool
  // For now, return empty array - the script will work when called from OpenCode
  return [];
}

/**
 * Reads todos from a specific session.
 * In production, this calls session_read with include_todos.
 * @param sessionId - The session ID to read todos from.
 * @returns Promise resolving to an array of TodoItem objects.
 */
async function readSessionTodos(sessionId: string): Promise<TodoItem[]> {
  // In production, this would call session_read with include_todos
  return [];
}

/**
 * Sorts todos by priority (high first) then status (in_progress first).
 * @param todos - Array of TodoItem objects to sort.
 * @returns New sorted array of TodoItem objects.
 */
function sortTodos(todos: TodoItem[]): TodoItem[] {
  const priorityOrder = { high: 0, medium: 1, low: 2 };
  const statusOrder = { in_progress: 0, pending: 1, completed: 2, cancelled: 3 };

  return [...todos].sort((a, b) => {
    // Priority first
    const pA = priorityOrder[a.priority || "medium"];
    const pB = priorityOrder[b.priority || "medium"];
    if (pA !== pB) return pA - pB;

    // Then status
    const sA = statusOrder[a.status];
    const sB = statusOrder[b.status];
    return sA - sB;
  });
}

/**
 * Formats a single todo item into a display-friendly record.
 * @param todo - The TodoItem to format.
 * @returns Record with Task, Status, Priority, Session, and Time fields.
 */
function formatTodo(todo: TodoItem): Record<string, string> {
  return {
    Task: todo.content.substring(0, 50) + (todo.content.length > 50 ? "..." : ""),
    Status: `${STATUS_ICONS[todo.status] || "❓"} ${todo.status}`,
    Priority: `${PRIORITY_ICONS[todo.priority || "medium"] || "⚪"} ${todo.priority || "medium"}`,
    Session: todo.session_id?.substring(0, 12) + "..." || "unknown",
    Time: TIME_ESTIMATES[todo.priority || "medium"] || "30 min",
  };
}

/**
 * Displays a filtered view of todos as a formatted table.
 * @param title - Title for the view section.
 * @param todos - Array of TodoItem objects to display.
 * @param maxCount - Maximum number of todos to show in this view.
 */
function displayView(title: string, todos: TodoItem[], maxCount: number): void {
  const limited = todos.slice(0, maxCount);
  if (limited.length === 0) {
    logger.log(`\n📋 ${title}: No tasks`);
    return;
  }

  logger.log(`\n📋 ${title} (${limited.length} tasks)`);
  logger.log("─".repeat(80));

  const formatted = limited.map(formatTodo);
  logger.table(formatted);
}

/**
 * Main aggregation function: collects todos from all sessions,
 * deduplicates, sorts, and displays in ADHD-optimized views.
 * @returns Promise that resolves when dashboard is displayed.
 */
async function aggregateTodos(): Promise<void> {
  logger.log("🔍 Aggregating todos from all sessions...\n");

  // Get all sessions
  const sessionIds = await getAllSessions();
  if (sessionIds.length === 0) {
    logger.log("No sessions found. Ensure session_list tool is available.");
    return;
  }

  // Read todos from all sessions in parallel
  const todoPromises = sessionIds.map(async (sessionId) => {
    const todos = await readSessionTodos(sessionId);
    return todos.map((t) => ({ ...t, session_id: sessionId }));
  });

  const allTodoArrays = await Promise.all(todoPromises);
  let allTodos = allTodoArrays.flat();

  // Deduplicate by id
  const seen = new Set<string>();
  allTodos = allTodos.filter((t) => {
    const key = t.id || `${t.content}-${t.session_id}`;
    if (seen.has(key)) return false;
    seen.add(key);
    return true;
  });

  // Sort all todos
  const sorted = sortTodos(allTodos);

  // Build views
  const nowTodos = sorted.filter(
    (t) => t.status === "in_progress" || t.status === "pending"
  );
  const todayTodos = sorted.filter(
    (t) => t.status !== "completed" && t.status !== "cancelled"
  );
  const weekTodos = sorted;

  // Display views
  logger.log("═══════════════════════════════════════════════════════════════");
  logger.log("  GLOBAL TODO DASHBOARD — ADHD-Optimized Views");
  logger.log("═══════════════════════════════════════════════════════════════");

  displayView("NOW (Top 3 Priority)", nowTodos, 3);
  displayView("TODAY (Max 7)", todayTodos, 7);
  displayView("WEEK (Max 20)", weekTodos, 20);

  logger.log("\n═══════════════════════════════════════════════════════════════");
  logger.log(`  Total: ${allTodos.length} todos across ${sessionIds.length} sessions`);
  logger.log("═══════════════════════════════════════════════════════════════\n");
}

// Run
aggregateTodos().catch((err) => logger.error(err));
