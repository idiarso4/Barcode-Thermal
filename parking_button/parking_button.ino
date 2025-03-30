// Pin Definitions
const int buttonPin = 2;    // Push button connected to digital pin 2
const int relayPin = 3;     // Relay connected to digital pin 3 (untuk palang/gate)
const int ledPin = 13;      // Built-in LED for status indication

// Variables
bool buttonState = HIGH;    // Current state of the button (HIGH with pull-up)
bool lastButtonState = HIGH; // Previous state of the button
bool systemEnabled = true;  // System state flag
unsigned long lastDebounceTime = 0;  // Last time the button state changed
unsigned long debounceDelay = 50;    // Debounce delay in milliseconds
unsigned long buttonPressCount = 0;   // Count button presses for debugging

void setup() {
  // Initialize Serial communication
  Serial.begin(9600);
  
  // Configure pin modes
  pinMode(buttonPin, INPUT_PULLUP);  // Enable internal pull-up resistor
  pinMode(relayPin, OUTPUT);         // Relay control
  pinMode(ledPin, OUTPUT);           // Status LED
  
  // Ensure outputs are initially off
  digitalWrite(relayPin, LOW);
  digitalWrite(ledPin, LOW);
  
  // Send startup message
  Serial.println("READY");
}

void loop() {
  if (!systemEnabled) {
    // If system is disabled, just blink LED and check for enable command
    blinkLED();
    checkSerialCommand();
    return;
  }
  
  // Read the current state of the button
  bool reading = digitalRead(buttonPin);
  
  // Check if the button state has changed
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }
  
  // If enough time has passed, check if the button state has really changed
  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading != buttonState) {
      buttonState = reading;
      
      // If button is pressed (LOW due to pull-up)
      if (buttonState == LOW) {
        handleButtonPress();
      }
    }
  }
  
  // Check for serial commands
  checkSerialCommand();
  
  // Update the last button state
  lastButtonState = reading;
}

void handleButtonPress() {
  // Increment press counter
  buttonPressCount++;
  
  // Visual feedback
  digitalWrite(ledPin, HIGH);
  
  // Activate relay (open gate)
  digitalWrite(relayPin, HIGH);
  
  // Send signal to computer
  Serial.println("PRESS");
  
  // Keep gate open for 1 second
  delay(1000);
  
  // Close gate and turn off LED
  digitalWrite(relayPin, LOW);
  digitalWrite(ledPin, LOW);
}

void checkSerialCommand() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();
    
    if (command == "DISABLE") {
      systemEnabled = false;
      digitalWrite(ledPin, HIGH);  // LED on indicates disabled state
      Serial.println("DISABLED");
    }
    else if (command == "ENABLE") {
      systemEnabled = true;
      digitalWrite(ledPin, LOW);   // LED off indicates enabled state
      Serial.println("ENABLED");
    }
    else if (command == "STATUS") {
      Serial.print("Status: ");
      Serial.println(systemEnabled ? "ENABLED" : "DISABLED");
      Serial.print("Button presses: ");
      Serial.println(buttonPressCount);
    }
  }
}

void blinkLED() {
  // Blink LED when system is disabled
  digitalWrite(ledPin, (millis() / 500) % 2);
} 