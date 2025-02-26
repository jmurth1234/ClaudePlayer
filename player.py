"""
Game Agent - An AI-powered game playing agent using Claude and PyBoy
"""
from dotenv import load_dotenv
import anthropic
from pyboy import PyBoy
import os
import logging
import json
from datetime import datetime
from typing import List, Dict, Any, Optional, Union

from utils import press_and_release_buttons, button_rules, take_screenshot

# -----------------------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------------------

class Config:
    """Configuration settings for the game agent."""
    ROM_PATH = 'gold.gbc'
    STATE_PATH = 'gold.gbc.state'
    LOG_FILE = 'game_agent.log'
    EMULATION_SPEED = 1
    ENABLE_WRAPPER = False
    MAX_HISTORY_MESSAGES = 30
    MODEL = "claude-3-7-sonnet-20250219"
    MAX_TOKENS = 20000
    THINKING_BUDGET = 16000
    SUMMARY_INTERVAL = 30

# -----------------------------------------------------------------------------
# Logging Setup
# -----------------------------------------------------------------------------

def setup_logging():
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(Config.LOG_FILE),
            logging.StreamHandler()
        ]
    )


# -----------------------------------------------------------------------------
# Game State Management
# -----------------------------------------------------------------------------

class GameState:
    """Manages the state of the game being played."""
    
    def __init__(self):
        self.identified_game = None
        self.current_goal = None
        self.memory_items = []
        self.turn_count = 0
        self.summary = ""
        self.complete_message_history = []  # Store ALL messages without truncation

    def add_to_complete_history(self, message):
        """Add a message to the complete history archive."""
        self.complete_message_history.append(message)

    def format_memory_for_prompt(self) -> str:
        """Format memory items for inclusion in the system prompt."""
        if not self.memory_items:
            return ""
            
        memory_section = "Memory:\n"
        for i, item in enumerate(self.memory_items):
            if isinstance(item, dict) and "category" in item and "item" in item:
                memory_section += f"[{i}] [{item['category']}] {item['item']}\n"
            elif isinstance(item, dict) and "item" in item:
                memory_section += f"[{i}] {item['item']}\n"
            else:
                memory_section += f"[{i}] {item}\n"
        return memory_section
    
    def get_current_state_summary(self) -> str:
        """Get a summary of the current game state."""
        state_summary = f"Current game: {self.identified_game or 'Not identified'}\nCurrent goal: {self.current_goal or 'Not set'}\n{self.format_memory_for_prompt()}"
        
        # Include the AI-generated summary if available
        if self.summary:
            state_summary += "\n\n=== GAME PROGRESS SUMMARY ===\n" + self.summary
            
        return state_summary
    
    def log_state(self):
        """Log the current game state."""
        logging.info(f"GAME: {self.identified_game or 'Not identified'}")
        logging.info(f"GOAL: {self.current_goal or 'Not set'}")
        logging.info(f"TURN: {self.turn_count}")
        logging.info(f"SUMMARY: {self.summary}")
        
        if self.memory_items:
            logging.info("MEMORY ITEMS:")
            for i, item in enumerate(self.memory_items):
                if isinstance(item, dict) and "category" in item and "item" in item:
                    logging.info(f"  [{i}] [{item['category']}] {item['item']}")
                elif isinstance(item, dict) and "item" in item:
                    logging.info(f"  [{i}] {item['item']}")
                else:
                    logging.info(f"  [{i}] {item}")

    def increment_turn(self):
        """Increment the turn counter."""
        self.turn_count += 1

    def update_summary(self, summary: str):
        """Update the summary."""
        self.summary = summary

# -----------------------------------------------------------------------------
# Tool Registry
# -----------------------------------------------------------------------------

