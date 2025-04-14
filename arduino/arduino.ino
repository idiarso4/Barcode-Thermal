const int buttonPin = 2;    // Pin for the push button
const int relayPin = 3;     // Pin for the relay control
const int printerStatusPin = 4; // Pin for printer status LED

// Variables
bool buttonState = HIGH;    // Current state of the button (HIGH with pull-up)
bool lastButtonState = HIGH; // Previous state of the button
int counter = 1;            // Counter to track the sequential number
unsigned long lastDebounceTime = 0; // Last time the button state changed
unsigned long debounceDelay = 50;  // Debounce delay in milliseconds
unsigned long lastStatusCheck = 0; // Last time status was checked
unsigned long statusCheckInterval = 5000; // Check status every 5 seconds
unsigned long lastPrintTime = 0; // Last time a print was initiated
unsigned long printCooldown = 2000; // Minimum time between prints (2 seconds)

void setup() {
  // Initialize Serial communication at 9600 baud rate
  Serial.begin(9600);
  while (!Serial) {
    ; // Wait for serial port to connect
  }

  // Configure pin modes
  pinMode(buttonPin, INPUT_PULLUP); // Enable internal pull-up resistor
  pinMode(relayPin, OUTPUT);        // Relay as output
  pinMode(printerStatusPin, OUTPUT); // Printer status LED

  // Ensure the relay is initially off
  digitalWrite(relayPin, LOW);
  digitalWrite(printerStatusPin, HIGH); // LED on = ready

  // Send ready signal
  Serial.println("READY");
}

void loop() {
  // Read the current state of the button
  bool reading = digitalRead(buttonPin);

  // Check if the button state has changed
  if (reading != lastButtonState) {
    // Reset the debounce timer
    lastDebounceTime = millis();
  }

  // If the debounce time has passed, update the button state
  if ((millis() - lastDebounceTime) > debounceDelay) {
    // Only update the button state if it has changed
    if (reading != buttonState) {
      buttonState = reading;

      // If the button was pressed (falling edge)
      if (buttonState == LOW) {
        // Check if enough time has passed since last print
        if (millis() - lastPrintTime >= printCooldown) {
          lastPrintTime = millis();
          
          // Step 1: Turn on the relay
          digitalWrite(relayPin, HIGH);
          digitalWrite(printerStatusPin, LOW); // LED off = printing

          // Step 2: Send the current counter value to the computer
          Serial.println(counter); // Send the counter value followed by a newline

          // Step 3: Increment the counter and reset if it exceeds 1000
          counter++;
          if (counter > 1000) {
            counter = 1; // Reset the counter to 1
          }

          // Step 4: Turn off the relay after a short delay
          delay(500); // Keep the relay on for 500 ms
          digitalWrite(relayPin, LOW);
          digitalWrite(printerStatusPin, HIGH); // LED on = ready
        } else {
          // Send error if button pressed too quickly
          Serial.println("ERROR:TOO_SOON");
        }
      }
    }
  }

  // Update the last button state
  lastButtonState = reading;

  // Check printer status periodically
  if (millis() - lastStatusCheck > statusCheckInterval) {
    lastStatusCheck = millis();
    // Send status to computer
    Serial.print("STATUS:");
    Serial.print(digitalRead(printerStatusPin) ? "READY" : "PRINTING");
    Serial.print(":");
    Serial.println(digitalRead(relayPin) ? "GATE_OPEN" : "GATE_CLOSED");
  }
}