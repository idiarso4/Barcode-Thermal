from django.db import models
from django.utils import timezone
from django.contrib.auth.models import User

class Shift(models.Model):
    operator = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField(default=timezone.now)
    end_time = models.DateTimeField(null=True, blank=True)
    is_active = models.BooleanField(default=True)
    total_vehicles = models.IntegerField(default=0)
    total_revenue = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    notes = models.TextField(blank=True, null=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.operator.username}'s shift on {self.start_time.strftime('%Y-%m-%d %H:%M')}"
    
    def end_shift(self):
        if self.is_active:
            self.end_time = timezone.now()
            self.is_active = False
            # Calculate totals
            from_time = self.start_time
            to_time = self.end_time
            sessions = ParkingSession.objects.filter(
                check_in_time__gte=from_time,
                check_in_time__lte=to_time,
                created_by=self.operator
            )
            self.total_vehicles = sessions.count()
            self.total_revenue = sum(s.fee or 0 for s in sessions)
            self.save()

class Vehicle(models.Model):
    VEHICLE_TYPES = [
        ('CAR', 'Car'),
        ('MOTORCYCLE', 'Motorcycle'),
        ('TRUCK', 'Truck'),
    ]
    
    license_plate = models.CharField(max_length=20, unique=True)
    vehicle_type = models.CharField(max_length=20, choices=VEHICLE_TYPES)
    owner_name = models.CharField(max_length=100)
    owner_contact = models.CharField(max_length=20)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.license_plate} - {self.vehicle_type}"

class ParkingSpot(models.Model):
    SPOT_TYPES = [
        ('CAR', 'Car'),
        ('MOTORCYCLE', 'Motorcycle'),
        ('TRUCK', 'Truck'),
    ]
    
    STATUS_CHOICES = [
        ('AVAILABLE', 'Available'),
        ('OCCUPIED', 'Occupied'),
        ('RESERVED', 'Reserved'),
        ('MAINTENANCE', 'Under Maintenance'),
    ]
    
    spot_number = models.CharField(max_length=10, unique=True)
    spot_type = models.CharField(max_length=20, choices=SPOT_TYPES)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='AVAILABLE')
    floor = models.IntegerField(default=1)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Spot {self.spot_number} ({self.get_status_display()})"

class ParkingSession(models.Model):
    vehicle = models.ForeignKey(Vehicle, on_delete=models.CASCADE)
    parking_spot = models.ForeignKey(ParkingSpot, on_delete=models.CASCADE)
    check_in_time = models.DateTimeField(default=timezone.now)
    check_out_time = models.DateTimeField(null=True, blank=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='created_sessions')
    checked_out_by = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, related_name='checked_out_sessions')
    shift = models.ForeignKey(Shift, on_delete=models.SET_NULL, null=True)

    def __str__(self):
        return f"{self.vehicle.license_plate} at {self.parking_spot.spot_number}"
    
    def calculate_fee(self):
        if not self.check_out_time:
            duration = timezone.now() - self.check_in_time
        else:
            duration = self.check_out_time - self.check_in_time
        
        hours = duration.total_seconds() / 3600
        # Base rate: Rp 5000 per hour
        base_rate = 5000
        
        if self.vehicle.vehicle_type == 'CAR':
            rate = base_rate
        elif self.vehicle.vehicle_type == 'MOTORCYCLE':
            rate = base_rate * 0.5  # 50% of base rate
        else:  # TRUCK
            rate = base_rate * 2  # 200% of base rate
        
        return round(hours * rate, 2)
    
    def check_out(self, operator=None):
        if self.is_active:
            self.check_out_time = timezone.now()
            self.fee = self.calculate_fee()
            self.is_active = False
            self.checked_out_by = operator
            self.parking_spot.status = 'AVAILABLE'
            self.parking_spot.save()
            self.save()

class Captureticket(models.Model):
    id = models.AutoField(primary_key=True)
    plat_no = models.CharField(max_length=50)  # Increased length to 50
    date_masuk = models.DateTimeField()
    date_keluar = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=50)
    biaya = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    timestamp = models.DateTimeField(auto_now_add=True)
    vehicle_type = models.CharField(max_length=50, null=True, blank=True)

    class Meta:
        managed = False
        db_table = 'captureticket'
        ordering = ['-date_masuk']

    def __str__(self):
        return f"{self.plat_no} - {self.date_masuk}"
