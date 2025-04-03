using System;
using System.IO.Ports;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Npgsql;

namespace ArduinoServerBridge
{
    class Program
    {
        // Serial port settings
        private const string SERIAL_PORT = "COM7"; // Update this to match your Arduino's port
        private const int BAUD_RATE = 9600;

        // Server settings - update with your linux-park server details
        private const string SERVER_URL = "http://192.168.2.6:5000"; // Update with your server URL
        private static readonly HttpClient httpClient = new HttpClient();

        // Database connection details - from your app2.py
        private const string DB_HOST = "192.168.2.6";
        private const string DB_PORT = "5432";
        private const string DB_NAME = "Parkir2";
        private const string DB_USER = "postgres";
        private const string DB_PASSWORD = "Postgres";

        private static SerialPort? serialPort;
        private static bool isRunning = true;

        static async Task Main(string[] args)
        {
            Console.WriteLine("Arduino Server Bridge - Starting");
            
            // Set up the serial port
            SetupSerialPort();
            
            // Set up a cancellation token to properly handle shutdown
            using (var cts = new CancellationTokenSource())
            {
                Console.CancelKeyPress += (sender, e) => {
                    e.Cancel = true;
                    cts.Cancel();
                    isRunning = false;
                    Console.WriteLine("Shutting down...");
                };

                try
                {
                    // Main processing loop
                    await ProcessArduinoData(cts.Token);
                }
                catch (OperationCanceledException)
                {
                    Console.WriteLine("Operation was canceled.");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"An error occurred: {ex.Message}");
                }
                finally
                {
                    // Clean up resources
                    CloseSerialPort();
                }
            }
            
            Console.WriteLine("Program ended. Press any key to exit.");
            Console.ReadKey();
        }

        private static void SetupSerialPort()
        {
            try
            {
                // Initialize the serial port
                serialPort = new SerialPort(SERIAL_PORT, BAUD_RATE)
                {
                    DataBits = 8,
                    Parity = Parity.None,
                    StopBits = StopBits.One,
                    Handshake = Handshake.None,
                    ReadTimeout = 500,
                    WriteTimeout = 500
                };
                
                // Open the serial port
                serialPort.Open();
                Console.WriteLine($"Connected to Arduino on {SERIAL_PORT} at {BAUD_RATE} baud");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error setting up serial port: {ex.Message}");
                throw;
            }
        }
        
        private static void CloseSerialPort()
        {
            if (serialPort != null && serialPort.IsOpen)
            {
                serialPort.Close();
                serialPort.Dispose();
                Console.WriteLine("Serial port closed");
            }
        }
        
        private static async Task ProcessArduinoData(CancellationToken cancellationToken)
        {
            Console.WriteLine("Waiting for data from Arduino...");
            
            while (isRunning && !cancellationToken.IsCancellationRequested)
            {
                try
                {
                    // Check if there's data to read from Arduino
                    if (serialPort != null && serialPort.IsOpen && serialPort.BytesToRead > 0)
                    {
                        // Read the data from Arduino
                        string receivedData = serialPort.ReadLine().Trim();
                        Console.WriteLine($"Received data from Arduino: {receivedData}");
                        
                        // Process the data
                        await ProcessReceivedData(receivedData);
                    }
                    
                    // Small delay to prevent high CPU usage
                    await Task.Delay(100, cancellationToken);
                }
                catch (TimeoutException)
                {
                    // This is normal when no data is available to read
                }
                catch (OperationCanceledException)
                {
                    throw;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error processing Arduino data: {ex.Message}");
                    
                    // Try to reconnect if connection was lost
                    try
                    {
                        if (serialPort != null && !serialPort.IsOpen)
                        {
                            Console.WriteLine("Attempting to reconnect to Arduino...");
                            serialPort.Open();
                        }
                    }
                    catch (Exception reconnectEx)
                    {
                        Console.WriteLine($"Failed to reconnect to Arduino: {reconnectEx.Message}");
                        await Task.Delay(5000, cancellationToken); // Wait before trying again
                    }
                }
            }
        }
        
        private static async Task ProcessReceivedData(string data)
        {
            // First, insert the data into the database
            await InsertIntoDatabase(data);
            
            // Then, send the data to the server
            await SendDataToServer(data);
            
            // Send response back to Arduino if needed
            if (serialPort != null && serialPort.IsOpen)
            {
                serialPort.WriteLine("ACK"); // Send acknowledgment
            }
        }
        
        private static async Task InsertIntoDatabase(string barcodeData)
        {
            using (var connection = new NpgsqlConnection(
                $"Host={DB_HOST};Port={DB_PORT};Database={DB_NAME};Username={DB_USER};Password={DB_PASSWORD}"))
            {
                try
                {
                    await connection.OpenAsync();
                    Console.WriteLine("Database connection opened");
                    
                    // Create and execute the command
                    using (var cmd = new NpgsqlCommand())
                    {
                        cmd.Connection = connection;
                        cmd.CommandText = "INSERT INTO Vehicles (Id) VALUES (@barcodeData)";
                        cmd.Parameters.AddWithValue("barcodeData", barcodeData);
                        
                        await cmd.ExecuteNonQueryAsync();
                        Console.WriteLine($"Inserted '{barcodeData}' into the database");
                    }
                }
                catch (NpgsqlException ex)
                {
                    Console.WriteLine($"Database error: {ex.Message}");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error inserting into database: {ex.Message}");
                }
            }
        }
        
        private static async Task SendDataToServer(string data)
        {
            try
            {
                // Create the JSON payload
                var payload = new
                {
                    Id = data,
                    Timestamp = DateTime.Now
                };
                
                // Serialize to JSON
                string jsonPayload = JsonConvert.SerializeObject(payload);
                
                // Send to the server endpoint
                var content = new StringContent(jsonPayload, Encoding.UTF8, "application/json");
                var response = await httpClient.PostAsync($"{SERVER_URL}/api/vehicles", content);
                
                if (response.IsSuccessStatusCode)
                {
                    Console.WriteLine("Data successfully sent to server");
                    string responseBody = await response.Content.ReadAsStringAsync();
                    Console.WriteLine($"Server response: {responseBody}");
                }
                else
                {
                    Console.WriteLine($"Failed to send data to server. Status code: {response.StatusCode}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error sending data to server: {ex.Message}");
            }
        }
        
        private static async Task SendCommandToArduino(string command)
        {
            if (serialPort != null && serialPort.IsOpen)
            {
                try
                {
                    serialPort.WriteLine(command);
                    Console.WriteLine($"Sent command to Arduino: {command}");
                    await Task.Delay(100); // Small delay to ensure command is sent
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error sending command to Arduino: {ex.Message}");
                }
            }
        }
    }
} 