#include <Arduino.h>

/*
 * Arduino Gate Control System
 * ------------------------
 * Controls gate and printer using:
 * - Push button (Pin 2)
 * - Serial input from PC
 * - ATMega output signals (Pin 3,4)
 * - LED indicators (Pin 12,13)
 */

// Pin definitions
const int buttonPin = 2;     // Input pin untuk push button
const int atmegaPin1 = 3;   // Output pin 1 ke ATMega (untuk push button)
const int atmegaPin2 = 4;   // Output pin 2 ke ATMega (untuk keyboard)
const int ledPin1 = 12;     // LED indikator untuk push button
const int ledPin2 = 13;     // LED indikator untuk keyboard

// Variables
bool buttonState = HIGH;     // Current state of the button (HIGH with pull-up)
bool lastButtonState = HIGH; // Previous state of the button
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;    // Debounce delay in milliseconds
unsigned long signalDuration = 200;  // Durasi sinyal ke ATMega (ms)

void setup() {
  // Setup pin modes
  pinMode(buttonPin, INPUT_PULLUP);    // Push button dengan pull-up
  pinMode(atmegaPin1, OUTPUT);         // Output ke ATMega untuk push button
  pinMode(atmegaPin2, OUTPUT);         // Output ke ATMega untuk keyboard
  pinMode(ledPin1, OUTPUT);            // LED indikator push button
  pinMode(ledPin2, OUTPUT);            // LED indikator keyboard
  
  // Inisialisasi serial untuk printer
  Serial.begin(9600);
  
  // Inisialisasi output pins
  digitalWrite(atmegaPin1, LOW);
  digitalWrite(atmegaPin2, LOW);
  digitalWrite(ledPin1, LOW);
  digitalWrite(ledPin2, LOW);
  
  // Kedipkan LED untuk indikasi sistem siap
  for(int i=0; i<3; i++) {
    digitalWrite(ledPin1, HIGH);
    digitalWrite(ledPin2, HIGH);
    delay(100);
    digitalWrite(ledPin1, LOW);
    digitalWrite(ledPin2, LOW);
    delay(100);
  }
}

void triggerSystem(bool isButton) {
  // Kirim sinyal ke ATMega untuk gate
  if (isButton) {
    digitalWrite(atmegaPin1, HIGH);
    digitalWrite(ledPin1, HIGH);
  } else {
    digitalWrite(atmegaPin2, HIGH);
    digitalWrite(ledPin2, HIGH);
  }
  
  // Kirim perintah cetak ke printer
  Serial.println("PRINT");  // Trigger printer
  
  // Tunggu printer selesai
  delay(signalDuration);
  
  // Matikan sinyal
  if (isButton) {
    digitalWrite(atmegaPin1, LOW);
    digitalWrite(ledPin1, LOW);
  } else {
    digitalWrite(atmegaPin2, LOW);
    digitalWrite(ledPin2, LOW);
  }
  
  // Tunggu sebelum siap menerima input berikutnya
  delay(1000);  // Delay 1 detik untuk mencegah double trigger
}

void processKeyboard() {
  if (Serial.available() > 0) {
    char command = Serial.read();
    if (command == '1') {
      triggerSystem(false);  // false = from keyboard
    }
  }
}

void loop() {
  // Process keyboard commands
  processKeyboard();
  
  // Read push button
  bool reading = digitalRead(buttonPin);

  // Check if button state changed
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }

  // If debounce time passed
  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading != buttonState) {
      buttonState = reading;

      // If button pressed (LOW karena pull-up)
      if (buttonState == LOW) {
        triggerSystem(true);  // true = from button
      }
    }
  }

  // Update button state
  lastButtonState = reading;
}