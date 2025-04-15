from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError

class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('CAR', 'Mobil'),
        ('MOTORCYCLE', 'Motor'),
        ('TRUCK', 'Truk'),
    ]
    
    license_plate = models.CharField(max_length=20, unique=True, verbose_name='Plat Nomor')
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES, default='CAR', verbose_name='Jenis Kendaraan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.license_plate} ({self.get_vehicle_type_display()})"
    
    class Meta:
        verbose_name = 'Kendaraan'
        verbose_name_plural = 'Kendaraan'

class Membership(models.Model):
    MEMBERSHIP_TYPES = [
        ('REGULAR', 'Regular'),
        ('SILVER', 'Silver'),
        ('GOLD', 'Gold'),
        ('PLATINUM', 'Platinum'),
    ]
    
    vehicle = models.OneToOneField(Vehicle, on_delete=models.CASCADE, verbose_name='Kendaraan')
    membership_type = models.CharField(max_length=20, choices=MEMBERSHIP_TYPES, default='REGULAR', verbose_name='Tipe Member')
    valid_until = models.DateTimeField(verbose_name='Berlaku Sampai')
    is_active = models.BooleanField(default=True, verbose_name='Status Aktif')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.vehicle.license_plate} - {self.get_membership_type_display()}"
    
    def is_valid(self):
        return self.is_active and self.valid_until > timezone.now()
    
    def get_discount_percentage(self):
        if not self.is_valid():
            return 0
        
        discounts = {
            'REGULAR': 0,
            'SILVER': 10,  # 10% discount
            'GOLD': 20,    # 20% discount
            'PLATINUM': 30 # 30% discount
        }
        return discounts.get(self.membership_type, 0)
    
    class Meta:
        verbose_name = 'Membership'
        verbose_name_plural = 'Memberships'

class ParkingTicket(models.Model):
    STATUS_CHOICES = [
        ('ACTIVE', 'Aktif'),
        ('COMPLETED', 'Selesai'),
        ('CANCELLED', 'Dibatalkan'),
    ]
    
    ticket_id = models.CharField(max_length=50, unique=True, verbose_name='ID Tiket')
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE, verbose_name='Kendaraan')
    entry_time = models.DateTimeField(default=timezone.now, verbose_name='Waktu Masuk')
    exit_time = models.DateTimeField(null=True, blank=True, verbose_name='Waktu Keluar')
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Biaya')
    is_paid = models.BooleanField(default=False, verbose_name='Sudah Dibayar')
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='ACTIVE', verbose_name='Status')
    barcode = models.CharField(max_length=100, unique=True, verbose_name='Barcode')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Operator')
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Tiket {self.ticket_id} - {self.vehicle.license_plate}"
    
    def calculate_duration(self):
        if self.exit_time:
            return self.exit_time - self.entry_time
        return timezone.now() - self.entry_time
    
    def calculate_fee(self):
        duration = self.calculate_duration()
        hours = duration.total_seconds() / 3600
        base_fee = 5000  # Biaya dasar
        hourly_fee = 2000  # Biaya per jam
        
        if self.vehicle.vehicle_type == 'MOTORCYCLE':
            base_fee = 2000
            hourly_fee = 1000
        elif self.vehicle.vehicle_type == 'TRUCK':
            base_fee = 10000
            hourly_fee = 5000
        
        total_fee = base_fee + (hourly_fee * round(hours))
        
        # Apply membership discount if available
        try:
            membership = self.vehicle.membership
            if membership.is_valid():
                discount = membership.get_discount_percentage()
                total_fee = total_fee * (100 - discount) / 100
        except Membership.DoesNotExist:
            pass
        
        return total_fee
    
    class Meta:
        verbose_name = 'Tiket Parkir'
        verbose_name_plural = 'Tiket Parkir'

class ParkingLog(models.Model):
    LOG_TYPES = [
        ('ENTRY', 'Masuk'),
        ('EXIT', 'Keluar'),
        ('PAYMENT', 'Pembayaran'),
        ('CANCEL', 'Pembatalan'),
    ]
    
    ticket = models.ForeignKey(ParkingTicket, on_delete=models.CASCADE, verbose_name='Tiket')
    log_type = models.CharField(max_length=20, choices=LOG_TYPES, verbose_name='Jenis Log')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Waktu')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Operator')
    details = models.TextField(blank=True, null=True, verbose_name='Detail')
    
    def __str__(self):
        return f"{self.get_log_type_display()} - {self.ticket.ticket_id} ({self.timestamp})"
    
    class Meta:
        verbose_name = 'Log Parkir'
        verbose_name_plural = 'Log Parkir'

