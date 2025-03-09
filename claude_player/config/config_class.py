import json
import os.path
import logging
from typing import Dict, Any, Optional, TypedDict

# Define typed configuration structures
class ModelConfig(TypedDict, total=False):
    MODEL: str
    THINKING: bool
    DYNAMIC_THINKING: bool
    EFFICIENT_TOOLS: bool
    MAX_TOKENS: int
    THINKING_BUDGET: int

class SummaryConfig(ModelConfig):
    INITIAL_SUMMARY: bool
    SUMMARY_INTERVAL: int

class ActionConfig(ModelConfig):
    pass

class ConfigClass:
    """Configuration settings for the game agent."""
    ROM_PATH: str
    STATE_PATH: Optional[str]
    LOG_FILE: str
    EMULATION_SPEED: int
    EMULATION_MODE: str  # Can be "turn_based" or "continuous"
    CONTINUOUS_ANALYSIS_INTERVAL: float  # How often to analyze the screen in continuous mode (in seconds)
    ENABLE_WRAPPER: bool
    ENABLE_SOUND: bool  # Whether to enable sound in continuous mode
    MAX_HISTORY_MESSAGES: int
    CUSTOM_INSTRUCTIONS: Optional[str]  # Custom instructions to inject into the system prompt
    MODEL_DEFAULTS: ModelConfig
    ACTION: ActionConfig
    SUMMARY: SummaryConfig
    
    @staticmethod
    def get_mode_config(mode_name: str, overrides: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Get a mode configuration with optional overrides.
        
        Args:
            mode_name: The name of the mode (e.g., "ACTION", "SUMMARY")
            overrides: Optional dictionary of settings to override
            
        Returns:
            A dictionary with the complete configuration for the mode
        """
        from claude_player.config.config_loader import Config
        config = getattr(Config, mode_name).copy()
        if overrides:
            config.update(overrides)
        return config 