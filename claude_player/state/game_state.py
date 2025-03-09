import time
import logging
from typing import List, Dict, Any, Optional

class GameState:
    """Manages the state of the game being played."""
    
    def __init__(self):
        self.identified_game = None
        self.current_goal = None
        self.memory_items = []
        self.turn_count = 0
        self.summary = ""
        self.complete_message_history = []  # Store ALL messages without truncation
        self.runtime_thinking_enabled = True  # Store the runtime thinking state

        # New memory management attributes
        self.memory_categories = {
            'items': {'schema': {'name': str, 'location': str, 'obtained': bool}},
            'npcs': {'schema': {'name': str, 'location': str, 'dialog': list}},
            'locations': {'schema': {'name': str, 'visited': bool, 'connections': list}},
            'quests': {'schema': {'name': str, 'status': str, 'requirements': list}},
            'game_mechanics': {'schema': {'name': str, 'description': str}},
            'stats': {'schema': {'name': str, 'value': any}}
        }
        
        # Initialize structured memory storage
        self.structured_memory = {
            category: [] for category in self.memory_categories.keys()
        }
        
        # Memory metadata
        self.memory_metadata = {
            'last_consolidated': 0,
            'total_items': 0,
            'category_counts': {cat: 0 for cat in self.memory_categories.keys()}
        }

    def add_memory_item(self, item: str, category: str = None, metadata: dict = None) -> dict:
        """
        Add a new item to memory with enhanced metadata and validation.
        
        Args:
            item: The information to remember
            category: Optional category for organizing memory
            metadata: Additional metadata like priority, confidence, etc.
            
        Returns:
            Dictionary containing the added memory item and its metadata
        """
        timestamp = time.time()
        memory_id = self.memory_metadata['total_items'] + 1
        
        memory_item = {
            'id': memory_id,
            'item': item,
            'category': category,
            'created_at': timestamp,
            'updated_at': timestamp,
            'version': 1,
            'priority': metadata.get('priority', 0) if metadata else 0,
            'confidence': metadata.get('confidence', 1.0) if metadata else 1.0,
            'context': metadata.get('context', {}) if metadata else {},
            'related_ids': metadata.get('related_ids', []) if metadata else [],
            'source': metadata.get('source', 'direct') if metadata else 'direct'
        }
        
        # Validate against category schema if provided
        if category and category in self.memory_categories:
            schema = self.memory_categories[category]['schema']
            try:
                # Basic schema validation could be enhanced
                if not all(isinstance(memory_item.get(k), v) for k, v in schema.items()):
                    logging.warning(f"Memory item doesn't match schema for category {category}")
            except Exception as e:
                logging.error(f"Schema validation error: {str(e)}")
        
        # Store in both flat and structured storage
        self.memory_items.append(memory_item)
        if category:
            self.structured_memory[category].append(memory_item)
            self.memory_metadata['category_counts'][category] += 1
        
        self.memory_metadata['total_items'] += 1
        
        # Trigger memory consolidation if needed
        self._check_consolidation_needed()
        
        return memory_item

    def update_memory_item(self, item_id: int, new_data: dict) -> Optional[dict]:
        """
        Update an existing memory item with version tracking.
        
        Args:
            item_id: ID of the item to update
            new_data: New data to update the item with
            
        Returns:
            Updated memory item or None if not found
        """
        for item in self.memory_items:
            if item['id'] == item_id:
                # Create new version
                item['version'] += 1
                item['updated_at'] = time.time()
                
                # Update fields while preserving metadata
                for key, value in new_data.items():
                    if key not in ['id', 'created_at', 'version']:
                        item[key] = value
                
                # Update structured storage if categorized
                if item['category']:
                    self._update_structured_memory(item)
                
                return item
        return None

    def search_memory(self, query: str, category: str = None, metadata_filters: dict = None) -> List[dict]:
        """
        Search memory items with advanced filtering.
        
        Args:
            query: Search string
            category: Optional category to search within
            metadata_filters: Optional filters for metadata fields
            
        Returns:
            List of matching memory items
        """
        results = []
        search_space = (
            self.structured_memory[category] if category
            else self.memory_items
        )
        
        for item in search_space:
            # Basic text matching
            if query.lower() in item['item'].lower():
                # Apply metadata filters if provided
                if metadata_filters:
                    if all(item.get(k) == v for k, v in metadata_filters.items()):
                        results.append(item)
                else:
                    results.append(item)
        
        # Sort by relevance (priority * confidence * recency)
        results.sort(key=lambda x: (
            x['priority'] * x['confidence'] * (1 / (time.time() - x['updated_at']))
        ), reverse=True)
        
        return results

    def consolidate_memory(self) -> None:
        """Consolidate similar memory items and clean up outdated information."""
        # Group similar items
        similarity_groups = {}
        for item in self.memory_items:
            # Simple similarity check - could be enhanced with better algorithms
            key_terms = set(item['item'].lower().split())
            for group_key, group in similarity_groups.items():
                group_terms = set(group[0]['item'].lower().split())
                if len(key_terms & group_terms) / len(key_terms | group_terms) > 0.7:
                    group.append(item)
                    break
            else:
                similarity_groups[item['id']] = [item]
        
        # Merge similar items
        for group in similarity_groups.values():
            if len(group) > 1:
                # Keep the most recent, highest priority item
                primary = max(group, key=lambda x: (
                    x['updated_at'],
                    x['priority'],
                    x['confidence']
                ))
                
                # Update related_ids and merge context
                for item in group:
                    if item != primary:
                        primary['related_ids'].extend(item['related_ids'])
                        primary['context'].update(item['context'])
                        self.memory_items.remove(item)
                        if item['category']:
                            self.structured_memory[item['category']].remove(item)
                            self.memory_metadata['category_counts'][item['category']] -= 1
        
        self.memory_metadata['last_consolidated'] = time.time()

    def _check_consolidation_needed(self) -> None:
        """Check if memory consolidation is needed based on various metrics."""
        current_time = time.time()
        total_items = len(self.memory_items)
        
        # Consolidate if:
        # 1. More than 100 items and hasn't been consolidated in last hour
        # 2. More than 50 items in any category
        # 3. Last consolidation was more than 24 hours ago
        should_consolidate = (
            (total_items > 100 and current_time - self.memory_metadata['last_consolidated'] > 3600) or
            any(count > 50 for count in self.memory_metadata['category_counts'].values()) or
            (current_time - self.memory_metadata['last_consolidated'] > 86400)
        )
        
        if should_consolidate:
            self.consolidate_memory()

    def _update_structured_memory(self, item: dict) -> None:
        """Update an item in the structured memory storage."""
        category = item['category']
        if category in self.structured_memory:
            # Remove old version
            self.structured_memory[category] = [
                x for x in self.structured_memory[category]
                if x['id'] != item['id']
            ]
            # Add updated version
            self.structured_memory[category].append(item)

    def format_memory_for_prompt(self) -> str:
        """Format memory items for inclusion in the system prompt."""
        if not self.memory_items:
            return ""
            
        memory_section = "Memory:\n"
        
        # Group by category
        categorized = {}
        uncategorized = []
        
        for item in self.memory_items:
            if item['category']:
                if item['category'] not in categorized:
                    categorized[item['category']] = []
                categorized[item['category']].append(item)
            else:
                uncategorized.append(item)
        
        # Format categorized items
        for category, items in categorized.items():
            memory_section += f"\n[{category.upper()}]\n"
            for item in sorted(items, key=lambda x: (-x['priority'], -x['confidence'])):
                memory_section += f"[{item['id']}] {item['item']}"
                if item['priority'] > 0 or item['confidence'] < 1.0:
                    memory_section += f" (priority: {item['priority']}, confidence: {item['confidence']:.1f})"
                memory_section += "\n"
        
        # Format uncategorized items
        if uncategorized:
            memory_section += "\n[UNCATEGORIZED]\n"
            for item in sorted(uncategorized, key=lambda x: (-x['priority'], -x['confidence'])):
                memory_section += f"[{item['id']}] {item['item']}\n"
        
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

    def add_to_complete_history(self, message):
        """Add a message to the complete history archive."""
        self.complete_message_history.append(message) 