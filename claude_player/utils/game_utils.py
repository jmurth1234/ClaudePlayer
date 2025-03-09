import time
import logging
import base64
from io import BytesIO
from pyboy import PyBoy
from pyboy import WindowEvent

# Define button rules documentation
button_rules = """Use the following notation for Game Boy buttons: A (A button), B (B button), U (UP), D (DOWN), L (LEFT), R (RIGHT), S (START), E (SELECT).
You can combine multiple button presses with their duration in this format: A5 (press A for 5 frames) U10 (hold UP for 10 frames).
Separate each input with spaces: "A2 B2 R5 L2 U2".
For quick taps, use inputs like: "A1 B1" or just "A B".
For discrete presses e.g. navigating menus, use inputs like: "R1 R1" to move right twice in a row.
For long holds, specify the number of frames: "U10" (hold UP for 10 frames).
Careful! Very long durations may result in missing other important events.
"""

def press_and_release_buttons(pyboy: PyBoy, input_string: str):
    """
    Parse a button input string and execute the button presses.
    
    Args:
        pyboy: The PyBoy instance
        input_string: String of button inputs in the format "A5 B2 R3 L1"
    """
    if not input_string.strip():
        logging.warning("Received empty input string")
        return
    
    try:
        # Parse input string
        inputs = input_string.strip().split()
        
        # Define button mappings
        button_map = {
            'A': WindowEvent.PRESS_BUTTON_A,
            'B': WindowEvent.PRESS_BUTTON_B,
            'U': WindowEvent.PRESS_ARROW_UP,
            'D': WindowEvent.PRESS_ARROW_DOWN,
            'L': WindowEvent.PRESS_ARROW_LEFT,
            'R': WindowEvent.PRESS_ARROW_RIGHT,
            'S': WindowEvent.PRESS_BUTTON_START,
            'E': WindowEvent.PRESS_BUTTON_SELECT
        }
        
        release_map = {
            'A': WindowEvent.RELEASE_BUTTON_A,
            'B': WindowEvent.RELEASE_BUTTON_B,
            'U': WindowEvent.RELEASE_ARROW_UP,
            'D': WindowEvent.RELEASE_ARROW_DOWN,
            'L': WindowEvent.RELEASE_ARROW_LEFT,
            'R': WindowEvent.RELEASE_ARROW_RIGHT,
            'S': WindowEvent.RELEASE_BUTTON_START,
            'E': WindowEvent.RELEASE_BUTTON_SELECT
        }
        
        for button_input in inputs:
            # Extract button and duration
            if len(button_input) == 1:
                # Single character means press for 1 frame
                button = button_input
                duration = 1
            else:
                # Otherwise parse the button and duration
                button = button_input[0]
                try:
                    duration = int(button_input[1:])
                except ValueError:
                    logging.warning(f"Invalid button input: {button_input}, using duration of 1")
                    duration = 1
            
            # Verify the button is valid
            if button not in button_map:
                logging.warning(f"Unknown button: {button}, skipping")
                continue
            
            # Press the button
            pyboy.send_input(button_map[button])
            
            # Hold for the specified duration
            for _ in range(duration):
                # Tick the emulator for each frame of hold time
                pyboy.tick()
            
            # Release the button
            pyboy.send_input(release_map[button])
            
    except Exception as e:
        logging.error(f"Error executing button inputs: {str(e)}")

def take_screenshot(pyboy: PyBoy, as_claude_content: bool = False) -> dict:
    """
    Take a screenshot of the current PyBoy screen.
    
    Args:
        pyboy: The PyBoy instance
        as_claude_content: Whether to format as Claude content block
        
    Returns:
        Screenshot as image data or Claude content block
    """
    try:
        # Updated for PyBoy 1.6.7 - the screen is now directly accessible via pyboy.botsupport_manager().screen()
        from pyboy.botsupport import BotSupportManager
        bot_support: BotSupportManager = pyboy.botsupport_manager()
        screen = bot_support.screen()
        
        # Get the screen image as a PIL image
        screen_image = screen.screen_image()
        
        # Convert to proper PNG with PIL and encode as base64
        buffer = BytesIO()
        screen_image.save(buffer, format="PNG")
        buffer.seek(0)
        
        # Convert to base64 string
        base64_string = base64.b64encode(buffer.getvalue()).decode('utf-8')
        
        # For Claude API format
        if as_claude_content:
            return {"type": "image", "source": {"type": "base64", "media_type": "image/png", "data": base64_string}}
        
        return screen_image
        
    except Exception as e:
        logging.error(f"Error taking screenshot: {str(e)}")
        # Return placeholder for Claude
        if as_claude_content:
            return {"type": "text", "text": "Error capturing screenshot"}
        return None 