class ToolRegistry:
    """
    A registry that manages tool definitions and handlers.
    Uses a decorator pattern to register tool handlers.
    """
    
    def __init__(self, pyboy: PyBoy, game_state: GameState):
        self.pyboy = pyboy
        self.game_state = game_state
        self.tools_definitions = []
        self.handlers = {}
    
    def register(self, name: str, description: str, input_schema: Dict[str, Any]):
        """
        Decorator to register a function as a tool handler.
        
        Args:
            name: The name of the tool
            description: Description of what the tool does
            input_schema: JSON schema for the tool's input
        """
        def decorator(handler_func):
            # Add to tool definitions
            self.tools_definitions.append({
                "name": name,
                "description": description,
                "input_schema": input_schema
            })
            
            # Register the handler function
            self.handlers[name] = handler_func
            return handler_func
        
        return decorator
    
    def get_tools(self) -> List[Dict[str, Any]]:
        """Get the list of available tools."""
        return self.tools_definitions
    
    def execute_tool(self, tool_name: str, tool_input: Dict[str, Any], tool_use_id: str) -> List[Dict[str, Any]]:
        """
        Execute a tool based on the provided name and input.
        
        Args:
            tool_name: The name of the tool to execute
            tool_input: The input parameters for the tool
            tool_use_id: The ID of the tool use request
            
        Returns:
            List of content blocks for the tool result
        """
        try:
            if tool_name in self.handlers:
                # Call the registered handler
                return self.handlers[tool_name](self, tool_input)
            else:
                error_msg = f"Unknown tool: {tool_name}"
                logging.error(error_msg)
                return [{"type": "text", "text": f"Error: {error_msg}"}]
        except Exception as e:
            error_msg = f"Error executing tool {tool_name}: {str(e)}"
            logging.error(error_msg)
            return [{"type": "text", "text": f"Error: {e}"}]

