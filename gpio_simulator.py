"""GPIO simulator for testing on non-Raspberry Pi systems"""

# GPIO modes
BCM = "BCM"
BOARD = "BOARD"

# GPIO directions
IN = "IN"
OUT = "OUT"

# GPIO states
HIGH = 1
LOW = 0

# GPIO pull up/down
PUD_UP = "PUD_UP"
PUD_DOWN = "PUD_DOWN"

# GPIO edges
FALLING = "FALLING"
RISING = "RISING"
BOTH = "BOTH"

_gpio_callbacks = {}

def setmode(mode):
    """Set GPIO mode"""
    pass

def setup(channel, direction, pull_up_down=None, initial=None):
    """Setup GPIO channel"""
    pass

def cleanup():
    """Clean up GPIO"""
    _gpio_callbacks.clear()

def add_event_detect(channel, edge, callback=None, bouncetime=None):
    """Add event detection to a GPIO channel"""
    if callback:
        _gpio_callbacks[channel] = callback

def remove_event_detect(channel):
    """Remove event detection for a GPIO channel"""
    if channel in _gpio_callbacks:
        del _gpio_callbacks[channel]

def simulate_button_press(channel):
    """Simulate a button press for testing"""
    if channel in _gpio_callbacks:
        _gpio_callbacks[channel](channel) 