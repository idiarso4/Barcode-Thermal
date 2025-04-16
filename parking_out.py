import tkinter as tk
from tkinter import ttk, messagebox
import psycopg2
from datetime import datetime
import configparser
import hashlib
import json
import os

class ParkingOutSystem:
    def __init__(self):
        self.window = tk.Tk()
        self.window.title("Parking Out System - RSI BNA")
        self.window.geometry("800x600")
        
        # Load config
        self.config = self.load_config()
        
        # Setup database
        self.setup_database()
        
        # Setup UI
        self.setup_login_ui()
        
        # State variables
        self.current_user = None
        self.current_page = 'login'
        
    def load_config(self):
        """Load konfigurasi dari file config.ini"""
        try:
            config = configparser.ConfigParser()
            config.read('config.ini')
            return config
        except Exception as e:
            messagebox.showerror("Error", f"Gagal membaca konfigurasi: {str(e)}")
            return None
            
    def setup_database(self):
        """Setup koneksi ke database"""
        try:
            db_config = self.config['database']
            self.conn = psycopg2.connect(
                dbname=db_config['dbname'],
                user=db_config['user'],
                password=db_config['password'],
                host=db_config['host']
            )
            print("✅ Database terkoneksi")
        except Exception as e:
            messagebox.showerror("Error", f"Gagal koneksi ke database: {str(e)}")
            self.conn = None
            
    def setup_login_ui(self):
        """Setup tampilan login"""
        # Clear window
        for widget in self.window.winfo_children():
            widget.destroy()
            
        # Header
        header = ttk.Label(
            self.window, 
            text="SISTEM PARKIR RSI BNA", 
            font=("Arial", 20, "bold")
        )
        header.pack(pady=20)
        
        # Login frame
        login_frame = ttk.LabelFrame(self.window, text="Login")
        login_frame.pack(padx=20, pady=20)
        
        # Username
        ttk.Label(login_frame, text="Username:").grid(row=0, column=0, padx=5, pady=5)
        self.username_entry = ttk.Entry(login_frame)
        self.username_entry.grid(row=0, column=1, padx=5, pady=5)
        
        # Password
        ttk.Label(login_frame, text="Password:").grid(row=1, column=0, padx=5, pady=5)
        self.password_entry = ttk.Entry(login_frame, show="*")
        self.password_entry.grid(row=1, column=1, padx=5, pady=5)
        
        # Login button
        login_btn = ttk.Button(
            login_frame, 
            text="Login",
            command=self.handle_login
        )
        login_btn.grid(row=2, column=0, columnspan=2, pady=20)
        
        # Bind Enter key
        self.window.bind('<Return>', lambda e: self.handle_login())
        
    def setup_main_ui(self):
        """Setup tampilan utama setelah login"""
        # Clear window
        for widget in self.window.winfo_children():
            widget.destroy()
            
        # Header with user info
        header_frame = ttk.Frame(self.window)
        header_frame.pack(fill='x', padx=20, pady=10)
        
        header = ttk.Label(
            header_frame,
            text=f"SISTEM PARKIR RSI BNA - {self.current_user}",
            font=("Arial", 16, "bold")
        )
        header.pack(side='left')
        
        logout_btn = ttk.Button(
            header_frame,
            text="Logout",
            command=self.handle_logout
        )
        logout_btn.pack(side='right')
        
        # Search frame
        search_frame = ttk.LabelFrame(self.window, text="Cari Tiket")
        search_frame.pack(fill='x', padx=20, pady=10)
        
        ttk.Label(search_frame, text="Nomor Tiket:").grid(row=0, column=0, padx=5, pady=5)
        self.ticket_entry = ttk.Entry(search_frame)
        self.ticket_entry.grid(row=0, column=1, padx=5, pady=5)
        
        search_btn = ttk.Button(
            search_frame,
            text="Cari",
            command=self.search_ticket
        )
        search_btn.grid(row=0, column=2, padx=5, pady=5)
        
        # Ticket info frame
        self.ticket_frame = ttk.LabelFrame(self.window, text="Informasi Tiket")
        self.ticket_frame.pack(fill='both', expand=True, padx=20, pady=10)
        
        # Bind Enter key to search
        self.ticket_entry.bind('<Return>', lambda e: self.search_ticket())
        
    def handle_login(self):
        """Handle login process"""
        username = self.username_entry.get()
        password = self.password_entry.get()
        
        if not username or not password:
            messagebox.showerror("Error", "Username dan password harus diisi")
            return
            
        try:
            cursor = self.conn.cursor()
            
            # Hash password
            hashed_password = hashlib.sha256(password.encode()).hexdigest()
            
            # Check credentials
            cursor.execute("""
                SELECT id, username, role 
                FROM users 
                WHERE username = %s AND password = %s
            """, (username, hashed_password))
            
            user = cursor.fetchone()
            cursor.close()
            
            if user:
                self.current_user = username
                messagebox.showinfo("Success", "Login berhasil!")
                self.setup_main_ui()
            else:
                messagebox.showerror("Error", "Username atau password salah")
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal login: {str(e)}")
            
    def handle_logout(self):
        """Handle logout process"""
        self.current_user = None
        self.setup_login_ui()
        
    def search_ticket(self):
        """Search for parking ticket"""
        ticket_number = self.ticket_entry.get()
        
        if not ticket_number:
            messagebox.showerror("Error", "Nomor tiket harus diisi")
            return
            
        try:
            cursor = self.conn.cursor()
            
            # Get ticket info
            cursor.execute("""
                SELECT ticket_id, entry_time, exit_time, status, 
                       vehicle_type, license_plate, fee
                FROM tickets 
                WHERE ticket_id = %s
            """, (ticket_number,))
            
            ticket = cursor.fetchone()
            cursor.close()
            
            if ticket:
                self.display_ticket_info(ticket)
            else:
                messagebox.showerror("Error", "Tiket tidak ditemukan")
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mencari tiket: {str(e)}")
            
    def display_ticket_info(self, ticket):
        """Display ticket information"""
        # Clear previous info
        for widget in self.ticket_frame.winfo_children():
            widget.destroy()
            
        # Unpack ticket data
        ticket_id, entry_time, exit_time, status, vehicle_type, license_plate, fee = ticket
        
        # Calculate duration and fee
        if not exit_time:
            exit_time = datetime.now()
            duration = exit_time - entry_time
            hours = duration.total_seconds() / 3600
            fee = self.calculate_fee(hours, vehicle_type)
            
        # Display info
        info = {
            "Nomor Tiket": ticket_id,
            "Waktu Masuk": entry_time.strftime("%d/%m/%Y %H:%M:%S"),
            "Durasi": f"{int(hours)} jam {int((hours % 1) * 60)} menit",
            "Status": status,
            "Jenis Kendaraan": vehicle_type or "Belum diisi",
            "Plat Nomor": license_plate or "Belum diisi",
            "Biaya": f"Rp {fee:,}"
        }
        
        row = 0
        for label, value in info.items():
            ttk.Label(self.ticket_frame, text=f"{label}:").grid(
                row=row, column=0, padx=5, pady=5, sticky='e'
            )
            ttk.Label(self.ticket_frame, text=value).grid(
                row=row, column=1, padx=5, pady=5, sticky='w'
            )
            row += 1
            
        # Add action buttons
        button_frame = ttk.Frame(self.ticket_frame)
        button_frame.grid(row=row, column=0, columnspan=2, pady=20)
        
        if status == 'ACTIVE':
            process_btn = ttk.Button(
                button_frame,
                text="Proses Keluar",
                command=lambda: self.process_exit(ticket_id)
            )
            process_btn.pack(side='left', padx=5)
            
        print_btn = ttk.Button(
            button_frame,
            text="Cetak Struk",
            command=lambda: self.print_receipt(ticket_id)
        )
        print_btn.pack(side='left', padx=5)
        
    def calculate_fee(self, hours, vehicle_type):
        """Calculate parking fee"""
        # Get fee configuration
        base_fee = int(self.config['fees']['base_fee'])
        hourly_fee = int(self.config['fees']['hourly_fee'])
        
        # Calculate total hours (round up)
        total_hours = int(hours + 0.5)
        
        # Calculate fee
        if total_hours <= 1:
            return base_fee
        else:
            return base_fee + (total_hours - 1) * hourly_fee
            
    def process_exit(self, ticket_id):
        """Process vehicle exit"""
        try:
            cursor = self.conn.cursor()
            
            # Update ticket
            cursor.execute("""
                UPDATE tickets 
                SET exit_time = NOW(),
                    status = 'COMPLETED',
                    updated_at = NOW()
                WHERE ticket_id = %s
            """, (ticket_id,))
            
            self.conn.commit()
            cursor.close()
            
            messagebox.showinfo("Success", "Kendaraan berhasil keluar")
            self.search_ticket()  # Refresh display
            
        except Exception as e:
            messagebox.showerror("Error", f"Gagal memproses keluar: {str(e)}")
            
    def print_receipt(self, ticket_id):
        """Print parking receipt"""
        try:
            cursor = self.conn.cursor()
            
            # Get ticket info
            cursor.execute("""
                SELECT ticket_id, entry_time, exit_time, status,
                       vehicle_type, license_plate, fee
                FROM tickets 
                WHERE ticket_id = %s
            """, (ticket_id,))
            
            ticket = cursor.fetchone()
            cursor.close()
            
            if ticket:
                # TODO: Implement receipt printing
                messagebox.showinfo("Info", "Fitur cetak struk dalam pengembangan")
            else:
                messagebox.showerror("Error", "Tiket tidak ditemukan")
                
        except Exception as e:
            messagebox.showerror("Error", f"Gagal mencetak struk: {str(e)}")
            
    def run(self):
        """Run the application"""
        self.window.mainloop()

if __name__ == "__main__":
    app = ParkingOutSystem()
    app.run() 