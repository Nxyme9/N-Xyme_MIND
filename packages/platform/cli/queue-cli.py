#!/usr/bin/env python3
"""CLI tool for SQLite message queue management."""

from __future__ import annotations

import argparse
import json
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from packages.orchestration.message_queue.message_queue import MessageQueue, MessagePriority


def cmd_enqueue(args):
    mq = MessageQueue()
    priority = MessagePriority[args.priority.upper()]
    ttl = args.ttl if args.ttl else None
    body = " ".join(args.body) if isinstance(args.body, list) else args.body
    msg_id = mq.enqueue(body, priority=priority, ttl_seconds=ttl)
    print(f"Enqueued message: {msg_id}")


def cmd_dequeue(args):
    mq = MessageQueue()
    consumer = args.consumer or "cli-worker"
    msg = mq.dequeue(consumer)
    if msg is None:
        print("No messages in queue.")
        return
    print(json.dumps(msg.to_dict(), indent=2))


def cmd_ack(args):
    mq = MessageQueue()
    success = mq.ack(args.message_id)
    if success:
        print(f"Acknowledged: {args.message_id}")
    else:
        print(f"Failed to ack {args.message_id} (not found or not processing)")
        sys.exit(1)


def cmd_nack(args):
    mq = MessageQueue()
    success = mq.nack(args.message_id, requeue=not args.no_requeue)
    if success:
        print(f"Nacked: {args.message_id}")
    else:
        print(f"Failed to nack {args.message_id}")
        sys.exit(1)


def cmd_stats(args):
    mq = MessageQueue()
    stats = mq.get_stats()
    depth_by_prio = mq.get_queue_depth_by_priority()
    output = {**stats, "by_priority": depth_by_prio}
    print(json.dumps(output, indent=2))


def cmd_depth(args):
    mq = MessageQueue()
    depth = mq.get_queue_depth()
    print(f"Queue depth: {depth}")


def cmd_dead_letters(args):
    mq = MessageQueue()
    letters = mq.get_dead_letters()
    if not letters:
        print("No dead letters.")
        return
    for letter in letters:
        print(json.dumps(letter.to_dict(), indent=2))
        print("---")


def cmd_purge(args):
    mq = MessageQueue()
    deleted = mq.purge_expired()
    print(f"Purged {deleted} expired message(s).")


def cmd_requeue_dl(args):
    mq = MessageQueue()
    success = mq.requeue_dead_letter(args.message_id)
    if success:
        print(f"Requeued dead letter: {args.message_id}")
    else:
        print(f"Failed to requeue {args.message_id}")
        sys.exit(1)


def cmd_delete_dl(args):
    mq = MessageQueue()
    success = mq.delete_dead_letter(args.message_id)
    if success:
        print(f"Deleted dead letter: {args.message_id}")
    else:
        print(f"Failed to delete {args.message_id}")
        sys.exit(1)


def cmd_vacuum(args):
    mq = MessageQueue()
    mq.vacuum()
    print("Database vacuumed.")


def main():
    parser = argparse.ArgumentParser(
        description="SQLite Message Queue CLI",
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    subparsers = parser.add_subparsers(dest="command", help="Available commands")

    p_enqueue = subparsers.add_parser("enqueue", help="Add a message to the queue")
    p_enqueue.add_argument("body", nargs="+", help="Message body")
    p_enqueue.add_argument(
        "-p", "--priority", default="normal", choices=["high", "normal", "low"]
    )
    p_enqueue.add_argument("-t", "--ttl", type=int, help="TTL in seconds")
    p_enqueue.set_defaults(func=cmd_enqueue)

    p_dequeue = subparsers.add_parser("dequeue", help="Get next message from queue")
    p_dequeue.add_argument("-c", "--consumer", help="Consumer ID")
    p_dequeue.set_defaults(func=cmd_dequeue)

    p_ack = subparsers.add_parser("ack", help="Acknowledge a message")
    p_ack.add_argument("message_id", help="Message ID")
    p_ack.set_defaults(func=cmd_ack)

    p_nack = subparsers.add_parser("nack", help="Negative acknowledge a message")
    p_nack.add_argument("message_id", help="Message ID")
    p_nack.add_argument("--no-requeue", action="store_true", help="Do not requeue")
    p_nack.set_defaults(func=cmd_nack)

    p_stats = subparsers.add_parser("stats", help="Show queue statistics")
    p_stats.set_defaults(func=cmd_stats)

    p_depth = subparsers.add_parser("depth", help="Show queue depth")
    p_depth.set_defaults(func=cmd_depth)

    p_dl = subparsers.add_parser("dead-letters", help="List dead letters")
    p_dl.set_defaults(func=cmd_dead_letters)

    p_purge = subparsers.add_parser("purge", help="Purge expired messages")
    p_purge.set_defaults(func=cmd_purge)

    p_requeue_dl = subparsers.add_parser("requeue-dl", help="Requeue a dead letter")
    p_requeue_dl.add_argument("message_id", help="Message ID")
    p_requeue_dl.set_defaults(func=cmd_requeue_dl)

    p_delete_dl = subparsers.add_parser("delete-dl", help="Delete a dead letter")
    p_delete_dl.add_argument("message_id", help="Message ID")
    p_delete_dl.set_defaults(func=cmd_delete_dl)

    p_vacuum = subparsers.add_parser("vacuum", help="Vacuum the database")
    p_vacuum.set_defaults(func=cmd_vacuum)

    args = parser.parse_args()
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()
