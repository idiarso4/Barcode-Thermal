const int buttonPin = 2;    // Pin for the push button
const int relayPin = 3;     // Pin for the relay control

// Variables
bool buttonState = HIGH;    // Current state of the button (HIGH with pull-up)
bool lastButtonState = HIGH; // Previous state of the button
int counter = 1;            // Counter to track the sequential number
unsigned long lastDebounceTime = 0; // Last time the button state changed
unsigned long debounceDelay = 50;  // Debounce delay in milliseconds

void setup() {
  // Initialize Serial communication at 9600 baud rate
  Serial.begin(9600);

  // Configure pin modes
  pinMode(buttonPin, INPUT_PULLUP); // Enable internal pull-up resistor
  pinMode(relayPin, OUTPUT);        // Relay as output

  // Ensure the relay is initially off
  digitalWrite(relayPin, LOW);
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
        // Step 1: Turn on the relay
        digitalWrite(relayPin, HIGH);

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
      }
    }
  }

  // Update the last button state
  lastButtonState = reading;
}