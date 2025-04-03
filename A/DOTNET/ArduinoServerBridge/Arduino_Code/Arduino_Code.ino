/*
  Arduino Code for Linux-Park System
  This sketch communicates with a C# application that connects to the linux-park server
  It reads data from sensors, RFID/barcode reader, etc. and sends it to the host computer
*/

// Pin definitions
const int TRIGGER_PIN = 2;     // Pin for trigger sensor (e.g., IR sensor, button)
const int BUTTON_PIN = 3;      // Pin for manual entry button
const int LED_PIN = 13;        // Built-in LED for status indication
const int GATE_CONTROL_PIN = 4; // Pin to control the gate
const int RELAY_PIN = 5;       // Pin to control relay for gate

// Variables
String inputString = "";        // String to hold incoming data
bool stringComplete = false;    // Whether a complete string has been received
bool sensorTriggered = false;   // Whether the sensor has been triggered
bool buttonPressed = false;     // Whether the button has been pressed
unsigned long lastSendTime = 0; // Last time data was sent
unsigned long lastButtonTime = 0; // Last time button was pressed
const int debounceDelay = 2000; // Debounce time in milliseconds
const int buttonDebounceDelay = 1000; // Button debounce time in milliseconds
int buttonCounter = 0;          // Counter for button presses

// Mock barcode data (in a real system, this would come from a barcode scanner)
// For testing purposes, we'll simulate a barcode when the sensor is triggered
String mockBarcodes[] = {"PARK001", "PARK002", "PARK003", "PARK004", "PARK005"};
int mockBarcodeIndex = 0;

void setup() {
  // Initialize serial port
  Serial.begin(9600);
  
  // Initialize pins
  pinMode(TRIGGER_PIN, INPUT_PULLUP); // Use pull-up resistor for sensor
  pinMode(BUTTON_PIN, INPUT_PULLUP);  // Use pull-up resistor for button
  pinMode(LED_PIN, OUTPUT);
  pinMode(GATE_CONTROL_PIN, OUTPUT);
  pinMode(RELAY_PIN, OUTPUT);
  
  // Initial state
  digitalWrite(LED_PIN, LOW);
  digitalWrite(GATE_CONTROL_PIN, LOW); // Gate closed
  digitalWrite(RELAY_PIN, LOW);        // Relay off
  
  // Reserve memory for inputString
  inputString.reserve(64);
  
  // Indicate the Arduino is ready
  blinkLED(3); // Blink 3 times to indicate ready
  
  // Debug message
  Serial.println("Arduino ready. Waiting for sensor trigger or button press...");
}

void loop() {
  // Check if the button has been pressed
  int buttonState = digitalRead(BUTTON_PIN);
  
  // Button is pressed (LOW with pull-up resistor) and enough time has passed since last press
  if (buttonState == LOW && !buttonPressed && millis() - lastButtonTime > buttonDebounceDelay) {
    buttonPressed = true;
    lastButtonTime = millis();
    
    // Generate a barcode
    String barcode = generateBarcode();
    
    // Send barcode to the computer with a BUTTON prefix to indicate it's from a button press
    Serial.println("BUTTON:" + barcode);
    
    // Indicate button press
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    
    // Wait for button to be released
    while (digitalRead(BUTTON_PIN) == LOW) {
      delay(10);
    }
    
    // Add additional delay to prevent bouncing
    delay(500);
  }
  
  // Reset the button state when it's released and enough time has passed
  if (buttonState == HIGH && buttonPressed && (millis() - lastButtonTime > 1000)) {
    buttonPressed = false;
  }
  
  // Check if the sensor has been triggered - ONLY READ SENSOR, DON'T PRINT
  int sensorState = digitalRead(TRIGGER_PIN);
  
  // If sensor is activated (LOW with pull-up resistor) and enough time has passed
  if (sensorState == LOW && !sensorTriggered && millis() - lastSendTime > debounceDelay) {
    sensorTriggered = true;
    lastSendTime = millis();
    
    // Generate a barcode
    String barcode = generateBarcode();
    
    // Send barcode to the computer with a SENSOR prefix to indicate it's from a sensor
    Serial.println("SENSOR:" + barcode);
    
    // Indicate data sent
    digitalWrite(LED_PIN, HIGH);
    delay(100);
    digitalWrite(LED_PIN, LOW);
    
    // Wait for sensor to return to HIGH before allowing another trigger
    while (digitalRead(TRIGGER_PIN) == LOW) {
      delay(10);
    }
    
    // Add additional delay to prevent bouncing
    delay(500);
  }
  
  // Reset the trigger when the sensor is no longer activated AND enough time has passed
  if (sensorState == HIGH && sensorTriggered && (millis() - lastSendTime > 5000)) {
    sensorTriggered = false;
  }
  
  // Process any incoming serial data
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
  // OPEN_GATE command - Open the gate
  else if (command == "OPEN_GATE") {
    // Open the gate
    digitalWrite(GATE_CONTROL_PIN, HIGH);
    digitalWrite(RELAY_PIN, HIGH);
    delay(100);
    blinkLED(2); // Blink twice to confirm
  }
  // CLOSE_GATE command - Close the gate
  else if (command == "CLOSE_GATE") {
    // Close the gate
    digitalWrite(GATE_CONTROL_PIN, LOW);
    digitalWrite(RELAY_PIN, LOW);
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