from django.db import models
from django.utils import timezone

class ParkingTicket(models.Model):
    ticket_id = models.CharField(max_length=50, unique=True)
    entry_time = models.DateTimeField(default=timezone.now)
    exit_time = models.DateTimeField(null=True, blank=True)
    fee = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    is_paid = models.BooleanField(default=False)
    vehicle_type = models.CharField(max_length=20, default='car')
    status = models.CharField(max_length=20, default='active')
    
    def __str__(self):
        return f"Ticket {self.ticket_id} ({self.status})"

class ExitLog(models.Model):
    ticket = models.ForeignKey(ParkingTicket, on_delete=models.CASCADE)
    exit_time = models.DateTimeField(auto_now_add=True)
    processed_by = models.CharField(max_length=50)
    gate_number = models.IntegerField(default=1)
    
    def __str__(self):
        return f"Exit log for {self.ticket.ticket_id} at {self.exit_time}" 