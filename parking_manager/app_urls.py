from django.urls import path
from . import views

urlpatterns = [
    path('', views.dashboard, name='dashboard'),
    path('exit/', views.vehicle_exit, name='vehicle_exit'),
    path('exit/<str:ticket_id>/', views.vehicle_exit, name='vehicle_exit_detail'),
    path('payment/<str:ticket_id>/', views.payment_process, name='payment_process'),
    path('ticket/<str:ticket_id>/', views.ticket_detail, name='ticket_detail'),
    path('search/', views.search_ticket, name='search_ticket'),
    path('reprint-receipt/<int:payment_id>/', views.reprint_receipt, name='reprint_receipt'),
    
    # Voucher management URLs
    path('vouchers/', views.voucher_list, name='voucher_list'),
    path('vouchers/create/', views.voucher_create, name='voucher_create'),
    path('vouchers/<int:voucher_id>/edit/', views.voucher_edit, name='voucher_edit'),
    path('vouchers/<int:voucher_id>/delete/', views.voucher_delete, name='voucher_delete'),
    path('vouchers/<int:voucher_id>/toggle/', views.voucher_toggle, name='voucher_toggle'),
    
    # Financial report URLs
    path('reports/financial/', views.financial_report, name='financial_report'),
    path('reports/export/', views.export_report, name='export_report'),
    path('reports/monthly/<int:year>/<int:month>/', views.monthly_report, name='monthly_report'),
    path('reports/transactions/', views.transaction_list, name='transaction_list'),
    path('reports/transactions/<int:transaction_id>/', views.transaction_detail, name='transaction_detail'),
] 