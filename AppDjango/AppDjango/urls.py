"""
URL configuration for AppDjango project.

The `urlpatterns` list routes URLs to views. For more information please see:
    https://docs.djangoproject.com/en/5.0/topics/http/urls/
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
from django.urls import path

#impotar app con mis vistas
from loginAdmin import views 

urlpatterns = [
    path('admin/', admin.site.urls),
    path('', views.index, name='index'),  # Ruta para la vista index
    path('login/', views.admin_login, name='login'),  # Ruta para la vista admin_login
    path('admin_menu/', views.admin_menu, name='admin_menu'),
    path('admin_carga_jugador/', views.admin_carga_jugador, name='admin_carga_jugador'),
    path('admin_datos_jugador/', views.admin_datos_jugador, name='admin_datos_jugador'),
    

]
