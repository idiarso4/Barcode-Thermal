# Generated by Django 5.2 on 2025-04-14 18:56

import django.db.models.deletion
import django.utils.timezone
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('parking', '0001_initial'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Captureticket',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('plat_no', models.CharField(max_length=20)),
                ('date_masuk', models.DateTimeField()),
                ('date_keluar', models.DateTimeField(blank=True, null=True)),
                ('status', models.CharField(max_length=50)),
                ('biaya', models.DecimalField(blank=True, decimal_places=2, max_digits=10, null=True)),
            ],
            options={
                'db_table': 'captureticket',
                'ordering': ['-date_masuk'],
                'managed': False,
            },
        ),
        migrations.AddField(
            model_name='parkingsession',
            name='checked_out_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='checked_out_sessions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.AddField(
            model_name='parkingsession',
            name='created_by',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='created_sessions', to=settings.AUTH_USER_MODEL),
        ),
        migrations.CreateModel(
            name='Shift',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('start_time', models.DateTimeField(default=django.utils.timezone.now)),
                ('end_time', models.DateTimeField(blank=True, null=True)),
                ('is_active', models.BooleanField(default=True)),
                ('total_vehicles', models.IntegerField(default=0)),
                ('total_revenue', models.DecimalField(decimal_places=2, default=0, max_digits=10)),
                ('notes', models.TextField(blank=True, null=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('operator', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.AddField(
            model_name='parkingsession',
            name='shift',
            field=models.ForeignKey(null=True, on_delete=django.db.models.deletion.SET_NULL, to='parking.shift'),
        ),
    ]
