import json
import os.path
import logging
from typing import Dict, Any, Optional
from claude_player.config.config_class import ConfigClass

# Create type for Config - will be initialized in main()
Config: Optional[ConfigClass] = None

def load_config(config_file='config.json') -> ConfigClass:
    """
    Load configuration from a JSON file with fallback to default values.
    If the configuration file doesn't exist, it will be created with default values.
    
    Args:
        config_file: Path to the configuration file (default: 'config.json')
        
    Returns:
        Configuration object with loaded values or defaults
    """
    # Default configuration values
    default_config = {
        "ROM_PATH": 'red.gb',
        "STATE_PATH": None,
        "LOG_FILE": 'game_agent.log',
        "EMULATION_SPEED": 1,
        "EMULATION_MODE": "turn_based",  # Options: "turn_based" or "continuous"
        "CONTINUOUS_ANALYSIS_INTERVAL": 1.0,  # How often to analyze the screen in continuous mode (in seconds)
        "ENABLE_WRAPPER": False,
        "ENABLE_SOUND": False,  # Whether to enable sound in continuous mode
        "MAX_HISTORY_MESSAGES": 30,
        "CUSTOM_INSTRUCTIONS": "",  # Custom instructions to inject into the system prompt

        # Common model settings - defaults that can be overridden
        "MODEL_DEFAULTS": {
            "MODEL": "claude-3-7-sonnet-20250219",
            "THINKING": True,
            "EFFICIENT_TOOLS": True,
            "MAX_TOKENS": 20000,
            "THINKING_BUDGET": 16000,
        },

        # Mode-specific settings (will inherit from MODEL_DEFAULTS if not specified)
        "ACTION": {
            # Any settings that differ from MODEL_DEFAULTS can be specified here
        },

        "SUMMARY": {
            # Any settings that differ from MODEL_DEFAULTS can be specified here
            "INITIAL_SUMMARY": True,
            "SUMMARY_INTERVAL": 30
        }
    }
    
    # Create configuration object
    config = ConfigClass()
    
    # Load configuration from file if it exists
    if os.path.exists(config_file):
        try:
            with open(config_file, 'r') as f:
                file_config = json.load(f)
            
            # Log that we're loading from file
            print(f"Loading configuration from {config_file}")
            
            # Update default configuration with values from file
            default_config.update(file_config)
        except Exception as e:
            print(f"Error loading configuration file: {str(e)}")
            print("Using default configuration values")
    else:
        print(f"Configuration file '{config_file}' not found, creating with default values")
        try:
            # Write default configuration to file
            with open(config_file, 'w') as f:
                json.dump(default_config, f, indent=2)
            print(f"Created default configuration file: {config_file}")
        except Exception as e:
            print(f"Error creating configuration file: {str(e)}")
    
    # Set configuration attributes
    for key, value in default_config.items():
        setattr(config, key, value)
    
    # Apply defaults to modes that inherit from MODEL_DEFAULTS
    for mode in ["ACTION", "SUMMARY"]:
        mode_config = default_config[mode].copy() if mode in default_config else {}
        # Merge with defaults (mode settings override defaults)
        for k, v in default_config["MODEL_DEFAULTS"].items():
            if k not in mode_config:
                mode_config[k] = v
        setattr(config, mode, mode_config)
    
    return config

def setup_logging(config: ConfigClass):
    """Configure logging for the application."""
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s [%(levelname)s] %(message)s',
        handlers=[
            logging.FileHandler(config.LOG_FILE),
            logging.StreamHandler()
        ]
    ) 