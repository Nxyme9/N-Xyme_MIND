with open('scripts/sync-agents.js', 'r') as f:
    lines = f.readlines()

# Find the problematic section and fix it
for i, line in enumerate(lines):
    if i >= 59 and i <= 72:
        print(f"L{i+1}: {line.rstrip()}")

