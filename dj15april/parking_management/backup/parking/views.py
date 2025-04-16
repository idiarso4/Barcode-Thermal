from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from .models import Vehicle, ParkingSpot, ParkingSession, Shift, Captureticket
from django.db.models import Q, Sum
from django.http import JsonResponse, HttpResponse
from django.db import connection
import psycopg2
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.decorators import login_required
from django.contrib.auth.models import User
from django.core.paginator import Paginator
from datetime import datetime, timedelta
import pandas as pd
import xlsxwriter
from io import BytesIO
import json
from django.views.decorators.cache import cache_page
from django.core.cache import cache
from django.db import transaction
from django.views.decorators.http import require_http_methods
import logging
from django.core.exceptions import ValidationError
from django.db.utils import DatabaseError
from django.http import Http404

logger = logging.getLogger('parking')

class ParkingError(Exception):
    """Custom exception for parking-related errors"""
    pass

def user_login(request):
    if request.method == 'POST':
        username = request.POST.get('username')
        password = request.POST.get('password')
        user = authenticate(request, username=username, password=password)
        
        if user is not None:
            login(request, user)
            messages.success(request, 'Login successful!')
            return redirect('parking:dashboard')
        else:
            messages.error(request, 'Invalid username or password.')
    
    return render(request, 'parking/login.html')

def user_logout(request):
    logout(request)
    messages.success(request, 'You have been logged out successfully.')
    return redirect('parking:login')

@login_required(login_url='parking:login')
def start_shift(request):
    # Check if user already has an active shift
    active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
    if active_shift:
        messages.warning(request, 'You already have an active shift!')
        return redirect('parking:dashboard')
    
    # Create new shift
    shift = Shift.objects.create(operator=request.user)
    messages.success(request, 'Shift started successfully!')
    return redirect('parking:dashboard')

@login_required(login_url='parking:login')
def end_shift(request):
    active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
    if not active_shift:
        messages.warning(request, 'No active shift found!')
        return redirect('parking:dashboard')
    
    if request.method == 'POST':
        notes = request.POST.get('notes', '')
        active_shift.notes = notes
        active_shift.end_shift()
        messages.success(request, 'Shift ended successfully!')
        return redirect('parking:shift_report', shift_id=active_shift.id)
    
    return render(request, 'parking/end_shift.html', {'shift': active_shift})

