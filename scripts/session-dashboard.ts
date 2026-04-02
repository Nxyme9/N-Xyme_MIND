#!/usr/bin/env tsx
/**
 * Session Dashboard - Lists all OpenCode sessions in a scannable table.
 *
 * Provides ADHD-optimized views:
 * - Full table sorted by status (active > stale > orphaned) then message count
 * - NOW view: top 3 priority sessions with todos or high activity
 *
 * Usage: npx tsx scripts/session-dashboard.ts
 */

import { execSync } from 'child_process';

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

/** Represents an OpenCode session with metadata. */
interface Session {
  id: string;
  message_count: number;
  agents_used: string[];
  first_message: string;
  last_message: string;
  has_todos: boolean;
  has_transcript: boolean;
}

/** Computed status for a session based on activity recency. */
interface SessionStatus {
  status: 'active' | 'stale' | 'orphaned';
  indicator: string;
  lastActive: string;
}

// ---------------------------------------------------------------------------
// Helper functions
// ---------------------------------------------------------------------------

/**
 * Computes the status of a session based on last activity time.
 * @param lastMessage - ISO 8601 timestamp of the last message.
 * @param messageCount - Total number of messages in the session.
 * @returns SessionStatus with status category, display indicator, and time-ago string.
 */
function getSessionStatus(lastMessage: string, messageCount: number): SessionStatus {
  const now = new Date();
  const lastActive = new Date(lastMessage);
  const hoursDiff = (now.getTime() - lastActive.getTime()) / (1000 * 60 * 60);

  if (hoursDiff < 1) {
    return { status: 'active', indicator: '🟢 Active', lastActive: formatTimeAgo(hoursDiff) };
  } else if (hoursDiff < 24) {
    return { status: 'stale', indicator: '🟡 Stale', lastActive: formatTimeAgo(hoursDiff) };
  } else {
    return { status: 'orphaned', indicator: '🔴 Orphaned', lastActive: formatTimeAgo(hoursDiff) };
  }
}

/**
 * Formats hours into a human-readable time-ago string.
 * @param hours - Number of hours since last activity.
 * @returns Formatted string like "30m ago", "2h ago", or "3d ago".
 */
function formatTimeAgo(hours: number): string {
  if (hours < 1) {
    const minutes = Math.floor(hours * 60);
    return `${minutes}m ago`;
  } else if (hours < 24) {
    return `${Math.floor(hours)}h ago`;
  } else {
    const days = Math.floor(hours / 24);
    return `${days}d ago`;
  }
}

/**
 * Formats an array of agent names into a compact display string.
 * @param agents - Array of agent name strings.
 * @returns Compact string representation (e.g., "build, oracle +1").
 */
function getAgentString(agents: string[]): string {
  if (agents.length === 0) return 'none';
  if (agents.length === 1) return agents[0];
  if (agents.length <= 3) return agents.join(', ');
  return `${agents.slice(0, 2).join(', ')} +${agents.length - 2}`;
}

/**
 * Truncates an ID string to a maximum length with ellipsis.
 * @param id - The ID string to truncate.
 * @param maxLength - Maximum allowed length (default: 12).
 * @returns Truncated string with "..." suffix if needed.
 */
function truncateId(id: string, maxLength: number = 12): string {
  if (id.length <= maxLength) return id;
  return id.substring(0, maxLength - 3) + '...';
}

/**
 * Right-pads a string to a fixed length.
 * @param str - String to pad.
 * @param length - Target length.
 * @returns Padded string.
 */
function padRight(str: string, length: number): string {
  return str.padEnd(length);
}

/**
 * Left-pads a string to a fixed length.
 * @param str - String to pad.
 * @param length - Target length.
 * @returns Padded string.
 */
function padLeft(str: string, length: number): string {
  return str.padStart(length);
}

// ---------------------------------------------------------------------------
// Data retrieval
// ---------------------------------------------------------------------------

/**
 * Retrieves all sessions from the OpenCode environment.
 * In production, this calls the session_list tool via execSync.
 * Currently returns mock data for development.
 * @returns Promise resolving to an array of Session objects.
 */
async function getSessions(): Promise<Session[]> {
  // In OpenCode environment, this would call the actual tools
  // For now, we'll simulate the data structure
  const mockSessions: Session[] = [
    {
      id: 'ses_abc123def456',
      message_count: 45,
      agents_used: ['build', 'oracle', 'librarian'],
      first_message: '2025-12-20T10:30:00Z',
      last_message: new Date(Date.now() - 30 * 60 * 1000).toISOString(), // 30 min ago
      has_todos: true,
      has_transcript: true
    },
    {
      id: 'ses_def456ghi789',
      message_count: 12,
      agents_used: ['build'],
      first_message: '2025-12-19T14:20:00Z',
      last_message: new Date(Date.now() - 2 * 60 * 60 * 1000).toISOString(), // 2 hours ago
      has_todos: false,
      has_transcript: true
    },
    {
      id: 'ses_ghi789jkl012',
      message_count: 3,
      agents_used: ['explore'],
      first_message: '2025-12-18T09:15:00Z',
      last_message: new Date(Date.now() - 25 * 60 * 60 * 1000).toISOString(), // 25 hours ago
      has_todos: false,
      has_transcript: false
    }
  ];

  return mockSessions;
}

