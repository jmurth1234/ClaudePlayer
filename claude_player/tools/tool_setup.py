import logging
from typing import Dict, Any, List
from pyboy import PyBoy
from claude_player.state.game_state import GameState
from claude_player.tools.tool_registry import ToolRegistry
from claude_player.utils.game_utils import press_and_release_buttons, take_screenshot

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
        description="Add a new item to memory with optional category and metadata. Categories help organize information about game state, items, NPCs, locations, etc. Available categories: items, npcs, locations, quests, game_mechanics, stats.",
        input_schema={
            "type": "object",
            "properties": {
                "item": {
                    "type": "string",
                    "description": "Information to remember"
                },
                "category": {
                    "type": "string",
                    "description": "Category for organizing memory (e.g., 'items', 'npcs', 'locations', 'quests', 'game_mechanics', 'stats')"
                },
                "priority": {
                    "type": "integer",
                    "description": "Priority level (0-10, higher is more important)",
                    "minimum": 0,
                    "maximum": 10
                },
                "confidence": {
                    "type": "number",
                    "description": "Confidence in the information (0.0-1.0)",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "context": {
                    "type": "object",
                    "description": "Additional context about when/where this information was obtained"
                }
            },
            "required": ["item"]
        }
    )
    def handle_add_to_memory(self, tool_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Extract metadata fields
        metadata = {
            'priority': tool_input.get('priority', 0),
            'confidence': tool_input.get('confidence', 1.0),
            'context': tool_input.get('context', {}),
        }
        
        # Add the memory item
        memory_item = self.game_state.add_memory_item(
            item=tool_input["item"],
            category=tool_input.get("category"),
            metadata=metadata
        )
        
        # Format response message
        response = f"Added to memory"
        if memory_item['category']:
            response += f" [{memory_item['category']}]"
        response += f" (id: {memory_item['id']})"
        if memory_item['priority'] > 0:
            response += f", priority: {memory_item['priority']}"
        if memory_item['confidence'] < 1.0:
            response += f", confidence: {memory_item['confidence']:.1f}"
        
        return [{"type": "text", "text": response}]
    
    # Register remove_from_memory tool
    @registry.register(
        name="remove_from_memory",
        description="Remove an item from memory by its ID. Use this when information is no longer relevant or is incorrect.",
        input_schema={
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "integer",
                    "description": "ID of the memory item to remove"
                }
            },
            "required": ["memory_id"]
        }
    )
    def handle_remove_from_memory(self, tool_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        memory_id = tool_input["memory_id"]
        
        # Find the item to remove
        item_to_remove = None
        for item in self.game_state.memory_items:
            if item['id'] == memory_id:
                item_to_remove = item
                break
        
        if item_to_remove:
            # Remove from both flat and structured storage
            self.game_state.memory_items.remove(item_to_remove)
            if item_to_remove['category']:
                self.game_state.structured_memory[item_to_remove['category']].remove(item_to_remove)
                self.game_state.memory_metadata['category_counts'][item_to_remove['category']] -= 1
            
            response = f"Removed memory item {memory_id}"
            if item_to_remove['category']:
                response += f" from category [{item_to_remove['category']}]"
            return [{"type": "text", "text": response}]
        else:
            return [{"type": "text", "text": f"Error: Memory item {memory_id} not found"}]
    
    # Register update_memory_item tool
    @registry.register(
        name="update_memory_item",
        description="Update an existing memory item by its ID. Can update the content, category, and metadata.",
        input_schema={
            "type": "object",
            "properties": {
                "memory_id": {
                    "type": "integer",
                    "description": "ID of the memory item to update"
                },
                "new_item": {
                    "type": "string",
                    "description": "Updated information"
                },
                "category": {
                    "type": "string",
                    "description": "New category (optional)"
                },
                "priority": {
                    "type": "integer",
                    "description": "New priority level (0-10)",
                    "minimum": 0,
                    "maximum": 10
                },
                "confidence": {
                    "type": "number",
                    "description": "New confidence value (0.0-1.0)",
                    "minimum": 0.0,
                    "maximum": 1.0
                },
                "context": {
                    "type": "object",
                    "description": "Additional context to merge with existing context"
                }
            },
            "required": ["memory_id", "new_item"]
        }
    )
    def handle_update_memory_item(self, tool_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        memory_id = tool_input["memory_id"]
        
        # Prepare update data
        update_data = {
            'item': tool_input['new_item']
        }
        
        # Add optional fields if provided
        for field in ['category', 'priority', 'confidence']:
            if field in tool_input:
                update_data[field] = tool_input[field]
        
        # Handle context separately (merge instead of replace)
        if 'context' in tool_input:
            update_data['context'] = tool_input['context']
        
        # Update the item
        updated_item = self.game_state.update_memory_item(memory_id, update_data)
        
        if updated_item:
            response = f"Updated memory item {memory_id}"
            if updated_item['category']:
                response += f" [{updated_item['category']}]"
            response += f" (version: {updated_item['version']})"
            return [{"type": "text", "text": response}]
        else:
            return [{"type": "text", "text": f"Error: Memory item {memory_id} not found"}]
    
    # Register search_memory tool
    @registry.register(
        name="search_memory",
        description="Search memory items by text and optional filters.",
        input_schema={
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Text to search for in memory items"
                },
                "category": {
                    "type": "string",
                    "description": "Optional category to search within"
                },
                "min_priority": {
                    "type": "integer",
                    "description": "Minimum priority level",
                    "minimum": 0,
                    "maximum": 10
                },
                "min_confidence": {
                    "type": "number",
                    "description": "Minimum confidence level",
                    "minimum": 0.0,
                    "maximum": 1.0
                }
            },
            "required": ["query"]
        }
    )
    def handle_search_memory(self, tool_input: Dict[str, Any]) -> List[Dict[str, Any]]:
        # Prepare metadata filters
        metadata_filters = {}
        if 'min_priority' in tool_input:
            metadata_filters['priority'] = lambda x: x >= tool_input['min_priority']
        if 'min_confidence' in tool_input:
            metadata_filters['confidence'] = lambda x: x >= tool_input['min_confidence']
        
        # Search memory
        results = self.game_state.search_memory(
            query=tool_input['query'],
            category=tool_input.get('category'),
            metadata_filters=metadata_filters
        )
        
        if results:
            response = "Found matching memory items:\n"
            for item in results:
                response += f"[{item['id']}] "
                if item['category']:
                    response += f"[{item['category']}] "
                response += item['item']
                if item['priority'] > 0 or item['confidence'] < 1.0:
                    response += f" (priority: {item['priority']}, confidence: {item['confidence']:.1f})"
                response += "\n"
        else:
            response = "No matching memory items found"
        
        return [{"type": "text", "text": response}]
    
    return registry 