@login_required(login_url='parking:login')
def shift_report(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    
    # Generate hourly activity data
    hours = []
    checkins = []
    checkouts = []
    
    if shift.end_time:
        current_hour = shift.start_time.replace(minute=0, second=0, microsecond=0)
        end_hour = shift.end_time.replace(minute=0, second=0, microsecond=0)
        
        while current_hour <= end_hour:
            next_hour = current_hour + timedelta(hours=1)
            hours.append(current_hour.strftime('%H:%M'))
            
            # Count check-ins and check-outs for this hour
            checkins.append(shift.parking_sessions.filter(
                check_in_time__gte=current_hour,
                check_in_time__lt=next_hour
            ).count())
            
            checkouts.append(shift.parking_sessions.filter(
                check_out_time__gte=current_hour,
                check_out_time__lt=next_hour
            ).count())
            
            current_hour = next_hour
    
    # Generate revenue distribution data
    revenue_dist = [0, 0, 0, 0]  # [<1h, 1-2h, 2-4h, 4h+]
    
    for session in shift.parking_sessions.filter(check_out_time__isnull=False):
        duration = session.check_out_time - session.check_in_time
        hours = duration.total_seconds() / 3600
        
        if hours < 1:
            revenue_dist[0] += session.fee
        elif hours < 2:
            revenue_dist[1] += session.fee
        elif hours < 4:
            revenue_dist[2] += session.fee
        else:
            revenue_dist[3] += session.fee
    
    context = {
        'shift': shift,
        'hourly_labels': json.dumps(hours),
        'hourly_checkins': checkins,
        'hourly_checkouts': checkouts,
        'revenue_distribution': revenue_dist,
    }
    
    return render(request, 'parking/shift_report.html', context)

@login_required(login_url='parking:login')
def shift_list(request):
    shifts = Shift.objects.all()
    
    # Filter by date range
    date_range = request.GET.get('date_range')
    if date_range:
        start_date, end_date = date_range.split(' - ')
        start_date = datetime.strptime(start_date, '%Y-%m-%d')
        end_date = datetime.strptime(end_date, '%Y-%m-%d')
        shifts = shifts.filter(start_time__date__range=[start_date, end_date])
    
    # Filter by status
    status = request.GET.get('status')
    if status == 'active':
        shifts = shifts.filter(end_time__isnull=True)
    elif status == 'completed':
        shifts = shifts.filter(end_time__isnull=False)
    
    # Sort
    sort_by = request.GET.get('sort', '-start_time')
    shifts = shifts.order_by(sort_by)
    
    # Pagination
    paginator = Paginator(shifts, 10)
    page = request.GET.get('page')
    shifts = paginator.get_page(page)
    
    return render(request, 'parking/shift_list.html', {'shifts': shifts})

@login_required(login_url='parking:login')
def export_shift_report(request, shift_id):
    shift = get_object_or_404(Shift, id=shift_id)
    
    # Create an in-memory output file for the Excel workbook
    output = BytesIO()
    
    # Create the Excel workbook and add a worksheet
    workbook = xlsxwriter.Workbook(output)
    
    # Add formats
    header_format = workbook.add_format({
        'bold': True,
        'bg_color': '#4F81BD',
        'font_color': 'white',
        'border': 1
    })
    
    cell_format = workbook.add_format({
        'border': 1
    })
    
    # Shift Summary Sheet
    summary_sheet = workbook.add_worksheet('Shift Summary')
    summary_sheet.set_column('A:B', 20)
    
    # Write shift summary
    summary_data = [
        ['Shift Information', ''],
        ['Operator', shift.operator.get_full_name()],
        ['Start Time', shift.start_time.strftime('%Y-%m-d %H:%M')],
        ['End Time', shift.end_time.strftime('%Y-%m-d %H:%M') if shift.end_time else 'Ongoing'],
        ['Total Vehicles', shift.total_vehicles],
        ['Total Revenue', f'Rp {shift.total_revenue}'],
        ['Status', 'Active' if shift.is_active else 'Completed'],
        ['Notes', shift.notes or '']
    ]
    
    for row, data in enumerate(summary_data):
        summary_sheet.write(row, 0, data[0], header_format if row == 0 else cell_format)
        summary_sheet.write(row, 1, data[1], header_format if row == 0 else cell_format)
    
    # Parking Sessions Sheet
    sessions_sheet = workbook.add_worksheet('Parking Sessions')
    sessions_sheet.set_column('A:G', 15)
    
    # Write headers
    headers = ['Check-in Time', 'Check-out Time', 'Vehicle', 'Spot', 'Duration', 'Fee', 'Status']
    for col, header in enumerate(headers):
        sessions_sheet.write(0, col, header, header_format)
    
    # Write parking session data
    sessions = shift.parking_sessions.all()
    for row, session in enumerate(sessions, start=1):
        data = [
            session.check_in_time.strftime('%Y-%m-d %H:%M'),
            session.check_out_time.strftime('%Y-%m-d %H:%M') if session.check_out_time else 'Ongoing',
            session.vehicle_license_plate,
            session.parking_spot.identifier,
            str(session.duration) if session.check_out_time else 'Ongoing',
            f'Rp {session.fee}',
            'Completed' if session.check_out_time else 'Active'
        ]
        for col, value in enumerate(data):
            sessions_sheet.write(row, col, value, cell_format)
    
    workbook.close()
    
    # Set up the response
    output.seek(0)
    response = HttpResponse(
        output.read(),
        content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
    )
    response['Content-Disposition'] = f'attachment; filename=shift_report_{shift_id}.xlsx'
    
    return response

@login_required(login_url='parking:login')
def dashboard(request):
    """Enhanced dashboard view with more information"""
    try:
        # Check for active shift
        active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
        
        if not active_shift:
            return render(request, 'parking/start_shift.html', {'active_shift': None})

        # Get basic statistics
        with connection.cursor() as cursor:
            # Parking overview
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_vehicles,
                    SUM(CASE WHEN date_keluar IS NULL THEN 1 ELSE 0 END) as active_vehicles,
                    SUM(CASE WHEN date_keluar IS NOT NULL THEN biaya ELSE 0 END) as total_revenue
                FROM captureticket 
                WHERE date_masuk::date = CURRENT_DATE
            """)
            overview = dict(zip(['total_vehicles', 'active_vehicles', 'total_revenue'], 
                              cursor.fetchone()))

            # Vehicle type distribution
            cursor.execute("""
                SELECT 
                    vehicle_type, 
                    COUNT(*) as count
                FROM captureticket 
                WHERE date_keluar IS NULL 
                GROUP BY vehicle_type
            """)
            vehicle_distribution = dict(cursor.fetchall())

            # Recent activities
            cursor.execute("""
                SELECT 
                    id, plat_no, date_masuk, date_keluar, status, biaya
                FROM captureticket 
                ORDER BY 
                    CASE WHEN date_keluar IS NULL THEN date_masuk ELSE date_keluar END DESC
                LIMIT 10
            """)
            recent_activities = [
                dict(zip(['id', 'plat_no', 'date_masuk', 'date_keluar', 'status', 'biaya'], 
                        row))
                for row in cursor.fetchall()
            ]

        context = {
            'active_shift': active_shift,
            'overview': overview,
            'vehicle_distribution': vehicle_distribution,
            'recent_activities': recent_activities,
            'user': request.user,
            'current_time': datetime.now(),
        }

        logger.info(f"Dashboard accessed by user {request.user.username}")
        return render(request, 'parking/dashboard.html', context)

    except DatabaseError as e:
        logger.error(f"Database error in dashboard: {str(e)}")
        messages.error(request, 'Database error occurred. Please try again later.')
        return redirect('parking:login')
    except Exception as e:
        logger.error(f"Unexpected error in dashboard: {str(e)}")
        messages.error(request, 'An unexpected error occurred. Please try again later.')
        return redirect('parking:login')

@login_required(login_url='parking:login')
def vehicle_list(request):
    vehicles = Vehicle.objects.all().order_by('-created_at')
    return render(request, 'parking/vehicle_list.html', {'vehicles': vehicles})

@login_required(login_url='parking:login')
def vehicle_add(request):
    if request.method == 'POST':
        license_plate = request.POST.get('license_plate')
        vehicle_type = request.POST.get('vehicle_type')
        owner_name = request.POST.get('owner_name')
        owner_contact = request.POST.get('owner_contact')
        
        Vehicle.objects.create(
            license_plate=license_plate,
            vehicle_type=vehicle_type,
            owner_name=owner_name,
            owner_contact=owner_contact
        )
        messages.success(request, 'Vehicle added successfully!')
        return redirect('parking:vehicle_list')
    
    return render(request, 'parking/vehicle_add.html')

@login_required(login_url='parking:login')
def parking_spot_list(request):
    spots = ParkingSpot.objects.all().order_by('floor', 'spot_number')
    return render(request, 'parking/spot_list.html', {'spots': spots})

@login_required(login_url='parking:login')
def parking_spot_add(request):
    if request.method == 'POST':
        spot_number = request.POST.get('spot_number')
        spot_type = request.POST.get('spot_type')
        floor = request.POST.get('floor')
        
        ParkingSpot.objects.create(
            spot_number=spot_number,
            spot_type=spot_type,
            floor=floor
        )
        messages.success(request, 'Parking spot added successfully!')
        return redirect('parking:parking_spot_list')
    
    return render(request, 'parking/spot_add.html')

@login_required(login_url='parking:login')
def check_in(request):
    # Check for active shift
    active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
    if not active_shift:
        messages.warning(request, 'Please start your shift first!')
        return redirect('parking:dashboard')

    if request.method == 'POST':
        vehicle_id = request.POST.get('vehicle')
        spot_id = request.POST.get('parking_spot')
        
        vehicle = get_object_or_404(Vehicle, id=vehicle_id)
        spot = get_object_or_404(ParkingSpot, id=spot_id)
        
        if spot.status != 'AVAILABLE':
            messages.error(request, 'This parking spot is not available!')
            return redirect('parking:check_in')
        
        # Create parking session with shift information
        ParkingSession.objects.create(
            vehicle=vehicle,
            parking_spot=spot,
            created_by=request.user,
            shift=active_shift
        )
        
        spot.status = 'OCCUPIED'
        spot.save()
        
        messages.success(request, 'Vehicle checked in successfully!')
        return redirect('parking:dashboard')
    
    vehicles = Vehicle.objects.all()
    available_spots = ParkingSpot.objects.filter(status='AVAILABLE')
    
    return render(request, 'parking/check_in.html', {
        'vehicles': vehicles,
        'spots': available_spots,
        'active_shift': active_shift
    })

@login_required(login_url='parking:login')
def check_out(request, session_id):
    # Check for active shift
    active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
    if not active_shift:
        messages.warning(request, 'Please start your shift first!')
        return redirect('parking:dashboard')

    session = get_object_or_404(ParkingSession, id=session_id)
    
    if not session.is_active:
        messages.error(request, 'This session is already checked out!')
        return redirect('parking:dashboard')
    
    session.check_out(operator=request.user)
    messages.success(request, f'Vehicle checked out successfully! Fee: Rp {session.fee}')
    return redirect('parking:dashboard')

@login_required(login_url='parking:login')
def session_list(request):
    sessions = ParkingSession.objects.all().order_by('-check_in_time')
    return render(request, 'parking/session_list.html', {'sessions': sessions})

def test_captureticket(request):
    try:
        # Connect to the database
        conn = psycopg2.connect(
            dbname="parkir2",
            user="postgres",
            password="postgres",
            host="192.168.2.6",
            port="5432"
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Get all records from captureticket table
        cur.execute("SELECT * FROM captureticket ORDER BY date_masuk DESC LIMIT 10")
        tickets = cur.fetchall()
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'tickets': [
                {
                    'id': ticket[0],
                    'plat_no': ticket[1],
                    'date_masuk': ticket[2].isoformat() if ticket[2] else None,
                    'date_keluar': ticket[3].isoformat() if ticket[3] else None,
                    'status': ticket[4],
                    'biaya': ticket[5]
                }
                for ticket in tickets
            ]
        })
            
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'error': str(e),
            'error_type': type(e).__name__
        })

@login_required(login_url='parking:login')
def view_captureticket(request):
    try:
        # Get the tickets using raw SQL for better control
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT id, plat_no, date_masuk, date_keluar, status, biaya 
                FROM captureticket 
                ORDER BY date_masuk DESC 
                LIMIT 100
            """)
            columns = [col[0] for col in cursor.description]
            tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]
            
            # Calculate statistics
            cursor.execute("""
                SELECT 
                    COUNT(*) as total_tickets,
                    COUNT(CASE WHEN date_keluar IS NULL THEN 1 END) as active_tickets,
                    COUNT(CASE WHEN date_keluar IS NOT NULL THEN 1 END) as completed_tickets,
                    SUM(CASE WHEN biaya IS NOT NULL THEN biaya ELSE 0 END) as total_revenue
                FROM captureticket
                WHERE date_masuk >= CURRENT_DATE
            """)
            stats = dict(zip(['total_tickets', 'active_tickets', 'completed_tickets', 'total_revenue'], cursor.fetchone()))
            
        return render(request, 'parking/captureticket_list.html', {
            'tickets': tickets,
            'stats': stats
        })
    except Exception as e:
        messages.error(request, f'Database error: {str(e)}')
        return redirect('parking:dashboard')

