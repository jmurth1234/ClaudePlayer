import logging
from typing import List, Dict, Any
from pyboy import PyBoy
from claude_player.state.game_state import GameState

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