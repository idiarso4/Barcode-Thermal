/*
  Arduino Code for Linux-Park System
  This sketch communicates with a C# application that connects to the linux-park server
  It reads data from sensors, RFID/barcode reader, etc. and sends it to the host computer
*/

// Pin definitions
const int TRIGGER_PIN = 2;     // Pin for trigger sensor (e.g., IR sensor, button)
const int LED_PIN = 13;        // Built-in LED for status indication
const int GATE_CONTROL_PIN = 4; // Pin to control the gate

// Variables
String inputString = "";        // String to hold incoming data
bool stringComplete = false;    // Whether a complete string has been received
bool sensorTriggered = false;   // Whether the sensor has been triggered
unsigned long lastSendTime = 0; // Last time data was sent
const int debounceDelay = 2000; // Debounce time in milliseconds

// Mock barcode data (in a real system, this would come from a barcode scanner)
// For testing purposes, we'll simulate a barcode when the sensor is triggered
String mockBarcodes[] = {"PARK001", "PARK002", "PARK003", "PARK004", "PARK005"};
int mockBarcodeIndex = 0;

void setup() {
  // Initialize serial port
  Serial.begin(9600);
  
  // Initialize pins
  pinMode(TRIGGER_PIN, INPUT_PULLUP); // Use pull-up resistor for sensor
  pinMode(LED_PIN, OUTPUT);
  pinMode(GATE_CONTROL_PIN, OUTPUT);
  
  // Initial state
  digitalWrite(LED_PIN, LOW);
  digitalWrite(GATE_CONTROL_PIN, LOW); // Gate closed
  
  // Reserve memory for inputString
  inputString.reserve(64);
  
  // Indicate the Arduino is ready
  blinkLED(3); // Blink 3 times to indicate ready
}

void loop() {
  // Check if the sensor has been triggered
  int sensorState = digitalRead(TRIGGER_PIN);
  
  // If sensor is activated (LOW with pull-up resistor) and enough time has passed
  if (sensorState == LOW && !sensorTriggered && millis() - lastSendTime > debounceDelay) {
    sensorTriggered = true;
    lastSendTime = millis();
    
    // Generate a barcode (in a real system this would come from a barcode reader)
    String barcode = generateBarcode();
    
    // Send barcode to the computer
    Serial.println(barcode);
    
    // Indicate data sent
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
  }
  
  // Reset the trigger when the sensor is no longer activated
  if (sensorState == HIGH && sensorTriggered) {
    sensorTriggered = false;
  }
  
  // Process any commands received from computer
  processSerialInput();
}

// Process incoming serial data
void processSerialInput() {
  while (Serial.available() > 0) {
    char inChar = (char)Serial.read();
    
    // Add character to input string
    if (inChar != '\n' && inChar != '\r') {
      inputString += inChar;
    }
    
    // If end of line, set flag
    if (inChar == '\n') {
      stringComplete = true;
    }
  }
  
  // Process the command when a complete string is received
  if (stringComplete) {
    // Process the command
    processCommand(inputString);
    
    // Clear the string for the next command
    inputString = "";
    stringComplete = false;
  }
}

// Process command from computer
void processCommand(String command) {
  command.trim(); // Remove any whitespace
  
  // ACK command - Acknowledgment received
  if (command == "ACK") {
    // Data was acknowledged, blink once
    blinkLED(1);
  }
  // OPEN command - Open the gate
  else if (command == "OPEN") {
    // Open the gate
    digitalWrite(GATE_CONTROL_PIN, HIGH);
    delay(100);
    blinkLED(2); // Blink twice to confirm
  }
  // CLOSE command - Close the gate
  else if (command == "CLOSE") {
    // Close the gate
    digitalWrite(GATE_CONTROL_PIN, LOW);
    delay(100);
    blinkLED(1); // Blink once to confirm
  }
  // Unknown command
  else {
    // Unrecognized command - blink 5 times quickly
    for (int i = 0; i < 5; i++) {
      digitalWrite(LED_PIN, HIGH);
      delay(50);
      digitalWrite(LED_PIN, LOW);
      delay(50);
    }
  }
}

// Generate a mock barcode (in a real system, this would read from a barcode scanner)
String generateBarcode() {
  // For testing: rotate through the mock barcodes
  String barcode = mockBarcodes[mockBarcodeIndex];
  
  // Increment index for next time
  mockBarcodeIndex = (mockBarcodeIndex + 1) % 5;
  
  return barcode;
}

// Blink the LED a specified number of times
void blinkLED(int times) {
  for (int i = 0; i < times; i++) {
    digitalWrite(LED_PIN, HIGH);
    delay(200);
    digitalWrite(LED_PIN, LOW);
    delay(200);
  }
} 