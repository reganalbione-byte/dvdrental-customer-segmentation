from django.contrib import admin
from django.urls import path, include
from customer_analytics import views

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.home, name='home'),
    path('analytics/', include('customer_analytics.urls')),
]
