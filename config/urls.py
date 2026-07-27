"""
URL configuration for config project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.2/topics/http/urls/
Examples:
Function views
    1. Add an import:  from my_app import views
    2. Add a URL to urlpatterns:  path('', views.home, name='home')
Class-based views
    1. Add an import:  from other_app.views import Home
    2. Add a URL to urlpatterns:  path('', Home.as_view(), name='home')
Including another URLconf
    1. Import the include() function: from django.urls import include, path
    2. Add a URL to urlpatterns:  path('blog/', include('blog.urls'))
"""
from django.contrib import admin
from django.urls import path, include
from common.views import HealthCheckView ,get_csrf

urlpatterns = [
    path('admin/', admin.site.urls),
    path('csrf-token/', get_csrf, name="csrf"),
    path('health/', HealthCheckView.as_view(), name="health"),
    path('users/', include("users.urls"), name='users'),
    path('apartments/', include("apartments.urls"), name='apartments'),
    path('tenancy/', include("tenancy.urls"), name='tenancy'),
    path('billings/', include("billing.urls"), name='billing'),
    path('payments/', include("payments.urls"), name='payment'),
]
