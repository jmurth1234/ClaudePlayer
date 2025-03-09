import os
import logging
import json
from typing import List, Dict, Any
from dotenv import load_dotenv
import anthropic
from claude_player.config.config_class import ConfigClass

class ClaudeInterface:
    """Interface for interacting with the Claude API."""
    
    def __init__(self, config: ConfigClass = None):
        """Initialize the Claude interface."""
        load_dotenv()
        self.client = anthropic.Client(api_key=os.getenv("ANTHROPIC_API_KEY"))
        self.config = config  # Store the config object
    
    def generate_system_prompt(self) -> str:
        """Generate the system prompt for Claude."""
        from claude_player.utils.game_utils import button_rules
        
        mode_specific_info = ""
        if self.config and self.config.EMULATION_MODE == "continuous":
            mode_specific_info = f"""
You are operating in continuous mode where the game is running in real-time at 1x speed.
Your analysis is performed approximately every {self.config.CONTINUOUS_ANALYSIS_INTERVAL} seconds, but this may be slower if you take longer to analyze the game state.
When you use the send_inputs tool, your inputs will be queued and executed as soon as possible.
Important timing considerations:
1. The game continues running between your analyses
2. There may be a delay between when you see a screenshot and when your inputs execute
3. Your inputs should be robust and adaptable to changing game states
4. If possible, use sequences of inputs that make sense even if the game state has changed slightly

Make your decisions based on the current screenshot but be prepared for the game state to have progressed slightly.
"""
        
        # Add custom instructions from config if available
        custom_instructions = ""
        if self.config and hasattr(self.config, 'CUSTOM_INSTRUCTIONS') and self.config.CUSTOM_INSTRUCTIONS:
            custom_instructions = f"\n{self.config.CUSTOM_INSTRUCTIONS}\n"
        
        return f"""You are an AI agent designed to play video games. You will be given frames from a video game and must use the provided tools to interact with the game. You are also given tools to give yourself a long term memory, as you can only keep a few messages in your short term memory. Your ultimate objective is to defeat the game.

<notation>
{button_rules}
</notation>

{mode_specific_info}

<custom_instructions>
{custom_instructions}
</custom_instructions>

Always use the tools provided to you to interact with the game.
"""
    
    def send_request(
            self,
            mode_config: Dict[str, Any],
            system_prompt: str, 
            chat_history: List[Dict[str, Any]], 
            tools: List[Dict[str, Any]]
        ) -> Any:
        """Send a request to the Claude API using mode configuration."""
        try:
            # Initialize an empty list for collecting beta features
            betas = []
            
            # Add token-efficient-tools beta if enabled
            if mode_config.get("EFFICIENT_TOOLS", False):
                betas.append("token-efficient-tools-2025-02-19")
                        
            # Create API request params (without betas by default)
            request_params = {
                "model": mode_config["MODEL"],
                "max_tokens": mode_config["MAX_TOKENS"],
                "thinking": {
                    "type": "enabled",
                    "budget_tokens": mode_config["THINKING_BUDGET"]
                } if mode_config.get("THINKING", False) else {
                    "type": "disabled"
                },
                "tools": tools,
                "system": system_prompt,
                "messages": chat_history,
            }
            
            # Only add betas parameter if we have at least one beta feature enabled
            if betas:
                request_params["betas"] = betas
            
            return self.client.beta.messages.create(**request_params)
        except Exception as e:
            logging.error(f"ERROR in Claude API request: {str(e)}")
            raise 