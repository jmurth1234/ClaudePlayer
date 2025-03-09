import logging
from typing import List, Dict, Any
from claude_player.config.config_class import ConfigClass
from claude_player.interface.claude_interface import ClaudeInterface
from claude_player.state.game_state import GameState
from claude_player.tools.tool_registry import ToolRegistry
from claude_player.utils.message_utils import MessageUtils
from claude_player.utils.game_utils import button_rules

class SummaryGenerator:
    """Generates game summaries to maintain context over long sessions."""
    
    def __init__(self, client: ClaudeInterface, game_state: GameState, tool_registry: ToolRegistry, config: ConfigClass):
        """Initialize the summary generator."""
        self.client = client
        self.game_state = game_state
        self.tool_registry = tool_registry
        self.config = config

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

The button rules are as follows:
{button_rules}

Write in a concise but comprehensive manner. Focus on information that would be most useful for continued gameplay.

You are given tools as a reference to help you create your summary. DO NOT CALL ANY TOOLS.
"""
        
        initial_summary_system_prompt = """You are an AI planning a gameplay session. Your task is to create a comprehensive summary of what will happen next to maintain context across gameplay sessions.

Your summary should include three clearly labeled sections:
1. GAMEPLAY SUMMARY: Identify the game, what the objective is, and what the initial state of the game is.
2. NEXT STEPS: Clear recommendations for immediate next goals and actions
3. GAMEPLAY TIPS: Any game specific knowledge that would be helpful for the player to know e.g. control scheme, game mechanics, etc.

The button rules are as follows:
{button_rules}

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

        system_prompt = initial_summary_system_prompt if self.game_state.turn_count == 1 else system_prompt

        try:
            response = self.client.send_request(self.config.SUMMARY, system_prompt, messages, self.tool_registry.get_tools())

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