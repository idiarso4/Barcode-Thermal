from .models import Shift

def active_shift(request):
    if request.user.is_authenticated:
        active_shift = Shift.objects.filter(operator=request.user, is_active=True).first()
        return {'active_shift': active_shift}
    return {'active_shift': None} 