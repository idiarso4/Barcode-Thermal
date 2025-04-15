from django.contrib import admin
from .models import Vehicle, ParkingSpot, ParkingSession

@admin.register(Vehicle)
class VehicleAdmin(admin.ModelAdmin):
    list_display = ('license_plate', 'vehicle_type', 'owner_name', 'owner_contact', 'created_at')
    search_fields = ('license_plate', 'owner_name')
    list_filter = ('vehicle_type',)

@admin.register(ParkingSpot)
class ParkingSpotAdmin(admin.ModelAdmin):
    list_display = ('spot_number', 'spot_type', 'status', 'floor', 'created_at')
    search_fields = ('spot_number',)
    list_filter = ('spot_type', 'status', 'floor')

@admin.register(ParkingSession)
class ParkingSessionAdmin(admin.ModelAdmin):
    list_display = ('vehicle', 'parking_spot', 'check_in_time', 'check_out_time', 'fee', 'is_active')
    search_fields = ('vehicle__license_plate', 'parking_spot__spot_number')
    list_filter = ('is_active', 'check_in_time')
