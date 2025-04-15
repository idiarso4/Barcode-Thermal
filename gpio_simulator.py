"""
GPIO Simulator for Windows environment
This module simulates basic GPIO functionality for testing on Windows
"""
import logging
import keyboard
from typing import Callable, Optional, Dict

logger = logging.getLogger(__name__)

# GPIO mode constants
BCM = "BCM"
BOARD = "BOARD"

# GPIO state constants
HIGH = 1
LOW = 0

# GPIO direction constants
OUT = "OUT"
IN = "IN"

# GPIO event constants
FALLING = "FALLING"
RISING = "RISING"
BOTH = "BOTH"

# GPIO pull up/down constants
PUD_UP = "PUD_UP"
PUD_DOWN = "PUD_DOWN"

# Store pin states and callbacks
_pin_states: Dict[int, int] = {}
_pin_callbacks: Dict[int, Callable] = {}
_current_mode = None

# Map GPIO pins to keyboard keys
PIN_TO_KEY = {
    17: '1',  # Button pin mapped to '1' key
    18: '2',  # Barrier pin mapped to '2' key
    27: '3',  # LED pin mapped to '3' key
    22: '4'   # Loop detector pin mapped to '4' key
}

def setmode(mode: str) -> None:
    """Set GPIO mode (BCM or BOARD)"""
    global _current_mode
    _current_mode = mode
    logger.info(f"GPIO mode set to {mode}")

def setup(pin: int, direction: str, pull_up_down: Optional[str] = None) -> None:
    """Setup GPIO pin"""
    _pin_states[pin] = HIGH if pull_up_down == PUD_UP else LOW
    logger.info(f"Pin {pin} setup as {direction} with pull_up_down={pull_up_down}")

def output(pin: int, state: int) -> None:
    """Set output pin state"""
    _pin_states[pin] = state
    logger.info(f"Pin {pin} set to {state}")
    # Visual feedback for state changes
    if state == HIGH:
        print(f"🔵 Pin {pin} ON")
    else:
        print(f"⚫ Pin {pin} OFF")

def input(pin: int) -> int:
    """Read input pin state"""
    return _pin_states.get(pin, LOW)

def add_event_detect(pin: int, edge: str, callback: Callable, bouncetime: int = None) -> None:
    """Add event detection to a pin"""
    _pin_callbacks[pin] = callback
    key = PIN_TO_KEY.get(pin)
    if key:
        keyboard.on_press_key(key, lambda _: _trigger_callback(pin))
        logger.info(f"Event detection added to pin {pin} (Press '{key}' to trigger)")
    else:
        logger.warning(f"No key mapping found for pin {pin}")

def _trigger_callback(pin: int) -> None:
    """Trigger pin callback"""
    if pin in _pin_callbacks:
        _pin_callbacks[pin](pin)

def cleanup() -> None:
    """Cleanup GPIO (reset all pins)"""
    global _pin_states, _pin_callbacks, _current_mode
    _pin_states = {}
    _pin_callbacks = {}
    _current_mode = None
    keyboard.unhook_all()
    logger.info("GPIO cleanup completed")

# Add loop detector simulation
keyboard.on_press_key('4', lambda _: _simulate_loop_detector_enter())
keyboard.on_press_key('5', lambda _: _simulate_loop_detector_exit())

def _simulate_loop_detector_enter():
    """Simulate vehicle entering loop detector"""
    if 22 in _pin_states:  # Loop detector pin
        _pin_states[22] = LOW
        logger.info("Loop detector: Vehicle entered")
        print("🚗 Loop detector: Vehicle entered")

def _simulate_loop_detector_exit():
    """Simulate vehicle exiting loop detector"""
    if 22 in _pin_states:  # Loop detector pin
        _pin_states[22] = HIGH
        logger.info("Loop detector: Vehicle exited")
        print("🚗 Loop detector: Vehicle exited") 