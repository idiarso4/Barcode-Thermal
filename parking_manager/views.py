from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q, Sum, Count, Avg
from django.db.models.functions import TruncDate, TruncMonth
from .models import Vehicle, ParkingTicket, ParkingLog, PaymentTransaction, Voucher
from .forms import VehicleForm, ParkingTicketForm, PaymentForm, VoucherForm
import uuid
from django.core.exceptions import ValidationError
from datetime import timedelta, datetime
import json
from django.http import HttpResponse
import xlsxwriter
from io import BytesIO

@login_required
def dashboard(request):
    active_tickets = ParkingTicket.objects.filter(status='ACTIVE').order_by('-entry_time')
    recent_logs = ParkingLog.objects.all().order_by('-timestamp')[:10]
    context = {
        'active_tickets': active_tickets,
        'recent_logs': recent_logs,
        'total_active': active_tickets.count(),
    }
    return render(request, 'parking_manager/dashboard.html', context)

@login_required
def vehicle_entry(request):
    if request.method == 'POST':
        vehicle_form = VehicleForm(request.POST)
        if vehicle_form.is_valid():
            vehicle = vehicle_form.save()
            
            # Generate unique ticket ID and barcode
            ticket_id = f"PKR{timezone.now().strftime('%Y%m%d%H%M%S')}"
            barcode = str(uuid.uuid4())
            
            # Create parking ticket
            ticket = ParkingTicket.objects.create(
                ticket_id=ticket_id,
                vehicle=vehicle,
                barcode=barcode,
                operator=request.user
            )
            
            # Log entry
            ParkingLog.objects.create(
                ticket=ticket,
                log_type='ENTRY',
                operator=request.user,
                details=f"Kendaraan {vehicle.license_plate} masuk"
            )
            
            messages.success(request, f'Tiket parkir {ticket_id} berhasil dibuat')
            return redirect('ticket_detail', ticket_id=ticket.ticket_id)
    else:
        vehicle_form = VehicleForm()
    
    return render(request, 'parking_manager/vehicle_entry.html', {'form': vehicle_form})

@login_required
def vehicle_exit(request, ticket_id):
    ticket = get_object_or_404(ParkingTicket, ticket_id=ticket_id)
    
    if request.method == 'POST':
        if not ticket.is_paid:
            messages.error(request, 'Tiket belum dibayar')
            return redirect('payment_process', ticket_id=ticket.ticket_id)
        
        ticket.exit_time = timezone.now()
        ticket.status = 'COMPLETED'
        ticket.save()
        
        # Log exit
        ParkingLog.objects.create(
            ticket=ticket,
            log_type='EXIT',
            operator=request.user,
            details=f"Kendaraan {ticket.vehicle.license_plate} keluar"
        )
        
        messages.success(request, f'Kendaraan {ticket.vehicle.license_plate} berhasil keluar')
        return redirect('dashboard')
    
    context = {
        'ticket': ticket,
        'duration': ticket.calculate_duration(),
        'fee': ticket.calculate_fee()
    }
    return render(request, 'parking_manager/vehicle_exit.html', context)