class Voucher(models.Model):
    VOUCHER_TYPES = [
        ('FIXED', 'Potongan Tetap'),
        ('PERCENTAGE', 'Potongan Persentase'),
    ]
    
    code = models.CharField(max_length=20, unique=True, verbose_name='Kode Voucher')
    description = models.CharField(max_length=200, verbose_name='Deskripsi')
    voucher_type = models.CharField(max_length=20, choices=VOUCHER_TYPES, verbose_name='Tipe Voucher')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Nilai Potongan')
    max_usage = models.IntegerField(default=1, verbose_name='Maksimal Penggunaan')
    used_count = models.IntegerField(default=0, verbose_name='Jumlah Penggunaan')
    valid_from = models.DateTimeField(verbose_name='Berlaku Dari')
    valid_until = models.DateTimeField(verbose_name='Berlaku Sampai')
    is_active = models.BooleanField(default=True, verbose_name='Status Aktif')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.code} - {self.get_voucher_type_display()}"
    
    def is_valid(self):
        now = timezone.now()
        return (
            self.is_active and
            self.valid_from <= now <= self.valid_until and
            self.used_count < self.max_usage
        )
    
    def calculate_discount(self, base_amount):
        """Menghitung potongan voucher"""
        if not self.is_valid():
            return 0
            
        if self.voucher_type == 'FIXED':
            return min(self.amount, base_amount)  # Tidak bisa lebih dari jumlah bayar
        else:  # PERCENTAGE
            return (base_amount * self.amount / 100)
    
    def use_voucher(self):
        """Mencatat penggunaan voucher"""
        if self.is_valid():
            self.used_count += 1
            self.save()
            return True
        return False
    
    class Meta:
        verbose_name = 'Voucher'
        verbose_name_plural = 'Voucher'

class VoucherUsage(models.Model):
    voucher = models.ForeignKey(Voucher, on_delete=models.CASCADE, verbose_name='Voucher')
    payment = models.ForeignKey(PaymentTransaction, on_delete=models.CASCADE, verbose_name='Pembayaran')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Nilai Potongan')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.voucher.code} - {self.payment.transaction_id}"
    
    class Meta:
        verbose_name = 'Penggunaan Voucher'
        verbose_name_plural = 'Penggunaan Voucher'

class PaymentTransaction(models.Model):
    PAYMENT_METHODS = [
        ('CASH', 'Tunai'),
        ('CARD', 'Kartu'),
        ('EWALLET', 'E-Wallet'),
    ]
    
    ticket = models.ForeignKey(ParkingTicket, on_delete=models.CASCADE, verbose_name='Tiket')
    amount = models.DecimalField(max_digits=10, decimal_places=2, verbose_name='Jumlah')
    payment_method = models.CharField(max_length=20, choices=PAYMENT_METHODS, default='CASH', verbose_name='Metode Pembayaran')
    transaction_id = models.CharField(max_length=100, unique=True, verbose_name='ID Transaksi')
    operator = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, verbose_name='Operator')
    timestamp = models.DateTimeField(auto_now_add=True, verbose_name='Waktu')
    notes = models.TextField(blank=True, null=True, verbose_name='Catatan')
    change_amount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Kembalian')
    receipt_printed = models.BooleanField(default=False, verbose_name='Struk Dicetak')
    voucher = models.ForeignKey(Voucher, null=True, blank=True, on_delete=models.SET_NULL, verbose_name='Voucher')
    voucher_discount = models.DecimalField(max_digits=10, decimal_places=2, default=0, verbose_name='Potongan Voucher')
    
    def __str__(self):
        return f"Pembayaran {self.transaction_id} - {self.ticket.ticket_id}"
    
    def clean(self):
        if self.amount < self.ticket.calculate_fee():
            raise ValidationError('Jumlah pembayaran kurang dari tarif yang ditetapkan')
    
    def calculate_change(self):
        """Menghitung kembalian"""
        return self.amount - self.ticket.calculate_fee()
    
    def calculate_total(self):
        """Menghitung total pembayaran setelah diskon"""
        total = self.ticket.calculate_fee()
        
        # Apply voucher discount if available
        if self.voucher and self.voucher.is_valid():
            self.voucher_discount = self.voucher.calculate_discount(total)
            total -= self.voucher_discount
            
        return total
    
    def generate_receipt_data(self):
        """Generate data untuk mencetak struk"""
        return {
            'transaction_id': self.transaction_id,
            'ticket_id': self.ticket.ticket_id,
            'datetime': self.timestamp.strftime('%d/%m/%Y %H:%M:%S'),
            'vehicle': self.ticket.vehicle.license_plate,
            'vehicle_type': self.ticket.vehicle.get_vehicle_type_display(),
            'entry_time': self.ticket.entry_time.strftime('%d/%m/%Y %H:%M:%S'),
            'duration': str(self.ticket.calculate_duration()).split('.')[0],
            'fee': self.ticket.fee,
            'amount_paid': self.amount,
            'change': self.change_amount,
            'payment_method': self.get_payment_method_display(),
            'operator': self.operator.get_full_name() if self.operator else 'System',
            'notes': self.notes
        }
    
    def save(self, *args, **kwargs):
        if not self.pk:  # Only on creation
            self.change_amount = self.calculate_change()
            
            # Process voucher if available
            if self.voucher:
                self.voucher.use_voucher()
                VoucherUsage.objects.create(
                    voucher=self.voucher,
                    payment=self,
                    amount=self.voucher_discount
                )
                
        super().save(*args, **kwargs)
    
    class Meta:
        verbose_name = 'Transaksi Pembayaran'
        verbose_name_plural = 'Transaksi Pembayaran' 