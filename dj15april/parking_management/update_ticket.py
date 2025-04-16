import os
import django
import sys

# Set up Django environment
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'parking_management.settings')
django.setup()

from parking.models import Captureticket
from django.utils.timezone import make_aware
from datetime import datetime

def update_database():
    try:
        # Create the ticket entry
        ticket = Captureticket(
            id=8429,
            plat_no='TKT20250414190611_8469',
            date_masuk=make_aware(datetime.strptime('2025-04-14 19:06:11.048622', '%Y-%m-%d %H:%M:%S.%f')),
            status='MASUK'
        )
        ticket.save()
        print('Ticket data inserted successfully!')
    except Exception as e:
        print(f'Error: {str(e)}')

if __name__ == '__main__':
    update_database() 