/**
 * Sorts sessions by status priority (active > stale > orphaned),
 * then by message count descending within each status group.
 * @param sessions - Array of Session objects to sort.
 * @returns New sorted array of Session objects.
 */
function sortSessions(sessions: Session[]): Session[] {
  return sessions.sort((a, b) => {
    const statusA = getSessionStatus(a.last_message, a.message_count);
    const statusB = getSessionStatus(b.last_message, b.message_count);

    // Sort by status priority: active > stale > orphaned
    const statusPriority = { active: 0, stale: 1, orphaned: 2 };
    const priorityDiff = statusPriority[statusA.status] - statusPriority[statusB.status];

    if (priorityDiff !== 0) return priorityDiff;

    // Then by message count descending
    return b.message_count - a.message_count;
  });
}

/**
 * Returns the top 3 priority sessions for the NOW view.
 * Filters for active/stale sessions with todos or high message count.
 * @param sessions - Array of Session objects to filter.
 * @returns Array of up to 3 priority Session objects.
 */
function getNowView(sessions: Session[]): Session[] {
  // Get top 3 active/stale sessions with todos or high message count
  return sessions
    .filter(s => {
      const status = getSessionStatus(s.last_message, s.message_count);
      return status.status !== 'orphaned' && (s.has_todos || s.message_count > 10);
    })
    .slice(0, 3);
}

// ---------------------------------------------------------------------------
// Display functions
// ---------------------------------------------------------------------------

/**
 * Displays all sessions in a formatted table with ID, messages, agents,
 * status, and last-active columns.
 * @param sessions - Array of Session objects to display.
 */
function displayTable(sessions: Session[]): void {
  logger.log('\n📊 SESSION DASHBOARD');
  logger.log('='.repeat(80));

  // Table header
  logger.log(
    padRight('ID', 15) +
    padLeft('Messages', 10) +
    padRight('  Agent', 20) +
    padRight('  Status', 15) +
    padRight('  Last Active', 15)
  );
  logger.log('-'.repeat(80));

  // Table rows
  sessions.forEach(session => {
    const status = getSessionStatus(session.last_message, session.message_count);
    const agentStr = getAgentString(session.agents_used);

    logger.log(
      padRight(truncateId(session.id), 15) +
      padLeft(session.message_count.toString(), 10) +
      padRight(`  ${agentStr}`, 20) +
      padRight(`  ${status.indicator}`, 15) +
      padRight(`  ${status.lastActive}`, 15)
    );
  });

  logger.log('='.repeat(80));
  logger.log(`Total: ${sessions.length} sessions`);
}

/**
 * Displays the NOW view showing top 3 priority sessions with
 * todo and message indicators.
 * @param sessions - Array of Session objects to filter and display.
 */
function displayNowView(sessions: Session[]): void {
  const nowView = getNowView(sessions);

  if (nowView.length === 0) {
    logger.log('\n🎯 NOW VIEW: No active sessions with tasks');
    return;
  }

  logger.log('\n🎯 NOW VIEW (Top 3 Priority)');
  logger.log('-'.repeat(40));

  nowView.forEach((session, index) => {
    const status = getSessionStatus(session.last_message, session.message_count);
    const priority = index + 1;
    const todoIndicator = session.has_todos ? '📋' : '  ';
    const msgIndicator = session.message_count > 10 ? '💬' : '  ';

    logger.log(
      `${priority}. ${truncateId(session.id, 10)} ` +
      `${todoIndicator}${msgIndicator} ` +
      `${session.message_count} msgs ` +
      `${status.indicator}`
    );
  });

  logger.log('-'.repeat(40));
}

// ---------------------------------------------------------------------------
// Main
// ---------------------------------------------------------------------------

/**
 * Main entry point: loads sessions, sorts, and displays dashboard views.
 * @returns Promise that resolves when dashboard is fully displayed.
 */
async function main(): Promise<void> {
  try {
    logger.log('Loading sessions...');

    const sessions = await getSessions();
    const sortedSessions = sortSessions(sessions);

    displayTable(sortedSessions);
    displayNowView(sortedSessions);

    logger.log('\n✅ Dashboard generated successfully');
  } catch (error) {
    logger.error('❌ Error generating dashboard:', error);
    process.exit(1);
  }
}

// Run if this is the main module
if (require.main === module) {
  main();
}

export { getSessions, sortSessions, getNowView, displayTable, displayNowView };
