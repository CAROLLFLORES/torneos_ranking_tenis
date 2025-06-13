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
from django.urls import path, include
from loginAdmin import views as loginadmin_views
from torneo import views as torneo_views
from jugador import views as jugador_views
from ranking import views as ranking_views

from torneo.views import listar_partidos  # ✅ Importa desde torneo, NO desde jugador
from torneo.views import actualizar_ranking, guardar_jornada, historial_jornada, listado_jugadores_master, generar_pdf_partidos_por_fecha
from ranking.views import ranking_torneo, ver_ranking, ranking_general
from ranking.views import confirmar_ascenso_final, ascender_jugadores


urlpatterns = [
    path('',loginadmin_views.index, name='index'),
    path('admin/', admin.site.urls),    
    # URLs para la app 
    path('login/', loginadmin_views.admin_login, name='login'),
    path('admin_menu/', loginadmin_views.admin_menu, name='admin_menu'), 
    path('liga_publico/', torneo_views.liga_publico, name='liga_publico'),    
   
    path('jugador/<str:dni>/', jugador_views.datos_jugador, name='listado_jugador'),  # Cambiado a dni
    path('menu/', loginadmin_views.menu, name='menu'),
    path('admin_carga_jugador/', jugador_views.CrearJugador, name='admin_carga_jugador'),
    path('guardar_jugador/', jugador_views.guardar_jugador, name='guardar_jugador'),
    path('listado_jugadores/', jugador_views.listado_jugadores, name='listado_jugadores'),
    path('exportar_jugadores_pdf/', jugador_views.exportar_jugadores_pdf, name='exportar_jugadores_pdf'),
    path('datos_jugador/<str:dni>/', jugador_views.datos_jugador, name='datos_jugador'),  # Este está correcto


    path('abm_categoria/', jugador_views.abm_categoria, name='abm_categoria'),
    path('jugadores/', jugador_views.listado_categorias, name='listados_categorias'),
    path('exito_categoria/', jugador_views.exito_categoria, name='exito_categoria'),
    path('categorias/eliminar/<int:id_categoria>/', jugador_views.eliminar_categoria, name='eliminar_categoria'),
    path('borrado_exitoso/<str:jugador_dni>/', jugador_views.borrado_exitoso, name='borrado_exitoso'),  # Cambiado a str
    path('modificar_jugador/<str:dni>/', jugador_views.modificar_jugador, name='modificar_jugador'),
    path('borrar_jugador/<str:dni>/', jugador_views.borrar_jugador, name='borrar_jugador'),
    
    path('abm_torneo/', torneo_views.abm_torneo, name='abm_torneo'),
    path('crear_torneo/', torneo_views.crear_torneo, name='crear_torneo'),
    path('eliminar_torneo/<int:id>/', torneo_views.eliminar_torneo, name='eliminar_torneo'),
    path('editar_torneo/<int:id>/', torneo_views.editar_torneo, name='abm_torneo_editar'),
    path('datos_torneo/<int:id>/', torneo_views.ver_caracteristicas_torneo, name='datos_torneo'),
    path('asociar_jugadores/<int:id>/', torneo_views.asociar_jugadores, name='asociar_jugadores'),
    path('redirigir_partidos/<int:torneo_id>/', torneo_views.redirigir_partidos, name='redirigir_partidos'),
    path('partido_doble/<int:torneo_id>/', torneo_views.partido_doble, name='partido_doble'),
    path('partido_single/<int:torneo_id>/', torneo_views.partido_single, name='partido_single'),
    path('torneo/<int:id>/', torneo_views.ver_caracteristicas_torneo, name='ver_caracteristicas_torneo'),
    path('asociar_equipos/<int:id>/', torneo_views.asociar_equipos, name='asociar_equipos'),
    path('redirigir_inscripcion/<int:torneo_id>/', torneo_views.redirigir_inscripcion, name='redirigir_inscripcion'),
    path('guardar_fecha/<int:torneo_id>/', torneo_views.guardar_fecha, name='guardar_fecha'),
    path('abm_cancha/', torneo_views.abm_cancha, name='abm_cancha'),
    path('listado_canchas/', torneo_views.listado_canchas, name='listado_canchas'),
    path('torneo/<int:torneo_id>/jornada/<int:jornada>/', torneo_views.jornada_detalle, name='jornada_detalle'),
    path('eliminar_partido/<int:partido_id>/', torneo_views.eliminar_partido, name='eliminar_partido'),
    path('modificar_partido/<int:partido_id>/', torneo_views.modificar_partido, name='modificar_partido'),
    path('guardar_resultados/', torneo_views.guardar_resultados, name='guardar_resultados'),
    path('validar_partido_existente/<int:torneo_id>/', torneo_views.validar_partido_existente, name='validar_partido_existente'),
    path('partidos/', listar_partidos, name='listar_partidos'),
    path('ranking/<int:torneo_id>/', actualizar_ranking, name='ranking_por_torneo'),
    path('guardar_jornada/<int:torneo_id>/', guardar_jornada, name='guardar_jornada'),
    path('historial/', historial_jornada, name='historial_jornada'),
    path('<int:torneo_id>/', ranking_torneo, name='ranking_torneo'),
    path('torneo/<int:torneo_id>/ranking/', ver_ranking, name='ver_ranking'),
    path('ranking/', ranking_general, name='ranking_general'),

    path('ascenso/', ranking_views.procesar_ascenso, name='procesar_ascenso'),

    path('jugadores_ascendentes/', ascender_jugadores, name='jugadores_ascendentes'),
    path('confirmar_ascenso_final/', confirmar_ascenso_final, name='confirmar_ascenso_final'),
    path('categorias/carga-masiva/', jugador_views.carga_masiva_categoria, name='carga_masiva_categoria'),
    path('canchas/carga-masiva/', torneo_views.carga_masiva_cancha, name='carga_masiva_cancha'),
    path('jugadores/carga-masiva/', jugador_views.carga_masiva_jugadores, name='carga_masiva_jugadores'),
    path('torneos/carga-masiva/', torneo_views.carga_masiva_torneos, name='carga_masiva_torneos'),
    path('master/listado_jugadores/<int:torneo_id>/', torneo_views.listado_jugadores_master, name='listado_jugadores_master'),
    path('generar_pdf_partidos_por_fecha', generar_pdf_partidos_por_fecha, name='generar_pdf_partidos_por_fecha'),

    path('sedes/nueva/', torneo_views.abm_sede, name='abm_sede'),
    path('sedes/listado/', torneo_views.listado_sedes, name='listado_sedes'),
    path("formulario_pdf/", torneo_views.formulario_pdf_fecha_sede, name="formulario_pdf"),

    path('validar_partido_fecha_hora_cancha/', torneo_views.validar_partido_fecha_hora_cancha, name='validar_partido_fecha_hora_cancha'),


]