@login_required(login_url='parking:login')
def test_connection(request):
    try:
        # Direct connection test using psycopg2
        conn = psycopg2.connect(
            dbname="parkir2",
            user="postgres",
            password="postgres",
            host="192.168.2.6",
            port="5432"
        )
        
        # Create a cursor
        cur = conn.cursor()
        
        # Test basic connection and get version
        cur.execute("SELECT version();")
        version = cur.fetchone()[0]
        
        # Get all schemas
        cur.execute("""
            SELECT schema_name 
            FROM information_schema.schemata
            WHERE schema_name NOT IN ('pg_catalog', 'information_schema')
        """)
        schemas = [row[0] for row in cur.fetchall()]
        
        # Get all tables from public schema
        cur.execute("""
            SELECT table_name 
            FROM information_schema.tables 
            WHERE table_schema = 'public'
            AND table_type = 'BASE TABLE'
        """)
        tables = [row[0] for row in cur.fetchall()]
        
        # Check if CaptureTicket table exists (case-insensitive)
        capture_table = None
        for table in tables:
            if table.lower() == 'captureticket':
                capture_table = table
                break
        
        # If we found the table, get its structure
        table_structure = []
        if capture_table:
            cur.execute(f"""
                SELECT column_name, data_type, character_maximum_length
                FROM information_schema.columns
                WHERE table_name = '{capture_table}'
                ORDER BY ordinal_position
            """)
            table_structure = cur.fetchall()
        
        # Close cursor and connection
        cur.close()
        conn.close()
        
        return JsonResponse({
            'status': 'Connected successfully',
            'version': version,
            'host': '192.168.2.6',
            'database': 'parkir2',
            'schemas': schemas,
            'tables': tables,
            'capture_ticket_table': {
                'name': capture_table,
                'columns': table_structure if capture_table else None
            }
        }, json_dumps_params={'indent': 2})
            
    except Exception as e:
        return JsonResponse({
            'status': 'Connection failed',
            'error': str(e),
            'error_type': type(e).__name__,
            'connection_details': {
                'host': '192.168.2.6',
                'database': 'parkir2',
                'port': '5432',
                'user': 'postgres'
            }
        }, json_dumps_params={'indent': 2})