# Create a function to initialize and set up the tool registry
def setup_tool_registry(pyboy: PyBoy, game_state: GameState) -> ToolRegistry:
    """Set up the tool registry with all available tools."""
    registry = ToolRegistry(pyboy, game_state)
    
    # Register send_inputs tool
    @registry.register(
        name="send_inputs",
        description="Send a sequence of button inputs to the game emulator. Please follow the notation rules.",
        input_schema={
            "type": "object",
            "properties": {
                "inputs": {
                    "type": "string",
                    "description": "Sequence of inputs, e.g., 'R5 U2 A2'"
                }
            },
            "required": ["inputs"]
        }
    )
    def handle_send_inputs(self, tool_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        inputs = tool_input["inputs"]
        logging.info(f"EXECUTING INPUTS: {inputs}")
        press_and_release_buttons(self.pyboy, inputs)
        # Capture new screenshot after applying inputs
        new_screenshot = take_screenshot(self.pyboy, True)
        return [
            {"type": "text", "text": "Inputs sent successfully"},
            new_screenshot
        ]
    
    # Register set_game tool
    @registry.register(
        name="set_game",
        description="Set the identified game. Use this tool when you have determined what game is being played based on the frames provided.",
        input_schema={
            "type": "object",
            "properties": {
                "game": {
                    "type": "string",
                    "description": "Name of the game"
                }
            },
            "required": ["game"]
        }
    )
    def handle_set_game(self, tool_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.game_state.identified_game = tool_input["game"]
        logging.info(f"GAME SET TO: {self.game_state.identified_game}")
        return [{"type": "text", "text": f"Game set to {self.game_state.identified_game}"}]
    
    # Register set_current_goal tool
    @registry.register(
        name="set_current_goal",
        description="Set the current goal in the game. Use this tool to update your objective as you progress through the game, such as 'reach the next level' or 'defeat the boss'.",
        input_schema={
            "type": "object",
            "properties": {
                "goal": {
                    "type": "string",
                    "description": "Current goal"
                }
            },
            "required": ["goal"]
        }
    )
    def handle_set_current_goal(self, tool_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        self.game_state.current_goal = tool_input["goal"]
        logging.info(f"GOAL SET TO: {self.game_state.current_goal}")
        return [{"type": "text", "text": f"Current goal set to {self.game_state.current_goal}"}]
    
    # Register add_to_memory tool
    @registry.register(
        name="add_to_memory",
        description="Add a new item to memory. Use this to store important information about the game state, discovered items, NPCs, locations, or other important facts.",
        input_schema={
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "description": "Information to remember"
                },
                "category": {
                    "type": "string",
                    "description": "Optional category for organizing memory (e.g., 'items', 'NPCs', 'locations', 'quests')"
                }
            },
            "required": ["item"]
        }
    )
    def handle_add_to_memory(self, tool_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        item = tool_input["item"]
        # Check if category is provided
        if "category" in tool_input and tool_input["category"]:
            self.game_state.memory_items.append({
                "item": item,
                "category": tool_input["category"]
            })
            memory_msg = f"MEMORY ADDED: [{tool_input['category']}] {item}"
            logging.info(memory_msg)
            return [{"type": "text", "text": f"Added to memory: [{tool_input['category']}] {item}"}]
        else:
            self.game_state.memory_items.append({"item": item})
            memory_msg = f"MEMORY ADDED: {item}"
            logging.info(memory_msg)
            return [{"type": "text", "text": f"Added to memory: {item}"}]
    
    # Register remove_from_memory tool
    @registry.register(
        name="remove_from_memory",
        description="Remove an item from memory. Use this when information is no longer relevant or is incorrect.",
        input_schema={
            "type": "object",
            "properties": {
                "item_index": {
                    "type": "integer",
                    "description": "Index of the item to remove (starting from 0)"
                }
            },
            "required": ["item_index"]
        }
    )
    def handle_remove_from_memory(self, tool_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        item_index = tool_input["item_index"]
        if 0 <= item_index < len(self.game_state.memory_items):
            removed_item = self.game_state.memory_items.pop(item_index)
            if isinstance(removed_item, dict) and "item" in removed_item:
                if "category" in removed_item:
                    memory_msg = f"MEMORY REMOVED: [{removed_item['category']}] {removed_item['item']}"
                    logging.info(memory_msg)
                    return [{"type": "text", "text": f"Removed from memory: [{removed_item['category']}] {removed_item['item']}"}]
                else:
                    memory_msg = f"MEMORY REMOVED: {removed_item['item']}"
                    logging.info(memory_msg)
                    return [{"type": "text", "text": f"Removed from memory: {removed_item['item']}"}]
            else:
                memory_msg = f"MEMORY REMOVED: {removed_item}"
                logging.info(memory_msg)
                return [{"type": "text", "text": f"Removed from memory: {removed_item}"}]
        else:
            error_msg = f"ERROR: Invalid memory item index {item_index}. Valid range: 0-{len(self.game_state.memory_items)-1}"
            logging.error(error_msg)
            return [{"type": "text", "text": f"Error: Invalid memory item index {item_index}. Valid range: 0-{len(self.game_state.memory_items)-1}"}]
    
    # Register update_memory_item tool
    @registry.register(
        name="update_memory_item",
        description="Update an existing memory item. Use this to modify or add details to previously stored information.",
        input_schema={
            "type": "object",
            "properties": {
                "item_index": {
                    "type": "integer",
                    "description": "Index of the item to update (starting from 0)"
                },
                "new_item": {
                    "type": "string",
                    "description": "Updated information"
                }
            },
            "required": ["item_index", "new_item"]
        }
    )
    def handle_update_memory_item(self, tool_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        item_index = tool_input["item_index"]
        new_item = tool_input["new_item"]
        if 0 <= item_index < len(self.game_state.memory_items):
            old_item = self.game_state.memory_items[item_index]
            # Preserve category if it exists
            if isinstance(old_item, dict) and "category" in old_item:
                self.game_state.memory_items[item_index] = {
                    "item": new_item,
                    "category": old_item["category"]
                }
                memory_msg = f"MEMORY UPDATED [{old_item['category']}]: {old_item['item']} → {new_item}"
                logging.info(memory_msg)
                return [{"type": "text", "text": f"Updated memory item [{old_item['category']}]: {old_item['item']} → {new_item}"}]
            else:
                self.game_state.memory_items[item_index] = {"item": new_item}
                if isinstance(old_item, dict) and "item" in old_item:
                    memory_msg = f"MEMORY UPDATED: {old_item['item']} → {new_item}"
                    logging.info(memory_msg)
                    return [{"type": "text", "text": f"Updated memory item: {old_item['item']} → {new_item}"}]
                else:
                    memory_msg = f"MEMORY UPDATED: {old_item} → {new_item}"
                    logging.info(memory_msg)
                    return [{"type": "text", "text": f"Updated memory item: {old_item} → {new_item}"}]
        else:
            error_msg = f"ERROR: Invalid memory item index {item_index}. Valid range: 0-{len(self.game_state.memory_items)-1}"
            logging.error(error_msg)
            return [{"type": "text", "text": f"Error: Invalid memory item index {item_index}. Valid range: 0-{len(self.game_state.memory_items)-1}"}]
    
    return registry

# -----------------------------------------------------------------------------
# Claude API Interaction
# -----------------------------------------------------------------------------

class ClaudeInterface:
    """Interface for interacting with the Claude API."""
    
    def __init__(self):
        """Initialize the Claude interface."""
        load_dotenv()
        self.client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))
    
    def generate_system_prompt(self) -> str:
        """Generate the system prompt for Claude."""
        return f"""You are an AI designed to play video games. You will be given frames from a video game and must use the provided tools to interact with the game. You are also given tools to give yourself a long term memory, as you can only keep a few messages in your short term memory. Your ultimate objective is to defeat the game.

<notation>
{button_rules}
</notation>"""
    
    def send_request(self, system_prompt: str, chat_history: List[Dict[str, Any]], tools: List[Dict[str, Any]]) -> Any:
        """Send a request to the Claude API."""
        try:
            return self.client.beta.messages.create(
                model=Config.MODEL,
                max_tokens=Config.MAX_TOKENS,
                thinking={
                    "type": "enabled",
                    "budget_tokens": Config.THINKING_BUDGET
                },
                tools=tools,
                system=system_prompt,
                messages=chat_history,
                betas=["token-efficient-tools-2025-02-19"]
            )
        except Exception as e:
            logging.error(f"ERROR in Claude API request: {str(e)}")
            raise


# -----------------------------------------------------------------------------
# Summary Generation
# -----------------------------------------------------------------------------

class SummaryGenerator:
    """Generates game summaries to maintain context over long sessions."""
    
    def __init__(self, client: ClaudeInterface, game_state: GameState, tool_registry: ToolRegistry):
        """Initialize the summary generator."""
        self.client = client
        self.game_state = game_state
        self.tool_registry = tool_registry

        self.previous_summary = ""
        self.summary_count = 0
        
    def generate_summary(self, chat_history: List[Dict[str, Any]]) -> str:
        """
        Generate a summary of the gameplay based on chat history and previous summary.
        
        Args:
            chat_history: Complete chat history to analyze (not truncated)
            
        Returns:
            A comprehensive summary of the gameplay
        """
        self.summary_count += 1
        logging.info(f"Generating gameplay summary #{self.summary_count}")
        
        # Create a system prompt for the summary generation
        system_prompt = """You are an AI analyzing a gameplay session. Your task is to create a comprehensive summary of what has happened so far to maintain context across gameplay sessions.

Your summary should include three clearly labeled sections:
1. GAMEPLAY SUMMARY: Key events, achievements, progress, important story developments, etc
2. CRITICAL REVIEW: Analysis of the last 30 steps of gameplay - what worked well, what could be improved, and any strategic patterns
3. NEXT STEPS: Clear recommendations for immediate next goals and actions

Write in a concise but comprehensive manner. Focus on information that would be most useful for continued gameplay.

You are given tools as a reference to help you create your summary. DO NOT CALL ANY TOOLS.
"""
        
        # Create a structured message that includes the previous summary and chat history
        messages = []

        # For summary generation, we need to truncate to a reasonable number to avoid context limits
        # Get the last 60 messages (twice the regular context window)
        recent_history = chat_history[-60:] if len(chat_history) > 60 else chat_history
        messages.extend(recent_history)
        
        # Prepare the full chat history in its original structure
        messages.append({
            "role": "user",
            "content": [
                {
                    "type": "text",
                    "text": "Please analyze the gameplay session and create a comprehensive summary according to the instructions in the system prompt."
                }
            ]
        })

        # Add the previous summary to the last user message
        if self.previous_summary:
            messages[-1]["content"].append({
                "type": "text",
                "text": f"Here is the previous gameplay summary:\n\n{self.game_state.summary}"
            })

        messages[-1]["content"].append({
            "type": "text",
            "text": f"Here is the current game state:\n\n{self.game_state.get_current_state_summary()}"
        })

        try:
            response = self.client.send_request(system_prompt, messages, self.tool_registry.get_tools())

            MessageUtils.debug_message_structure(response)

            message_content = MessageUtils.print_and_extract_message_content(response)
            text_blocks = message_content["text_blocks"]

            summary = ""

            # loop through text blocks and add to summary
            for block in text_blocks:
                summary += block.text

            logging.info(f"Summary generated successfully ({len(summary)} chars)")
            
            # Save this as the previous summary for next time
            self.previous_summary = summary
            return summary
            
        except Exception as e:
            error_msg = f"ERROR generating summary: {str(e)}"
            logging.error(error_msg)
            return f"Summary generation failed: {str(e)}"

# -----------------------------------------------------------------------------
# Message Utilities
# -----------------------------------------------------------------------------

class MessageUtils:
    """Utilities for analyzing and logging message structures."""
    
    @staticmethod
    def debug_message_structure(message):
        """Debug function to analyze and log the structure of a Claude API response message."""
        
        content_blocks = message.content
        
        logging.info("===== DEBUG: MESSAGE STRUCTURE =====")
        logging.info(f"Total blocks: {len(content_blocks)}")
        
        for i, block in enumerate(content_blocks):
            block_type = block.type
            
            # Extract a sample of the content based on block type
            if block_type == "text":
                # Trim long text responses
                sample = block.text[:100] + "..." if len(block.text) > 100 else block.text
                logging.info(f"Block {i}: type={block_type}, content={sample}")
            elif block_type == "thinking":
                sample = block.thinking[:100] + "..." if len(block.thinking) > 100 else block.thinking
                logging.info(f"Block {i}: type={block_type}, content={sample}")
            elif block_type == "tool_use":
                logging.info(f"Block {i}: type={block_type}, tool={block.name}, input={json.dumps(block.input, indent=2)[:100]}")
            else:
                logging.info(f"Block {i}: type={block_type}")
        
        logging.info("===== END DEBUG: MESSAGE STRUCTURE =====")

    @staticmethod
    def print_and_extract_message_content(message):
        """Extract message text and print it."""
        # Extract and process tool use blocks
        content_blocks = message.content

        tool_use_blocks = [block for block in content_blocks if block.type == "tool_use"]
        text_blocks = [block for block in content_blocks if block.type == "text"]
        thinking_blocks = [block for block in content_blocks if block.type == "thinking"]
        
        # Log Claude's thinking if available
        if thinking_blocks:
            logging.info("CLAUDE'S THINKING:")
            for block in thinking_blocks:
                logging.info(f"  {block.thinking}")
        
        # Log Claude's text response
        if text_blocks:
            logging.info("CLAUDE'S RESPONSE:")
            for block in text_blocks:
                logging.info(f"  {block.text}")
        
        # Log tool usage
        if tool_use_blocks:
            logging.info("TOOLS USED:")
            for block in tool_use_blocks:
                tool_input_str = json.dumps(block.input, indent=2)
                logging.info(f"  Tool: {block.name}")
                logging.info(f"  Input: {tool_input_str}")

        return {
            "text_blocks": text_blocks,
            "tool_use_blocks": tool_use_blocks,
            "thinking_blocks": thinking_blocks
        }

# -----------------------------------------------------------------------------
# Game Agent
# -----------------------------------------------------------------------------

class GameAgent:
    """Main game agent class that orchestrates the AI gameplay."""
    
    def __init__(self):
        """Initialize the game agent."""
        setup_logging()
        
        # Initialize game components
        self.pyboy = PyBoy(Config.ROM_PATH, game_wrapper=True)
        self.pyboy.set_emulation_speed(target_speed=Config.EMULATION_SPEED)
        
        # Load saved state if available
        with open(Config.STATE_PATH, "rb") as file:
            self.pyboy.load_state(file)
        
        # Initialize game wrapper if enabled
        self.wrapper = self.pyboy.game_wrapper()
        if self.wrapper is not None and Config.ENABLE_WRAPPER:
            self.wrapper.start_game()
        
        # Initialize game state
        self.game_state = GameState()
        
        # Initialize tool registry
        self.tool_registry = setup_tool_registry(self.pyboy, self.game_state)
        
        # Initialize Claude interface
        self.claude = ClaudeInterface()

        # Initialize summary generator
        self.summary_generator = SummaryGenerator(self.claude, self.game_state, self.tool_registry)
        
        # Initialize chat history
        self.chat_history = []
    
    def run_turn(self):
        """Run a single turn of the game."""
        # Log the beginning of a new turn

        # Increment turn counter
        self.game_state.increment_turn()

        logging.info(f"======= NEW TURN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =======")
        self.game_state.log_state()

        # Check if we need to generate a summary
        if self.game_state.turn_count % Config.SUMMARY_INTERVAL == 0 and self.game_state.turn_count > 0:
            logging.info(f"Generating summary at turn {self.game_state.turn_count}")
            # Use the complete message history for summary generation
            summary = self.summary_generator.generate_summary(self.game_state.complete_message_history)
            self.game_state.update_summary(summary)
        
        # Capture current screenshot
        screenshot = take_screenshot(self.pyboy, True)
        
        # Prepare user content with screenshot and optional wrapper text
        user_content = [screenshot]
        if self.wrapper is not None and Config.ENABLE_WRAPPER:
            user_content.append({"type": "text", "text": f"A textual representation of the current screen is:\n{self.wrapper}"})
        
        # Add user message to chat history if it's the first turn
        if len(self.chat_history) == 0:
            user_message = {"role": "user", "content": user_content}
            self.chat_history.append(user_message)
            self.game_state.add_to_complete_history(user_message)
        else:
            current_memory = self.game_state.get_current_state_summary()
            user_message = {"role": "user", "content": [{"type": "text", "text": current_memory}]}
            self.chat_history.append(user_message)
            self.game_state.add_to_complete_history(user_message)
        
        try:
            # Generate system prompt
            system_prompt = self.claude.generate_system_prompt()
            
            # Get tools
            tools = self.tool_registry.get_tools()
            
            # Send request to Claude
            message = self.claude.send_request(system_prompt, self.chat_history, tools)
            
            # Debug message structure
            MessageUtils.debug_message_structure(message)
            
            # Get assistant response and add to chat history
            assistant_content = message.content
            assistant_message = {"role": "assistant", "content": assistant_content}
            self.chat_history.append(assistant_message)
            self.game_state.add_to_complete_history(assistant_message)
            
            message_content = MessageUtils.print_and_extract_message_content(message)
            tool_use_blocks = message_content["tool_use_blocks"]

            # Process tool use blocks
            tool_results = []
            for tool_use in tool_use_blocks:
                tool_name = tool_use.name
                tool_input = tool_use.input
                tool_use_id = tool_use.id
                
                try:
                    # Execute the tool
                    tool_result_content = self.tool_registry.execute_tool(tool_name, tool_input, tool_use_id)
                    
                    # Add tool result to results list
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": tool_result_content
                    })
                except Exception as e:
                    error_msg = f"ERROR executing tool {tool_name}: {str(e)}"
                    logging.error(error_msg)
                    
                    # Add error result to maintain conversation flow
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tool_use_id,
                        "content": [{"type": "text", "text": f"Error: {str(e)}"}]
                    })
            
            # Add tool results to chat history if there are any
            if tool_results:
                tool_results_message = {
                    "role": "user",
                    "content": tool_results
                }
                self.chat_history.append(tool_results_message)
                self.game_state.add_to_complete_history(tool_results_message)
            
            # Limit chat history to max_messages (but keep complete history intact)
            if len(self.chat_history) > Config.MAX_HISTORY_MESSAGES:
                self.chat_history = self.chat_history[-Config.MAX_HISTORY_MESSAGES:]
            
        except Exception as e:
            error_msg = f"CRITICAL ERROR: {str(e)}"
            logging.critical(error_msg)
            
            # Check if we have a tool_use in history that needs a response
            if len(self.chat_history) >= 2 and self.chat_history[-1]["role"] == "assistant":
                assistant_content = self.chat_history[-1]["content"]
                tool_use_blocks = [block for block in assistant_content if block.type == "tool_use"]
                
                if tool_use_blocks:
                    # Create error responses for each tool use
                    tool_results = []
                    for tool_use in tool_use_blocks:
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use.id,
                            "content": [{"type": "text", "text": f"Error: {str(e)}"}]
                        })
                    
                    # Add tool results to chat history to maintain API conversation requirements
                    tool_results_message = {
                        "role": "user",
                        "content": tool_results
                    }
                    self.chat_history.append(tool_results_message)
                    self.game_state.add_to_complete_history(tool_results_message)
        
        # Log the end of the turn
        logging.info(f"======= END TURN: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =======\n")
    
    def run(self):
        """Run the game agent until completion."""
        # Print game title
        print(f"Game: {self.pyboy.cartridge_title()}")
        
        # Main game loop
        while not self.pyboy.tick():
            self.run_turn()

# -----------------------------------------------------------------------------
# Entry Point
# -----------------------------------------------------------------------------

if __name__ == "__main__":
    agent = GameAgent()
    agent.run()