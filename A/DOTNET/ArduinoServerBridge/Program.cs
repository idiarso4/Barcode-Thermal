using System;
using System.IO.Ports;
using System.Net.Http;
using System.Text;
using System.Threading;
using System.Threading.Tasks;
using Newtonsoft.Json;
using Npgsql;
using System.Net.NetworkInformation;
using System.Collections.Generic;
using Microsoft.AspNetCore.SignalR.Client;
using System.Net.Sockets;
using System.IO;
using System.Runtime.InteropServices; // For DllImport
using System.Text.RegularExpressions;

namespace ArduinoServerBridge
{
    class Program
    {
        // Win32 Printing API
        [DllImport("winspool.drv", CharSet = CharSet.Auto, SetLastError = true)]
        public static extern bool OpenPrinter(string pPrinterName, out IntPtr phPrinter, IntPtr pDefault);
        
        [DllImport("winspool.drv", SetLastError = true)]
        public static extern bool ClosePrinter(IntPtr hPrinter);
        
        [DllImport("winspool.drv", CharSet = CharSet.Auto, SetLastError = true)]
        public static extern int StartDocPrinter(IntPtr hPrinter, int Level, ref DOCINFOA pDocInfo);
        
        [DllImport("winspool.drv", SetLastError = true)]
        public static extern bool EndDocPrinter(IntPtr hPrinter);
        
        [DllImport("winspool.drv", SetLastError = true)]
        public static extern bool StartPagePrinter(IntPtr hPrinter);
        
        [DllImport("winspool.drv", SetLastError = true)]
        public static extern bool EndPagePrinter(IntPtr hPrinter);
        
        [DllImport("winspool.drv", SetLastError = true)]
        public static extern bool WritePrinter(IntPtr hPrinter, IntPtr pBytes, int dwCount, out int dwWritten);
        
        [DllImport("winspool.drv", CharSet = CharSet.Auto, SetLastError = true)]
        public static extern bool GetDefaultPrinter(StringBuilder pszBuffer, ref int pcchBuffer);
        
        [StructLayout(LayoutKind.Sequential, CharSet = CharSet.Ansi)]
        public struct DOCINFOA
        {
            [MarshalAs(UnmanagedType.LPStr)]
            public string pDocName;
            [MarshalAs(UnmanagedType.LPStr)]
            public string pOutputFile;
            [MarshalAs(UnmanagedType.LPStr)]
            public string pDataType;
        }
        
        // Pengaturan Serial Port
        private const string SERIAL_PORT = "COM7"; // Ubah sesuai dengan port Arduino Anda
        private const int BAUD_RATE = 9600;

        // Pengaturan Server - sesuaikan dengan detail server linux-park Anda
        private const string SERVER_HOST = "192.168.2.6";
        private const string DB_NAME = "parkir2";
        private const string DB_USER = "postgres";
        private const string DB_PASSWORD = "postgres";
        private const int DB_PORT = 5432;
        private const int SERVER_PORT = 5050;
        private const string SERVER_URL = "http://192.168.2.6:5050";
        private const string API_ENDPOINT = "/api/parking";
        private const string SIGNALR_HUB = "/parkingHub";
        private const string AUTH_USERNAME = "admin";
        private const string AUTH_PASSWORD = "admin";
        
        // ZKing Barcode Printer settings
        private const string PRINTER_IP = "192.168.2.10"; // Replace with actual ZKing printer IP
        private const int PRINTER_PORT = 9100; // Default port for most network printers
        private static bool isPrinterAvailable = false;
        
        // Local Windows printer settings for ESC/POS printing
        private const bool USE_LOCAL_PRINTER = true; // Set to true to use Windows default printer
        private static string defaultPrinterName = ""; // Will be populated at runtime
        
        // Camera settings for vehicle image capture
        private const string CAMERA_IP = "192.168.2.20"; // IP camera address
        private const int CAMERA_PORT = 80; // Default camera port
        private const string CAMERA_USERNAME = "admin"; // Camera username
        private const string CAMERA_PASSWORD = "@dminparkir"; // Camera password
        private static readonly string CAMERA_URL = $"http://{CAMERA_IP}:{CAMERA_PORT}/snapshot"; // For IP camera
        private const string IMAGE_SAVE_PATH = "C:\\ParkImages\\"; // Path to save captured images
        private static bool isCameraAvailable = false;
        
        // Gate control settings
        private const string GATE_COMMAND_OPEN = "OPEN_GATE"; // Command to send to Arduino to open gate
        private const string GATE_COMMAND_CLOSE = "CLOSE_GATE"; // Command to send to Arduino to close gate
        private const int GATE_TIMEOUT_MS = 5000; // Time before gate closes automatically (5 seconds)
        
        // Push button settings
        private const string PUSH_BUTTON_PREFIX = "BUTTON:"; // Prefix for push button commands from Arduino
        private const string MANUAL_ENTRY_BUTTON = "ENTRY"; // Button identifier for manual entry
        private const string MANUAL_EXIT_BUTTON = "EXIT"; // Button identifier for manual exit
        private const string EMERGENCY_BUTTON = "EMERGENCY"; // Button identifier for emergency control
        
        private static readonly HttpClient httpClient = new HttpClient();
        private static DateTime _lastApiCall = DateTime.MinValue;
        private static readonly TimeSpan _apiRateLimit = TimeSpan.FromSeconds(5); // Meningkatkan batas menjadi 5 detik
        
        // Static field for dbConnectionString
        private static string dbConnectionString = string.Empty;
        
        // SignalR connection
        private static HubConnection? hubConnection;
        private static bool isSignalRConnected = false;

        private static SerialPort? serialPort;
        private static bool isRunning = true;
        private static bool isDatabaseAvailable = false;
        private static bool isServerAvailable = false;
        
        // Memory cache untuk menyimpan data saat database tidak tersedia
        private static readonly List<string> DataCache = new List<string>();
        private static readonly object CacheLock = new object();

        // Tambahkan variabel global untuk mencatat waktu terakhir mencetak
        private static DateTime _lastPrintTime = DateTime.MinValue;
        private static readonly TimeSpan _minimumPrintInterval = TimeSpan.FromSeconds(10); // Minimum 10 detik antara cetak
        private static bool _printingEnabled = true; // Flag untuk mengaktifkan/nonaktifkan pencetakan

        // Tambahkan variabel untuk mematikan pemrosesan data otomatis
        private static bool _autoProcessingEnabled = true;

