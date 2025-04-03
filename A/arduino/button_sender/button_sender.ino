/*
 * Button Sender - Simple Arduino code to detect button presses
 * and send signal over serial
 */

// Button pin - change this to the pin your button is connected to
const int BUTTON_PIN = 2;  

// Button debounce time in milliseconds
const unsigned long DEBOUNCE_TIME = 50;  

// Cooldown period in milliseconds
const unsigned long COOLDOWN_PERIOD = 3000;  // 3 seconds between allowed presses

// Variables to track button state
int lastButtonState = HIGH;  // Assuming pull-up resistor (button connects to GND)
unsigned long lastDebounceTime = 0;
unsigned long lastPressTime = 0;

void setup() {
  // Initialize serial communication
  Serial.begin(9600);
  
  // Configure button pin as input with pull-up resistor
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  
  // Wait for serial connection
  delay(1000);
  
  Serial.println("Button Sender Ready");
}

void loop() {
  // Read the current button state
  int reading = digitalRead(BUTTON_PIN);
  
  // Check if the button state has changed
  if (reading != lastButtonState) {
    // Reset the debounce timer
    lastDebounceTime = millis();
  }
  
  // Check if enough time has passed since the last bounce
  if ((millis() - lastDebounceTime) > DEBOUNCE_TIME) {
    // If the button state has changed and is now LOW (pressed)
    if (reading == LOW && lastButtonState == HIGH) {
      // Check if enough time has passed since the last press
      unsigned long currentTime = millis();
      if (currentTime - lastPressTime > COOLDOWN_PERIOD) {
        // Send the button press signal
        Serial.println("BUTTON_PRESSED");
        lastPressTime = currentTime;
      }
    }
    
    // Update the last button state
    lastButtonState = reading;
  }
  
  // Small delay to prevent bouncing
  delay(10);
} 