@login_required
def payment_process(request, ticket_id):
    ticket = get_object_or_404(ParkingTicket, ticket_id=ticket_id)
    
    if request.method == 'POST':
        form = PaymentForm(request.POST)
        if form.is_valid():
            try:
                payment = form.save(commit=False)
                payment.ticket = ticket
                payment.operator = request.user
                payment.transaction_id = f"TRX{timezone.now().strftime('%Y%m%d%H%M%S')}"
                
                # Process voucher if provided
                voucher_code = form.cleaned_data.get('voucher_code')
                if voucher_code:
                    try:
                        voucher = Voucher.objects.get(code=voucher_code)
                        if voucher.is_valid():
                            payment.voucher = voucher
                            payment.voucher_discount = voucher.calculate_discount(ticket.calculate_fee())
                        else:
                            messages.error(request, 'Voucher tidak valid atau sudah kadaluarsa')
                            return redirect('payment_process', ticket_id=ticket.ticket_id)
                    except Voucher.DoesNotExist:
                        messages.error(request, 'Kode voucher tidak ditemukan')
                        return redirect('payment_process', ticket_id=ticket.ticket_id)
                
                # Calculate total after voucher
                total_amount = payment.calculate_total()
                
                # Validate payment amount
                if payment.amount < total_amount:
                    messages.error(request, 'Jumlah pembayaran kurang dari total yang harus dibayar')
                    return redirect('payment_process', ticket_id=ticket.ticket_id)
                
                # Save payment
                payment.save()
                
                # Update ticket
                ticket.is_paid = True
                ticket.fee = total_amount
                ticket.save()
                
                # Log payment with voucher info if used
                log_details = f"Pembayaran {payment.get_payment_method_display()} sebesar Rp {payment.amount:,.0f}"
                if payment.voucher:
                    log_details += f" (Voucher: {payment.voucher.code}, Potongan: Rp {payment.voucher_discount:,.0f})"
                
                ParkingLog.objects.create(
                    ticket=ticket,
                    log_type='PAYMENT',
                    operator=request.user,
                    details=log_details
                )
                
                # Print receipt
                try:
                    from .utils import ReceiptPrinter
                    printer = ReceiptPrinter()
                    if printer.print_receipt(payment.generate_receipt_data()):
                        payment.receipt_printed = True
                        payment.save()
                        messages.success(request, 'Pembayaran berhasil dan struk telah dicetak')
                    else:
                        messages.warning(request, 'Pembayaran berhasil tetapi gagal mencetak struk')
                except Exception as e:
                    messages.warning(request, f'Pembayaran berhasil tetapi gagal mencetak struk: {str(e)}')
                
                return redirect('vehicle_exit', ticket_id=ticket.ticket_id)
                
            except ValidationError as e:
                messages.error(request, str(e))
                return redirect('payment_process', ticket_id=ticket.ticket_id)
    else:
        initial_amount = ticket.calculate_fee()
        form = PaymentForm(initial={'amount': initial_amount})
    
    context = {
        'ticket': ticket,
        'form': form,
        'duration': ticket.calculate_duration(),
        'fee': initial_amount
    }
    return render(request, 'parking_manager/payment_process.html', context)

@login_required
def reprint_receipt(request, payment_id):
    """View untuk mencetak ulang struk"""
    payment = get_object_or_404(PaymentTransaction, id=payment_id)
    
    try:
        from .utils import ReceiptPrinter
        printer = ReceiptPrinter()
        if printer.print_receipt(payment.generate_receipt_data()):
            messages.success(request, 'Struk berhasil dicetak ulang')
        else:
            messages.error(request, 'Gagal mencetak ulang struk')
    except Exception as e:
        messages.error(request, f'Gagal mencetak ulang struk: {str(e)}')
    
    return redirect('ticket_detail', ticket_id=payment.ticket.ticket_id)

@login_required
def ticket_detail(request, ticket_id):
    ticket = get_object_or_404(ParkingTicket, ticket_id=ticket_id)
    logs = ParkingLog.objects.filter(ticket=ticket).order_by('-timestamp')
    payments = PaymentTransaction.objects.filter(ticket=ticket).order_by('-timestamp')
    
    context = {
        'ticket': ticket,
        'logs': logs,
        'payments': payments,
        'duration': ticket.calculate_duration(),
        'fee': ticket.calculate_fee()
    }
    return render(request, 'parking_manager/ticket_detail.html', context)

@login_required
def search_ticket(request):
    query = request.GET.get('q', '')
    tickets = []
    
    if query:
        tickets = ParkingTicket.objects.filter(
            Q(ticket_id__icontains=query) |
            Q(barcode__icontains=query) |
            Q(vehicle__license_plate__icontains=query)
        ).order_by('-entry_time')
    
    context = {
        'query': query,
        'tickets': tickets
    }
    return render(request, 'parking_manager/search_ticket.html', context)

@login_required
def voucher_list(request):
    """View untuk menampilkan daftar voucher"""
    vouchers = Voucher.objects.all().order_by('-created_at')
    
    context = {
        'vouchers': vouchers
    }
    return render(request, 'parking_manager/voucher_list.html', context)

@login_required
def voucher_create(request):
    """View untuk membuat voucher baru"""
    if request.method == 'POST':
        form = VoucherForm(request.POST)
        if form.is_valid():
            voucher = form.save()
            messages.success(request, f'Voucher {voucher.code} berhasil dibuat')
            return redirect('voucher_list')
    else:
        form = VoucherForm()
    
    context = {
        'form': form,
        'title': 'Buat Voucher Baru'
    }
    return render(request, 'parking_manager/voucher_form.html', context)

