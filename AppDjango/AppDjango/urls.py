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
from loginAdmin import views as loginadmin_views
from torneo import views as torneo_views
from jugador import views as jugador_views

urlpatterns = [
    path('admin/', admin.site.urls),    
    # URLs para la app 
    path('login/', loginadmin_views.admin_login, name='login'),
    path('admin_menu/', loginadmin_views.admin_menu, name='admin_menu'),    
    path('jugador/<str:dni>/', jugador_views.datos_jugador, name='listado_jugador'),  # Cambiado a dni
    path('menu/', loginadmin_views.menu, name='menu'),
    path('', torneo_views.index, name='index'),
    path('admin_carga_jugador/', jugador_views.CrearJugador, name='admin_carga_jugador'),
    path('guardar_jugador/', jugador_views.guardar_jugador, name='guardar_jugador'),
    path('listado_jugadores/', jugador_views.listado_jugadores, name='listado_jugadores'),
    path('abm_categoria/', jugador_views.abm_categoria, name='abm_categoria'),
    path('datos_jugador/<str:dni>/', jugador_views.datos_jugador, name='datos_jugador'),  # Este está correcto
    path('jugadores/', jugador_views.listado_categorias, name='listados_categorias'),
    path('exito_categoria/', jugador_views.exito_categoria, name='exito_categoria'),
    path('categorias/eliminar/<int:id_categoria>/', jugador_views.eliminar_categoria, name='eliminar_categoria'),
    path('borrado_exitoso/<str:jugador_dni>/', jugador_views.borrado_exitoso, name='borrado_exitoso'),  # Cambiado a str
    path('modificar_jugador/<str:dni>/', jugador_views.modificar_jugador, name='modificar_jugador'),
    path('borrar_jugador/<str:dni>/', jugador_views.borrar_jugador, name='borrar_jugador'),
    


]
