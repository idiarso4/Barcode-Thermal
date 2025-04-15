from django import forms
from .models import Vehicle, ParkingTicket, PaymentTransaction, Voucher

class VehicleForm(forms.ModelForm):
    class Meta:
        model = Vehicle
        fields = ['license_plate', 'vehicle_type']
        widgets = {
            'license_plate': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Masukkan plat nomor'}),
            'vehicle_type': forms.Select(attrs={'class': 'form-control'}),
        }

class ParkingTicketForm(forms.ModelForm):
    class Meta:
        model = ParkingTicket
        fields = ['vehicle', 'notes']
        widgets = {
            'vehicle': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }

class PaymentForm(forms.ModelForm):
    voucher_code = forms.CharField(
        max_length=20, 
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Masukkan kode voucher'
        })
    )
    
    class Meta:
        model = PaymentTransaction
        fields = ['amount', 'payment_method', 'notes']
        widgets = {
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'payment_method': forms.Select(attrs={'class': 'form-control'}),
            'notes': forms.Textarea(attrs={'class': 'form-control', 'rows': 3}),
        }
    
    def clean_voucher_code(self):
        code = self.cleaned_data.get('voucher_code')
        if code:
            try:
                voucher = Voucher.objects.get(code=code)
                if not voucher.is_valid():
                    raise forms.ValidationError('Voucher tidak valid atau sudah kadaluarsa')
                return code
            except Voucher.DoesNotExist:
                raise forms.ValidationError('Kode voucher tidak ditemukan')
        return code

class SearchForm(forms.Form):
    query = forms.CharField(
        max_length=100,
        required=False,
        widget=forms.TextInput(attrs={
            'class': 'form-control',
            'placeholder': 'Cari tiket berdasarkan ID, barcode, atau plat nomor'
        })
    )

class VoucherForm(forms.ModelForm):
    class Meta:
        model = Voucher
        fields = ['code', 'description', 'voucher_type', 'amount', 'max_usage', 'valid_from', 'valid_until']
        widgets = {
            'code': forms.TextInput(attrs={'class': 'form-control'}),
            'description': forms.TextInput(attrs={'class': 'form-control'}),
            'voucher_type': forms.Select(attrs={'class': 'form-control'}),
            'amount': forms.NumberInput(attrs={'class': 'form-control'}),
            'max_usage': forms.NumberInput(attrs={'class': 'form-control'}),
            'valid_from': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
            'valid_until': forms.DateTimeInput(attrs={'class': 'form-control', 'type': 'datetime-local'}),
        }
    
    def clean(self):
        cleaned_data = super().clean()
        valid_from = cleaned_data.get('valid_from')
        valid_until = cleaned_data.get('valid_until')
        
        if valid_from and valid_until:
            if valid_from >= valid_until:
                raise forms.ValidationError('Tanggal berlaku harus lebih awal dari tanggal kadaluarsa')
        
        return cleaned_data 