@login_required
def voucher_edit(request, voucher_id):
    """View untuk mengedit voucher"""
    voucher = get_object_or_404(Voucher, id=voucher_id)
    
    if request.method == 'POST':
        form = VoucherForm(request.POST, instance=voucher)
        if form.is_valid():
            voucher = form.save()
            messages.success(request, f'Voucher {voucher.code} berhasil diperbarui')
            return redirect('voucher_list')
    else:
        form = VoucherForm(instance=voucher)
    
    context = {
        'form': form,
        'title': 'Edit Voucher',
        'voucher': voucher
    }
    return render(request, 'parking_manager/voucher_form.html', context)

@login_required
def voucher_delete(request, voucher_id):
    """View untuk menghapus voucher"""
    voucher = get_object_or_404(Voucher, id=voucher_id)
    
    if request.method == 'POST':
        voucher.delete()
        messages.success(request, f'Voucher {voucher.code} berhasil dihapus')
        return redirect('voucher_list')
    
    context = {
        'voucher': voucher
    }
    return render(request, 'parking_manager/voucher_confirm_delete.html', context)

@login_required
def voucher_toggle(request, voucher_id):
    """View untuk mengaktifkan/nonaktifkan voucher"""
    voucher = get_object_or_404(Voucher, id=voucher_id)
    voucher.is_active = not voucher.is_active
    voucher.save()
    
    status = 'diaktifkan' if voucher.is_active else 'dinonaktifkan'
    messages.success(request, f'Voucher {voucher.code} berhasil {status}')
    return redirect('voucher_list')

