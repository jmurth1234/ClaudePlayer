# Claude Player

This is an open source project that uses the PyBoy Game Boy emulator and the Anthropic AI API to create an AI bot that plays Game Boy (Colour) games using Claude 3.

## How it works

The project consists of several key components:

1. `emu_setup.py` - A simple script to load the Pokemon Gold ROM into PyBoy and save the initial game state after any intro screens/menus. This saved state is loaded to start the bot.

2. `utils.py` - Contains utility functions for:
    - Taking screenshots of the PyBoy emulator screen 
    - Parsing AI-generated button press sequences into PyBoy control inputs
    - Debugging by saving conversation history and screenshots

3. `player.py` - The main script that runs the bot. It:
    - Loads the saved game state in PyBoy 
    - Sends the current screenshot to the Anthropic API
    - Receives the AI's response with the next actions to take
    - Parses the response and sends the corresponding button presses to PyBoy
    - Repeats this process in a loop to play the game

4. Anthropic API - The AI assistant powering the bot. It analyzes the game screenshots, determines the next actions to take based on the current game state and its knowledge, and returns button press sequences.

## Running the Bot

1. Install dependencies with `pipenv install`
2. Add your Anthropic API key to a `.env` file (use the `.env.example` as a template)
3. Run `emu_setup.py` to save the initial game state
4. Run `player.py` to start the bot

The bot will play the game automatically, saving screenshots and conversation logs to the `frames` directory for debugging.

## Known Limitations

- The bot relies on the AI to correctly interpret the game state from pixel data alone. Complex gameplay mechanics may be difficult to handle.
- Long term goals and multi-step planning is challenging for the AI given its limited context window. The bot plays "reactively" to the current state.
- Performance is limited by the latency of API calls to the Anthropic servers for each observation-action loop.

Overall, this project demonstrates the potential of integrating AI into game bots and the challenges involved in doing so. Contributions and bug reports are welcome!