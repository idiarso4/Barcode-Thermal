// Pin Definitions
const int buttonPin = 2;    // Push button connected to digital pin 2
const int relayPin = 3;     // Relay connected to digital pin 3 (untuk palang/gate)
const int ledPin = 13;      // Built-in LED for status indication

// Variables
bool buttonState = HIGH;     // Current state of the button (HIGH with pull-up)
bool lastButtonState = HIGH; // Previous state of the button
unsigned long lastDebounceTime = 0;  // Last time the button state changed
unsigned long debounceDelay = 50;    // Debounce delay in milliseconds

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
  
  // Blink LED twice to indicate ready
  for(int i=0; i<2; i++) {
    digitalWrite(ledPin, HIGH);
    delay(100);
    digitalWrite(ledPin, LOW);
    delay(100);
  }
  
  // Send startup message
  Serial.println("READY");
}

void loop() {
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
  
  // Update the last button state
  lastButtonState = reading;
}

void handleButtonPress() {
  // Visual feedback
  digitalWrite(ledPin, HIGH);
  
  // Activate relay (open gate)
  digitalWrite(relayPin, HIGH);
  
  // Send signal to computer
  Serial.println("1");
  
  // Keep gate open for 500ms
  delay(500);
  
  // Close gate and turn off LED
  digitalWrite(relayPin, LOW);
  digitalWrite(ledPin, LOW);
  
  // Additional delay to prevent multiple triggers
  delay(200);
} 