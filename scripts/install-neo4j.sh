#!/usr/bin/env bash
set -e

echo "=== Installing Neo4j for Graphiti Memory ==="

pacman -Q psmisc &>/dev/null || sudo pacman -S --noconfirm psmisc
paru -S --noconfirm neo4j-community-bin
sudo systemctl enable neo4j
sudo systemctl start neo4j
sleep 10
sudo systemctl status neo4j --no-pager || true

echo ""
echo "=== Neo4j Ready ==="
echo "Connection: bolt://localhost:7687"
echo "User: neo4j"
echo "Password: neo4j (default, change with 'sudo neo4j-admin dbms set-initial-password <pwd>')"
echo "Update .env with your password!"
