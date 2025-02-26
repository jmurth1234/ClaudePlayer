import base64
import json
import os
import time
from pyboy import WindowEvent

TICK_FRAMES = 20

# Start time
start_time = time.time()
last_screenshot_path = None

button_rules = f"""
<format>
Single Press: Press a button once, e.g., 'A' (press A once).
Hold: Press and hold a button for a specified number of ticks, e.g., 'A2' (press and hold A for 2 ticks).
Simultaneous Press: Press multiple buttons simultaneously once, e.g., 'AB' (press A and B simultaneously once).
Wait: Wait for a specified number of ticks without pressing any buttons, e.g., 'W' (wait for 1 tick) or 'W2' (wait for 2 ticks).
Wait then Press: Wait for a specified number of ticks, then press a button once, e.g., 'W R' (wait for 1 tick, then press 'R' once).
Repeated Actions: To repeat an action for multiple ticks, use a number after the button symbol, e.g., 'R2' (move right for 2 ticks). Do not use spaces or multiple button symbols to repeat actions, as only the first symbol will be executed.
</format>

<rules>
Use Gameboy button symbols as specified below.
Numbers after a button indicate the duration of the hold in ticks.
Actions are performed in the order they are written.
One tick is equal to {TICK_FRAMES} frames.
Always use a number before a button symbol to specify the duration of the action.
Spaces separate individual actions. Always use spaces between actions.
Never repeat a button symbol within the same action.
Waiting should not be used to stall the game, and should only be used to wait for e.g. animations to complete. Priority should be given to pressing buttons.
</rules>

<symbols>
U: Up
D: Down
L: Left
R: Right
A: A
B: B
S: Start
X: Select
W: Wait
</symbols>

<examples>
Incorrect: 'RR A UUU UB'
Correct: 'R2 A U3 UB'

Incorrect: 'LULA DRDA URUA'
Correct: 'L U L A D R D A U R U A'
</examples>
"""

controls_mapping = {
    'U': (WindowEvent.PRESS_ARROW_UP, WindowEvent.RELEASE_ARROW_UP),
    'D': (WindowEvent.PRESS_ARROW_DOWN, WindowEvent.RELEASE_ARROW_DOWN),
    'L': (WindowEvent.PRESS_ARROW_LEFT, WindowEvent.RELEASE_ARROW_LEFT),
    'R': (WindowEvent.PRESS_ARROW_RIGHT, WindowEvent.RELEASE_ARROW_RIGHT),
    'A': (WindowEvent.PRESS_BUTTON_A, WindowEvent.RELEASE_BUTTON_A),
    'B': (WindowEvent.PRESS_BUTTON_B, WindowEvent.RELEASE_BUTTON_B),
    'S': (WindowEvent.PRESS_BUTTON_START, WindowEvent.RELEASE_BUTTON_START),
    'X': (WindowEvent.PRESS_BUTTON_SELECT, WindowEvent.RELEASE_BUTTON_SELECT)
}

# Function to take a screenshot
def take_screenshot(pyboy, set_last_screenshot_path=False):
    global start_time
    pil_image = pyboy.screen_image()
    os.makedirs(f"./frames/{start_time}", exist_ok=True)
    path = f"./frames/{start_time}/screenshot-{time.time()}.png"

    # make image 2x larger to make it easier to read (nearest neighbor interpolation)
    pil_image = pil_image.resize((pil_image.width * 4, pil_image.height * 4), resample=0)

    pil_image.save(path)

    if set_last_screenshot_path:
        global last_screenshot_path
        last_screenshot_path = path
    
    with open(path, "rb") as image_file:
        encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

    return {
        "type": "image",
        "source": {
            "type": "base64",
            "media_type": "image/png",
            "data": encoded_string
        }
    }

def parse_sequence(sequence):
    actions = []
    tokens = sequence.split()
    
    for token in tokens:
        if token.startswith('W'):
            # Extract the number after W, if any
            if len(token) > 1:
                try:
                    duration = int(token[1:])
                except ValueError:
                    raise ValueError(f"Invalid wait duration: {token[1:]}")
            else:
                duration = 1
            actions.append(('W', duration))
        else:
            # Initialize variables
            buttons = ''
            duration_str = ''
            
            # First, find where the buttons end and the digits begin
            i = 0
            while i < len(token) and not token[i].isdigit():
                if token[i] in controls_mapping or token[i] == '+':
                    buttons += token[i]
                else:
                    raise ValueError(f"Invalid character: {token[i]}")
                i += 1
            
            # Extract duration
            if i < len(token):
                duration_str = token[i:]
                try:
                    duration = int(duration_str)
                except ValueError:
                    raise ValueError(f"Invalid duration: {duration_str}")
            else:
                duration = 1
            
            actions.append((buttons, duration))
    
    return actions

def press_and_release_buttons(pyboy, sequence, mapping=controls_mapping):
    actions = parse_sequence(sequence)
    
    print(f"Executing sequence: {sequence}")
    print(f"Actions: {actions}")
    
    for buttons, duration in actions:
        if buttons == 'W':
            print(f"Waiting for {duration} ticks")
            for _ in range(duration * TICK_FRAMES):
                pyboy.tick()
                take_screenshot(pyboy)
        else:
            # Press buttons
            for button in buttons:
                press_event = mapping.get(button, (None, None))[0]
                if press_event:
                    print(f"Pressing {button} for {duration} ticks")
                    pyboy.send_input(press_event)
            
            # Tick for duration
            for _ in range(duration * TICK_FRAMES):
                pyboy.tick()
                take_screenshot(pyboy)
            
            # Release buttons
            for button in buttons:
                release_event = mapping.get(button, (None, None))[1]
                if release_event:
                    print(f"Releasing {button}")
                    pyboy.send_input(release_event)

        
    for _ in range(TICK_FRAMES):
        pyboy.tick()
        take_screenshot(pyboy)

    return actions

def debug(chat_history, system_prompt):
    global last_screenshot_path

    # set last screenshot path on last user message
    last_message = chat_history[-2]
    last_message["screen"] = last_screenshot_path
    chat_history[-2] = last_message

    history = [{"role": "system", "content": system_prompt}] + chat_history
    json.dump(history, open("chat_history.json", "w"), indent=4)

    with open("chat_history.md", "w") as f:
        for item in history:
            if item["role"] == "user":
                f.write(f"User: \n\n![]({item['screen']})\n")
            elif item["role"] == "assistant":
                f.write(f"AI: {item['content']}\n")
            else:
                f.write(f"System: {item['content']}\n")
                    
            f.write("\n-----------------\n\n")
                
    print(f"AI: {chat_history[-1]['content']}")

if __name__ == "__main__":
    # Test the parser
    print(parse_sequence("W"))
    # Expected output: [('W', 1)]
    
    print(parse_sequence("W2"))
    # Expected output: [('W', 2)]
    
    print(parse_sequence("A"))
    # Expected output: [('A', 1)]
    
    print(parse_sequence("AB"))
    # Expected output: [('AB', 1)]
    
    print(parse_sequence("R5 R3 A2"))
    # Expected output: [('R', 5), ('R', 3), ('A', 2)]
    
    print(parse_sequence("R2 A U2 B"))
    # Expected output: [('R', 2), ('A', 1), ('U', 2), ('B', 1)]
    
    print(parse_sequence("R4 A B W L D2 A"))
    # Expected output: [('R', 4), ('A', 1), ('B', 1), ('W', 1), ('L', 1), ('D', 2), ('A', 1)]