@require_http_methods(["GET"])
def get_active_tickets(request):
    """Get all active parking tickets"""
    try:
        # Get cached data first
        cached_tickets = cache.get('active_tickets')
        if cached_tickets:
            return JsonResponse({'success': True, 'data': cached_tickets})

        # If no cache, query database
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    id, 
                    plat_no, 
                    date_masuk, 
                    status, 
                    vehicle_type,
                    EXTRACT(EPOCH FROM (NOW() - date_masuk)) as duration
                FROM captureticket 
                WHERE date_keluar IS NULL 
                AND status = 'ACTIVE'
                ORDER BY date_masuk DESC
            """)
            columns = [col[0] for col in cursor.description]
            tickets = [dict(zip(columns, row)) for row in cursor.fetchall()]

            # Format datetime objects
            for ticket in tickets:
                ticket['date_masuk'] = ticket['date_masuk'].strftime('%Y-%m-%d %H:%M:%S')
                ticket['duration_hours'] = round(float(ticket['duration']) / 3600, 2)
                
                # Calculate fee based on duration
                hours = float(ticket['duration']) / 3600
                base_rate = 5000  # Base rate per hour
                
                if ticket['vehicle_type'] == 'MOTOR':
                    rate = base_rate * 0.5
                elif ticket['vehicle_type'] == 'MOBIL':
                    rate = base_rate
                else:  # TRUCK
                    rate = base_rate * 2
                    
                ticket['current_fee'] = round(hours * rate)

        # Cache the results for 30 seconds
        cache.set('active_tickets', tickets, 30)
        
        return JsonResponse({
            'success': True,
            'data': tickets,
            'total_count': len(tickets)
        })
        
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["POST"])
@transaction.atomic
def process_exit(request):
    """Process vehicle exit"""
    try:
        data = json.loads(request.body)
        ticket_id = data.get('ticket_id')
        plat_no = data.get('plat_no')
        
        if not ticket_id and not plat_no:
            return JsonResponse({
                'success': False,
                'error': 'Either ticket_id or plat_no is required'
            }, status=400)

        with connection.cursor() as cursor:
            # Find the ticket
            if ticket_id:
                cursor.execute("""
                    SELECT id, plat_no, date_masuk, vehicle_type
                    FROM captureticket 
                    WHERE id = %s AND date_keluar IS NULL
                """, [ticket_id])
            else:
                cursor.execute("""
                    SELECT id, plat_no, date_masuk, vehicle_type
                    FROM captureticket 
                    WHERE plat_no = %s AND date_keluar IS NULL
                    ORDER BY date_masuk DESC
                    LIMIT 1
                """, [plat_no])

            ticket = cursor.fetchone()
            
            if not ticket:
                return JsonResponse({
                    'success': False,
                    'error': 'Active ticket not found'
                }, status=404)

            # Calculate duration and fee
            date_masuk = ticket[2]
            date_keluar = datetime.now()
            duration = date_keluar - date_masuk
            hours = duration.total_seconds() / 3600
            
            # Calculate fee based on vehicle type
            base_rate = 5000  # Base rate per hour
            vehicle_type = ticket[3]
            
            if vehicle_type == 'MOTOR':
                rate = base_rate * 0.5
            elif vehicle_type == 'MOBIL':
                rate = base_rate
            else:  # TRUCK
                rate = base_rate * 2
                
            fee = round(hours * rate)

            # Update the ticket
            cursor.execute("""
                UPDATE captureticket 
                SET 
                    date_keluar = %s,
                    status = 'COMPLETED',
                    biaya = %s
                WHERE id = %s
                RETURNING id, plat_no, date_masuk, date_keluar, biaya
            """, [date_keluar, fee, ticket[0]])
            
            updated_ticket = cursor.fetchone()

            # Clear the cache
            cache.delete('active_tickets')
            
            return JsonResponse({
                'success': True,
                'data': {
                    'ticket_id': updated_ticket[0],
                    'plat_no': updated_ticket[1],
                    'date_masuk': updated_ticket[2].strftime('%Y-%m-%d %H:%M:%S'),
                    'date_keluar': updated_ticket[3].strftime('%Y-%m-%d %H:%M:%S'),
                    'duration_hours': round(hours, 2),
                    'fee': updated_ticket[4]
                }
            })

    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def check_connection(request):
    """Check database connection status"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
            cursor.fetchone()
            
        return JsonResponse({
            'success': True,
            'message': 'Database connection successful',
            'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        })
    except Exception as e:
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=500)

@require_http_methods(["GET"])
def get_vehicle_statistics(request):
    """Get statistics about vehicles currently in the parking lot"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    vehicle_type,
                    COUNT(*) as count,
                    AVG(EXTRACT(EPOCH FROM (NOW() - date_masuk))/3600) as avg_duration
                FROM captureticket 
                WHERE date_keluar IS NULL 
                GROUP BY vehicle_type
            """)
            stats = [dict(zip(['vehicle_type', 'count', 'avg_duration'], row)) 
                    for row in cursor.fetchall()]
            
            logger.info(f"Retrieved vehicle statistics: {stats}")
            return JsonResponse({'success': True, 'data': stats})
            
    except DatabaseError as e:
        logger.error(f"Database error in get_vehicle_statistics: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Database error occurred',
            'details': str(e)
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in get_vehicle_statistics: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)

