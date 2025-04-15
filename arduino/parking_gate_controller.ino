const int GATE_PIN = 13;      // Pin untuk mengontrol gate/relay
const int BUTTON_PIN = 2;     // Pin untuk push button
const int LED_PIN = 12;       // Pin untuk LED indikator

// Variabel untuk debouncing
unsigned long lastDebounceTime = 0;
unsigned long debounceDelay = 50;    // Delay debounce dalam milliseconds
int buttonState;             // State button saat ini
int lastButtonState = HIGH;  // State button sebelumnya

void setup() {
  // Inisialisasi komunikasi serial
  Serial.begin(9600);
  
  // Setup pin modes
  pinMode(GATE_PIN, OUTPUT);
  pinMode(BUTTON_PIN, INPUT_PULLUP);  // Gunakan internal pull-up resistor
  pinMode(LED_PIN, OUTPUT);
  
  // Inisialisasi state awal
  digitalWrite(GATE_PIN, LOW);    // Gate tertutup saat mulai
  digitalWrite(LED_PIN, LOW);     // LED mati saat mulai
  
  // Tunggu stabilisasi
  delay(1000);
  
  // Kirim pesan ready
  Serial.println("READY");
}

void openGate() {
  digitalWrite(GATE_PIN, HIGH);  // Aktifkan relay/gate
  digitalWrite(LED_PIN, HIGH);   // Nyalakan LED
  delay(500);                    // Tunggu setengah detik
  Serial.println("GATE_OPENED"); // Kirim konfirmasi ke PC
}

void closeGate() {
  digitalWrite(GATE_PIN, LOW);   // Matikan relay/gate
  digitalWrite(LED_PIN, LOW);    // Matikan LED
  Serial.println("GATE_CLOSED"); // Kirim konfirmasi ke PC
}

void processSerialCommand() {
  if (Serial.available() > 0) {
    String command = Serial.readStringUntil('\n');
    command.trim();  // Hapus whitespace
    
    if (command == "TEST") {
      Serial.println("OK");
    }
    else if (command == "INIT") {
      closeGate();  // Pastikan gate tertutup saat inisialisasi
      Serial.println("INITIALIZED");
    }
    else if (command == "OPEN") {
      openGate();
      delay(5000);  // Tunggu 5 detik
      closeGate();  // Tutup gate otomatis
    }
    else if (command == "ACK") {
      Serial.println("ACK_RECEIVED");
    }
  }
}

void checkButton() {
  // Baca state button
  int reading = digitalRead(BUTTON_PIN);
  
  // Cek jika ada perubahan state
  if (reading != lastButtonState) {
    lastDebounceTime = millis();
  }
  
  // Cek jika sudah melewati waktu debounce
  if ((millis() - lastDebounceTime) > debounceDelay) {
    if (reading != buttonState) {
      buttonState = reading;
      
      // Jika button ditekan (LOW karena pull-up)
      if (buttonState == LOW) {
        Serial.println("BUTTON_PRESSED");
        openGate();
        delay(5000);  // Tunggu 5 detik
        closeGate();
      }
    }
  }
  
  lastButtonState = reading;
}

void loop() {
  processSerialCommand();  // Cek perintah dari PC
  checkButton();          // Cek push button
  delay(10);             // Delay kecil untuk stabilitas
} 