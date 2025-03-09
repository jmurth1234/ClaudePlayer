import os
import sys
import logging
import json
import time
import threading
from datetime import datetime
from typing import List, Dict, Any, Optional
from pyboy import PyBoy

from claude_player.config.config_class import ConfigClass
from claude_player.config.config_loader import setup_logging
from claude_player.state.game_state import GameState
from claude_player.tools.tool_setup import setup_tool_registry
from claude_player.interface.claude_interface import ClaudeInterface
from claude_player.agent.summary_generator import SummaryGenerator
from claude_player.utils.message_utils import MessageUtils
from claude_player.utils.game_utils import take_screenshot

class GameAgent:
    """Main game agent class that orchestrates the AI gameplay."""
    
    def __init__(self, config: ConfigClass):
        """Initialize the game agent with a configuration object."""
        self.config = config
        setup_logging(self.config)
        
        # Check if ROM file exists
        if not os.path.exists(self.config.ROM_PATH):
            error_msg = f"ERROR: ROM file not found: {self.config.ROM_PATH}"
            logging.critical(error_msg)
            logging.critical("Please check your configuration and ensure the ROM file exists.")
            logging.critical(f"If you're using a custom configuration file, verify the 'ROM_PATH' setting.")
            sys.exit(1)
        
        # Initialize game components with sound enabled if in continuous mode
        pyboy_kwargs = {
            "game_wrapper": True,
        }
        
        # Enable sound in continuous mode if configured
        if hasattr(self.config, 'ENABLE_SOUND') and self.config.ENABLE_SOUND and self.config.EMULATION_MODE == "continuous":
            logging.info("Sound enabled in continuous mode")
            pyboy_kwargs["sound"] = True
            pyboy_kwargs["sound_system"] = "SDL2"
        
        self.pyboy = PyBoy(self.config.ROM_PATH, **pyboy_kwargs)
        self.pyboy.set_emulation_speed(target_speed=self.config.EMULATION_SPEED)
        
        # Load saved state if available
        if self.config.STATE_PATH:
            if not os.path.exists(self.config.STATE_PATH):
                logging.warning(f"Saved state file not found: {self.config.STATE_PATH}")
                print(f"Warning: Saved state file not found: {self.config.STATE_PATH}")
            else:
                with open(self.config.STATE_PATH, "rb") as file:
                    self.pyboy.load_state(file)
        
        # Initialize game wrapper if enabled
        self.wrapper = self.pyboy.game_wrapper()
        if self.wrapper is not None and self.config.ENABLE_WRAPPER:
            self.wrapper.start_game()
        
        # Initialize game state
        self.game_state = GameState()
        self.game_state.runtime_thinking_enabled = self.config.ACTION.get("THINKING", True)
        
        # Initialize tool registry
        self.tool_registry = setup_tool_registry(self.pyboy, self.game_state)
        
        # Initialize Claude interface
        self.claude = ClaudeInterface(self.config)

        # Initialize summary generator
        self.summary_generator = SummaryGenerator(self.claude, self.game_state, self.tool_registry, self.config)
        
        # Initialize chat history
        self.chat_history = []
    
    def prepare_turn_state(self):
        """Prepare the game state for a new turn or analysis."""
        # Increment turn counter
        self.game_state.increment_turn()
        
        # Log the turn
        current_time_str = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        logging.info(f"======= NEW TURN: {current_time_str} =======")
        self.game_state.log_state()
        
        # Capture current screenshot
        screenshot = take_screenshot(self.pyboy, True)
        
        # Prepare user content with screenshot and optional wrapper text
        user_content = [screenshot]
        if self.wrapper is not None and self.config.ENABLE_WRAPPER:
            user_content.append({"type": "text", "text": f"A textual representation of the current screen is:\n{self.wrapper}"})
        
        # Add timing information in continuous mode
        if hasattr(self.config, 'EMULATION_MODE') and self.config.EMULATION_MODE == "continuous":
            user_content.insert(0, {"type": "text", "text": f"Current time: {current_time_str}\nTurn #{self.game_state.turn_count}"})
        
        # Add user message to chat history
        if len(self.chat_history) == 0:
            user_message = {"role": "user", "content": user_content}
            self.chat_history.append(user_message)
            self.game_state.add_to_complete_history(user_message)
        else:
            current_memory = self.game_state.get_current_state_summary()
            user_message = {"role": "user", "content": [{"type": "text", "text": current_memory}] + user_content}
            self.chat_history.append(user_message)
            self.game_state.add_to_complete_history(user_message)
        
        # Check if we need to generate a summary
        if (self.config.SUMMARY["INITIAL_SUMMARY"] and self.game_state.turn_count == 1) or (self.game_state.turn_count % self.config.SUMMARY["SUMMARY_INTERVAL"] == 0 and self.game_state.turn_count > 0):
            logging.info(f"Generating summary at turn {self.game_state.turn_count}")
            summary = self.summary_generator.generate_summary(self.game_state.complete_message_history)
            self.game_state.update_summary(summary)

    def get_ai_response(self):
        """Get AI response for the current game state."""
        try:
            # Generate system prompt
            system_prompt = self.claude.generate_system_prompt()
            
            # Get tools
            tools = self.tool_registry.get_tools()
            
            # Create a copy of the config.ACTION dictionary so we can modify it
            action_config = self.config.ACTION.copy()
            
            # Override the THINKING setting with the runtime value from GameState
            if hasattr(self.game_state, 'runtime_thinking_enabled'):
                action_config["THINKING"] = self.config.MODEL_DEFAULTS.get("THINKING", True) and self.game_state.runtime_thinking_enabled
            
            # Send request to Claude
            message = self.claude.send_request(
                action_config, 
                system_prompt, 
                self.chat_history, 
                tools
            )
            
            # Debug message structure
            MessageUtils.debug_message_structure(message)
            
            # Get assistant response and add to chat history
            assistant_content = message.content
            assistant_message = {"role": "assistant", "content": assistant_content}
            self.chat_history.append(assistant_message)
            self.game_state.add_to_complete_history(assistant_message)
            
            message_content = MessageUtils.print_and_extract_message_content(message)
            return message_content
            
        except Exception as e:
            error_msg = f"ERROR in get_ai_response: {str(e)}"
            logging.error(error_msg)
            # Re-raise the exception so the caller can handle it
            raise
    
    def process_tool_results(self, message_content, execute_tools=True):
        """Process tool results from AI response."""
        tool_use_blocks = message_content["tool_use_blocks"]
        
        # Process tool use blocks
        tool_results = []
        pending_actions = []
        
        for tool_use in tool_use_blocks:
            tool_name = tool_use.name
            tool_input = tool_use.input
            tool_use_id = tool_use.id
            
            # Handle send_inputs separately in continuous mode
            if tool_name == "send_inputs" and not execute_tools:
                pending_actions.append(tool_input["inputs"])
                logging.info(f"Queued input for later execution: {tool_input['inputs']} (queue size: {len(pending_actions)})")
                # Even in continuous mode, we need to provide a tool_result for send_inputs
                # to keep the conversation flow valid, but we'll execute the inputs later
                tool_results.append({
                    "type": "tool_result",
                    "tool_use_id": tool_use_id,
                    "content": [{"type": "text", "text": "Input queued for execution"}]
                })
            else:
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
        if len(self.chat_history) > self.config.MAX_HISTORY_MESSAGES:
            self.chat_history = self.chat_history[-self.config.MAX_HISTORY_MESSAGES:]
            
        return pending_actions

    def run_turn(self):
        """Run a single turn of the game."""
        try:
            # Prepare turn state
            self.prepare_turn_state()
            
            # Get AI response
            message_content = self.get_ai_response()
            
            # Process tools (execute all tools immediately)
            self.process_tool_results(message_content, execute_tools=True)
            
        except Exception as e:
            error_msg = f"CRITICAL ERROR: {str(e)}"
            logging.critical(error_msg)
            
            # Check if we have a tool_use in history that needs a response
            if len(self.chat_history) >= 2 and self.chat_history[-1]["role"] == "assistant":
                assistant_content = self.chat_history[-1]["content"]
                # Fix: Use proper access method for the content blocks based on their type
                tool_use_blocks = []
                for block in assistant_content:
                    if isinstance(block, dict) and block.get("type") == "tool_use":
                        tool_use_blocks.append(block)
                    elif hasattr(block, "type") and block.type == "tool_use":
                        tool_use_blocks.append(block)
                
                if tool_use_blocks:
                    # Create error responses for each tool use
                    tool_results = []
                    for tool_use in tool_use_blocks:
                        # Handle both dictionary and object access
                        tool_use_id = tool_use.get("id") if isinstance(tool_use, dict) else tool_use.id
                        tool_results.append({
                            "type": "tool_result",
                            "tool_use_id": tool_use_id,
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
            
    def run_continuous(self):
        """Run the game agent in continuous mode where the emulator runs at 1x speed continuously."""
        logging.info("Starting continuous emulation mode")
        print(f"Running in continuous mode at 1x speed with analysis every {self.config.CONTINUOUS_ANALYSIS_INTERVAL} seconds")
        
        # Set emulation speed to 1x (real-time)
        self.pyboy.set_emulation_speed(target_speed=1)
        
        # Variables to track time for AI analysis
        last_analysis_time = time.time()
        last_analysis_duration = 0
        adaptive_interval = self.config.CONTINUOUS_ANALYSIS_INTERVAL
        
        ai_is_analyzing = False
        ai_thread = None
        
        # Create a flag to signal when AI has completed its analysis
        analysis_complete = False
        pending_actions = []
        
        # Error tracking variables
        self.error_count = 0
        self.last_error_time = 0
        
        # Add threading lock for shared variables
        lock = threading.Lock()
        
        # Function to run AI analysis in a separate thread
        def run_analysis():
            nonlocal analysis_complete, pending_actions, last_analysis_duration, adaptive_interval
            
            analysis_start_time = time.time()
            message_content = None
            
            try:
                # Prepare turn state
                self.prepare_turn_state()
                
                # Get AI response
                message_content = self.get_ai_response()
                
                # Process tools (don't execute send_inputs immediately)
                actions = self.process_tool_results(message_content, execute_tools=False)
                
                # Safely update shared variables
                with lock:
                    pending_actions.extend(actions)
                
                # Calculate how long the analysis took
                analysis_end_time = time.time()
                last_analysis_duration = analysis_end_time - analysis_start_time
                
                # Update adaptive interval - use a moving average to smooth changes
                # Mix 70% of current interval with 30% of new duration to smooth transitions
                with lock:
                    adaptive_interval = (0.7 * adaptive_interval) + (0.3 * last_analysis_duration)
                    adaptive_interval = max(adaptive_interval, self.config.CONTINUOUS_ANALYSIS_INTERVAL)
                
                logging.info(f"======= END ANALYSIS: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} =======")
                logging.info(f"Analysis took {last_analysis_duration:.2f} seconds, adaptive interval: {adaptive_interval:.2f}s")
                
                # Log a warning if the analysis took longer than the configured interval
                if last_analysis_duration > self.config.CONTINUOUS_ANALYSIS_INTERVAL:
                    logging.warning(f"Analysis took {last_analysis_duration:.2f} seconds, which is longer than " 
                                   f"the configured interval of {self.config.CONTINUOUS_ANALYSIS_INTERVAL} seconds")
                    logging.warning("Using adaptive interval to optimize analysis frequency")
                
                # Reset error count after successful analysis
                with lock:
                    self.error_count = 0
                
            except Exception as e:
                error_msg = f"CRITICAL ERROR during analysis: {str(e)}"
                logging.critical(error_msg)
                
                # Track error frequency
                current_time = time.time()
                with lock:
                    if current_time - self.last_error_time < 60:  # Within a minute
                        self.error_count += 1
                    else:
                        self.error_count = 1
                    self.last_error_time = current_time
                
                    # If too many errors in a short time, increase the delay
                    if self.error_count > 3:
                        logging.warning(f"Multiple errors ({self.error_count}) detected, increasing delay between analyses")
                        time.sleep(5.0)  # More aggressive delay
                        adaptive_interval = max(adaptive_interval * 1.5, 10.0)  # Increase interval dramatically
                    else:
                        # Add delay after error to avoid rapid error loops
                        time.sleep(2.0)
                
                # Try to handle any existing tool_use blocks
                if message_content is not None and "tool_use_blocks" in message_content:
                    # Handle tool_use blocks that might exist in message_content
                    tool_use_blocks = message_content["tool_use_blocks"]
                    if tool_use_blocks:
                        tool_results = []
                        for tool_use in tool_use_blocks:
                            # Handle both dictionary and object access
                            tool_use_id = tool_use.get("id") if isinstance(tool_use, dict) else tool_use.id
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": [{"type": "text", "text": f"Error: {str(e)}"}]
                            })
                        
                        # Add tool results to chat history to maintain API conversation requirements
                        tool_results_message = {
                            "role": "user",
                            "content": tool_results
                        }
                        self.chat_history.append(tool_results_message)
                        self.game_state.add_to_complete_history(tool_results_message)
                        logging.info("Added error responses for pending tool use blocks from message_content")
                # Fall back to checking chat history if message_content is None or doesn't have tool_use_blocks
                elif len(self.chat_history) >= 2 and self.chat_history[-1]["role"] == "assistant":
                    assistant_content = self.chat_history[-1]["content"]
                    # Fix: Use proper access method for the content blocks based on their type
                    tool_use_blocks = []
                    for block in assistant_content:
                        if isinstance(block, dict) and block.get("type") == "tool_use":
                            tool_use_blocks.append(block)
                        elif hasattr(block, "type") and block.type == "tool_use":
                            tool_use_blocks.append(block)
                    
                    if tool_use_blocks:
                        # Create error responses for each tool use
                        tool_results = []
                        for tool_use in tool_use_blocks:
                            # Handle both dictionary and object access
                            tool_use_id = tool_use.get("id") if isinstance(tool_use, dict) else tool_use.id
                            tool_results.append({
                                "type": "tool_result",
                                "tool_use_id": tool_use_id,
                                "content": [{"type": "text", "text": f"Error: {str(e)}"}]
                            })
                        
                        # Add tool results to chat history to maintain API conversation requirements
                        tool_results_message = {
                            "role": "user",
                            "content": tool_results
                        }
                        self.chat_history.append(tool_results_message)
                        self.game_state.add_to_complete_history(tool_results_message)
                        logging.info("Added error responses for pending tool use blocks from chat history")
            
            # Mark analysis as complete
            with lock:
                analysis_complete = True
        
        # Main continuous emulation loop
        try:
            while True:
                current_time = time.time()
                
                # Process any pending actions from the AI
                action = None
                with lock:
                    if not ai_is_analyzing and pending_actions:
                        action = pending_actions.pop(0)
                
                if action:
                    logging.info(f"Executing pending action: {action} (remaining: {len(pending_actions)})")
                    try:
                        from claude_player.utils.game_utils import press_and_release_buttons
                        press_and_release_buttons(self.pyboy, action)
                    except Exception as e:
                        logging.error(f"Error executing inputs '{action}': {str(e)}")
                        # Continue with next actions rather than crashing
                
                # Check if it's time to run AI analysis and we're not already analyzing
                time_since_last_analysis = current_time - last_analysis_time
                
                start_analysis = False
                with lock:
                    if (not ai_is_analyzing and time_since_last_analysis >= adaptive_interval):
                        start_analysis = True
                        ai_is_analyzing = True
                        analysis_complete = False
                
                if start_analysis:
                    logging.info(f"Starting analysis (adaptive interval: {adaptive_interval:.2f}s, " 
                                f"time since last: {time_since_last_analysis:.2f}s)")
                    
                    # Start AI analysis in a separate thread
                    ai_thread = threading.Thread(target=run_analysis)
                    ai_thread.daemon = True  # Make thread a daemon so it exits when main program exits
                    ai_thread.start()
                    last_analysis_time = current_time
                
                # Check if AI analysis has completed
                with lock:
                    if ai_is_analyzing and analysis_complete:
                        ai_is_analyzing = False
                    
                # Tick the emulator regardless of AI state
                if self.pyboy.tick():
                    # PyBoy signal to exit
                    break
                
                # Sleep a tiny amount to avoid maxing out CPU
                time.sleep(0.001)
                
        except KeyboardInterrupt:
            logging.info("Received keyboard interrupt, stopping emulation")
            print("\nStopping emulation...")
        
        # Clean up
        if ai_thread and ai_thread.is_alive():
            # Wait for AI thread to complete (with timeout)
            ai_thread.join(timeout=2.0)

    def run(self):
        """Run the game agent until completion."""
        # Print game title
        print(f"Game: {self.pyboy.cartridge_title()}")
        
        # Main game loop based on emulation mode
        if self.config.EMULATION_MODE == "turn_based":
            # Turn-based emulation mode
            while not self.pyboy.tick():
                self.run_turn()
        elif self.config.EMULATION_MODE == "continuous":
            # Continuous emulation mode
            self.run_continuous()
        else:
            error_msg = f"Invalid EMULATION_MODE: {self.config.EMULATION_MODE}. Valid options are 'turn_based' or 'continuous'."
            logging.critical(error_msg)
            print(error_msg)
            sys.exit(1) 