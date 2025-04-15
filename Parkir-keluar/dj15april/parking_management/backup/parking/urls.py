from django.urls import path
from . import views
from . import api

app_name = 'parking'

urlpatterns = [
    path('login/', views.user_login, name='login'),
    path('logout/', views.user_logout, name='logout'),
    path('dashboard/', views.dashboard, name='dashboard'),
    path('vehicles/', views.vehicle_list, name='vehicle_list'),
    path('vehicles/add/', views.vehicle_add, name='vehicle_add'),
    path('spots/', views.parking_spot_list, name='parking_spot_list'),
    path('spots/add/', views.parking_spot_add, name='parking_spot_add'),
    path('check-in/', views.check_in, name='check_in'),
    path('check-out/<int:session_id>/', views.check_out, name='check_out'),
    path('sessions/', views.session_list, name='session_list'),
    path('test-captureticket/', views.test_captureticket, name='test_captureticket'),
    path('server-tickets/', views.view_captureticket, name='view_captureticket'),
    path('test-connection/', views.test_connection, name='test_connection'),
    path('shifts/', views.shift_list, name='shift_list'),
    path('shifts/<int:shift_id>/', views.shift_report, name='shift_report'),
    path('shifts/<int:shift_id>/export/', views.export_shift_report, name='export_shift_report'),
    path('start-shift/', views.start_shift, name='start_shift'),
    path('end-shift/', views.end_shift, name='end_shift'),
    
    # API endpoints
    path('api/gate/capture-tickets/', api.capture_tickets, name='api_capture_tickets'),
    path('api/gate/exit/tickets/', api.exit_tickets, name='api_exit_tickets'),
    path('api/gate/exit/process/', api.process_exit, name='api_process_exit'),
    path('api/dashboard/', api.dashboard, name='api_dashboard'),
    
    # Real-time data endpoints
    path('api/active-tickets/', views.get_active_tickets, name='active_tickets'),
    path('api/process-exit/', views.process_exit, name='process_exit'),
    path('api/check-connection/', views.check_connection, name='check_connection'),
    path('api/vehicle-statistics/', views.get_vehicle_statistics, name='vehicle_statistics'),
    path('api/revenue-report/', views.get_revenue_report, name='revenue_report'),
    path('api/parking-capacity/', views.get_parking_capacity, name='parking_capacity'),
    path('api/peak-hours/', views.get_peak_hours, name='peak_hours'),
] 