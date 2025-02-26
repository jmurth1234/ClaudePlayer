# Claude Player

An AI-powered game playing agent using Claude and PyBoy

![Game Screenshot](image.png)

[![Python 3.10](https://img.shields.io/badge/python-3.10-blue.svg)](https://www.python.org/downloads/release/python-31012/)
[![PyBoy](https://img.shields.io/badge/emulator-PyBoy-green.svg)](https://github.com/Baekalfen/PyBoy)
[![Claude](https://img.shields.io/badge/AI-Claude%203.7-purple.svg)](https://anthropic.com/claude)

## Overview

Claude Player is an AI agent that allows Claude AI to play Game Boy games through the PyBoy emulator. It creates an intelligent gaming agent that can observe game frames, make decisions, track game state, and control the emulator through a button input system.

I have been working on this project for a while, and have been meaning to clean it up and release it, and with the release of Claude 3.7 (especially given their semi official https://www.twitch.tv/claudeplayspokemon stream of a similar project), I thought it was a good time to do so.

I've taken some imspiration from their official implementation by adding additional memory tools and summarisation, however mine differs in that I don't have any coordinate based movement helpers: it is purely button based. Additionally, the emulator only ticks when the AI sends inputs, so it is not running at real time speed. 

## Features

- **AI-Powered Gameplay**: Uses Claude 3.7 Sonnet to analyze game frames and determine strategic actions
- **PyBoy Integration**: Controls a Game Boy emulator to play actual game ROMs
- **Memory System**: Implements short-term and long-term memory to maintain context throughout gameplay
- **Automatic Summarization**: Periodically generates game progress summaries to maintain context
- **Tool-Based Control**: Allows the AI to use structured tools to interact with the game and manage its state
- **Screenshot Capture**: Automatically captures and saves game frames for analysis and debugging

## Limitations

- The spacial awareness is not yet very good. It will try to move around the screen in a way that is not always logical.
- It will sometimes get stuck in loops, such as trying to go downstairs at the bottom edge of the room.

## Requirements

- Python 3.10.12
- PyBoy emulator
- Pillow (for image processing)
- Anthropic API key (for Claude access)
- Game Boy ROM files (e.g., Pokemon Gold as shown in the code)
- Saved state file (for starting from a specific point)

## Installation

1. Clone the repository:
   ```
   git clone https://github.com/yourusername/game-agent.git
   cd game-agent
   ```

2. Install dependencies using Pipenv (recommended):
   ```
   pipenv install
   ```
   
   The project uses Python 3.10.12 and includes the following dependencies:
   - pyboy
   - pillow
   - python-dotenv
   - anthropic

   Alternatively, you can install packages manually:
   ```
   pip install anthropic pyboy python-dotenv pillow
   ```

3. Create a `.env` file with your Anthropic API key:
   ```
   ANTHROPIC_API_KEY=your_api_key_here
   ```

4. Place your Game Boy ROM file in the project directory.

## Configuration

The main configuration settings are located in the `Config` class:

```python
class Config:
    """Configuration settings for the game agent."""
    ROM_PATH = 'gold.gbc'            # Path to the Game Boy ROM file
    STATE_PATH = 'gold.gbc.state'    # Path to a saved state (optional)
    LOG_FILE = 'game_agent.log'      # Path to the log file
    EMULATION_SPEED = 1              # Emulation speed multiplier
    ENABLE_WRAPPER = False           # Enable PyBoy game wrapper
    MAX_HISTORY_MESSAGES = 30        # Max messages kept in context
    MODEL = "claude-3-7-sonnet-20250219"  # Claude model to use
    MAX_TOKENS = 20000               # Maximum tokens for Claude response
    THINKING_BUDGET = 16000          # Tokens allocated for Claude thinking
    SUMMARY_INTERVAL = 30            # Generate summary every N turns
```

Adjust these settings as needed for your specific use case.

## Usage

1. Activate the Pipenv environment:
   ```
   pipenv shell
   ```

2. Run the agent:
   ```
   python game_agent.py
   ```

The agent will initialize the emulator, load the ROM (and saved state if available), and begin playing the game automatically.

## Game Control System

The agent uses a structured input notation to control the game:

- **Single Press**: `A` (press A once)
- **Hold**: `A2` (press and hold A for 2 ticks)
- **Simultaneous Press**: `AB` (press A and B simultaneously)
- **Wait**: `W` or `W2` (wait for 1 or 2 ticks)
- **Wait then Press**: `W R` (wait for 1 tick, then press R)
- **Repeated Actions**: `R2` (move right for 2 ticks)

Available button symbols:
- `U`: Up
- `D`: Down
- `L`: Left
- `R`: Right
- `A`: A button
- `B`: B button
- `S`: Start button
- `X`: Select button
- `W`: Wait (no button)

Examples:
- `R2 A U3 UB` (move right for 2 ticks, press A once, move up for 3 ticks, press Up+B simultaneously)

## Tool System

The AI agent has access to several tools to interact with the game and manage its state:

1. **send_inputs**: Send a sequence of button inputs to the game
2. **set_game**: Set the identified game name
3. **set_current_goal**: Set the current goal in the game
4. **add_to_memory**: Add information to the agent's memory
5. **remove_from_memory**: Remove an item from memory
6. **update_memory_item**: Update an existing memory item

## Memory System

The agent maintains two types of memory:

1. **Short-Term Memory**: Recent conversation context (limited to 30 messages)
2. **Long-Term Memory**: Persistent information stored through the memory tools

Memory items can be categorized (e.g., 'items', 'NPCs', 'locations', 'quests') and are formatted in the prompt for the AI to reference.

## Summarization

Every 30 turns, the agent generates a comprehensive summary of the gameplay, including:

1. **Gameplay Summary**: Key events, achievements, and progress
2. **Critical Review**: Analysis of recent gameplay and strategic patterns
3. **Next Steps**: Recommended goals and actions

This helps maintain context over long gaming sessions.

## Debugging and Monitoring

### Screenshots
All game frames are captured and saved to `./frames/{timestamp}/` for debugging and analysis. Each screenshot is timestamped and saved as a PNG file.

### Logging
Detailed logs are saved to `game_agent.log` and include:
- Turn information and timestamps
- Game state (identified game, current goal, memory items)
- Claude's thinking process and responses
- Tool usage with inputs and outputs
- Error messages and warnings

The `debug` function in `utils.py` can also generate a `chat_history.json` and `chat_history.md` file for easier review of the conversation between the agent and Claude.

## Customization

To adapt the agent for different games:

1. Change the `ROM_PATH` in the Config class
2. Adjust `EMULATION_SPEED` as needed (higher values increase speed)
3. Modify the system prompt or tool descriptions if needed for specific games

## How It Works

### Core Workflow
1. The agent initializes the PyBoy emulator and loads the ROM and saved state
2. On each turn, it:
   - Captures the current screen
   - Sends the screenshot to Claude with relevant context
   - Processes Claude's thinking and response
   - Executes any tool calls (game inputs, memory updates, etc.)
   - Saves detailed logs and screenshots
3. Periodically generates summaries to maintain long-term context
4. Uses both short-term (message history) and long-term (memory items) memory systems

### Key Components
- **GameAgent**: Main class that orchestrates the gameplay session
- **GameState**: Manages and tracks the state of the game being played
- **ClaudeInterface**: Handles communication with the Claude API
- **ToolRegistry**: Manages the tools available to Claude 
- **SummaryGenerator**: Creates periodic summaries of gameplay progress
- **MessageUtils**: Utilities for processing and logging Claude's responses

## Examples

### Game Identification and Goal Setting

Here's an example of the agent identifying a game and setting goals:

```
2025-02-26 08:33:22,603 [INFO] ======= NEW TURN: 2025-02-26 08:33:22 =======
2025-02-26 08:33:22,603 [INFO] GAME: Pokémon Gold/Silver/Crystal
2025-02-26 08:33:22,603 [INFO] GOAL: Leave the house and meet Professor Elm to get our first Pokémon
2025-02-26 08:33:22,603 [INFO] TURN: 58
2025-02-26 08:33:22,603 [INFO] SUMMARY: [snipped]
2025-02-26 08:33:29,337 [INFO] HTTP Request: POST https://api.anthropic.com/v1/messages?beta=true "HTTP/1.1 200 OK"
2025-02-26 08:33:29,338 [INFO] ===== DEBUG: MESSAGE STRUCTURE =====
2025-02-26 08:33:29,339 [INFO] Total blocks: 3
2025-02-26 08:33:29,339 [INFO] Block 0: type=thinking, content=I see that I'm still not finding the exit. Let me try a different approach. In Pokémon Gold/Silver/C...
2025-02-26 08:33:29,339 [INFO] Block 1: type=text, content=Let me move one tile more to the left to stand directly on the white doormat, and then press down:
2025-02-26 08:33:29,339 [INFO] Block 2: type=tool_use, tool=send_inputs, input={
  "inputs": "L1 D1"
}
2025-02-26 08:33:29,339 [INFO] ===== END DEBUG: MESSAGE STRUCTURE =====
2025-02-26 08:33:29,339 [INFO] CLAUDE'S THINKING:
2025-02-26 08:33:29,339 [INFO]   I see that I'm still not finding the exit. Let me try a different approach. In Pokémon Gold/Silver/Crystal, the exit from the house is typically a carpet or mat at the bottom of the room, and you need to press down when standing on it to leave.

Let me try:
1. First, let me try standing directly on the white object to the left (which appears to be a carpet or doormat) and pressing down
2. If that doesn't work, I'll try the center area between furniture
3. I should also use the Start button to check the menu and see if there's any useful information there

Let me try pressing down while standing on the white object:
2025-02-26 08:33:29,339 [INFO] CLAUDE'S RESPONSE:
2025-02-26 08:33:29,339 [INFO]   Let me move one tile more to the left to stand directly on the white doormat, and then press down:
2025-02-26 08:33:29,339 [INFO] TOOLS USED:
2025-02-26 08:33:29,339 [INFO]   Tool: send_inputs
2025-02-26 08:33:29,339 [INFO]   Input: {
  "inputs": "L1 D1"
}
2025-02-26 08:33:29,339 [INFO] EXECUTING INPUTS: L1 D1
Executing sequence: L1 D1
Actions: [('L', 1), ('D', 1)]
Pressing L for 1 ticks
Releasing L
Pressing D for 1 ticks
Releasing D
2025-02-26 08:33:30,340 [INFO] ======= END TURN: 2025-02-26 08:33:30 =======
```

### Example Summarization

```
# Pokémon Gold/Silver/Crystal Gameplay Summary

## GAMEPLAY SUMMARY
- We're at the very beginning of Pokémon Gold/Silver/Crystal, with our character starting in their home in New Bark Town.
- Our character appears to be the male protagonist based on the sprite's appearance with characteristic red hair.
- We've been exploring the small house, which contains typical home furniture including a table/cabinet on the right side and what appears to be a TV or dresser on the left.
- No NPC interactions have occurred yet, as we haven't spoken to any characters.
- We haven't yet found the exit to leave the house, which is our first objective.

## CRITICAL REVIEW
- The exploration has been somewhat inefficient, with repeated movements across similar areas of the house.
- We've been missing the exit mat that should be located somewhere along the bottom wall of the house.
- The search pattern has been unsystematic, moving back and forth between areas we've already checked rather than methodically checking new areas.
- We've been looking in the correct general area (the bottom of the house) but haven't found the specific exit point yet.
- There hasn't been any attempt to interact with objects in the house or check the menu for any initial items.

## NEXT STEPS
1. **Find the exit mat:** Continue searching along the bottom wall of the house, likely in the center-bottom area. Try moving to each position along the bottom wall and pressing down to check for the exit.
2. **Use the A button:** When near suspicious areas (door mats, door-shaped objects), try pressing A to interact.
3. **Check the menu:** Press Start to check if we have any items or to review any initial game information.
4. **Once outside:** After leaving the house, look for Professor Elm's laboratory, which should be nearby in New Bark Town.
5. **Talk to NPCs:** When encountering other characters, talk to them for potential hints about where to go.
```

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.

## License

[MIT License](LICENSE)

## Acknowledgments

- Anthropic for the Claude AI model
- PyBoy developers for the Game Boy emulator