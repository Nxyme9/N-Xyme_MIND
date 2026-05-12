# N-Xyme Audio Workflow Engine

AI-powered music production workflow system for Bitwig Studio.

## Features

- **Natural Language Processing**: Convert commands like "Start a new track at 140bpm in A minor" to Bitwig OSC commands
- **N-Xyme Memory Integration**: Remembers production patterns and user preferences
- **Production Templates**: Pre-built workflows for recording, mixing, and beat creation
- **Context Awareness**: Tracks project state (tempo, key, tracks) and suggests next actions

## Installation

Requirement already satisfied: pyyaml in /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.venv/lib/python3.14/site-packages (6.0.3)
Requirement already satisfied: requests in /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.venv/lib/python3.14/site-packages (2.33.1)
Requirement already satisfied: charset_normalizer<4,>=2 in /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.venv/lib/python3.14/site-packages (from requests) (3.4.7)
Requirement already satisfied: idna<4,>=2.5 in /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.venv/lib/python3.14/site-packages (from requests) (3.11)
Requirement already satisfied: urllib3<3,>=1.26 in /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.venv/lib/python3.14/site-packages (from requests) (2.6.3)
Requirement already satisfied: certifi>=2023.5.7 in /home/nxyme/N-Xyme_CODE/N-Xyme_MIND/.venv/lib/python3.14/site-packages (from requests) (2026.2.25)

## Usage

### CLI Mode



### Python API



## Configuration

Edit  to customize settings for Bitwig OSC bridge, memory system, and default plugins.

## Supported Commands

| Natural Language | Action |
|---------------|--------|
| "Start a new track at 140bpm in A minor" | Create track with tempo/key |
| "Add some reverb to vocals" | Add Reverb+ to vocal track |
| "Create a drum pattern" | Create drum machine with pattern |

## License

MIT License
