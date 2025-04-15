// Pin Definitions
const int relayPin = 2; // Pin for the relay control (Digital Pin 3)
const int ledPin = 13; //

void setup() {
  // Initialize Serial communication at 9600 baud rate
  Serial.begin(9600);

  // Configure pin modes
  pinMode(relayPin, OUTPUT);
  pinMode(ledPin, OUTPUT);

  // Ensure the relay is initially off
  digitalWrite(relayPin, LOW);
  digitalWrite(ledPin, HIGH);

  // Print a startup message
  Serial.println("Relay Control Ready. Send 'ON' to activate or 'OFF' to deactivate.");
}

void loop() {
  // Check if data is available on the serial port
  if (Serial.available() > 0) {
    // Read the incoming command
    String command = Serial.readStringUntil('\n');
    command.trim(); // Remove any extra whitespace or newline characters

    // Process the command
    if (command == "ON") {
      // Turn on the relay
      digitalWrite(relayPin, HIGH);
      digitalWrite(ledPin, HIGH);
      Serial.println("Relay ON");
    } else if (command == "OFF") {
      // Turn off the relay
      digitalWrite(relayPin, LOW);
      digitalWrite(ledPin, LOW);
      Serial.println("Relay OFF");
    } else {
      // Invalid command received
      Serial.println("Invalid command. Use 'ON' or 'OFF'.");
    }
  }
}
