from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Count, Sum
from django.db.models.functions import TruncDate
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from .models import Captureticket, ParkingSession, Vehicle
from datetime import datetime, timedelta
import json
import psycopg2
from rest_framework.response import Response

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def capture_tickets(request):
    """Get capture tickets data"""
    tickets = Captureticket.objects.all().order_by('-date_masuk')[:100]  # Limit to last 100 tickets
    data = [{
        'id': ticket.id,
        'ticket_number': ticket.plat_no,
        'image_path': None,  # Add image path handling if needed
        'capture_time': ticket.date_masuk.isoformat(),
        'status': ticket.status,
        'vehicle_type': ticket.vehicle_type,
        'plate_number': ticket.plat_no
    } for ticket in tickets]
    return JsonResponse(data, safe=False)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def exit_tickets(request):
    """Get active parking sessions"""
    sessions = ParkingSession.objects.filter(is_active=True).order_by('-check_in_time')
    data = [{
        'id': session.id,
        'ticketNumber': str(session.id),
        'imagePath': None,  # Add image path handling if needed
        'captureTime': session.check_in_time.isoformat(),
        'status': 'ACTIVE',
        'vehicleType': session.vehicle.vehicle_type,
        'plateNumber': session.vehicle.license_plate
    } for session in sessions]
    return JsonResponse(data, safe=False)

@api_view(['POST'])
@permission_classes([IsAuthenticated])
def process_exit(request):
    """Process exit ticket"""
    try:
        data = json.loads(request.body)
        ticket_number = data.get('ticketNumber')
        vehicle_type = data.get('vehicleType', 'CAR')
        
        # Find the active session
        session = ParkingSession.objects.get(id=ticket_number, is_active=True)
        
        # Process checkout
        session.check_out(operator=request.user)
        
        return JsonResponse({
            'success': True,
            'message': 'Exit processed successfully',
            'data': {
                'fee': float(session.fee) if session.fee else 0
            }
        })
    except ParkingSession.DoesNotExist:
        return JsonResponse({
            'success': False,
            'message': 'Active session not found'
        }, status=404)
    except Exception as e:
        return JsonResponse({
            'success': False,
            'message': str(e)
        }, status=500)

@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard(request):
    """Get dashboard data"""
    today = timezone.now().date()
    start_date = today - timedelta(days=30)  # Last 30 days
    
    # Get active sessions
    active_sessions = ParkingSession.objects.filter(is_active=True)
    
    # Get completed sessions in date range
    completed_sessions = ParkingSession.objects.filter(
        is_active=False,
        check_out_time__date__gte=start_date
    )
    
    # Calculate statistics
    stats = {
        'totalVehicles': Vehicle.objects.count(),
        'activeVehicles': active_sessions.count(),
        'totalRevenue': float(completed_sessions.aggregate(Sum('fee'))['fee__sum'] or 0),
        'dailyAverage': float(completed_sessions.aggregate(Sum('fee'))['fee__sum'] or 0) / 30
    }
    
    # Get recent tickets
    recent_tickets = Captureticket.objects.all().order_by('-date_masuk')[:10]
    recent_tickets_data = [{
        'id': ticket.id,
        'ticket_number': ticket.plat_no,
        'capture_time': ticket.date_masuk.isoformat(),
        'status': ticket.status,
        'vehicle_type': ticket.vehicle_type,
        'plate_number': ticket.plat_no
    } for ticket in recent_tickets]
    
    # Get vehicle type distribution
    vehicle_types = Vehicle.objects.values('vehicle_type').annotate(
        count=Count('id')
    ).order_by('vehicle_type')
    
    # Get revenue by day
    revenue_by_day = completed_sessions.annotate(
        date=TruncDate('check_out_time')
    ).values('date').annotate(
        amount=Sum('fee')
    ).order_by('-date')[:30]
    
    return JsonResponse({
        'success': True,
        'data': {
            'stats': stats,
            'recentTickets': recent_tickets_data,
            'vehicleTypes': list(vehicle_types),
            'revenueByDay': list(revenue_by_day)
        }
    })

@api_view(['POST'])
def process_exit_ticket(request):
    try:
        ticket_number = request.data.get('ticket_number')
        
        # Connect to database
        conn = psycopg2.connect(
            dbname="parkir2",
            user="postgres",
            password="postgres",
            host="192.168.2.6",
            port="5432"
        )
        
        cur = conn.cursor()
        
        # Get ticket data
        cur.execute("""
            SELECT id, plat_no, date_masuk, status
            FROM captureticket
            WHERE plat_no = %s AND status = 'MASUK'
        """, (ticket_number,))
        
        ticket = cur.fetchone()
        
        if not ticket:
            return JsonResponse({
                'status': 'error',
                'message': 'Ticket not found or already processed'
            })
        
        # Calculate duration and fee
        now = timezone.now()
        duration = now - ticket[2]  # date_masuk
        hours = duration.total_seconds() / 3600
        
        # Basic fee calculation (can be modified based on your requirements)
        if hours <= 1:
            fee = 3000
        elif hours <= 2:
            fee = 6000
        elif hours <= 4:
            fee = 10000
        else:
            fee = 15000
        
        # Update ticket
        cur.execute("""
            UPDATE captureticket
            SET date_keluar = %s,
                status = 'KELUAR',
                biaya = %s
            WHERE id = %s
        """, (now, fee, ticket[0]))
        
        conn.commit()
        cur.close()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'ticket': {
                'id': ticket[0],
                'plat_no': ticket[1],
                'date_masuk': ticket[2].isoformat(),
                'date_keluar': now.isoformat(),
                'duration_hours': round(hours, 2),
                'fee': fee
            }
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        })

@api_view(['GET'])
def get_active_tickets(request):
    try:
        # Connect to database
        conn = psycopg2.connect(
            dbname="parkir2",
            user="postgres",
            password="postgres",
            host="192.168.2.6",
            port="5432"
        )
        
        cur = conn.cursor()
        
        # Get all active tickets
        cur.execute("""
            SELECT id, plat_no, date_masuk, status
            FROM captureticket
            WHERE status = 'MASUK'
            ORDER BY date_masuk DESC
        """)
        
        tickets = cur.fetchall()
        
        cur.close()
        conn.close()
        
        return JsonResponse({
            'status': 'success',
            'tickets': [{
                'id': ticket[0],
                'plat_no': ticket[1],
                'date_masuk': ticket[2].isoformat(),
                'status': ticket[3]
            } for ticket in tickets]
        })
        
    except Exception as e:
        return JsonResponse({
            'status': 'error',
            'message': str(e)
        }) 