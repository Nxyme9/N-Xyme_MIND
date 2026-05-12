#!/usr/bin/env python3
"""N-Xyme CLI - Command-line interface for nxyme_core modules."""
import sys
import json
import argparse
import asyncio
from typing import Optional

def run_agent(args):
    from nxyme_core.agent_tool import AgentTool
    tool = AgentTool()
    if args.action == 'spawn':
        result = tool.spawn_subagent(args.agent_type, args.prompt)
        print(result)
    elif args.action == 'list':
        result = tool.list_subagents()
        print(json.dumps(result, indent=2))
    elif args.action == 'kill':
        result = tool.kill_subagent(args.task_id)
        print(result)

def run_task(args):
    from nxyme_core.task_manager import TaskManager
    mgr = TaskManager()
    if args.action == 'create':
        name = args.name or getattr(args, 'title', 'Untitled')
        result = mgr.create_task(name, json.loads(args.metadata or '{}'))
        print(result)
    elif args.action == 'list':
        result = mgr.list_tasks(limit=int(args.limit))
        print(json.dumps(result, indent=2))
    elif args.action == 'get':
        result = mgr.get_task(args.task_id)
        print(json.dumps(result, indent=2))
    elif args.action == 'update':
        result = mgr.update_task(args.task_id, status=args.status)
        print(result)
    elif args.action == 'delete':
        result = mgr.delete_task(args.task_id)
        print(result)

async def run_skill(args):
    from nxyme_core.skill_loader import SkillLoader
    loader = SkillLoader()
    if args.action == 'list':
        result = loader.list_skills()
        print(json.dumps(result, indent=2))
    elif args.action == 'execute':
        result = await loader.execute_skill(args.skill_name, user_message=args.message)
        print(result)

def run_team(args):
    from nxyme_core.team_manager import TeamManager
    mgr = TeamManager()
    if args.action == 'create':
        result = mgr.create_team(args.name)
        print(result)
    elif args.action == 'delete':
        result = mgr.delete_team(args.team_id)
        print(result)

def run_schedule(args):
    from nxyme_core.schedule_manager import SchedulerManager
    mgr = SchedulerManager()
    if args.action == 'create':
        result = mgr.create_cron(args.name, args.cron, args.command)
        print(result)
    elif args.action == 'list':
        result = mgr.list_jobs()
        print(json.dumps(result, indent=2))
    elif args.action == 'delete':
        result = mgr.delete_job(args.job_id)
        print(result)

def main():
    parser = argparse.ArgumentParser(prog='nxyme', description='N-Xyme CLI')
    subparsers = parser.add_subparsers(dest='module', help='Module to use')
    
    agent_parser = subparsers.add_parser('agent', help='Agent tool operations')
    agent_parser.add_argument('action', choices=['spawn', 'list', 'kill'])
    agent_parser.add_argument('--agent-type', default='general')
    agent_parser.add_argument('--prompt', default='')
    agent_parser.add_argument('--task-id', dest='task_id')
    
    task_parser = subparsers.add_parser('task', help='Task management')
    task_parser.add_argument('action', choices=['create', 'list', 'get', 'update', 'delete'])
    task_parser.add_argument('--name', '--title', dest='name', default=None)
    task_parser.add_argument('--metadata', default='{}')
    task_parser.add_argument('--limit', default='50')
    task_parser.add_argument('--task-id', dest='task_id')
    task_parser.add_argument('--status')
    
    skill_parser = subparsers.add_parser('skill', help='Skill operations')
    skill_parser.add_argument('action', choices=['list', 'execute'])
    skill_parser.add_argument('--skill-name', dest='skill_name')
    skill_parser.add_argument('--message', default='')
    
    team_parser = subparsers.add_parser('team', help='Team management')
    team_parser.add_argument('action', choices=['create', 'delete'])
    team_parser.add_argument('--name')
    team_parser.add_argument('--team-id', dest='team_id')
    
    sched_parser = subparsers.add_parser('schedule', help='Scheduler operations')
    sched_parser.add_argument('action', choices=['create', 'list', 'delete'])
    sched_parser.add_argument('--name')
    sched_parser.add_argument('--cron')
    sched_parser.add_argument('--command')
    sched_parser.add_argument('--job-id', dest='job_id')
    
    args = parser.parse_args()
    
    if args.module == 'agent':
        run_agent(args)
    elif args.module == 'task':
        run_task(args)
    elif args.module == 'skill':
        asyncio.run(run_skill(args))
    elif args.module == 'team':
        run_team(args)
    elif args.module == 'schedule':
        run_schedule(args)
    else:
        parser.print_help()

if __name__ == '__main__':
    main()