@login_required
def financial_report(request):
    # Get date range from request, default to 30 days
    date_range = request.GET.get('date_range', '30')
    days = int(date_range)
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get transactions within date range
    transactions = PaymentTransaction.objects.filter(
        timestamp__range=(start_date, end_date)
    ).select_related('ticket')
    
    # Calculate summary data
    summary = {
        'total_revenue': transactions.aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_transactions': transactions.count(),
        'average_fee': transactions.aggregate(Avg('amount'))['amount__avg'] or 0,
        'total_vehicles': transactions.values('ticket__vehicle__license_plate').distinct().count(),
    }
    
    # Daily revenue data
    daily_revenue = transactions.annotate(
        date=TruncDate('timestamp')
    ).values('date').annotate(
        total=Sum('amount')
    ).order_by('date')
    
    revenue_data = {
        'labels': [entry['date'].strftime('%Y-%m-%d') for entry in daily_revenue],
        'data': [float(entry['total']) for entry in daily_revenue]
    }
    
    # Vehicle type distribution
    vehicle_types = transactions.values(
        'ticket__vehicle__vehicle_type'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    vehicle_data = {
        'labels': [entry['ticket__vehicle__vehicle_type'] for entry in vehicle_types],
        'data': [entry['count'] for entry in vehicle_types]
    }
    
    # Payment method distribution
    payment_methods = transactions.values(
        'payment_method'
    ).annotate(
        count=Count('id')
    ).order_by('-count')
    
    payment_data = {
        'labels': [entry['payment_method'] for entry in payment_methods],
        'data': [entry['count'] for entry in payment_methods]
    }
    
    # Combine all chart data
    chart_data = {
        'revenue': revenue_data,
        'vehicle_types': vehicle_data,
        'payment_methods': payment_data
    }
    
    context = {
        'summary': summary,
        'chart_data': chart_data,
        'date_range': date_range
    }
    
    return render(request, 'parking_manager/financial_report.html', context)

@login_required
def export_report(request):
    # Get date range from request, default to 30 days
    date_range = request.GET.get('date_range', '30')
    days = int(date_range)
    
    # Calculate date range
    end_date = datetime.now()
    start_date = end_date - timedelta(days=days)
    
    # Get transactions within date range
    transactions = PaymentTransaction.objects.filter(
        timestamp__range=(start_date, end_date)
    ).select_related('ticket')
    
    # Create Excel file in memory
    output = BytesIO()
    workbook = xlsxwriter.Workbook(output)
    worksheet = workbook.add_worksheet()
    
    # Add headers
    headers = ['Tanggal', 'ID Tiket', 'Plat Nomor', 'Jenis Kendaraan', 
              'Metode Pembayaran', 'Jumlah', 'Durasi (Jam)', 'Catatan']
    for col, header in enumerate(headers):
        worksheet.write(0, col, header)
    
    # Add data rows
    for row, trans in enumerate(transactions, 1):
        worksheet.write(row, 0, trans.timestamp.strftime('%Y-%m-%d %H:%M:%S'))
        worksheet.write(row, 1, trans.ticket.id)
        worksheet.write(row, 2, trans.ticket.vehicle.license_plate)
        worksheet.write(row, 3, trans.ticket.vehicle.vehicle_type)
        worksheet.write(row, 4, trans.payment_method)
        worksheet.write(row, 5, float(trans.amount))
        worksheet.write(row, 6, trans.ticket.calculate_duration())
        worksheet.write(row, 7, trans.notes or '')
    
    workbook.close()
    
    # Prepare response
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=parking_report_{datetime.now().strftime("%Y%m%d")}.xlsx'
    
    return response

@login_required
def monthly_report(request, year, month):
    """View for detailed monthly financial reports"""
    # Calculate start and end dates for the month
    start_date = datetime(year, month, 1)
    if month == 12:
        end_date = datetime(year + 1, 1, 1)
    else:
        end_date = datetime(year, month + 1, 1)
    
    # Get transactions for the month
    transactions = PaymentTransaction.objects.filter(
        timestamp__range=(start_date, end_date)
    ).select_related('ticket')
    
    # Calculate monthly summary
    summary = {
        'total_revenue': transactions.aggregate(Sum('amount'))['amount__sum'] or 0,
        'total_transactions': transactions.count(),
        'average_fee': transactions.aggregate(Avg('amount'))['amount__avg'] or 0,
        'total_vehicles': transactions.values('ticket__vehicle__license_plate').distinct().count(),
    }
    
    # Daily revenue data
    daily_revenue = transactions.annotate(
        date=TruncDate('timestamp')
    ).values('date').annotate(
        total=Sum('amount')
    ).order_by('date')
    
    revenue_data = {
        'labels': [entry['date'].strftime('%Y-%m-%d') for entry in daily_revenue],
        'data': [float(entry['total']) for entry in daily_revenue]
    }
    
    context = {
        'summary': summary,
        'revenue_data': revenue_data,
        'year': year,
        'month': month,
        'month_name': start_date.strftime('%B %Y')
    }
    
    return render(request, 'parking_manager/monthly_report.html', context)

@login_required
def transaction_list(request):
    """View for listing all transactions with filtering and sorting"""
    # Get filter parameters
    start_date = request.GET.get('start_date')
    end_date = request.GET.get('end_date')
    payment_method = request.GET.get('payment_method')
    vehicle_type = request.GET.get('vehicle_type')
    sort_by = request.GET.get('sort', '-timestamp')
    
    # Base queryset
    transactions = PaymentTransaction.objects.select_related(
        'ticket', 'ticket__vehicle'
    ).order_by(sort_by)
    
    # Apply filters
    if start_date:
        transactions = transactions.filter(timestamp__date__gte=start_date)
    if end_date:
        transactions = transactions.filter(timestamp__date__lte=end_date)
    if payment_method:
        transactions = transactions.filter(payment_method=payment_method)
    if vehicle_type:
        transactions = transactions.filter(ticket__vehicle__vehicle_type=vehicle_type)
    
    context = {
        'transactions': transactions,
        'payment_methods': PaymentTransaction.objects.values_list(
            'payment_method', flat=True
        ).distinct(),
        'vehicle_types': Vehicle.objects.values_list(
            'vehicle_type', flat=True
        ).distinct(),
        'filters': {
            'start_date': start_date,
            'end_date': end_date,
            'payment_method': payment_method,
            'vehicle_type': vehicle_type,
            'sort_by': sort_by
        }
    }
    
    return render(request, 'parking_manager/transaction_list.html', context)

@login_required
def transaction_detail(request, transaction_id):
    """View for detailed transaction information"""
    transaction = get_object_or_404(
        PaymentTransaction.objects.select_related(
            'ticket', 'ticket__vehicle', 'voucher'
        ),
        id=transaction_id
    )
    
    context = {
        'transaction': transaction,
        'ticket': transaction.ticket,
        'vehicle': transaction.ticket.vehicle,
        'voucher': transaction.voucher
    }
    
    return render(request, 'parking_manager/transaction_detail.html', context) 