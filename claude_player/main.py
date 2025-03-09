"""
Claude Player - An AI-powered game playing agent using Claude and PyBoy
"""
import argparse
from claude_player.config.config_loader import load_config
from claude_player.agent.game_agent import GameAgent

def main():
    """Entry point for the Claude Player application."""
    # Parse command-line arguments
    parser = argparse.ArgumentParser(description="Claude Player - An AI-powered game playing agent using Claude and PyBoy")
    parser.add_argument("--config", type=str, default="config.json", help="Path to the configuration file")
    args = parser.parse_args()
    
    # Load configuration
    config = load_config(args.config)
    
    # Create and run the agent
    agent = GameAgent(config)
    agent.run()

if __name__ == "__main__":
    main() 