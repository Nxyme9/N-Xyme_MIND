#!/usr/bin/env python3
import re, sys

patterns = [
    re.compile(r'(?i)api[_-]?key\s*[:=]\s*["\\']?([^"\\']{20,})'),
    re.compile(r'(?i)secret[_-]?key\s*[:=]\s*["\\']?([^"\\']{20,})'),
    re.compile(r'(?i)aws[_-]?secret[_-]?access[_-]?key\s*[:=]\s*["\\']?([^"\\']{40})')
]

def redact_line(line):
    for pat in patterns:
        m = pat.search(line)
        if m:
            line = line[:m.start()] + '[REDACTED_SECRET]' + line[m.end():]
    return line

def redact_file(path):
    with open(path, 'r', encoding='utf-8', errors='ignore') as f:
        lines = f.readlines()
    new_lines = [redact_line(l) for l in lines]
    with open(path, 'w', encoding='utf-8') as f:
        f.writelines(new_lines)
    print(f'Redacted secrets in {path}')

if __name__ == '__main__':
    if len(sys.argv) < 2:
        print('Usage: redact_secrets.py <path1> [path2 ...]')
        sys.exit(2)
    for p in sys.argv[1:]:
        redact_file(p)
