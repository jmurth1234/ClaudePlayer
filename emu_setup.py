import time
from pyboy import PyBoy, WindowEvent
from PIL import Image
import numpy as np

# Initialize PyBoy with the path to your ROM
pyboy = PyBoy('gold.gbc', game_wrapper=True)

print(pyboy.cartridge_title())

pokemon = pyboy.game_wrapper()

file = open("gold.gbc.state", "rb")
pyboy.load_state(file)

# Start the game
while not pyboy.tick():
    # simple file to run the emu to setup a state
    pass

