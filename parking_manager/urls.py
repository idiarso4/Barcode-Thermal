from django.contrib import admin
from django.urls import path, include
from django.contrib.auth import views as auth_views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', include('parking_manager.app_urls')),
    
    # Authentication URLs
    path('login/', auth_views.LoginView.as_view(template_name='parking_manager/login.html'), name='login'),
    path('logout/', auth_views.LogoutView.as_view(next_page='login'), name='logout'),
] 