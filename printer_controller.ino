#include <SoftwareSerial.h>
#include <Adafruit_Thermal.h>

// Pin definitions
#define PRINTER_RX 2
#define PRINTER_TX 3
#define GATE_PIN 4
#define BUTTON_PIN 5
#define STATUS_LED 6

// Constants
#define BAUD_RATE 115200
#define GATE_OPEN_TIME 5000  // 5 seconds
#define DEBOUNCE_DELAY 50    // 50ms
#define MAX_RETRIES 3
#define RETRY_DELAY 1000     // 1 second

// Global variables
SoftwareSerial printerSerial(PRINTER_RX, PRINTER_TX);
Adafruit_Thermal printer(&printerSerial);
bool isPrinting = false;
unsigned long lastButtonPress = 0;
unsigned long lastGateOpen = 0;
int retryCount = 0;

void setup() {
  // Initialize serial communication
  Serial.begin(BAUD_RATE);
  printerSerial.begin(BAUD_RATE);
  
  // Initialize pins
  pinMode(GATE_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);
  pinMode(STATUS_LED, OUTPUT);
  
  // Initialize printer
  printer.begin();
  printer.setDefault();
  
  // Initial status
  digitalWrite(STATUS_LED, HIGH);  // LED on = ready
  Serial.println("READY");
}

void loop() {
  // Check for incoming data
  if (Serial.available()) {
    String command = Serial.readStringUntil('\n');
    processCommand(command);
  }
  
  // Check button press
  if (digitalRead(BUTTON_PIN) == LOW) {
    if (millis() - lastButtonPress > DEBOUNCE_DELAY) {
      lastButtonPress = millis();
      sendButtonPress();
    }
  }
  
  // Check gate status
  if (digitalRead(GATE_PIN) == HIGH && millis() - lastGateOpen > GATE_OPEN_TIME) {
    digitalWrite(GATE_PIN, LOW);
  }
}

void processCommand(String command) {
  if (command.startsWith("TICKET:")) {
    processTicket(command);
  } else if (command == "STATUS") {
    sendStatus();
  } else if (command == "TEST") {
    sendTestResponse();
  }
}

void processTicket(String command) {
  // Parse ticket data
  String ticketNumber = getValue(command, ':', 1);
  String timestamp = getValue(command, ':', 2);
  String plateNumber = getValue(command, ':', 3);
  String vehicleType = getValue(command, ':', 4);
  
  // Print ticket
  if (printTicket(ticketNumber, timestamp, plateNumber, vehicleType)) {
    // Open gate
    openGate();
    Serial.println("OK");
  } else {
    Serial.println("ERROR");
  }
}

bool printTicket(String ticketNumber, String timestamp, String plateNumber, String vehicleType) {
  if (isPrinting) {
    return false;
  }
  
  isPrinting = true;
  digitalWrite(STATUS_LED, LOW);  // LED off = printing
  
  try {
    // Print header
    printer.justify('C');
    printer.setSize('L');
    printer.println("PARKIR RSI BNA");
    printer.setSize('S');
    printer.println("====================");
    
    // Print ticket details
    printer.justify('L');
    printer.println("Tiket: " + ticketNumber);
    printer.println("Waktu: " + timestamp);
    printer.println("Plat: " + plateNumber);
    printer.println("Tipe: " + vehicleType);
    
    // Print barcode
    printer.justify('C');
    printer.printBarcode(ticketNumber.c_str(), CODE39);
    
    // Print footer
    printer.println("\n");
    printer.justify('C');
    printer.println("Terima kasih");
    printer.println("Jangan hilangkan tiket ini");
    
    // Feed and cut
    printer.feed(2);
    printer.cut();
    
    isPrinting = false;
    digitalWrite(STATUS_LED, HIGH);  // LED on = ready
    return true;
    
  } catch (...) {
    isPrinting = false;
    digitalWrite(STATUS_LED, HIGH);
    return false;
  }
}

void openGate() {
  digitalWrite(GATE_PIN, HIGH);
  lastGateOpen = millis();
}

void sendButtonPress() {
  Serial.println("BUTTON_PRESSED");
}

void sendStatus() {
  String status = "STATUS:";
  status += isPrinting ? "PRINTING" : "READY";
  status += ":";
  status += digitalRead(GATE_PIN) ? "GATE_OPEN" : "GATE_CLOSED";
  Serial.println(status);
}

void sendTestResponse() {
  Serial.println("OK");
}

String getValue(String data, char separator, int index) {
  int found = 0;
  int strIndex[] = {0, -1};
  int maxIndex = data.length() - 1;

  for (int i = 0; i <= maxIndex && found <= index; i++) {
    if (data.charAt(i) == separator || i == maxIndex) {
      found++;
      strIndex[0] = strIndex[1] + 1;
      strIndex[1] = (i == maxIndex) ? i + 1 : i;
    }
  }
  return found > index ? data.substring(strIndex[0], strIndex[1]) : "";
} 