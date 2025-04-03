# Arduino-Server Communication Bridge for Linux-Park

This project provides a communication bridge between Arduino hardware and the linux-park server system. It allows Arduino devices to send data to the server and receive commands back.

## Components

1. **C# Application**: Acts as a bridge between Arduino and the server
   - Communicates with Arduino via serial port
   - Sends data to the linux-park server via HTTP API
   - Inserts data directly into the PostgreSQL database
   - Relays commands from the server to Arduino

2. **Arduino Sketch**: Runs on Arduino hardware
   - Reads data from sensors or input devices (e.g., barcode scanner, RFID reader)
   - Sends data to the C# application via serial port
   - Receives and processes commands from the C# application
   - Controls hardware like gates, lights, etc.

## Prerequisites

### C# Application
- .NET 6.0 SDK or higher
- Required NuGet packages:
  - System.IO.Ports
  - Npgsql
  - Newtonsoft.Json

### Arduino
- Arduino IDE
- Arduino board (e.g., Arduino Uno, Mega, etc.)
- Required components:
  - Sensors or input devices (e.g., IR sensor, button, barcode scanner)
  - Output devices (e.g., gate control relay, LED indicators)

## Setup Instructions

### C# Application

1. Update configuration in `Program.cs`:
   - Set `SERIAL_PORT` to match your Arduino's COM port
   - Set `SERVER_URL` to your linux-park server URL
   - Update database connection details (`DB_HOST`, `DB_PORT`, etc.)

2. Build and run the application:
   ```
   dotnet build
   dotnet run
   ```

### Arduino

1. Open `Arduino_Code.ino` in the Arduino IDE
2. Modify pin definitions if needed to match your hardware setup
3. Upload the sketch to your Arduino board
4. Connect the Arduino to your computer via USB

## Hardware Setup

1. Connect a sensor to `TRIGGER_PIN` (default: pin 2)
   - This could be an IR sensor, button, or other input device
   - When triggered, it will generate a barcode/ID and send it to the server

2. Connect a gate control mechanism to `GATE_CONTROL_PIN` (default: pin 4)
   - This could be a relay that controls a gate or barrier

3. The built-in LED (`LED_PIN`, default: pin 13) is used for status indication

## How It Works

1. When the sensor is triggered, the Arduino generates a barcode/ID
2. The Arduino sends this data to the C# application via serial port
3. The C# application:
   - Inserts the data into the PostgreSQL database
   - Sends the data to the linux-park server via HTTP API
   - Sends an acknowledgment back to the Arduino
4. The linux-park server processes the data and may send commands back
5. The C# application forwards these commands to the Arduino
6. The Arduino executes the commands (e.g., opening/closing a gate)

## Commands

The following commands can be sent from the C# application to the Arduino:

- `ACK`: Acknowledgment that data was received
- `OPEN`: Open the gate/barrier
- `CLOSE`: Close the gate/barrier

## Customization

### Adding More Sensors

1. Define additional pin constants in the Arduino sketch
2. Initialize the pins in `setup()`
3. Add code to read from them in `loop()`
4. Format and send the data to the serial port

### Supporting Different Hardware

1. Modify the Arduino sketch to support your specific hardware
2. Update the C# application to handle different data formats

## Troubleshooting

1. **Serial Port Connection Issues**
   - Verify the correct COM port is set in the C# application
   - Ensure the Arduino is connected and recognized by your computer
   - Check the baud rate matches (default: 9600)

2. **Server Connection Issues**
   - Verify the server URL is correct
   - Ensure the server is running and accessible from your network
   - Check any firewall settings that might block the connection

3. **Database Connection Issues**
   - Verify the database connection details are correct
   - Ensure PostgreSQL is running and accessible
   - Check the database schema matches what the application expects

## License

This project is distributed under the MIT License. 