        static async Task Main(string[] args)
        {
            Console.WriteLine("Arduino Server Bridge - Memulai");
            
            // Get default printer name
            if (USE_LOCAL_PRINTER && OperatingSystem.IsWindows())
            {
                try
                {
                    defaultPrinterName = GetDefaultPrinterName();
                    if (string.IsNullOrEmpty(defaultPrinterName))
                    {
                        Console.WriteLine("[WARNING] No default printer found. Set a default printer in Windows to use local printing.");
                        Console.WriteLine("[TIP] Go to Settings > Devices > Printers & scanners and set a printer as default.");
                    }
                    else
                    {
                        Console.WriteLine($"[INFO] Using default Windows printer: '{defaultPrinterName}'");
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[ERROR] Failed to get default printer: {ex.Message}");
                }
            }
            
            // Periksa koneksi ke server dan database
            await CheckRemoteConnections();
            
            // Check printer availability
            CheckPrinterAvailability();
            
            // Check camera availability
            await CheckCameraAvailability();
            
            // Setup SignalR connection
            await SetupSignalRConnection();
            
            // Siapkan serial port
            SetupSerialPort();
            
            // Siapkan token pembatalan untuk menangani shutdown dengan benar
            using (var cts = new CancellationTokenSource())
            {
                Console.CancelKeyPress += (sender, e) => {
                    e.Cancel = true;
                    cts.Cancel();
                    isRunning = false;
                    Console.WriteLine("Mematikan...");
                };

                try
                {
                    // Start connection monitoring task
                    var monitorTask = MonitorRemoteConnections(cts.Token);
                    
                    // Ensure image directory exists
                    Directory.CreateDirectory(IMAGE_SAVE_PATH);
                    
                    // Loop pemrosesan utama
                    await ProcessArduinoData(cts.Token);
                }
                catch (OperationCanceledException)
                {
                    Console.WriteLine("Operasi dibatalkan.");
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Terjadi kesalahan: {ex.Message}");
                }
                finally
                {
                    // Bersihkan sumber daya
                    CloseSerialPort();
                    
                    // Tutup SignalR connection
                    if (hubConnection != null)
                    {
                        await hubConnection.DisposeAsync();
                        Console.WriteLine("SignalR connection ditutup");
                    }
                }
            }
            
            Console.WriteLine("Program berakhir. Tekan tombol apa saja untuk keluar.");
            Console.ReadKey();
        }

        private static async Task SetupSignalRConnection()
        {
            try
            {
                Console.WriteLine($"Menyiapkan koneksi SignalR ke {SERVER_URL + SIGNALR_HUB}");
                
                // Use the documented URL and authentication
                hubConnection = new HubConnectionBuilder()
                    .WithUrl(SERVER_URL + SIGNALR_HUB, options =>
                    {
                        // Add basic authentication header
                        var authValue = Convert.ToBase64String(Encoding.ASCII.GetBytes($"{AUTH_USERNAME}:{AUTH_PASSWORD}"));
                        options.Headers.Add("Authorization", $"Basic {authValue}");
                        
                        // Add additional headers that might help with connection
                        options.Headers.Add("Accept", "text/plain, application/json");
                        options.Headers.Add("User-Agent", "ArduinoServerBridge/1.0");
                        
                        // Disable negotiation for simpler connection if needed
                        // options.SkipNegotiation = true;
                        // options.Transports = HttpTransportType.WebSockets;
                    })
                    .WithAutomaticReconnect(new[] { TimeSpan.FromSeconds(0), TimeSpan.FromSeconds(2), TimeSpan.FromSeconds(5), TimeSpan.FromSeconds(10) })
                    .Build();
                
                hubConnection.Closed += async (error) =>
                {
                    isSignalRConnected = false;
                    Console.WriteLine($"SignalR connection closed: {error?.Message}");
                    await Task.Delay(new Random().Next(0, 5) * 1000);
                    try {
                        await hubConnection.StartAsync();
                        isSignalRConnected = true;
                        Console.WriteLine("SignalR koneksi dibuka kembali setelah terputus");
                    }
                    catch (Exception ex) {
                        Console.WriteLine($"Gagal membuka kembali koneksi SignalR: {ex.Message}");
                    }
                };
                
                hubConnection.Reconnecting += (error) =>
                {
                    isSignalRConnected = false;
                    Console.WriteLine($"SignalR reconnecting: {error?.Message}");
                    return Task.CompletedTask;
                };
                
                hubConnection.Reconnected += (connectionId) =>
                {
                    isSignalRConnected = true;
                    Console.WriteLine($"SignalR reconnected with ID: {connectionId}");
                    return Task.CompletedTask;
                };
                
                // Register handlers for server-to-client methods
                hubConnection.On<string>("ReceiveCommand", async (command) =>
                {
                    Console.WriteLine($"Received command from server: {command}");
                    await ProcessServerCommand(command);
                });
                
                hubConnection.On<string, string>("ReceiveMessage", (user, message) =>
                {
                    Console.WriteLine($"Message from {user}: {message}");
                });
                
                // More specific methods based on the server implementation
                hubConnection.On<object>("VehicleAdded", (data) =>
                {
                    Console.WriteLine($"Vehicle added notification from server: {JsonConvert.SerializeObject(data)}");
                });
                
                // Try to connect with retry logic
                try
                {
                    await ConnectWithRetryAsync(hubConnection);
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Gagal terhubung ke SignalR hub setelah beberapa percobaan: {ex.Message}");
                    isSignalRConnected = false;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat setup SignalR: {ex.Message}");
            }
        }

        private static async Task ConnectWithRetryAsync(HubConnection connection)
        {
            bool connected = false;
            int retryCount = 0;
            const int maxRetryCount = 5;
            
            while (!connected && retryCount < maxRetryCount)
            {
                try
                {
                    await connection.StartAsync();
                    isSignalRConnected = true;
                    isServerAvailable = true;
                    connected = true;
                    Console.WriteLine("SignalR berhasil terhubung");
                }
                catch (Exception ex)
                {
                    retryCount++;
                    Console.WriteLine($"Gagal terhubung ke SignalR (Percobaan {retryCount}/{maxRetryCount}): {ex.Message}");
                    
                    if (retryCount < maxRetryCount)
                    {
                        // Exponential backoff: wait longer between each retry
                        int delayMilliseconds = Math.Min(1000 * (int)Math.Pow(2, retryCount), 30000);
                        Console.WriteLine($"Mencoba lagi dalam {delayMilliseconds/1000} detik...");
                        await Task.Delay(delayMilliseconds);
                    }
                    else
                    {
                        Console.WriteLine("Menyerah setelah beberapa kali percobaan. SignalR tidak tersedia.");
                        isSignalRConnected = false;
                    }
                }
            }
        }

        private static async Task CheckRemoteConnections()
        {
            try
            {
                // Update connection string first
                UpdateConnectionString();
                
                // Check database connection
                Console.WriteLine($"Memeriksa koneksi ke database di {SERVER_HOST}...");
                
                using (var ping = new Ping())
                {
                    var reply = ping.Send(SERVER_HOST, 1000);
                    if (reply.Status == IPStatus.Success)
                    {
                        Console.WriteLine($"Server database {SERVER_HOST} dapat dijangkau (ping: {reply.RoundtripTime}ms)");
                        
                        try
                        {
                            // Try to connect with updated credentials and retry logic
                            int maxRetries = 3;
                            int retryCount = 0;
                            bool connected = false;
                            
                            while (!connected && retryCount < maxRetries)
                            {
                                try
                                {
                                    using (var conn = new NpgsqlConnection(dbConnectionString))
                                    {
                                        // Set shorter timeout for connection attempt
                                        var timeoutTask = Task.Delay(10000); // 10 second timeout
                                        var connectTask = conn.OpenAsync();
                                        
                                        // Wait for either connection or timeout
                                        var completedTask = await Task.WhenAny(connectTask, timeoutTask);
                                        
                                        if (completedTask == connectTask)
                                        {
                                            // Connection successful
                                            Console.WriteLine("Berhasil terhubung ke database PostgreSQL");
                                            isDatabaseAvailable = true;
                                            await conn.CloseAsync();
                                            
                                            // Periksa dan buat tabel jika belum ada
                                            await EnsureTableExists();
                                            connected = true;
                                        }
                                        else
                                        {
                                            // Connection timed out
                                            throw new TimeoutException("Koneksi database timeout setelah 10 detik");
                                        }
                                    }
                                }
                                catch (Exception retryEx)
                                {
                                    retryCount++;
                                    if (retryCount < maxRetries)
                                    {
                                        Console.WriteLine($"Percobaan koneksi database ke-{retryCount} gagal: {retryEx.Message}");
                                        Console.WriteLine($"Mencoba lagi dalam {retryCount} detik...");
                                        await Task.Delay(retryCount * 1000); // Exponential backoff
                                    }
                                    else
                                    {
                                        Console.WriteLine($"Error saat memeriksa koneksi database setelah {maxRetries} percobaan: {retryEx.Message}");
                                        isDatabaseAvailable = false;
                                        
                                        // Coba koneksi ke database lokal sebagai fallback jika tersedia
                                        Console.WriteLine("Mencoba koneksi ke database lokal sebagai fallback...");
                                        try
                                        {
                                            string localDbConnectionString = "Host=localhost;Port=5432;Database=parkir_local;Username=postgres;Password=postgres;Timeout=5";
                                            using (var localConn = new NpgsqlConnection(localDbConnectionString))
                                            {
                                                await localConn.OpenAsync();
                                                Console.WriteLine("Berhasil terhubung ke database PostgreSQL lokal");
                                                dbConnectionString = localDbConnectionString; // Gunakan koneksi lokal
                                                isDatabaseAvailable = true;
                                                await localConn.CloseAsync();
                                            }
                                        }
                                        catch (Exception localEx)
                                        {
                                            Console.WriteLine($"Koneksi ke database lokal juga gagal: {localEx.Message}");
                                        }
                                    }
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Error saat memeriksa koneksi database: {ex.Message}");
                            isDatabaseAvailable = false;
                        }
                    }
                    else
                    {
                        Console.WriteLine($"Server database tidak dapat dijangkau: {reply.Status}");
                        isDatabaseAvailable = false;
                    }
                }
                
                // Check server connection with improved method
                Console.WriteLine($"Memeriksa koneksi ke server HTTP di {SERVER_URL}...");
                try
                {
                    // Ekstrak hostname dari URL
                    var uri = new Uri(SERVER_URL);
                    var host = uri.Host;
                    
                    // Ping server first
                    using (var ping = new Ping())
                    {
                        var reply = await ping.SendPingAsync(host, 1000);
                        if (reply.Status == IPStatus.Success)
                        {
                            Console.WriteLine($"Server HTTP {host} dapat dijangkau (ping: {reply.RoundtripTime}ms)");
                            
                            // Try HTTP connection using the test-connection endpoint
                            try
                            {
                                var tempClient = new HttpClient();
                                tempClient.Timeout = TimeSpan.FromSeconds(5);
                                
                                // Add authentication
                                var authValue = Convert.ToBase64String(Encoding.ASCII.GetBytes($"{AUTH_USERNAME}:{AUTH_PASSWORD}"));
                                tempClient.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Basic", authValue);
                                
                                var response = await tempClient.GetAsync($"{SERVER_URL}/api/test-connection");
                                var content = await response.Content.ReadAsStringAsync();
                                
                                Console.WriteLine($"Berhasil terhubung ke server HTTP: {response.StatusCode}");
                                Console.WriteLine($"Response: {content}");
                                
                                isServerAvailable = true;
                            }
                            catch (Exception ex)
                            {
                                // Fallback to basic connection test
                                try
                                {
                                    var fallbackClient = new HttpClient();
                                    fallbackClient.Timeout = TimeSpan.FromSeconds(5);
                                    var response = await fallbackClient.GetAsync(SERVER_URL);
                                    Console.WriteLine($"Berhasil terhubung ke server HTTP: {response.StatusCode}");
                                    isServerAvailable = true;
                                }
                                catch (Exception fallbackEx)
                                {
                                    Console.WriteLine($"Tidak dapat terhubung ke server HTTP: {fallbackEx.Message}");
                                    isServerAvailable = false;
                                }
                            }
                        }
                        else
                        {
                            Console.WriteLine($"Tidak dapat menjangkau server HTTP {host}: {reply.Status}");
                            isServerAvailable = false;
                        }
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error saat memeriksa koneksi HTTP server: {ex.Message}");
                    isServerAvailable = false;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat memeriksa koneksi: {ex.Message}");
            }
            
            if (!isDatabaseAvailable)
            {
                Console.WriteLine("[WARNING] Database tidak tersedia. Data akan disimpan sementara di memori.");
            }
            
            if (!isServerAvailable)
            {
                Console.WriteLine("[WARNING] Server API tidak tersedia. Data akan disimpan sementara di database lokal.");
            }
        }

        private static void SetupSerialPort()
        {
            try
            {
                // Check if running on Windows
                if (OperatingSystem.IsWindows())
                {
                    // Daftar port yang akan dicoba jika port utama tidak tersedia
                    string[] portsToTry = { SERIAL_PORT, "COM3", "COM4", "COM5", "COM6" };
                    bool connected = false;
                    
                    // Tampilkan port yang tersedia
                    string[] availablePorts = SerialPort.GetPortNames();
                    Console.WriteLine("Port serial yang tersedia: " + string.Join(", ", availablePorts));
                    
                    // Coba port satu per satu
                    foreach (string port in portsToTry)
                    {
                        try
                        {
                            if (!Array.Exists(availablePorts, p => p == port))
                            {
                                Console.WriteLine($"Port {port} tidak tersedia, melewati...");
                                continue;
                            }
                            
                            // Inisialisasi serial port
                            serialPort = new SerialPort(port, BAUD_RATE)
                            {
                                DataBits = 8,
                                Parity = Parity.None,
                                StopBits = StopBits.One,
                                Handshake = Handshake.None,
                                ReadTimeout = 500,
                                WriteTimeout = 500
                            };
                            
                            // Buka serial port
                            serialPort.Open();
                            Console.WriteLine($"Terhubung ke Arduino pada port {port} dengan kecepatan {BAUD_RATE} baud");
                            connected = true;
                            break;
                        }
                        catch (UnauthorizedAccessException)
                        {
                            Console.WriteLine($"Akses ke port {port} ditolak. Port mungkin sedang digunakan oleh aplikasi lain.");
                            if (serialPort != null)
                            {
                                serialPort.Dispose();
                                serialPort = null;
                            }
                        }
                        catch (Exception portEx)
                        {
                            Console.WriteLine($"Error saat mencoba port {port}: {portEx.Message}");
                            if (serialPort != null)
                            {
                                serialPort.Dispose();
                                serialPort = null;
                            }
                        }
                    }
                    
                    if (!connected)
                    {
                        Console.WriteLine("[WARNING] Tidak dapat terhubung ke port serial manapun. Aplikasi akan berjalan tanpa koneksi Arduino.");
                        Console.WriteLine("[TIP] Pastikan Arduino terhubung dan tidak digunakan oleh aplikasi lain.");
                        Console.WriteLine("[TIP] Coba jalankan aplikasi sebagai Administrator untuk mendapatkan akses penuh ke port serial.");
                    }
                }
                else
                {
                    Console.WriteLine("Error: System.IO.Ports hanya didukung pada Windows.");
                    throw new PlatformNotSupportedException("System.IO.Ports hanya didukung pada Windows.");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat setup serial port: {ex.Message}");
                // Tidak melempar exception agar program tetap berjalan
            }
        }
        
        private static void CloseSerialPort()
        {
            if (serialPort != null && serialPort.IsOpen)
            {
                serialPort.Close();
                serialPort.Dispose();
                Console.WriteLine("Serial port ditutup");
            }
        }
        
        private static async Task ProcessArduinoData(CancellationToken cancellationToken)
        {
            Console.WriteLine("Menunggu data dari Arduino...");
            
            // Add last processed data tracking to prevent duplicate processing
            string lastProcessedData = string.Empty;
            DateTime lastProcessTime = DateTime.MinValue;
            int minProcessIntervalMs = 3000; // Minimum 3 seconds between processing the same data
            
            while (isRunning && !cancellationToken.IsCancellationRequested)
            {
                try
                {
                    // Periksa apakah ada data untuk dibaca dari Arduino
                    if (serialPort != null && serialPort.IsOpen && serialPort.BytesToRead > 0)
                    {
                        // Baca data dari Arduino
                        string receivedData = serialPort.ReadLine().Trim();
                        
                        // Cek apakah ini adalah perintah khusus
                        if (receivedData.StartsWith("CMD:"))
                        {
                            string command = receivedData.Substring(4).Trim().ToLower();
                            if (command == "stop_auto")
                            {
                                _autoProcessingEnabled = false;
                                Console.WriteLine("[INFO] Pemrosesan otomatis dinonaktifkan. Gunakan 'CMD:START_AUTO' untuk mengaktifkan kembali.");
                                continue;
                            }
                            else if (command == "start_auto")
                            {
                                _autoProcessingEnabled = true;
                                Console.WriteLine("[INFO] Pemrosesan otomatis diaktifkan.");
                                continue;
                            }
                            else if (command == "disable_print")
                            {
                                _printingEnabled = false;
                                Console.WriteLine("[INFO] Pencetakan dinonaktifkan.");
                                continue;
                            }
                            else if (command == "enable_print")
                            {
                                _printingEnabled = true;
                                Console.WriteLine("[INFO] Pencetakan diaktifkan.");
                                continue;
                            }
                            else if (command == "reset")
                            {
                                _autoProcessingEnabled = true;
                                _printingEnabled = true;
                                _lastPrintTime = DateTime.MinValue;
                                Console.WriteLine("[INFO] Sistem direset.");
                                continue;
                            }
                        }
                        
                        // Cek jika pemrosesan otomatis dinonaktifkan
                        if (!_autoProcessingEnabled)
                        {
                            Console.WriteLine($"[DEBUG] Data diterima tapi tidak diproses (auto processing off): {receivedData}");
                            continue;
                        }
                        
                        // Skip empty data
                        if (string.IsNullOrWhiteSpace(receivedData))
                        {
                            await Task.Delay(100, cancellationToken);
                            continue;
                        }
                        
                        // Check if this is the same data we just processed (debounce)
                        if (receivedData == lastProcessedData && 
                            (DateTime.Now - lastProcessTime).TotalMilliseconds < minProcessIntervalMs)
                        {
                            Console.WriteLine($"[DEBUG] Ignoring duplicate data: {receivedData} (debounce)");
                            await Task.Delay(100, cancellationToken);
                            continue;
                        }
                        
                        Console.WriteLine($"Menerima data dari Arduino: {receivedData}");
                        
                        // Update tracking variables
                        lastProcessedData = receivedData;
                        lastProcessTime = DateTime.Now;
                        
                        // Tambahkan validasi lebih ketat untuk format data
                        // Hanya proses data dengan format yang jelas
                        if (receivedData.StartsWith("BUTTON:") || 
                            receivedData.StartsWith("BTN:") || 
                            receivedData.StartsWith("PARK") || 
                            Regex.IsMatch(receivedData, @"^[A-Z0-9]{7,}$"))
                        {
                            // Proses data yang valid
                            // Different ways to handle input based on format
                            if (receivedData.StartsWith(PUSH_BUTTON_PREFIX))
                            {
                                // Format 1: Data with BUTTON: prefix from newer Arduino code
                                string buttonId = receivedData.Substring(PUSH_BUTTON_PREFIX.Length).Trim();
                                await HandlePushButtonTrigger(buttonId);
                            }
                            else if (receivedData.StartsWith("BTN:"))
                            {
                                // Format 2: BTN: prefix for buttons
                                string buttonId = receivedData.Substring(4).Trim();
                                await HandlePushButtonTrigger(buttonId);
                            }
                            else if (receivedData.Equals("ENTRY", StringComparison.OrdinalIgnoreCase) || 
                                    receivedData.Equals("EXIT", StringComparison.OrdinalIgnoreCase) || 
                                    receivedData.Equals("EMERGENCY", StringComparison.OrdinalIgnoreCase))
                            {
                                // Format 3: Direct button command
                                await HandlePushButtonTrigger(receivedData);
                            }
                            else if (receivedData.StartsWith("BUTTON"))
                            {
                                // Format 4: BUTTON text with number or ID
                                string[] parts = receivedData.Split(new[] { ' ', '_', ':', '-' }, StringSplitOptions.RemoveEmptyEntries);
                                if (parts.Length >= 2)
                                {
                                    // Find the button type part
                                    string buttonType = parts[1].ToUpper();
                                    if (buttonType.Contains("ENTRY") || buttonType.Equals("IN"))
                                        await HandlePushButtonTrigger(MANUAL_ENTRY_BUTTON);
                                    else if (buttonType.Contains("EXIT") || buttonType.Equals("OUT"))
                                        await HandlePushButtonTrigger(MANUAL_EXIT_BUTTON);
                                    else if (buttonType.Contains("EMERG"))
                                        await HandlePushButtonTrigger(EMERGENCY_BUTTON);
                                    else
                                        Console.WriteLine($"Unrecognized button type: {buttonType}");
                                }
                                else
                                {
                                    // Just "BUTTON" with no additional info
                                    await HandlePushButtonTrigger(MANUAL_ENTRY_BUTTON); // Default to ENTRY
                                }
                            }
                            // Format 5: Check if the received data is a number (counter from Arduino)
                            else if (int.TryParse(receivedData, out int counterValue))
                            {
                                Console.WriteLine($"[IMPORTANT] Button press detected with counter value: {counterValue}");
                                
                                // Generate a manual vehicle ID using the counter
                                string manualVehicleId = $"BTN{counterValue:D4}";
                                
                                // Generate a unique ticket ID
                                string ticketId = $"{DateTime.Now:yyyyMMdd_HHmmss}_{counterValue:D4}";
                                
                                Console.WriteLine($"[DEBUG] Generated vehicle ID: {manualVehicleId}, ticket ID: {ticketId}");
                                
                                await ProcessButtonPress(manualVehicleId, ticketId);
                            }
                            // Format 6: Also check for numeric value with BUTTON: prefix
                            else if (receivedData.StartsWith("BUTTON:") && int.TryParse(receivedData.Substring(7).Trim(), out int btnValue))
                            {
                                Console.WriteLine($"[IMPORTANT] Button press detected with BUTTON: prefix, value: {btnValue}");
                                
                                // Generate a manual vehicle ID using the counter
                                string manualVehicleId = $"BTN{btnValue:D4}";
                                
                                // Generate a unique ticket ID
                                string ticketId = $"{DateTime.Now:yyyyMMdd_HHmmss}_{btnValue:D4}";
                                
                                Console.WriteLine($"[DEBUG] Generated vehicle ID: {manualVehicleId}, ticket ID: {ticketId}");
                                
                                await ProcessButtonPress(manualVehicleId, ticketId);
                            }
                            else
                            {
                                // Process as barcode data (default)
                                await ProcessReceivedData(receivedData);
                            }
                        }
                        else
                        {
                            Console.WriteLine($"[IGNORED] Data tidak dalam format yang valid: {receivedData}");
                        }
                        
                        // Send acknowledgment back to Arduino
                        if (serialPort != null && serialPort.IsOpen)
                        {
                            await Task.Delay(50); // Small delay to ensure Arduino is ready
                            serialPort.WriteLine("ACK"); // Acknowledge receipt of data
                        }
                    }
                    
                    // Delay kecil untuk mencegah CPU usage tinggi
                    await Task.Delay(100, cancellationToken);
                }
                catch (TimeoutException)
                {
                    // Ini normal ketika tidak ada data yang tersedia untuk dibaca
                }
                catch (OperationCanceledException)
                {
                    throw;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error saat memproses data Arduino: {ex.Message}");
                    
                    // Coba hubungkan kembali jika koneksi terputus
                    try
                    {
                        if (serialPort != null && !serialPort.IsOpen)
                        {
                            Console.WriteLine("Mencoba menghubungkan kembali ke Arduino...");
                            serialPort.Open();
                        }
                    }
                    catch (Exception reconnectEx)
                    {
                        Console.WriteLine($"Gagal menyambung kembali ke Arduino: {reconnectEx.Message}");
                        await Task.Delay(5000, cancellationToken); // Tunggu sebelum mencoba lagi
                    }
                }
            }
        }
        
        private static async Task HandlePushButtonTrigger(string buttonId)
        {
            Console.WriteLine($"Push button terdeteksi: {buttonId}");
            
            try
            {
                switch (buttonId)
                {
                    case MANUAL_ENTRY_BUTTON:
                        Console.WriteLine("Tombol ENTRY ditekan - memproses entri manual");
                        
                        // Generate a random vehicle ID for manual entry
                        string manualVehicleId = $"MANUAL_{DateTime.Now:yyyyMMddHHmmss}";
                        
                        // Process entry like normal vehicle
                        await ProcessReceivedData(manualVehicleId);
                        break;
                        
                    case MANUAL_EXIT_BUTTON:
                        Console.WriteLine("Tombol EXIT ditekan - membuka gate keluar");
                        
                        // Just open the gate for manual exit
                        await OpenEntryGate();
                        
                        // Log the manual exit
                        if (isDatabaseAvailable)
                        {
                            try
                            {
                                using (var connection = new NpgsqlConnection(dbConnectionString))
                                {
                                    await connection.OpenAsync();
                                    
                                    using (var cmd = new NpgsqlCommand())
                                    {
                                        cmd.Connection = connection;
                                        cmd.CommandText = @"
                                            INSERT INTO ManualOperations (OperationType, Timestamp, Description)
                                            VALUES ('MANUAL_EXIT', @timestamp, 'Manual exit button pressed')";
                                        
                                        cmd.Parameters.AddWithValue("timestamp", DateTime.Now);
                                        
                                        await cmd.ExecuteNonQueryAsync();
                                        Console.WriteLine("Manual exit logged to database");
                                    }
                                }
                            }
                            catch (Exception ex)
                            {
                                Console.WriteLine($"Error saat mencatat manual exit: {ex.Message}");
                            }
                        }
                        break;
                        
                    case EMERGENCY_BUTTON:
                        Console.WriteLine("Tombol EMERGENCY ditekan - membuka gate dalam mode darurat");
                        
                        // Open gate immediately in emergency mode - don't auto-close
                        if (serialPort != null && serialPort.IsOpen)
                        {
                            serialPort.WriteLine(GATE_COMMAND_OPEN);
                            Console.WriteLine("EMERGENCY: Gate dibuka dalam mode darurat");
                            
                            // Log the emergency
                            if (isDatabaseAvailable)
                            {
                                try
                                {
                                    using (var connection = new NpgsqlConnection(dbConnectionString))
                                    {
                                        await connection.OpenAsync();
                                        
                                        using (var cmd = new NpgsqlCommand())
                                        {
                                            cmd.Connection = connection;
                                            cmd.CommandText = @"
                                                INSERT INTO ManualOperations (OperationType, Timestamp, Description)
                                                VALUES ('EMERGENCY', @timestamp, 'Emergency button pressed')";
                                            
                                            cmd.Parameters.AddWithValue("timestamp", DateTime.Now);
                                            
                                            await cmd.ExecuteNonQueryAsync();
                                            Console.WriteLine("Emergency operation logged to database");
                                        }
                                    }
                                }
                                catch (Exception ex)
                                {
                                    Console.WriteLine($"Error saat mencatat operasi darurat: {ex.Message}");
                                }
                            }
                            
                            // Alert via SignalR if available
                            if (isSignalRConnected && hubConnection != null)
                            {
                                try
                                {
                                    await hubConnection.InvokeAsync("EmergencyAlert", "Emergency button pressed at entry gate");
                                    Console.WriteLine("Emergency alert sent to server via SignalR");
                                }
                                catch (Exception ex)
                                {
                                    Console.WriteLine($"Error saat mengirim alert darurat: {ex.Message}");
                                }
                            }
                        }
                        break;
                        
                    default:
                        Console.WriteLine($"Tombol tidak dikenal: {buttonId}");
                        break;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat memproses push button: {ex.Message}");
            }
        }
        
        private static async Task ProcessReceivedData(string data)
        {
            try
            {
                // Generate a unique ticket ID based on timestamp
                string ticketId = $"{DateTime.Now:yyyyMMdd_HHmmss}_{new Random().Next(1000, 9999)}";
                
                // 1. Capture vehicle image
                string imagePath = await CaptureVehicleImageAsync(ticketId);
                
                // 2. Insert data to database with image path
                await InsertIntoDatabase(data, ticketId, imagePath);
                
                // 3. Send data to server
                await SendDataToServer(data, ticketId, imagePath);
                
                // 4. Print entry ticket
                await PrintEntryTicket(data, ticketId);
                
                // 5. Open gate
                await OpenEntryGate();
                
                // Send acknowledgment to Arduino
                if (serialPort != null && serialPort.IsOpen)
                {
                    await Task.Delay(50); // Small delay to ensure Arduino is ready
                    serialPort.WriteLine("ACK"); // Acknowledge receipt of data
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error dalam pemrosesan data: {ex.Message}");
            }
        }
        
        private static async Task<string> CaptureVehicleImageAsync(string ticketId)
        {
            if (!isCameraAvailable)
            {
                Console.WriteLine("Kamera tidak tersedia. Gambar tidak diambil.");
                return string.Empty;
            }
            
            try
            {
                Console.WriteLine("Mengambil gambar kendaraan...");
                
                // Ensure directory exists
                Directory.CreateDirectory(IMAGE_SAVE_PATH);
                
                // Generate file name based on ticketId
                string fileName = $"{ticketId}.jpg";
                string fullPath = Path.Combine(IMAGE_SAVE_PATH, fileName);
                
                // For IP camera, download image from URL with authentication
                using (var client = new HttpClient())
                {
                    // Add authentication for camera
                    var authString = $"{CAMERA_USERNAME}:{CAMERA_PASSWORD}";
                    var base64Auth = Convert.ToBase64String(Encoding.UTF8.GetBytes(authString));
                    client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Basic", base64Auth);
                    
                    // Set a reasonable timeout
                    client.Timeout = TimeSpan.FromSeconds(10);
                    
                    Console.WriteLine($"Menghubungkan ke kamera di {CAMERA_URL}...");
                    var response = await client.GetAsync(CAMERA_URL);
                    
                    if (response.IsSuccessStatusCode)
                    {
                        using (var imageStream = await response.Content.ReadAsStreamAsync())
                        using (var fileStream = File.Create(fullPath))
                        {
                            await imageStream.CopyToAsync(fileStream);
                        }
                        
                        Console.WriteLine($"Gambar kendaraan disimpan di: {fullPath}");
                        return fullPath;
                    }
                    else
                    {
                        Console.WriteLine($"Gagal mengambil gambar. Status: {response.StatusCode}");
                        if (response.StatusCode == System.Net.HttpStatusCode.Unauthorized)
                        {
                            Console.WriteLine("Autentikasi kamera gagal. Periksa username dan password.");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat mengambil gambar: {ex.Message}");
                isCameraAvailable = false; // Mark camera as unavailable
            }
            
            return string.Empty;
        }
        
        private static async Task InsertIntoDatabase(string barcodeData, string ticketId, string imagePath)
        {
            if (!isDatabaseAvailable)
            {
                Console.WriteLine($"Database tidak tersedia. Data '{barcodeData}' disimpan di cache.");
                
                // Add to cache with additional info
                lock (CacheLock)
                {
                    // Store as JSON to include all data
                    var cacheData = JsonConvert.SerializeObject(new 
                    { 
                        BarcodeData = barcodeData,
                        TicketId = ticketId,
                        ImagePath = imagePath,
                        Timestamp = DateTime.Now
                    });
                    
                    DataCache.Add(cacheData);
                    Console.WriteLine($"Cache: {DataCache.Count} item dalam cache");
                }
                
                return;
            }
            
            using (var connection = new NpgsqlConnection(dbConnectionString))
            {
                try
                {
                    await connection.OpenAsync();
                    
                    // Buat dan eksekusi perintah dengan info tambahan
                    using (var cmd = new NpgsqlCommand())
                    {
                        cmd.Connection = connection;
                        cmd.CommandText = @"
                            INSERT INTO Vehicles (Id, TicketId, ImagePath, EntryTime, Status) 
                            VALUES (@barcodeData, @ticketId, @imagePath, @entryTime, 'IN')";
                        
                        cmd.Parameters.AddWithValue("barcodeData", barcodeData);
                        cmd.Parameters.AddWithValue("ticketId", ticketId);
                        cmd.Parameters.AddWithValue("imagePath", imagePath ?? (object)DBNull.Value);
                        cmd.Parameters.AddWithValue("entryTime", DateTime.Now);
                        
                        await cmd.ExecuteNonQueryAsync();
                        Console.WriteLine($"Memasukkan '{barcodeData}' dengan ticket ID '{ticketId}' ke dalam database");
                    }
                }
                catch (NpgsqlException ex)
                {
                    Console.WriteLine($"Error database: {ex.Message}");
                    // If insertion fails, add to cache
                    lock (CacheLock)
                    {
                        var cacheData = JsonConvert.SerializeObject(new 
                        { 
                            BarcodeData = barcodeData,
                            TicketId = ticketId,
                            ImagePath = imagePath,
                            Timestamp = DateTime.Now
                        });
                        
                        DataCache.Add(cacheData);
                        Console.WriteLine($"Cache: Data disimpan ke cache karena error database");
                    }
                    
                    // Database might not be available anymore
                    isDatabaseAvailable = false;
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error saat memasukkan ke database: {ex.Message}");
                    // If insertion fails, add to cache
                    lock (CacheLock)
                    {
                        var cacheData = JsonConvert.SerializeObject(new 
                        { 
                            BarcodeData = barcodeData,
                            TicketId = ticketId,
                            ImagePath = imagePath,
                            Timestamp = DateTime.Now
                        });
                        
                        DataCache.Add(cacheData);
                        Console.WriteLine($"Cache: Data disimpan ke cache karena error");
                    }
                }
            }
        }
        
        private static async Task SendDataToServer(string vehicleId, string ticketId, string imagePath)
        {
            if (!isServerAvailable)
            {
                Console.WriteLine($"Server tidak tersedia. Data akan disimpan di cache: {vehicleId}");
                AddToCache(vehicleId);
                return;
            }
            
            try
            {
                // Check if we need to respect rate limits
                var timeSinceLastCall = DateTime.Now - _lastApiCall;
                if (timeSinceLastCall < _apiRateLimit)
                {
                    var waitTime = _apiRateLimit - timeSinceLastCall;
                    Console.WriteLine($"Menunggu {waitTime.TotalSeconds:F1} detik untuk rate limit...");
                    await Task.Delay(waitTime);
                }
                
                Console.WriteLine($"[DEBUG] Sending data to server for vehicleId: {vehicleId}");
                
                // Ensure the HTTP client has the correct timeout
                httpClient.Timeout = TimeSpan.FromSeconds(30);
                
                // Set authentication for all requests
                var authValue = Convert.ToBase64String(Encoding.ASCII.GetBytes($"{AUTH_USERNAME}:{AUTH_PASSWORD}"));
                httpClient.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Basic", authValue);
                
                // Set cache control headers
                httpClient.DefaultRequestHeaders.CacheControl = new System.Net.Http.Headers.CacheControlHeaderValue
                {
                    NoCache = true,
                    NoStore = true,
                    MustRevalidate = true,
                    MaxAge = TimeSpan.Zero
                };
                
                // Define retry parameters
                int maxRetries = 3;
                bool success = false;
                int retryCount = 0;
                
                // Create the correct payload format according to server expectations
                var payload = new
                {
                    VehicleId = vehicleId,
                    PlateNumber = vehicleId, // Use vehicleId as PlateNumber if not available
                    VehicleType = "Motorcycle", // Default vehicle type
                    Timestamp = DateTime.Now
                };
                
                // Main retry loop for all connection attempts
                while (!success && retryCount < maxRetries)
                {
                    retryCount++;
                    Console.WriteLine($"[INFO] Connection attempt {retryCount} of {maxRetries}...");
                    
                    int delayMs = retryCount * 1000; // Progressive delay: 1s, 2s, 3s
                    
                    // 1. Try SignalR first (if connected)
                    if (hubConnection != null && isSignalRConnected)
                    {
                        try
                        {
                            Console.WriteLine($"[DEBUG] Sending via SignalR: {JsonConvert.SerializeObject(payload)}");
                            
                            // Try the documented method name with correct casing
                            await hubConnection.InvokeAsync("AddVehicle", payload);
                            Console.WriteLine("[INFO] Data sent successfully via SignalR");
                            _lastApiCall = DateTime.Now;
                            success = true;
                            break; // Exit retry loop on success
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"[ERROR] SignalR send failed: {ex.Message}. Falling back to HTTP.");
                            // Continue to HTTP fallback
                        }
                    }
                    
                    // 2. Try JSON POST to main endpoint
                    try
                    {
                        var jsonContent = new StringContent(
                            JsonConvert.SerializeObject(payload),
                            Encoding.UTF8,
                            "application/json");
                            
                        Console.WriteLine($"[DEBUG] Sending JSON to {SERVER_URL + API_ENDPOINT}");
                        
                        var response = await httpClient.PostAsync(SERVER_URL + API_ENDPOINT, jsonContent);
                        var responseContent = await response.Content.ReadAsStringAsync();
                        
                        if (response.IsSuccessStatusCode)
                        {
                            Console.WriteLine($"[INFO] Data berhasil dikirim ke server melalui HTTP JSON: {vehicleId}");
                            Console.WriteLine($"[DEBUG] Response: {responseContent}");
                            _lastApiCall = DateTime.Now;
                            success = true;
                            break; // Exit retry loop on success
                        }
                        else
                        {
                            Console.WriteLine($"[ERROR] HTTP JSON failed with status {response.StatusCode}: {responseContent}");
                            
                            // Wait before next attempt or fallback
                            if (!success && retryCount < maxRetries)
                            {
                                Console.WriteLine($"[INFO] Retrying in {delayMs}ms...");
                                await Task.Delay(delayMs);
                            }
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"[ERROR] HTTP JSON error: {ex.Message}. Trying form data.");
                        
                        // Wait before fallback
                        if (!success && retryCount < maxRetries)
                        {
                            Console.WriteLine($"[INFO] Retrying in {delayMs}ms...");
                            await Task.Delay(delayMs);
                        }
                    }
                    
                    // 3. Try form data as fallback
                    if (!success)
                    {
                        try
                        {
                            var formData = new MultipartFormDataContent();
                            formData.Add(new StringContent(payload.VehicleId), "VehicleId");
                            formData.Add(new StringContent(payload.PlateNumber), "PlateNumber");
                            formData.Add(new StringContent(payload.VehicleType), "VehicleType");
                            formData.Add(new StringContent(payload.Timestamp.ToString("o")), "Timestamp");
                            
                            if (!string.IsNullOrEmpty(imagePath) && File.Exists(imagePath))
                            {
                                // Add image if available
                                var imageContent = new ByteArrayContent(File.ReadAllBytes(imagePath));
                                imageContent.Headers.ContentType = new System.Net.Http.Headers.MediaTypeHeaderValue("image/jpeg");
                                formData.Add(imageContent, "image", Path.GetFileName(imagePath));
                            }
                            
                            Console.WriteLine($"[DEBUG] Sending form data to {SERVER_URL + API_ENDPOINT}");
                            
                            var response = await httpClient.PostAsync(SERVER_URL + API_ENDPOINT, formData);
                            var responseContent = await response.Content.ReadAsStringAsync();
                            
                            if (response.IsSuccessStatusCode)
                            {
                                Console.WriteLine($"[INFO] Data berhasil dikirim ke server melalui form data: {vehicleId}");
                                Console.WriteLine($"[DEBUG] Response: {responseContent}");
                                _lastApiCall = DateTime.Now;
                                success = true;
                                break; // Exit retry loop on success
                            }
                            else
                            {
                                Console.WriteLine($"[ERROR] Form data failed with status {response.StatusCode}: {responseContent}");
                                
                                // 4. Try alternate endpoints as last resort
                                if (!success && retryCount == maxRetries) // Only on last retry
                                {
                                    Console.WriteLine("[INFO] Trying alternate endpoints as last resort...");
                                    
                                    foreach (var endpoint in new[] { "/api/vehicle/add", "/api/vehicles", "/parkir/add" })
                                    {
                                        try
                                        {
                                            response = await httpClient.PostAsync(SERVER_URL + endpoint, formData);
                                            responseContent = await response.Content.ReadAsStringAsync();
                                            
                                            if (response.IsSuccessStatusCode)
                                            {
                                                Console.WriteLine($"[INFO] Data berhasil dikirim ke server via {endpoint}: {vehicleId}");
                                                Console.WriteLine($"[DEBUG] Response: {responseContent}");
                                                _lastApiCall = DateTime.Now;
                                                success = true;
                                                break; // Exit endpoint loop on success
                                            }
                                        }
                                        catch { /* Continue trying other endpoints */ }
                                    }
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"[ERROR] Form data error: {ex.Message}");
                        }
                    }
                    
                    // Wait before next retry if still unsuccessful
                    if (!success && retryCount < maxRetries)
                    {
                        Console.WriteLine($"[INFO] Retrying in {delayMs}ms...");
                        await Task.Delay(delayMs);
                    }
                }
                
                // If all attempts fail, add to cache
                if (!success)
                {
                    Console.WriteLine($"[WARNING] Failed to send data to server after {maxRetries} attempts. Caching: {vehicleId}");
                    AddToCache(vehicleId);
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat mengirim data ke server: {ex.Message}");
                AddToCache(vehicleId);
            }
        }
        
        private static async Task SendCommandToArduino(string command)
        {
            if (serialPort != null && serialPort.IsOpen)
            {
                try
                {
                    serialPort.WriteLine(command);
                    Console.WriteLine($"Mengirim perintah ke Arduino: {command}");
                    await Task.Delay(100); // Delay kecil untuk memastikan perintah terkirim
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Error saat mengirim perintah ke Arduino: {ex.Message}");
                }
            }
        }

        private static async Task MonitorRemoteConnections(CancellationToken cancellationToken)
        {
            while (isRunning && !cancellationToken.IsCancellationRequested)
            {
                // Only check connections if they're not already available
                if (!isDatabaseAvailable || !isServerAvailable || !isSignalRConnected)
                {
                    await RetryConnections();
                }
                
                // Wait 30 seconds before checking again
                try
                {
                    await Task.Delay(30000, cancellationToken);
                }
                catch (OperationCanceledException)
                {
                    // This is expected if cancellation is requested
                    break;
                }
            }
        }
        
        private static async Task RetryConnections()
        {
            bool wasDbUnavailable = !isDatabaseAvailable;
            
            // Retry database connection if not available
            if (!isDatabaseAvailable)
            {
                try
                {
                    using (var connection = new NpgsqlConnection(dbConnectionString))
                    {
                        await connection.OpenAsync();
                        isDatabaseAvailable = true;
                        Console.WriteLine($"Berhasil terhubung ke database {DB_NAME}");
                        
                        // Jika koneksi ke database baru tersedia dan ada data di cache, flush cache
                        if (wasDbUnavailable)
                        {
                            await FlushCacheToDatabase();
                        }
                    }
                }
                catch (Exception)
                {
                    // Don't log every retry failure
                }
            }
            
            // Retry SignalR connection if not connected
            if (!isSignalRConnected && hubConnection != null)
            {
                try
                {
                    if (hubConnection.State != HubConnectionState.Connected)
                    {
                        await hubConnection.StartAsync();
                        isSignalRConnected = true;
                        isServerAvailable = true;
                        Console.WriteLine("SignalR berhasil terhubung kembali");
                    }
                }
                catch (Exception)
                {
                    // Don't log every retry failure
                }
            }
            
            // Retry server REST API connection if not available and SignalR is also not available
            if (!isServerAvailable && !isSignalRConnected)
            {
                try
                {
                    var client = new HttpClient();
                    client.Timeout = TimeSpan.FromSeconds(3);
                    var response = await client.GetAsync(SERVER_URL);
                    isServerAvailable = true;
                    Console.WriteLine($"Berhasil terhubung ke server HTTP: {response.StatusCode}");
                }
                catch (Exception)
                {
                    // Don't log every retry failure
                }
            }
        }
        
        private static async Task FlushCacheToDatabase()
        {
            List<string> itemsToProcess;
            
            // Get all cached items while holding lock
            lock (CacheLock)
            {
                if (DataCache.Count == 0)
                {
                    return;
                }
                
                itemsToProcess = new List<string>(DataCache);
                Console.WriteLine($"Mencoba flush {itemsToProcess.Count} item dari cache ke database");
            }
            
            // Process cached items
            foreach (var item in itemsToProcess)
            {
                try
                {
                    // Deserialize cached JSON data
                    dynamic cachedData = JsonConvert.DeserializeObject<dynamic>(item)!;
                    string barcodeData = cachedData.BarcodeData;
                    string ticketId = cachedData.TicketId;
                    string imagePath = cachedData.ImagePath;
                    DateTime timestamp = cachedData.Timestamp;
                    
                    Console.WriteLine($"Cache: Memproses data cached '{barcodeData}' dengan ticket ID '{ticketId}'");
                    
                    // Insert item into database
                    using (var connection = new NpgsqlConnection(dbConnectionString))
                    {
                        await connection.OpenAsync();
                        
                        using (var cmd = new NpgsqlCommand())
                        {
                            cmd.Connection = connection;
                            cmd.CommandText = @"
                                INSERT INTO Vehicles (Id, TicketId, ImagePath, EntryTime, Status) 
                                VALUES (@barcodeData, @ticketId, @imagePath, @entryTime, 'IN')
                                ON CONFLICT (TicketId) DO NOTHING";
                            
                            cmd.Parameters.AddWithValue("barcodeData", barcodeData);
                            cmd.Parameters.AddWithValue("ticketId", ticketId);
                            cmd.Parameters.AddWithValue("imagePath", imagePath ?? (object)DBNull.Value);
                            cmd.Parameters.AddWithValue("entryTime", timestamp);
                            
                            await cmd.ExecuteNonQueryAsync();
                            Console.WriteLine($"Cache: Memasukkan '{barcodeData}' ke database");
                            
                            // Remove from cache once successfully saved
                            lock (CacheLock)
                            {
                                DataCache.Remove(item);
                            }
                        }
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"Cache: Gagal menyimpan item ke database: {ex.Message}");
                    // Leave in cache if failed
                    break;
                }
            }
            
            lock (CacheLock)
            {
                if (DataCache.Count == 0)
                {
                    Console.WriteLine("Cache telah berhasil di-flush ke database");
                }
                else
                {
                    Console.WriteLine($"Cache: {DataCache.Count} item masih tersisa di cache");
                }
            }
        }

        private static async Task EnsureTableExists()
        {
            try
            {
                // Check and create Vehicles table
                await EnsureVehiclesTableExists();
                
                // Check and create ManualOperations table
                await EnsureManualOperationsTableExists();
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat memeriksa/membuat tabel: {ex.Message}");
                throw;
            }
        }
        
        private static async Task EnsureVehiclesTableExists()
        {
            try
            {
                using (var connection = new NpgsqlConnection(dbConnectionString))
                {
                    await connection.OpenAsync();
                    
                    using (var cmd = new NpgsqlCommand())
                    {
                        cmd.Connection = connection;
                        cmd.CommandText = @"
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = 'vehicles'
                            )";
                        
                        bool tableExists = (bool)await cmd.ExecuteScalarAsync();
                        
                        if (!tableExists)
                        {
                            Console.WriteLine("Tabel Vehicles tidak ditemukan. Membuat tabel baru...");
                            
                            // Buat tabel vehicle
                            cmd.CommandText = @"
                                CREATE TABLE vehicles (
                                    id SERIAL PRIMARY KEY,
                                    vehicle_id VARCHAR(50) NOT NULL,
                                    ticket_id VARCHAR(50) NOT NULL,
                                    image_path TEXT,
                                    entry_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                    exit_time TIMESTAMP,
                                    status VARCHAR(10) DEFAULT 'IN'
                                )";
                            
                            await cmd.ExecuteNonQueryAsync();
                            Console.WriteLine("Tabel Vehicles berhasil dibuat");
                        }
                        else
                        {
                            Console.WriteLine("Tabel Vehicles sudah ada");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat memeriksa/membuat tabel Vehicles: {ex.Message}");
                throw;
            }
        }
        
        private static async Task EnsureManualOperationsTableExists()
        {
            try
            {
                using (var connection = new NpgsqlConnection(dbConnectionString))
                {
                    await connection.OpenAsync();
                    
                    using (var cmd = new NpgsqlCommand())
                    {
                        cmd.Connection = connection;
                        cmd.CommandText = @"
                            SELECT EXISTS (
                                SELECT FROM information_schema.tables 
                                WHERE table_name = 'manual_operations'
                            )";
                        
                        bool tableExists = (bool)await cmd.ExecuteScalarAsync();
                        
                        if (!tableExists)
                        {
                            Console.WriteLine("Tabel ManualOperations tidak ditemukan. Membuat tabel baru...");
                            
                            // Buat tabel untuk operasi manual
                            cmd.CommandText = @"
                                CREATE TABLE manual_operations (
                                    id SERIAL PRIMARY KEY,
                                    vehicle_id VARCHAR(50) NOT NULL,
                                    ticket_id VARCHAR(50) NOT NULL,
                                    operation_type VARCHAR(20) NOT NULL,
                                    operation_time TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP,
                                    operator_name VARCHAR(50),
                                    notes TEXT
                                )";
                            
                            await cmd.ExecuteNonQueryAsync();
                            Console.WriteLine("Tabel ManualOperations berhasil dibuat");
                        }
                        else
                        {
                            Console.WriteLine("Tabel ManualOperations sudah ada");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat memeriksa/membuat tabel ManualOperations: {ex.Message}");
                throw;
            }
        }

        private static void CheckPrinterAvailability()
        {
            try
            {
                Console.WriteLine($"Memeriksa koneksi ke printer barcode di {PRINTER_IP}:{PRINTER_PORT}...");
                
                using (var ping = new Ping())
                {
                    var reply = ping.Send(PRINTER_IP, 1000);
                    if (reply.Status == IPStatus.Success)
                    {
                        Console.WriteLine($"Printer barcode dapat dijangkau (ping: {reply.RoundtripTime}ms)");
                        
                        // Try to connect to the printer port
                        try
                        {
                            using (var client = new TcpClient())
                            {
                                var result = client.BeginConnect(PRINTER_IP, PRINTER_PORT, null, null);
                                var success = result.AsyncWaitHandle.WaitOne(TimeSpan.FromSeconds(1));
                                if (success && client.Connected)
                                {
                                    isPrinterAvailable = true;
                                    Console.WriteLine("Printer barcode tersedia dan siap digunakan");
                                    client.EndConnect(result);
                                }
                                else
                                {
                                    Console.WriteLine($"Tidak dapat terhubung ke port printer {PRINTER_PORT}");
                                }
                            }
                        }
                        catch (Exception ex)
                        {
                            Console.WriteLine($"Error saat memeriksa koneksi ke printer: {ex.Message}");
                        }
                    }
                    else
                    {
                        Console.WriteLine($"Tidak dapat menjangkau printer barcode: {reply.Status}");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat memeriksa ketersediaan printer: {ex.Message}");
            }
            
            if (!isPrinterAvailable)
            {
                Console.WriteLine("\nPERINGATAN: Printer barcode tidak tersedia. Tiket tidak akan dicetak.");
            }
        }

        private static async Task PrintEntryTicket(string vehicleId, string ticketId)
        {
            // Tambahkan pengecekan interval waktu cetak
            var timeSinceLastPrint = DateTime.Now - _lastPrintTime;
            if (timeSinceLastPrint < _minimumPrintInterval)
            {
                Console.WriteLine($"[BLOCK] Mencegah pencetakan terlalu sering. Tunggu {(_minimumPrintInterval - timeSinceLastPrint).TotalSeconds:F1} detik lagi.");
                return;
            }

            // Cek apakah pencetakan dinonaktifkan
            if (!_printingEnabled)
            {
                Console.WriteLine("[BLOCK] Pencetakan dinonaktifkan. Gunakan perintah 'ENABLE_PRINT' untuk mengaktifkan.");
                return;
            }

            Console.WriteLine($"=== PRINT REQUEST STARTED for {vehicleId}, ticket {ticketId} ===");
            Console.WriteLine($"[DEBUG] PrintEntryTicket called for vehicleId: {vehicleId}, ticketId: {ticketId}");
            Console.WriteLine($"[DEBUG] USE_LOCAL_PRINTER: {USE_LOCAL_PRINTER}, defaultPrinterName: '{defaultPrinterName}', IsWindows: {OperatingSystem.IsWindows()}");
            
            bool printSuccess = false;
            
            try 
            {
                // Update time of last print attempt
                _lastPrintTime = DateTime.Now;

                // If Windows local printer is enabled and available, use ESC/POS
                if (USE_LOCAL_PRINTER && !string.IsNullOrEmpty(defaultPrinterName) && OperatingSystem.IsWindows())
                {
                    try
                    {
                        Console.WriteLine("[DEBUG] Using local Windows printer with ESC/POS");
                        PrintWithEscPos(vehicleId, ticketId);
                        printSuccess = true;
                        Console.WriteLine("[SUCCESS] ESC/POS printing completed successfully");
                        return;
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"[ERROR] ESC/POS printing failed: {ex.Message}");
                        // Continue to fallback methods
                    }
                }
                else 
                {
                    if (USE_LOCAL_PRINTER && string.IsNullOrEmpty(defaultPrinterName))
                        Console.WriteLine("[ERROR] Default printer name is empty - Check printer settings");
                }
                
                // Try fallback direct text printing
                try 
                {
                    if (!string.IsNullOrEmpty(defaultPrinterName) && OperatingSystem.IsWindows())
                    {
                        Console.WriteLine("[DEBUG] Attempting direct text printing fallback");
                        await DirectTextPrinting(vehicleId, ticketId);
                        printSuccess = true;
                        Console.WriteLine("[SUCCESS] Direct text printing completed successfully");
                        return;
                    }
                }
                catch (Exception ex)
                {
                    Console.WriteLine($"[ERROR] Direct text printing failed: {ex.Message}");
                }
                
                // Try network printer with ZPL if available
                if (isPrinterAvailable)
                {
                    try
                    {
                        Console.WriteLine($"[DEBUG] Using network printer at {PRINTER_IP}:{PRINTER_PORT}");
                        
                        // Format tanggal dan waktu untuk tiket
                        string dateTime = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                        string date = DateTime.Now.ToString("yyyy-MM-dd");
                        string time = DateTime.Now.ToString("HH:mm:ss");
                        
                        // Create ZPL commands for ZKing/Zebra printer
                        string zplCommand = $@"
^XA
^CF0,40
^FO50,50^FDParking Ticket^FS
^CF0,30
^FO50,100^FDTicket ID: {ticketId}^FS
^FO50,140^FDVehicle ID: {vehicleId}^FS
^FO50,180^FDDate: {date}^FS
^FO50,220^FDTime In: {time}^FS
^FO50,260^FDLocation: Main Parking^FS
^FO50,300^FDBase Rate: Rp 5,000^FS
^FO50,340^FDStatus: IN^FS

^FO50,390^GB500,3,3^FS

^FO150,410^BY3
^BCN,100,Y,N,N
^FD{ticketId}^FS

^FO150,530^FDScan to Exit^FS

^XZ";
                        
                        // Connect to the network printer and send the ZPL commands
                        using (var client = new TcpClient())
                        {
                            await client.ConnectAsync(PRINTER_IP, PRINTER_PORT);
                            
                            using (var stream = client.GetStream())
                            using (var writer = new StreamWriter(stream))
                            {
                                await writer.WriteAsync(zplCommand);
                                await writer.FlushAsync();
                            }
                            
                            Console.WriteLine("Tiket berhasil dicetak");
                            printSuccess = true;
                            return;
                        }
                    }
                    catch (Exception ex)
                    {
                        Console.WriteLine($"[ERROR] ZPL printing failed: {ex.Message}");
                        isPrinterAvailable = false; // Mark printer as unavailable after error
                    }
                }
                else
                {
                    Console.WriteLine("[WARNING] Network printer not available");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] PrintEntryTicket main exception: {ex.Message}");
            }
            
            // If we get here, no printing method succeeded - fall back to saving as file
            if (!printSuccess)
            {
                Console.WriteLine("[DEBUG] All printing methods failed. Saving ticket to file.");
                await WriteTicketToFileAsync(vehicleId, ticketId);
            }
            
            Console.WriteLine($"=== PRINT REQUEST COMPLETED for {vehicleId} ===");
        }
        
        private static void PrintWithEscPos(string vehicleId, string ticketId)
        {
            Console.WriteLine($"[DEBUG] PrintWithEscPos started for vehicleId: {vehicleId}, ticketId: {ticketId}");
            
            // Quick check if printer name is valid
            if (string.IsNullOrEmpty(defaultPrinterName))
            {
                Console.WriteLine("[ERROR] Default printer name is null or empty");
                throw new Exception("No default printer found");
            }
            
            try
            {
                Console.WriteLine($"[DEBUG] Using Windows printer: '{defaultPrinterName}'");

                IntPtr printerHandle = IntPtr.Zero;
                
                try
                {
                    // Open the printer
                    Console.WriteLine("[DEBUG] Attempting to open printer...");
                    if (!OpenPrinter(defaultPrinterName, out printerHandle, IntPtr.Zero))
                    {
                        int error = Marshal.GetLastWin32Error();
                        Console.WriteLine($"[ERROR] Cannot open printer. Win32 Error: {error}");
                        throw new Exception($"Cannot open printer. Win32 Error: {error}");
                    }
                    Console.WriteLine($"[DEBUG] Printer opened successfully. Handle: {printerHandle}");
                    
                    // Setup document info
                    DOCINFOA docInfo = new DOCINFOA();
                    docInfo.pDocName = "Barcode Print Job";
                    docInfo.pOutputFile = null;
                    docInfo.pDataType = "RAW";
                    
                    // Start a print job
                    Console.WriteLine("[DEBUG] Starting print job...");
                    int jobId = StartDocPrinter(printerHandle, 1, ref docInfo);
                    if (jobId == 0)
                    {
                        int error = Marshal.GetLastWin32Error();
                        Console.WriteLine($"[ERROR] StartDocPrinter failed. Win32 Error: {error}");
                        throw new Exception($"StartDocPrinter failed. Win32 Error: {error}");
                    }
                    Console.WriteLine($"[DEBUG] Print job started. Job ID: {jobId}");
                    
                    // Start a page
                    Console.WriteLine("[DEBUG] Starting page...");
                    if (!StartPagePrinter(printerHandle))
                    {
                        int error = Marshal.GetLastWin32Error();
                        Console.WriteLine($"[ERROR] StartPagePrinter failed. Win32 Error: {error}");
                        throw new Exception($"StartPagePrinter failed. Win32 Error: {error}");
                    }
                    Console.WriteLine("[DEBUG] Page started successfully");
                    
                    // Create ESC/POS commands
                    string timeStamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                    
                    Console.WriteLine("[DEBUG] Creating ESC/POS command sequence - SIMPLIFIED VERSION");
                    
                    // Simplified ESC/POS commands that are more broadly compatible
                    // Initialize printer
                    byte[] initPrinter = new byte[] { 0x1B, 0x40 };
                    
                    // Text formatting - normal size, center align
                    byte[] textFormat = new byte[] { 
                        0x1B, 0x21, 0x00,       // Normal text
                        0x1B, 0x61, 0x01        // Center align
                    };
                    
                    // Add header text
                    string headerText = $"PARKING TICKET\r\n\r\nID: {vehicleId}\r\nTicket: {ticketId}\r\nDate: {timeStamp}\r\n\r\n";
                    byte[] headerBytes = Encoding.ASCII.GetBytes(headerText);
                    
                    // Set text to double height and width for the barcode data
                    byte[] emphasizedOn = new byte[] { 0x1B, 0x21, 0x30 }; // Double width and height
                    
                    // Simple barcode representation (just text)
                    string barcodeAsText = $"*{ticketId}*\r\n";
                    byte[] barcodeTextBytes = Encoding.ASCII.GetBytes(barcodeAsText);
                    
                    // Reset text formatting
                    byte[] normalText = new byte[] { 0x1B, 0x21, 0x00 };
                    
                    // Footer
                    string footerText = "\r\nScan to exit\r\nThank you\r\n\r\n\r\n";
                    byte[] footerBytes = Encoding.ASCII.GetBytes(footerText);
                    
                    // Feed and cut
                    byte[] feedAndCut = new byte[] { 
                        0x1B, 0x64, 0x05,      // Feed 5 lines
                        0x1D, 0x56, 0x41, 0x00 // Cut paper
                    };
                    
                    // Calculate total size
                    int totalSize = 
                        initPrinter.Length + 
                        textFormat.Length + 
                        headerBytes.Length + 
                        emphasizedOn.Length + 
                        barcodeTextBytes.Length + 
                        normalText.Length + 
                        footerBytes.Length + 
                        feedAndCut.Length;
                    
                    // Combine all commands
                    byte[] allCommands = new byte[totalSize];
                    
                    int pos = 0;
                    Array.Copy(initPrinter, 0, allCommands, pos, initPrinter.Length);
                    pos += initPrinter.Length;
                    
                    Array.Copy(textFormat, 0, allCommands, pos, textFormat.Length);
                    pos += textFormat.Length;
                    
                    Array.Copy(headerBytes, 0, allCommands, pos, headerBytes.Length);
                    pos += headerBytes.Length;
                    
                    Array.Copy(emphasizedOn, 0, allCommands, pos, emphasizedOn.Length);
                    pos += emphasizedOn.Length;
                    
                    Array.Copy(barcodeTextBytes, 0, allCommands, pos, barcodeTextBytes.Length);
                    pos += barcodeTextBytes.Length;
                    
                    Array.Copy(normalText, 0, allCommands, pos, normalText.Length);
                    pos += normalText.Length;
                    
                    Array.Copy(footerBytes, 0, allCommands, pos, footerBytes.Length);
                    pos += footerBytes.Length;
                    
                    Array.Copy(feedAndCut, 0, allCommands, pos, feedAndCut.Length);
                    
                    Console.WriteLine($"[DEBUG] ESC/POS command sequence created. Total size: {allCommands.Length} bytes");
                    
                    // Allocate unmanaged memory and copy command bytes to it
                    IntPtr pUnmanagedBytes = Marshal.AllocCoTaskMem(allCommands.Length);
                    Console.WriteLine($"[DEBUG] Allocated unmanaged memory at {pUnmanagedBytes}");
                    
                    Marshal.Copy(allCommands, 0, pUnmanagedBytes, allCommands.Length);
                    Console.WriteLine("[DEBUG] Copied command bytes to unmanaged memory");
                    
                    // Send commands to printer
                    Console.WriteLine("[DEBUG] Sending data to printer...");
                    int bytesWritten = 0;
                    if (!WritePrinter(printerHandle, pUnmanagedBytes, allCommands.Length, out bytesWritten))
                    {
                        int error = Marshal.GetLastWin32Error();
                        Console.WriteLine($"[ERROR] WritePrinter failed. Win32 Error: {error}");
                        throw new Exception($"WritePrinter failed. Win32 Error: {error}");
                    }
                    Console.WriteLine($"[DEBUG] Data sent to printer. Bytes written: {bytesWritten}");
                    
                    // Free the unmanaged memory
                    Console.WriteLine("[DEBUG] Freeing unmanaged memory");
                    Marshal.FreeCoTaskMem(pUnmanagedBytes);
                    
                    // End the page and document
                    Console.WriteLine("[DEBUG] Ending page...");
                    if (!EndPagePrinter(printerHandle))
                    {
                        int error = Marshal.GetLastWin32Error();
                        Console.WriteLine($"[ERROR] EndPagePrinter failed. Win32 Error: {error}");
                        throw new Exception($"EndPagePrinter failed. Win32 Error: {error}");
                    }
                    
                    Console.WriteLine("[DEBUG] Ending document...");
                    if (!EndDocPrinter(printerHandle))
                    {
                        int error = Marshal.GetLastWin32Error();
                        Console.WriteLine($"[ERROR] EndDocPrinter failed. Win32 Error: {error}");
                        throw new Exception($"EndDocPrinter failed. Win32 Error: {error}");
                    }
                    
                    Console.WriteLine("[INFO] ESC/POS ticket printed successfully");
                }
                finally
                {
                    // Always close the printer handle
                    if (printerHandle != IntPtr.Zero)
                    {
                        Console.WriteLine("[DEBUG] Closing printer handle...");
                        ClosePrinter(printerHandle);
                        Console.WriteLine("[DEBUG] Printer handle closed");
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] PrintWithEscPos exception: {ex.Message}");
                Console.WriteLine($"[ERROR] Stack trace: {ex.StackTrace}");
                throw; // Rethrow to let the calling method handle it
            }
        }
        
        private static async Task DirectTextPrinting(string vehicleId, string ticketId)
        {
            Console.WriteLine("[DEBUG] Starting direct text printing...");
            
            try
            {
                string timeStamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                string ticketText = 
$@"
       PARKING TICKET

ID: {vehicleId}
Ticket: {ticketId}
Date: {timeStamp}

       *{ticketId}*

       Scan to exit
       Thank you

";
                
                // Use System.Drawing.Printing for simple text printing
                using (System.Diagnostics.Process process = new System.Diagnostics.Process())
                {
                    process.StartInfo.FileName = "notepad.exe";
                    process.StartInfo.CreateNoWindow = true;
                    process.StartInfo.UseShellExecute = false;
                    
                    // Create temporary file
                    string tempFile = Path.Combine(Path.GetTempPath(), $"Ticket_{Guid.NewGuid()}.txt");
                    await File.WriteAllTextAsync(tempFile, ticketText);
                    
                    process.StartInfo.Arguments = $"/p {tempFile}";
                    
                    Console.WriteLine($"[DEBUG] Printing with notepad /p to default printer: {tempFile}");
                    
                    process.Start();
                    await process.WaitForExitAsync();
                    
                    // Clean up temp file
                    try {
                        if (File.Exists(tempFile)) {
                            File.Delete(tempFile);
                        }
                    } catch {}
                    
                    Console.WriteLine("[DEBUG] Notepad print process completed");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] DirectTextPrinting exception: {ex.Message}");
                throw;
            }
        }
        
        private static async Task OpenEntryGate()
        {
            try
            {
                Console.WriteLine("Membuka gate masuk...");
                
                // Send command to Arduino to open gate
                if (serialPort != null && serialPort.IsOpen)
                {
                    serialPort.WriteLine(GATE_COMMAND_OPEN);
                    Console.WriteLine("Perintah buka gate terkirim ke Arduino");
                    
                    // Wait for gate timeout then close
                    await Task.Delay(GATE_TIMEOUT_MS);
                    
                    // Send close command
                    serialPort.WriteLine(GATE_COMMAND_CLOSE);
                    Console.WriteLine("Perintah tutup gate terkirim ke Arduino (timeout)");
                }
                else
                {
                    Console.WriteLine("Serial port tidak tersedia. Gate tidak dapat dibuka.");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat membuka gate: {ex.Message}");
            }
        }
        
        private static async Task CheckCameraAvailability()
        {
            try
            {
                Console.WriteLine($"Memeriksa koneksi ke kamera di {CAMERA_URL}...");
                
                using (var client = new HttpClient())
                {
                    // Add authentication for camera
                    var authString = $"{CAMERA_USERNAME}:{CAMERA_PASSWORD}";
                    var base64Auth = Convert.ToBase64String(Encoding.UTF8.GetBytes(authString));
                    client.DefaultRequestHeaders.Authorization = new System.Net.Http.Headers.AuthenticationHeaderValue("Basic", base64Auth);
                    
                    client.Timeout = TimeSpan.FromSeconds(5);
                    var response = await client.GetAsync(CAMERA_URL);
                    
                    if (response.IsSuccessStatusCode)
                    {
                        isCameraAvailable = true;
                        Console.WriteLine("Kamera tersedia dan siap digunakan");
                        
                        // Check if we got valid image data
                        var contentType = response.Content.Headers.ContentType?.MediaType;
                        if (contentType != null && contentType.StartsWith("image/"))
                        {
                            Console.WriteLine("Kamera mengembalikan gambar valid");
                        }
                        else
                        {
                            Console.WriteLine($"Peringatan: Kamera mengembalikan tipe konten tidak terduga: {contentType}");
                        }
                    }
                    else
                    {
                        Console.WriteLine($"Kamera tidak tersedia. Status: {response.StatusCode}");
                        if (response.StatusCode == System.Net.HttpStatusCode.Unauthorized)
                        {
                            Console.WriteLine("Autentikasi kamera gagal. Periksa username dan password.");
                        }
                    }
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat memeriksa ketersediaan kamera: {ex.Message}");
                isCameraAvailable = false;
            }
            
            if (!isCameraAvailable)
            {
                Console.WriteLine("\nPERINGATAN: Kamera tidak tersedia. Gambar kendaraan tidak akan diambil.");
            }
        }

        private static string GetDefaultPrinterName()
        {
            StringBuilder buffer = new StringBuilder(256);
            int size = buffer.Capacity;
            try
            {
                if (GetDefaultPrinter(buffer, ref size))
                {
                    string printerName = buffer.ToString();
                    Console.WriteLine($"[DEBUG] Found default printer: '{printerName}'");
                    return printerName;
                }
                else
                {
                    int errorCode = Marshal.GetLastWin32Error();
                    Console.WriteLine($"[ERROR] Failed to get default printer. Win32 Error: {errorCode}");
                    return string.Empty;
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Exception in GetDefaultPrinterName: {ex.Message}");
                return string.Empty;
            }
        }

        private static async Task WriteTicketToFileAsync(string vehicleId, string ticketId)
        {
            try
            {
                string ticketsFolder = Path.Combine(AppDomain.CurrentDomain.BaseDirectory, "Tickets");
                Directory.CreateDirectory(ticketsFolder); // Create if it doesn't exist
                
                string fileName = Path.Combine(ticketsFolder, $"Ticket_{vehicleId}_{ticketId}.txt");
                string timeStamp = DateTime.Now.ToString("yyyy-MM-dd HH:mm:ss");
                
                string ticketContent = 
$@"PARKING TICKET
==============
ID: {vehicleId}
Ticket: {ticketId}
Date: {timeStamp}
Status: IN
==============
";
                
                await File.WriteAllTextAsync(fileName, ticketContent);
                Console.WriteLine($"[INFO] Ticket saved to file: {fileName}");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Failed to save ticket to file: {ex.Message}");
            }
        }

        private static void UpdateConnectionString()
        {
            // Tambahkan parameter timeout dan retry untuk meningkatkan keberhasilan koneksi
            dbConnectionString = $"Host={SERVER_HOST};Port={DB_PORT};Database={DB_NAME};Username={DB_USER};Password={DB_PASSWORD};Timeout=15;CommandTimeout=30;Maximum Pool Size=20;Retry=3;";
            Console.WriteLine($"[DEBUG] Updated connection string: Host={SERVER_HOST};Port={DB_PORT};Database={DB_NAME};Username={DB_USER};Password=******;Timeout=15;CommandTimeout=30");
        }

        private static void AddToCache(string data)
        {
            lock (CacheLock)
            {
                DataCache.Add(data);
                Console.WriteLine($"Cache: {DataCache.Count} item dalam cache");
            }
        }

        private static async Task ProcessServerCommand(string command)
        {
            Console.WriteLine($"[INFO] Processing server command: {command}");
            
            try
            {
                // Normalize command by trimming and converting to lower case
                string normalizedCommand = command.Trim().ToLowerInvariant();
                
                // Add print control commands
                if (normalizedCommand == "disable_print" || normalizedCommand == "stop_print")
                {
                    _printingEnabled = false;
                    Console.WriteLine("[INFO] Printing has been disabled");
                    return;
                }
                else if (normalizedCommand == "enable_print" || normalizedCommand == "start_print")
                {
                    _printingEnabled = true;
                    Console.WriteLine("[INFO] Printing has been enabled");
                    return;
                }
                else if (normalizedCommand == "reset_printing")
                {
                    _printingEnabled = true;
                    _lastPrintTime = DateTime.MinValue;
                    Console.WriteLine("[INFO] Print system has been reset");
                    return;
                }
                
                if (normalizedCommand.Contains("gate") && normalizedCommand.Contains("open"))
                {
                    Console.WriteLine("[INFO] Executing open gate command");
                    await OpenEntryGate();
                }
                else if (normalizedCommand.Contains("gate") && normalizedCommand.Contains("close"))
                {
                    Console.WriteLine("[INFO] Executing close gate command");
                    await CloseEntryGate();
                }
                else if (normalizedCommand.Contains("print") || normalizedCommand.Contains("ticket"))
                {
                    // Extract ID if available
                    string vehicleId = "AUTO" + DateTime.Now.ToString("HHmmss");
                    
                    // Check if command contains an ID
                    var match = System.Text.RegularExpressions.Regex.Match(command, @"id[:\s=]+([a-z0-9]+)", 
                        System.Text.RegularExpressions.RegexOptions.IgnoreCase);
                    
                    if (match.Success && match.Groups.Count > 1)
                    {
                        vehicleId = match.Groups[1].Value;
                    }
                    
                    string ticketId = $"{DateTime.Now:yyyyMMdd_HHmmss}_{vehicleId}";
                    Console.WriteLine($"[INFO] Executing print ticket command for {vehicleId}");
                    await PrintEntryTicket(vehicleId, ticketId);
                }
                else if (normalizedCommand.Contains("status") || normalizedCommand.Contains("ping"))
                {
                    // Send status back through SignalR if connected
                    if (isSignalRConnected && hubConnection != null)
                    {
                        var statusInfo = new
                        {
                            deviceId = Environment.MachineName,
                            status = "online",
                            timestamp = DateTime.Now.ToString("o"),
                            databaseConnected = isDatabaseAvailable,
                            serverConnected = isServerAvailable,
                            cacheItems = DataCache.Count
                        };
                        
                        await hubConnection.InvokeAsync("DeviceStatus", statusInfo);
                        Console.WriteLine("[INFO] Sent status information to server");
                    }
                }
                else
                {
                    Console.WriteLine($"[WARNING] Unknown command: {command}");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Failed to process command: {ex.Message}");
            }
        }

        private static async Task CloseEntryGate()
        {
            try
            {
                Console.WriteLine("Menutup pintu gerbang...");
                
                // Send command to Arduino
                if (serialPort != null && serialPort.IsOpen)
                {
                    serialPort.WriteLine(GATE_COMMAND_CLOSE);
                    Console.WriteLine("Perintah tutup gerbang dikirim ke Arduino");
                }
                else
                {
                    Console.WriteLine("Serial port tidak tersedia. Tidak dapat mengirim perintah ke Arduino.");
                }
            }
            catch (Exception ex)
            {
                Console.WriteLine($"Error saat menutup gerbang: {ex.Message}");
            }
        }

        private static async Task ProcessButtonPress(string vehicleId, string ticketId)
        {
            // Validasi tambahan untuk memastikan ini adalah button press yang valid
            if ((!vehicleId.StartsWith("BTN") && !vehicleId.StartsWith("BUTTON:")) || string.IsNullOrEmpty(ticketId))
            {
                Console.WriteLine("[BLOCK] Invalid button press data detected. Ignoring.");
                return;
            }

            Console.WriteLine($"[INFO] Processing validated button press: {vehicleId}");
            
            // 1. Skip image capture since this is a manual entry
            
            // 2. Insert data to database
            try
            {
                await InsertIntoDatabase(vehicleId, ticketId, string.Empty);
                Console.WriteLine("[INFO] Vehicle data saved to database successfully");
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Database insert failed: {ex.Message}");
            }
            
            // 3. Send data to server with proper vehicle data format
            try
            {
                await SendDataToServer(vehicleId, ticketId, string.Empty);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Server send failed: {ex.Message}");
            }
            
            // 4. Print entry ticket
            try
            {
                Console.WriteLine("[IMPORTANT] Attempting to print ticket for button press...");
                await PrintEntryTicket(vehicleId, ticketId);
            }
            catch (Exception ex)
            {
                Console.WriteLine($"[ERROR] Printing failed: {ex.Message}");
                Console.WriteLine($"[ERROR] Stack trace: {ex.StackTrace}");
                
                // Try one last direct notepad printing as emergency fallback
                try {
                    Console.WriteLine("[IMPORTANT] Trying emergency notepad printing...");
                    await DirectTextPrinting(vehicleId, ticketId);
                }
                catch (Exception printEx) {
                    Console.WriteLine($"[ERROR] Emergency printing also failed: {printEx.Message}");
                    
                    // Additional emergency fallback - write to file
                    try {
                        await WriteTicketToFileAsync(vehicleId, ticketId);
                        Console.WriteLine("[INFO] Wrote ticket data to file as last resort");
                    }
                    catch (Exception fileEx) {
                        Console.WriteLine($"[ERROR] All printing attempts failed: {fileEx.Message}");
                    }
                }
            }
            
            // 5. Open gate (already done by Arduino via relay)
            Console.WriteLine($"[INFO] Processed button press for: {vehicleId}");
        }
    }
}