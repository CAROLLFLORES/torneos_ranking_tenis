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
from django.urls import path, include
#impotar app con mis vistas
from loginAdmin import views as loginadmin_views
from torneo import views as torneo_views



urlpatterns = [
    path('admin/', admin.site.urls),    
    # URLs para la app 
    path('login/', loginadmin_views.admin_login, name='login'),
    path('admin_menu/', loginadmin_views.admin_menu, name='admin_menu'),
    path('admin_carga_jugador/', loginadmin_views.admin_carga_jugador, name='admin_carga_jugador'),
    path('admin_datos_jugador/', loginadmin_views.admin_datos_jugador, name='admin_datos_jugador'),
    path('menu/', loginadmin_views.menu, name='menu'),
    path('index/', torneo_views.index, name='index'),
    

]

