import logging
import json

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