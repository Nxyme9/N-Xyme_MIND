#!/bin/bash
# Show all processes in KDE System Monitor
kwriteconfig5 --file ksysguardrc --group ProcessSelector --key ShowAllProcesses true
echo "System Monitor fixed! Restart System Monitor to see all processes."