@require_http_methods(["GET"])
def get_revenue_report(request):
    """Get revenue report for a specific time period"""
    try:
        period = request.GET.get('period', 'today')
        
        with connection.cursor() as cursor:
            if period == 'today':
                date_filter = "date_keluar::date = CURRENT_DATE"
            elif period == 'week':
                date_filter = "date_keluar >= CURRENT_DATE - INTERVAL '7 days'"
            elif period == 'month':
                date_filter = "date_keluar >= CURRENT_DATE - INTERVAL '30 days'"
            else:
                raise ValidationError("Invalid period specified")

            cursor.execute(f"""
                SELECT 
                    vehicle_type,
                    COUNT(*) as transactions,
                    SUM(biaya) as total_revenue,
                    AVG(biaya) as avg_revenue
                FROM captureticket 
                WHERE date_keluar IS NOT NULL 
                AND {date_filter}
                GROUP BY vehicle_type
            """)
            
            revenue_data = [dict(zip(['vehicle_type', 'transactions', 'total_revenue', 'avg_revenue'], row)) 
                           for row in cursor.fetchall()]
            
            logger.info(f"Generated revenue report for period {period}")
            return JsonResponse({
                'success': True,
                'period': period,
                'data': revenue_data
            })
            
    except ValidationError as e:
        logger.warning(f"Validation error in get_revenue_report: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except DatabaseError as e:
        logger.error(f"Database error in get_revenue_report: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Database error occurred'
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in get_revenue_report: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)

@require_http_methods(["GET"])
def get_parking_capacity(request):
    """Get current parking capacity and occupancy"""
    try:
        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    vehicle_type,
                    COUNT(*) as occupied_spots,
                    (
                        SELECT COUNT(*) 
                        FROM parking_spot 
                        WHERE spot_type = vehicle_type
                    ) as total_spots
                FROM captureticket 
                WHERE date_keluar IS NULL
                GROUP BY vehicle_type
            """)
            
            capacity_data = [dict(zip(['vehicle_type', 'occupied_spots', 'total_spots'], row)) 
                           for row in cursor.fetchall()]
            
            for data in capacity_data:
                data['occupancy_rate'] = round(
                    (data['occupied_spots'] / data['total_spots']) * 100 
                    if data['total_spots'] > 0 else 0, 2
                )
            
            logger.info("Retrieved parking capacity information")
            return JsonResponse({
                'success': True,
                'data': capacity_data
            })
            
    except DatabaseError as e:
        logger.error(f"Database error in get_parking_capacity: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Database error occurred'
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in get_parking_capacity: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)

@require_http_methods(["GET"])
def get_peak_hours(request):
    """Get peak hours analysis"""
    try:
        days = int(request.GET.get('days', 7))
        if days <= 0 or days > 30:
            raise ValidationError("Days parameter must be between 1 and 30")

        with connection.cursor() as cursor:
            cursor.execute("""
                SELECT 
                    EXTRACT(HOUR FROM date_masuk) as hour,
                    COUNT(*) as entries,
                    vehicle_type
                FROM captureticket 
                WHERE date_masuk >= CURRENT_DATE - INTERVAL %s DAY
                GROUP BY EXTRACT(HOUR FROM date_masuk), vehicle_type
                ORDER BY hour
            """, [days])
            
            peak_data = [dict(zip(['hour', 'entries', 'vehicle_type'], row)) 
                        for row in cursor.fetchall()]
            
            logger.info(f"Generated peak hours analysis for last {days} days")
            return JsonResponse({
                'success': True,
                'days_analyzed': days,
                'data': peak_data
            })
            
    except ValidationError as e:
        logger.warning(f"Validation error in get_peak_hours: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': str(e)
        }, status=400)
    except DatabaseError as e:
        logger.error(f"Database error in get_peak_hours: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'Database error occurred'
        }, status=500)
    except Exception as e:
        logger.error(f"Unexpected error in get_peak_hours: {str(e)}")
        return JsonResponse({
            'success': False,
            'error': 'An unexpected error occurred'
        }, status=500)
