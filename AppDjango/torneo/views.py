
# 05/04/2025 - Agrego ID Carga masiva Cancha 100 y Carga Masiva de Torneo 103
# 05/04/2025 - Se esta poniendo en funcionamiento el doble y mixto 104
# 05/04/2025 - Se crear partido Doble 106


# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import TorneoForms
from .models import Torneo, TorneoCategoria, TorneoJugador, Partido, Equipo, Cancha
from jugador.models import Categoria, Jugador
from django.core.paginator import Paginator, PageNotAnInteger, EmptyPage
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
import random
from django.http import JsonResponse, HttpResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json
from django.http import JsonResponse
from torneo.models import Partido, HistorialJornada, Torneo
from django.db.models.signals import post_save
from django.dispatch import receiver
from ranking.models import Ranking, RankingEquipo
from .models import HistorialJornada, Partido, ResultadoPartido
import pandas as pd
from django.db.models import F, Value
from django.db.models.functions import Coalesce
from ranking.views import actualizar_ranking_manual_equipos, actualizar_ranking
#esto agregrue para el guardado de resultaultado por partidofrom django.http import JsonResponse
import json
# NUEVO import para parsear fechas/horas
from datetime import datetime, date, time
from django.http import HttpResponseBadRequest
from ranking.views import actualizar_ranking_manual, revertir_ranking_doble, revertir_ranking_single
from reportlab.lib.pagesizes import A4, landscape
from reportlab.pdfgen import canvas
from reportlab.lib.units import cm
from reportlab.platypus import Table, TableStyle
from reportlab.lib import colors
from .models import Sede
from django.db import transaction
from django.contrib.auth import authenticate, login
from django.contrib.auth.decorators import user_passes_test
import os
from django.conf import settings
from datetime import datetime, timedelta


ruta_imagen = os.path.join(settings.BASE_DIR, 'static', 'imagenes', 'apur.png')

def es_admin(user):
    return user.is_authenticated and user.is_staff


def liga_publico(request):
    return render(request, 'liga_publico.html')


def contar_sets_ganados(set1_a, set1_b, set2_a, set2_b, set3_a, set3_b):
    sets_ganados = 0
    if set1_a != 0 or set1_b != 0:
        if set1_a > set1_b:
            sets_ganados += 1
    if set2_a != 0 or set2_b != 0:
        if set2_a > set2_b:
            sets_ganados += 1
    if set3_a != 0 or set3_b != 0:
        if set3_a > set3_b:
            sets_ganados += 1
    return sets_ganados




def abm_torneo(request):
    all_categorias = Categoria.objects.all()
    categoria_id = request.GET.get('categoria')
    search_query = request.GET.get('search')
    fecha = request.GET.get('fecha')  # <- este campo nuevo

    form = TorneoForms()

    torneos = Torneo.objects.all().order_by('-fecha_inicio')

    if categoria_id:
        torneos = torneos.filter(torneo_categorias__categoria__id_categoria=categoria_id)

    if search_query:
        torneos = torneos.filter(nombre__icontains=search_query)

    if fecha:
        torneos = torneos.filter(fecha_inicio=fecha)

    paginator = Paginator(torneos, 50)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    sedes = Sede.objects.all()

    filtros = {
        'search': search_query,
        'categoria': categoria_id,
        'fecha': fecha,
    }

    return render(request, 'abm_torneo.html', {
        'form': form,
        'page_obj': page_obj,
        'all_categorias': all_categorias,
        'categoria_id': categoria_id,
        'search': search_query,
        'sedes': sedes,
        'filtros': filtros,
    })

def crear_torneo(request):
    if request.method == 'POST':
        form = TorneoForms(request.POST)
        if form.is_valid():
            categorias = form.cleaned_data['categorias']
            try:
                with transaction.atomic():
                    torneo = form.save()
                    for categoria in categorias:
                        TorneoCategoria.objects.get_or_create(torneo=torneo, categoria=categoria)
                messages.success(request, 'Torneo creado exitosamente.')
                # form = TorneoForms()
                return redirect('abm_torneo')
            except IntegrityError:
                messages.error(request, 'Error: Ya existe una relación entre este torneo y una de las categorías seleccionadas.')
            except Exception as e:
                messages.error(request, f'Error al crear el torneo: {e}')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = TorneoForms()
    
    torneos = Torneo.objects.all().order_by('nombre').prefetch_related('categorias')
    paginator = Paginator(torneos, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    all_categorias = Categoria.objects.all()
    sedes = Sede.objects.all()


    return render(request, 'abm_torneo.html', {
        'form': form,
        'page_obj': page_obj,
        'all_categorias': all_categorias,
        'sedes': sedes,

    })


@require_POST
def eliminar_torneo(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    torneo.delete()
    messages.success(request, 'Torneo eliminado exitosamente.')
    return redirect('abm_torneo')



def editar_torneo(request, id):
    torneo = get_object_or_404(Torneo, id=id)

    if request.method == 'POST':
        form = TorneoForms(request.POST, instance=torneo)

        if form.is_valid():
            categorias = form.cleaned_data['categorias']

            try:
                with transaction.atomic():
                    # Solo actualizás los campos del torneo, NO categorías
                    torneo.nombre = form.cleaned_data['nombre']
                    torneo.fecha_inicio = form.cleaned_data['fecha_inicio']
                    torneo.fecha_fin = form.cleaned_data['fecha_fin']
                    torneo.tipo = form.cleaned_data['tipo']
                    torneo.save()

                    # Limpiar y actualizar las categorías
                    TorneoCategoria.objects.filter(torneo=torneo).delete()
                    for categoria in categorias:
                        TorneoCategoria.objects.create(torneo=torneo, categoria=categoria)

                messages.success(request, 'Torneo actualizado exitosamente.')
                return redirect('abm_torneo')

            except IntegrityError:
                messages.error(request, 'Error: Ya existe una relación entre este torneo y una de las categorías seleccionadas.')
            except Exception as e:
                messages.error(request, f'Error al actualizar el torneo: {e}')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = TorneoForms(instance=torneo)

    return render(request, 'editar_torneo.html', {'form': form, 'torneo': torneo})

def programacion(request):
    torneos = Torneo.objects.order_by('nombre')

    if not torneos.exists():
        empty_qs = Partido.objects.none()
        paginator = Paginator(empty_qs, 30)
        page_obj = paginator.get_page(1)
        return render(request, 'programacion.html', {
            'torneo': None,
            'torneos': [],
            'es_doble': False,
            'jornada': 'Todas',
            'numero_jornada': 0,
            'partidos': page_obj,
            'canchas': Cancha.objects.all(),
            'filtros': {'torneo': '', 'fecha': '', 'search': ''},
            'mensaje': 'No hay torneos disponibles.'
        })

    torneo_id = request.GET.get('torneo', '')
    fecha = request.GET.get('fecha', '')
    search = request.GET.get('search', '').strip()

    partidos_qs = Partido.objects.select_related(
        'torneo', 'cancha', 'resultado',
        'equipo1__jugador1', 'equipo1__jugador2',
        'equipo2__jugador1', 'equipo2__jugador2',
        'jugador1', 'jugador2'
    )

    if torneo_id:
        partidos_qs = partidos_qs.filter(torneo__id=torneo_id)
    if fecha:
        partidos_qs = partidos_qs.filter(fecha=fecha)
    if search:
        partidos_qs = partidos_qs.filter(
            Q(equipo1__jugador1__nombre__icontains=search) |
            Q(equipo1__jugador1__apellido__icontains=search) |
            Q(equipo1__jugador2__nombre__icontains=search) |
            Q(equipo1__jugador2__apellido__icontains=search) |
            Q(equipo2__jugador1__nombre__icontains=search) |
            Q(equipo2__jugador1__apellido__icontains=search) |
            Q(equipo2__jugador2__nombre__icontains=search) |
            Q(equipo2__jugador2__apellido__icontains=search) |
            Q(jugador1__nombre__icontains=search) |
            Q(jugador1__apellido__icontains=search) |
            Q(jugador2__nombre__icontains=search) |
            Q(jugador2__apellido__icontains=search)
        )

    partidos_qs = partidos_qs.order_by('-fecha', '-hora', 'cancha')
    paginator = Paginator(partidos_qs, 30)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'programacion.html', {
        'torneos': torneos,
        'partidos': page_obj,
        'canchas': Cancha.objects.all(),
        'filtros': {'torneo': torneo_id, 'fecha': fecha, 'search': search},
    })
  
def datos_torneo(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    es_doble = torneo.categorias.filter(
        Q(tipo_juego__iexact='Doble') | Q(tipo_juego__iexact='Mixto')
    ).exists()

    # jornadas = Partido.objects.filter(torneo=torneo).values('jornada').distinct().order_by('jornada')
    # no usamos jornadas
    numero_jornada = 0
    canchas = Cancha.objects.all()

    if request.method == 'POST':
        return handle_post_datos_torneo(request, torneo, es_doble, numero_jornada)

    return handle_get_datos_torneo(request, torneo, es_doble, numero_jornada, canchas)

def handle_get_datos_torneo(request, torneo, es_doble, numero_jornada, canchas):
    fecha = request.GET.get('fecha', '')
    hora = request.GET.get('hora', '')
    cancha_id = request.GET.get('cancha', '')
    search = request.GET.get('search', '').strip()

    if es_doble:
        partidos_qs = Partido.objects.filter(torneo=torneo).select_related(
            'equipo1__jugador1', 'equipo1__jugador2',
            'equipo2__jugador1', 'equipo2__jugador2',
            'cancha', 'resultado'
        )

        if search:
            partidos_qs = partidos_qs.filter(
                Q(equipo1__jugador1__nombre__icontains=search) |
                Q(equipo1__jugador1__apellido__icontains=search) |
                Q(equipo1__jugador2__nombre__icontains=search) |
                Q(equipo1__jugador2__apellido__icontains=search) |
                Q(equipo2__jugador1__nombre__icontains=search) |
                Q(equipo2__jugador1__apellido__icontains=search) |
                Q(equipo2__jugador2__nombre__icontains=search) |
                Q(equipo2__jugador2__apellido__icontains=search)
            )

        if fecha:
            partidos_qs = partidos_qs.filter(fecha=fecha)

        if hora:
            partidos_qs = partidos_qs.filter(hora=hora)

        if cancha_id:
            partidos_qs = partidos_qs.filter(cancha__id=cancha_id)

        partidos_qs = partidos_qs.order_by('-fecha', '-hora', 'cancha')
        paginator = Paginator(partidos_qs, 30)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        equipos = Equipo.objects.filter(torneo=torneo).select_related('jugador1', 'jugador2').order_by('jugador1__apellido')

        return render(request, 'datos_torneo.html', {
            'torneo': torneo,
            'es_doble': True,
            'jornada': 'Todas',
            'numero_jornada': numero_jornada,
            'partidos': page_obj,
            'equipos': equipos,
            'canchas': canchas,
            'filtros': {
                'fecha': fecha,
                'hora': hora,
                'cancha': cancha_id,
                'search': search,
            }
        })
    else:
        partidos_qs = Partido.objects.filter(torneo=torneo).select_related(
            'jugador1', 'jugador2', 'cancha', 'resultado'
        )

        if search:
            partidos_qs = partidos_qs.filter(
                Q(jugador1__nombre__icontains=search) |
                Q(jugador1__apellido__icontains=search) |
                Q(jugador2__nombre__icontains=search) |
                Q(jugador2__apellido__icontains=search)
            )

        if fecha:
            partidos_qs = partidos_qs.filter(fecha=fecha)

        if hora:
            partidos_qs = partidos_qs.filter(hora=hora)

        if cancha_id:
            partidos_qs = partidos_qs.filter(cancha__id=cancha_id)

        partidos_qs = partidos_qs.order_by('-fecha', '-hora', 'cancha')
        paginator = Paginator(partidos_qs, 30)
        page_number = request.GET.get('page')
        page_obj = paginator.get_page(page_number)

        # Traer jugadores del torneo sin usar ranking
        jugadores = Jugador.objects.filter(
            jugador_torneos__torneo=torneo  # relación que indica que el jugador participa en este torneo
        ).distinct().order_by('apellido', 'nombre')


        return render(request, 'datos_torneo.html', {
            'torneo': torneo,
            'es_doble': False,
            'jornada': 'Todas',
            'numero_jornada': numero_jornada,
            'partidos': page_obj,
            'jugadores': jugadores,
            'canchas': canchas,
            'filtros': {
                'fecha': fecha,
                'hora': hora,
                'cancha': cancha_id,
                'search': search,
            }
        })

def handle_post_datos_torneo(request, torneo, es_doble, numero_jornada):
    fechas = request.POST.getlist('fecha[]')
    horas = request.POST.getlist('hora[]')
    canchas_post = request.POST.getlist('cancha[]')
    forzar_creacion = request.POST.get('forzar') == '1'

    advertencias = []
    partidos_creados = []

    if es_doble:
        equipos1 = request.POST.getlist('jugador1[]')
        equipos2 = request.POST.getlist('jugador2[]')
        if not equipos1 or not equipos2 or not fechas or not horas or not canchas_post:
            return JsonResponse({'status': 'error', 'messages': ['Faltan datos para crear partidos dobles.']})

        for equipo1, equipo2, fecha_str, hora_str, cancha_id in zip(equipos1, equipos2, fechas, horas, canchas_post):
            partido, advertencia = crear_partido(
                torneo=torneo,
                jornada=numero_jornada,
                jugador1_id=equipo1,
                jugador2_id=equipo2,
                fecha_str=fecha_str,
                hora_str=hora_str,
                cancha_id=cancha_id,
                es_doble=True,
                forzar_creacion=forzar_creacion
            )
            if advertencia:
                advertencias.extend(advertencia if isinstance(advertencia, list) else [advertencia])
            elif partido:
                partidos_creados.append(partido)

    else:
        jugadores1 = request.POST.getlist('jugador1[]')
        jugadores2 = request.POST.getlist('jugador2[]')
        if not jugadores1 or not jugadores2 or not fechas or not horas or not canchas_post:
            return JsonResponse({'status': 'error', 'messages': ['Faltan datos para crear partidos individuales.']})

        for jugador1, jugador2, fecha_str, hora_str, cancha_id in zip(jugadores1, jugadores2, fechas, horas, canchas_post):
            partido, advertencia = crear_partido(
                torneo=torneo,
                jornada=numero_jornada,
                jugador1_id=jugador1,
                jugador2_id=jugador2,
                fecha_str=fecha_str,
                hora_str=hora_str,
                cancha_id=cancha_id,
                es_doble=False,
                forzar_creacion=forzar_creacion
            )
            if advertencia:
                advertencias.extend(advertencia if isinstance(advertencia, list) else [advertencia])
            elif partido:
                partidos_creados.append(partido)

    if advertencias and not forzar_creacion:
        return JsonResponse({'status': 'conflicto', 'messages': advertencias})

    if partidos_creados:
        return JsonResponse({'status': 'ok', 'messages': []})

    return JsonResponse({'status': 'error', 'messages': ['No se pudieron crear los partidos.']})

def crear_partido(torneo, jornada, jugador1_id, jugador2_id, fecha_str, hora_str, cancha_id, es_doble=False, forzar_creacion=False):
    try:
        fecha_obj = date.fromisoformat(fecha_str)
        hora_obj = datetime.strptime(hora_str, '%H:%M').time()
    except ValueError as e:
        return None, f"Error en fecha/hora: {e}"

    advertencias = []

    # Validación 1: jugadores o equipos ya se enfrentaron en el torneo
    if es_doble:
        ya_jugaron = Partido.objects.filter(
            torneo=torneo,
            equipo1_id=jugador1_id,
            equipo2_id=jugador2_id
        ).exists() or Partido.objects.filter(
            torneo=torneo,
            equipo1_id=jugador2_id,
            equipo2_id=jugador1_id
        ).exists()
    else:
        ya_jugaron = Partido.objects.filter(
            torneo=torneo,
            jugador1_id=jugador1_id,
            jugador2_id=jugador2_id
        ).exists() or Partido.objects.filter(
            torneo=torneo,
            jugador1_id=jugador2_id,
            jugador2_id=jugador1_id
        ).exists()

    if ya_jugaron:
        tipo = 'equipos' if es_doble else 'jugadores'
        advertencias.append(f"Ya existe un partido entre estos {tipo} en este torneo.")

    # Validación 2: misma hora y cancha
    conflicto = Partido.objects.filter(
        fecha=fecha_obj,
        hora=hora_obj,
        cancha_id=cancha_id
    ).exists()

    if conflicto:
        advertencias.append("Ya hay un partido programado en esa cancha y hora.")

    # Si hay advertencias y NO se está forzando, no se crea
    if advertencias and not forzar_creacion:
        return None, advertencias

    # Si no hay advertencias o se está forzando, se crea igual
    partido = Partido(
        torneo=torneo,
        jornada=jornada,
        fecha=fecha_obj,
        hora=hora_obj,
        cancha_id=cancha_id
    )

    if es_doble:
        partido.equipo1_id = jugador1_id
        partido.equipo2_id = jugador2_id
    else:
        partido.jugador1_id = jugador1_id
        partido.jugador2_id = jugador2_id

    partido.save()
    return partido, None


def ver_caracteristicas_torneo(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    return render(request, 'datos_torneo.html', {'torneo': torneo})


def asociar_jugadores(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    search = request.GET.get('search', '')  # ✅ Captura el texto de búsque
    
    if torneo.tipo == 'F':
        jugadores_disponibles = Jugador.objects.filter(sexo='F').exclude(jugador_torneos__torneo=torneo)
    elif torneo.tipo == 'M':
        jugadores_disponibles = Jugador.objects.filter(sexo='M').exclude(jugador_torneos__torneo=torneo)
    elif torneo.tipo == 'Mixto':
        jugadores_disponibles = Jugador.objects.filter(sexo__in=['F', 'M']).exclude(jugador_torneos__torneo=torneo)
    else:
        jugadores_disponibles = Jugador.objects.none()
        
        
    # ✅ Filtrar si hay búsqueda
    if search:
        jugadores_disponibles = jugadores_disponibles.filter(
            Q(nombre__icontains=search) | Q(apellido__icontains=search)
        )

    # ✅ Excluir ya asociados y ordenar
   
    jugadores_disponibles = jugadores_disponibles.order_by('apellido', 'nombre')  # ✅ solo una vez
    jugadores_asociados = Jugador.objects.filter(jugador_torneos__torneo=torneo).order_by('apellido', 'nombre')
    
    if request.method == 'POST':
        action = request.POST.get('action')
        jugadores_dni = request.POST.getlist('jugadores')
        jugadores_seleccionados_dni = request.POST.getlist('jugadores_seleccionados')

        try:
            with transaction.atomic():
                if action == "asociar":
                    if jugadores_dni:
                        jugadores = Jugador.objects.filter(dni__in=jugadores_dni)
                        for jugador in jugadores:
                            TorneoJugador.objects.get_or_create(torneo=torneo, jugador=jugador)
                            
                            # ✅ Crear entrada en RANKING si no existe
                            Ranking.objects.get_or_create(
                                jugador=jugador,
                                torneo=torneo,
                                defaults={
                                    "categoria": torneo.categorias.first(),
                                    "anio": torneo.fecha_inicio.year,
                                    "bimestre": 1,  # o el que corresponda
                                    "pj": 0,
                                    "pg": 0,
                                    "pp": 0,
                                    "games": 0,
                                    "sets": 0,
                                    "puntaje_total_categoria": 0,
                                    "puntaje_acumulador": 0,
                                    "activo": True  # ✅ para que sea visible
                                }
                            )
                        messages.success(request, 'Jugadores asociados exitosamente al torneo.')

                elif action == "desasociar":
                    if jugadores_seleccionados_dni:
                        jugadores = Jugador.objects.filter(dni__in=jugadores_seleccionados_dni)
                        TorneoJugador.objects.filter(torneo=torneo, jugador__in=jugadores).delete()
                        messages.success(request, 'Jugadores desasociados exitosamente del torneo.')

            return redirect('asociar_jugadores', torneo.id)

        except IntegrityError:
            messages.error(request, 'Ocurrió un error con la base de datos.')
        except Exception as e:
            messages.error(request, f'Error al procesar la solicitud: {e}')

    return render(request, 'asociar_jugadores.html', {
        'torneo': torneo,
        'jugadores_disponibles': jugadores_disponibles,
        'jugadores_asociados': jugadores_asociados,
        'search': search
    })

#--------------------------------------------------------------------------------------------------------------
@csrf_exempt
def asociar_equipos(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    search = request.GET.get('search', '').strip()
    search1 = request.GET.get('search1', '').strip()
    search2 = request.GET.get('search2', '').strip()
    modo_equipo = request.GET.get('busqueda_equipo') == '1'


    jugadores_disponibles = Jugador.objects.none()
    if torneo.tipo == 'F':
        jugadores_disponibles = Jugador.objects.filter(sexo='F')
    elif torneo.tipo == 'M':
        jugadores_disponibles = Jugador.objects.filter(sexo='M')
    elif torneo.tipo == 'Mixto':
        jugadores_disponibles = Jugador.objects.filter(sexo__in=['F', 'M'])

    # Excluir jugadores ya en equipos del torneo
    jugadores_en_equipo = Equipo.objects.filter(torneo=torneo).values_list('jugador1__dni', 'jugador2__dni')
    dnis_en_equipo = [dni for par in jugadores_en_equipo for dni in par]
    jugadores_disponibles = jugadores_disponibles.exclude(dni__in=dnis_en_equipo)

    # ✅ Aplicar búsqueda si hay texto ingresado
    # ✅ Buscar solo si no es modo_equipo (esto mantiene el comportamiento anterior)
    if not modo_equipo and search:
        jugadores_disponibles = jugadores_disponibles.filter(
            Q(nombre__icontains=search) | Q(apellido__icontains=search)
        )

# ✅ Lógica de búsqueda doble exclusiva de esta vista
    if modo_equipo and (search1 or search2):
        filtros = Q()
        if search1:
            filtros |= Q(nombre__icontains=search1) | Q(apellido__icontains=search1)
        if search2:
            filtros |= Q(nombre__icontains=search2) | Q(apellido__icontains=search2)
        jugadores_disponibles = jugadores_disponibles.filter(filtros).distinct()


    # Ordenar por apellido y nombre
    jugadores_disponibles = jugadores_disponibles.order_by('apellido', 'nombre')

    equipos_asociados = Equipo.objects.filter(torneo=torneo).select_related('jugador1', 'jugador2')

    if request.method == 'POST':
        action = request.POST.get('action')

        if action == "crear_equipo":
            jugador1_id = request.POST.get('jugador1')
            jugador2_id = request.POST.get('jugador2')

            if jugador1_id and jugador2_id and jugador1_id != jugador2_id:
                jugador1 = get_object_or_404(Jugador, dni=jugador1_id)
                jugador2 = get_object_or_404(Jugador, dni=jugador2_id)

                equipo_existente = Equipo.objects.filter(
                    torneo=torneo
                ).filter(
                    Q(jugador1=jugador1, jugador2=jugador2) |
                    Q(jugador1=jugador2, jugador2=jugador1)
                ).exists()

                if equipo_existente:
                    return JsonResponse({'success': False, 'error': 'Este equipo ya existe.'})

                nuevo_equipo = Equipo.objects.create(
                    torneo=torneo,
                    jugador1=jugador1,
                    jugador2=jugador2
                )

                total_equipos = Equipo.objects.filter(torneo=torneo).count()

                return JsonResponse({
                    'success': True,
                    'equipo_id': nuevo_equipo.id,
                    'jugador1_dni': jugador1.dni,
                    'jugador2_dni': jugador2.dni,
                    'jugador1_nombre': f"{jugador1.apellido} {jugador1.nombre}",
                    'jugador2_nombre': f"{jugador2.apellido} {jugador2.nombre}",
                    'equipo_numero': total_equipos,
                    'total_equipos': total_equipos
                })

        elif action == "desasociar":
            equipos_ids = request.POST.getlist('equipos[]')

            jugadores_reintegrados = []
            for equipo_id in equipos_ids:
                equipo = get_object_or_404(Equipo, id=equipo_id, torneo=torneo)
                jugadores_reintegrados.append({
                    'dni': equipo.jugador1.dni,
                    'nombre': f"{equipo.jugador1.apellido} {equipo.jugador1.nombre}"
                })
                jugadores_reintegrados.append({
                    'dni': equipo.jugador2.dni,
                    'nombre': f"{equipo.jugador2.apellido} {equipo.jugador2.nombre}"
                })
                equipo.delete()

            return JsonResponse({
                'success': True,
                'jugadores_reintegrados': jugadores_reintegrados,
                'equipos_eliminados': equipos_ids
            })

    all_messages = [m.message for m in messages.get_messages(request)]
    return render(request, 'asociar_equipos.html', {
    'torneo': torneo,
    'jugadores_disponibles': jugadores_disponibles,
    'equipos_asociados': equipos_asociados,
    'all_messages': all_messages,
    'search': search,
    'search1': search1,
    'search2': search2,
    'modo_equipo': modo_equipo,
})


#-------------------------------------------------------------------------------------------------------------- 

def redirigir_inscripcion(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    categorias = torneo.categorias.all()
    tiene_doble = categorias.filter(tipo_juego__iexact='Doble').exists()
    tiene_mixto = categorias.filter(tipo_juego__iexact='Mixto').exists()

    if tiene_doble or tiene_mixto:
        return redirect('asociar_equipos', id=torneo.id)
    else:
        return redirect('asociar_jugadores', id=torneo.id)



def redirigir_partidos(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    # es_doble = torneo.categorias.filter(tipo_juego__iexact='Doble').exists()
    es_doble = torneo.categorias.filter(Q(tipo_juego__iexact='Doble') | Q(tipo_juego__iexact='Mixto')).exists()


    if es_doble:
        return redirect('partido_doble', torneo_id=torneo.id)
    else:
        return redirect('partido_single', torneo_id=torneo.id)


#--------------------------------------------------------------------------------------------------------------
#partido Doble 106
def partido_doble(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    if request.method == 'POST':
        numero_jornada = request.POST.get('numero_jornada')
        equipos1 = request.POST.getlist('jugador1[]')  # Ahora representa equipo1
        equipos2 = request.POST.getlist('jugador2[]')  # Ahora representa equipo2
        fechas = request.POST.getlist('fecha[]')
        horas = request.POST.getlist('hora[]')
        canchas = request.POST.getlist('cancha[]')

        if not equipos1 or not equipos2 or not fechas or not horas or not canchas:
            messages.error(request, "No se recibieron todos los datos necesarios desde el formulario.")
            return redirect('partido_doble', torneo_id=torneo_id)

        advertencias = []
        partidos_creados = []

        for equipo1, equipo2, fecha_str, hora_str, cancha_id in zip(equipos1, equipos2, fechas, horas, canchas):
            try:
                fecha_obj = date.fromisoformat(fecha_str)
                hora_obj = datetime.strptime(hora_str, '%H:%M').time()
            except ValueError as e:
                messages.warning(request, f"Error en fecha/hora: {e}")
                continue

            if Partido.objects.filter(
                torneo=torneo,
                jornada=numero_jornada,
                equipo1_id=equipo1,
                equipo2_id=equipo2
            ).exists():
                advertencias.append(f"El partido entre equipo {equipo1} y equipo {equipo2} ya existe.")
                continue

            partido = Partido(
                torneo=torneo,
                jornada=numero_jornada,
                equipo1_id=equipo1,  # ✅ BIEN
                equipo2_id=equipo2,  # ✅ BIEN
                fecha=fecha_obj,
                hora=hora_obj,
                cancha_id=cancha_id
            )
            partido.save()
            partidos_creados.append(partido)

        if advertencias:
            for adv in advertencias:
                messages.warning(request, adv)
        if partidos_creados:
            messages.success(
                request,
                f"Se han creado {len(partidos_creados)} partidos para la jornada {numero_jornada}."
            )

        return redirect('partido_doble', torneo_id=torneo_id)

    # Render GET
    jornadas = Partido.objects.filter(torneo=torneo).values('jornada').distinct().order_by('jornada')
    numero_jornada = jornadas.count() + 1
    equipos = Equipo.objects.filter(torneo=torneo).select_related('jugador1', 'jugador2').order_by('jugador1__apellido')
    canchas = Cancha.objects.all()

    return render(request, 'partido_doble.html', {
        'torneo': torneo,
        'numero_jornada': numero_jornada,
        'equipos': equipos,
        'canchas': canchas,
        'jornadas': jornadas,
    })

#--------------------------------------------------------------------------------------------------------------

from datetime import datetime, date
def guardar_fecha(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    if request.method == 'POST':
        numero_jornada = request.POST.get('numero_jornada')
        fechas = request.POST.getlist('fecha[]')
        horas = request.POST.getlist('hora[]')
        canchas = request.POST.getlist('cancha[]')

        if torneo.tipo_juego in ['Doble', 'Mixto']:
            jugadores1 = request.POST.getlist('jugador1[]')  # en realidad, equipos
            jugadores2 = request.POST.getlist('jugador2[]')
        else:
            jugadores1 = request.POST.getlist('jugador1[]')
            jugadores2 = request.POST.getlist('jugador2[]')

        partidos_creados = []

        for i in range(len(fechas)):
            try:
                partido = Partido(
                    torneo=torneo,
                    jornada=numero_jornada,
                    fecha=date.fromisoformat(fechas[i]),
                    hora=datetime.strptime(horas[i], '%H:%M').time(),
                    cancha_id=canchas[i]
                )

                if torneo.tipo_juego in ['Doble', 'Mixto']:
                    partido.equipo1_id = jugadores1[i]
                    partido.equipo2_id = jugadores2[i]
                else:
                    partido.jugador1_id = jugadores1[i]
                    partido.jugador2_id = jugadores2[i]

                partido.save()
                partidos_creados.append(partido)

            except Exception as e:
                print(f"❌ Error al guardar el partido en la fila {i + 1}: {str(e)}")

        if partidos_creados:
            messages.success(request, f"✅ Se guardaron {len(partidos_creados)} partidos correctamente.")

        return redirect('jornada_detalle', torneo_id=torneo.id, jornada=numero_jornada)

    return redirect('jornada_detalle', torneo_id=torneo.id, jornada=request.POST.get('numero_jornada'))

@csrf_exempt
def guardar_resultados2(request):
    if request.method != 'POST':
        return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

    try:
        data = json.loads(request.body)
        partido_id = data.get('partido_id')
        partido = get_object_or_404(Partido, id=partido_id)
        torneo = partido.torneo
        es_doble = torneo.tipo_juego in ['Doble', 'Mixto']

        # ----------------------
        # 1) Guardar datos administrativos SIEMPRE
        # ----------------------
        # Fecha / Hora
        if 'fecha' in data:
            partido.fecha = data.get('fecha')
        if 'hora' in data:
            partido.hora = data.get('hora')

        # Cancha (si viene)
        cancha_id = data.get('cancha')
        if cancha_id:
            partido.cancha = get_object_or_404(Cancha, id=int(cancha_id))

        # Jugadores / Equipos (si vienen, se actualizan siempre)
        if es_doble:
            equipo1_id = data.get('equipo1_id')
            equipo2_id = data.get('equipo2_id')
            partido.equipo1 = Equipo.objects.get(id=int(equipo1_id)) if equipo1_id else None
            partido.equipo2 = Equipo.objects.get(id=int(equipo2_id)) if equipo2_id else None
            partido.jugador1 = None
            partido.jugador2 = None
        else:
            dni_jugador1 = data.get('jugador1_dni')
            dni_jugador2 = data.get('jugador2_dni')
            partido.jugador1 = Jugador.objects.get(dni=int(dni_jugador1)) if dni_jugador1 else None
            partido.jugador2 = Jugador.objects.get(dni=int(dni_jugador2)) if dni_jugador2 else None
            partido.equipo1 = None
            partido.equipo2 = None

        partido.save()

        # ----------------------
        # 2) Determinar si el payload TRAE datos de resultado
        # ----------------------
        result_keys = [
            'set1_jugador1','set2_jugador1','set3_jugador1',
            'set1_jugador2','set2_jugador2','set3_jugador2',
            # ganador keys:
            'ganador_dni','ganador_equipo_id'
        ]

        def key_has_value(d, k):
            return (k in d) and (d[k] is not None) and (str(d[k]).strip() != "")

        has_result_payload = any(key_has_value(data, k) for k in result_keys)

        # Obtener resultado anterior (si existe)
        resultado_original = ResultadoPartido.objects.filter(partido=partido).first()

        # Si NO existe resultado anterior y NO hay payload de resultado: no creamos ni tocamos ResultadoPartido
        if not resultado_original and not has_result_payload:
            return JsonResponse({'success': True, 'message': '✅ Partido actualizado (sin resultados).'})


        # ----------------------
        # 3) Crear o tomar el objeto ResultadoPartido
        # ----------------------
        if resultado_original:
            resultado = resultado_original
            es_edicion = True
        else:
            resultado = ResultadoPartido(partido=partido)
            es_edicion = False

        # Guardar copia de datos anteriores para comparar (puede ser None si no existía)
        if resultado_original:
            if es_doble:
                datos_anteriores = (
                    resultado_original.set1_equipo1,
                    resultado_original.set2_equipo1,
                    resultado_original.set3_equipo1,
                    resultado_original.set1_equipo2,
                    resultado_original.set2_equipo2,
                    resultado_original.set3_equipo2,
                    resultado_original.ganador_equipo_id
                )
            else:
                datos_anteriores = (
                    resultado_original.set1_jugador1,
                    resultado_original.set2_jugador1,
                    resultado_original.set3_jugador1,
                    resultado_original.set1_jugador2,
                    resultado_original.set2_jugador2,
                    resultado_original.set3_jugador2,
                    resultado_original.ganador_jugador_id
                )
        else:
            datos_anteriores = None

        # ----------------------
        # 4) Asignar campos de resultado SOLO si vienen en el payload
        #     (si no vienen, no tocamos el campo)
        # ----------------------
        def asignar_int_si_presente(attr_name, key_name):
            if key_name in data:
                raw = data.get(key_name)
                if raw is None or str(raw).strip() == "":
                    setattr(resultado, attr_name, None)
                else:
                    try:
                        setattr(resultado, attr_name, int(raw))
                    except (ValueError, TypeError):
                        setattr(resultado, attr_name, None)

        if es_doble:
            # sets mapeados a campos de equipo
            asignar_int_si_presente('set1_equipo1', 'set1_jugador1')
            asignar_int_si_presente('set2_equipo1', 'set2_jugador1')
            asignar_int_si_presente('set3_equipo1', 'set3_jugador1')
            asignar_int_si_presente('set1_equipo2', 'set1_jugador2')
            asignar_int_si_presente('set2_equipo2', 'set2_jugador2')
            asignar_int_si_presente('set3_equipo2', 'set3_jugador2')

            # ganador: solo si la clave viene en payload
            if 'ganador_equipo_id' in data:
                ganador_equipo_id = data.get('ganador_equipo_id')
                if ganador_equipo_id is None or str(ganador_equipo_id).strip() == "":
                    resultado.ganador_equipo = None
                else:
                    resultado.ganador_equipo = Equipo.objects.get(id=int(ganador_equipo_id))
                resultado.ganador_jugador = None
        else:
            # singles: sets ya tienen nombres correctos
            asignar_int_si_presente('set1_jugador1', 'set1_jugador1')
            asignar_int_si_presente('set2_jugador1', 'set2_jugador1')
            asignar_int_si_presente('set3_jugador1', 'set3_jugador1')
            asignar_int_si_presente('set1_jugador2', 'set1_jugador2')
            asignar_int_si_presente('set2_jugador2', 'set2_jugador2')
            asignar_int_si_presente('set3_jugador2', 'set3_jugador2')

            # ganador: solo si la clave viene
            if 'ganador_dni' in data:
                ganador_dni = data.get('ganador_dni')
                if ganador_dni is None or str(ganador_dni).strip() == "":
                    resultado.ganador_jugador = None
                else:
                    resultado.ganador_jugador = Jugador.objects.get(dni=int(ganador_dni))
                resultado.ganador_equipo = None

        # ----------------------
        # 5) Comparar y guardar si cambió algo
        # ----------------------
        if es_doble:
            datos_nuevos = (
                resultado.set1_equipo1,
                resultado.set2_equipo1,
                resultado.set3_equipo1,
                resultado.set1_equipo2,
                resultado.set2_equipo2,
                resultado.set3_equipo2,
                resultado.ganador_equipo_id
            )
        else:
            datos_nuevos = (
                resultado.set1_jugador1,
                resultado.set2_jugador1,
                resultado.set3_jugador1,
                resultado.set1_jugador2,
                resultado.set2_jugador2,
                resultado.set3_jugador2,
                resultado.ganador_jugador_id
            )

        # Si no existía resultado anterior y no hubo cambios en resultado -> dejamos sin crear
        if resultado_original is None and datos_nuevos == (None, None, None, None, None, None, None):
            # No hay nada de resultado para guardar
            return JsonResponse({'success': True, 'message': '✅ Partido actualizado (sin resultados).'})


        # Si hay diferencias, guardamos y ejecutamos la lógica asociada
        if datos_anteriores != datos_nuevos:
            # desconectar señal temporalmente
            # from django.db.models.signals import post_save
            # post_save.disconnect(actualizar_ranking, sender=ResultadoPartido)

            resultado.save()

            # reconectar señal
            # post_save.connect(actualizar_ranking, sender=ResultadoPartido)

            # Aquí podés reactivar la lógica de ranking manual si la necesitás:
            # if es_edicion:
            #     ... revertir ranking ...
            # actualizar_ranking_manual(resultado)  # o la función que uses

            return JsonResponse({'success': True, 'message': '✅ Resultado actualizado correctamente.'})
        else:
            # No cambió el resultado (pero sí pueden haber cambiado los datos del partido)
            return JsonResponse({'success': True, 'message': '⚠️ Se modificaron los datos del partido.'})

    except Exception as e:
        import traceback
        traceback.print_exc()
        return JsonResponse({'success': False, 'message': str(e)})


@csrf_exempt
def guardar_resultados(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            partido_id = data.get('partido_id')
            partido = Partido.objects.get(id=partido_id)
            torneo = partido.torneo
            es_doble = torneo.tipo_juego in ['Doble', 'Mixto']

            resultado = ResultadoPartido.objects.filter(partido=partido).first()
            es_edicion = resultado is not None

            if not resultado:
                resultado = ResultadoPartido(partido=partido)

            # Copia del resultado anterior para comparar
            resultado_original = ResultadoPartido.objects.filter(partido=partido).first()
            datos_anteriores = (
                resultado_original.set1_jugador1,
                resultado_original.set2_jugador1,
                resultado_original.set3_jugador1,
                resultado_original.set1_jugador2,
                resultado_original.set2_jugador2,
                resultado_original.set3_jugador2,
                resultado_original.ganador_jugador_id
            ) if resultado_original and not es_doble else (
                resultado_original.set1_equipo1,
                resultado_original.set2_equipo1,
                resultado_original.set3_equipo1,
                resultado_original.set1_equipo2,
                resultado_original.set2_equipo2,
                resultado_original.set3_equipo2,
                resultado_original.ganador_equipo_id
            ) if resultado_original else None

            # 🟡 Guardar nuevo resultado
            if es_doble:
                resultado.set1_equipo1 = int(data.get('set1_jugador1') or 0)
                resultado.set2_equipo1 = int(data.get('set2_jugador1') or 0)
                resultado.set3_equipo1 = int(data.get('set3_jugador1') or 0)
                resultado.set1_equipo2 = int(data.get('set1_jugador2') or 0)
                resultado.set2_equipo2 = int(data.get('set2_jugador2') or 0)
                resultado.set3_equipo2 = int(data.get('set3_jugador2') or 0)

                ganador_equipo_id = data.get('ganador_equipo_id')
                resultado.ganador_equipo = Equipo.objects.get(id=int(ganador_equipo_id)) if ganador_equipo_id else None
                resultado.ganador_jugador = None
            else:
                resultado.set1_jugador1 = int(data.get('set1_jugador1') or 0)
                resultado.set2_jugador1 = int(data.get('set2_jugador1') or 0)
                resultado.set3_jugador1 = int(data.get('set3_jugador1') or 0)
                resultado.set1_jugador2 = int(data.get('set1_jugador2') or 0)
                resultado.set2_jugador2 = int(data.get('set2_jugador2') or 0)
                resultado.set3_jugador2 = int(data.get('set3_jugador2') or 0)

                ganador_dni = data.get('ganador_dni')
                resultado.ganador_jugador = Jugador.objects.get(dni=int(ganador_dni)) if ganador_dni else None
                resultado.ganador_equipo = None

            # Comparar con los valores anteriores antes de guardar y actualizar ranking
            datos_nuevos = (
                resultado.set1_jugador1,
                resultado.set2_jugador1,
                resultado.set3_jugador1,
                resultado.set1_jugador2,
                resultado.set2_jugador2,
                resultado.set3_jugador2,
                resultado.ganador_jugador_id
            ) if not es_doble else (
                resultado.set1_equipo1,
                resultado.set2_equipo1,
                resultado.set3_equipo1,
                resultado.set1_equipo2,
                resultado.set2_equipo2,
                resultado.set3_equipo2,
                resultado.ganador_equipo_id
            )

            if datos_anteriores != datos_nuevos:
                # Desconectar signal para evitar doble ejecución
                from django.db.models.signals import post_save
                # post_save.disconnect(actualizar_ranking, sender=ResultadoPartido)

                resultado.save()

                # post_save.connect(actualizar_ranking, sender=ResultadoPartido)

                # ✅ Revertir si es edición
                # if es_edicion:
                #     if es_doble:
                #         revertir_ranking_doble(resultado_original)
                #     else:
                #         revertir_ranking_single(resultado_original)

                # ✅ Aplicar resultado nuevo
                # if es_doble:
                #     actualizar_ranking_manual_equipos(resultado)
                # else:
                #     actualizar_ranking_manual(resultado)

                return JsonResponse({'success': True, 'message': '✅ Resultado actualizado correctamente.'})
            else:
                return JsonResponse({'success': True, 'message': '⚠️ No hubo cambios en el resultado.'})

        except Exception as e:
            import traceback
            traceback.print_exc()
            return JsonResponse({'success': False, 'message': str(e)})



def revertir_ranking(partido, ganador_anterior, s1_j1, s2_j1, s3_j1, s1_j2, s2_j2, s3_j2):
    torneo = partido.torneo
    categoria = torneo.categorias.first()

    perdedor = partido.jugador1 if partido.jugador2 == ganador_anterior else partido.jugador2

    # Recalcular sets y games como se hizo originalmente
    sets_ganador = int(s1_j1 > s1_j2) + int(s2_j1 > s2_j2) + int(s3_j1 > s3_j2) if ganador_anterior == partido.jugador1 else \
                   int(s1_j2 > s1_j1) + int(s2_j2 > s2_j1) + int(s3_j2 > s3_j1)
    sets_perdedor = 3 - sets_ganador

    games_ganador = (s1_j1 + s2_j1) if ganador_anterior == partido.jugador1 else (s1_j2 + s2_j2)
    games_perdedor = (s1_j2 + s2_j2) if ganador_anterior == partido.jugador1 else (s1_j1 + s2_j1)

    # Revertir GANADOR
    ranking_ganador = Ranking.objects.filter(jugador=ganador_anterior, torneo=torneo).first()
    if ranking_ganador:
        ranking_ganador.pj -= 1
        ranking_ganador.pg -= 1
        ranking_ganador.sets -= (sets_ganador - sets_perdedor)
        ranking_ganador.games -= (games_ganador - games_perdedor)
        ranking_ganador.puntaje_total_categoria -= 100
        ranking_ganador.save()

    # Revertir PERDEDOR
    ranking_perdedor = Ranking.objects.filter(jugador=perdedor, torneo=torneo).first()
    if ranking_perdedor:
        ranking_perdedor.pj -= 1
        ranking_perdedor.pp -= 1
        ranking_perdedor.sets -= (sets_perdedor - sets_ganador)
        ranking_perdedor.games -= (games_perdedor - games_ganador)
        ranking_perdedor.puntaje_total_categoria += 50
        ranking_perdedor.save()


def partido_single(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    if request.method == 'POST':
        # Capturar datos enviados desde el formulario
        numero_jornada = request.POST.get('numero_jornada')
        jugadores1 = request.POST.getlist('jugador1[]')
        jugadores2 = request.POST.getlist('jugador2[]')
        fechas = request.POST.getlist('fecha[]')
        horas = request.POST.getlist('hora[]')
        canchas = request.POST.getlist('cancha[]')

        # Imprimir los datos capturados
        print("Número de jornada:", numero_jornada)
        print("Jugadores 1:", jugadores1)
        print("Jugadores 2:", jugadores2)
        print("Fechas:", fechas)
        print("Horas:", horas)
        print("Canchas:", canchas)

        # Verificar si los datos están vacíos
        if not jugadores1 or not jugadores2 or not fechas or not horas or not canchas:
            messages.error(request, "No se recibieron todos los datos necesarios desde el formulario.")
            return redirect('partido_single', torneo_id=torneo_id)

        # Restante lógica para crear partidos
        advertencias = []
        partidos_creados = []

        for jugador1, jugador2, fecha_str, hora_str, cancha_id in zip(jugadores1, jugadores2, fechas, horas, canchas):
            # 1) Parse de fecha y hora
            try:
                fecha_obj = date.fromisoformat(fecha_str)
                hora_obj = datetime.strptime(hora_str, '%H:%M').time()
            except ValueError as e:
                messages.warning(request, f"Error en fecha/hora: {e}")
                continue

            # 2) Validación de duplicados
            if Partido.objects.filter(
                torneo=torneo,
                jornada=numero_jornada,
                jugador1_id=jugador1,
                jugador2_id=jugador2,
            ).exists():
                advertencias.append(f"El partido entre {jugador1} y {jugador2} ya existe.")
                continue

            # Crear el partido
            partido = Partido(
                torneo=torneo,
                jornada=numero_jornada,
                jugador1_id=jugador1,
                jugador2_id=jugador2,
                fecha=fecha_obj,
                hora=hora_obj,
                cancha_id=cancha_id
            )
            partido.save()
            partidos_creados.append(partido)

        # Mensajes de resultado
        if advertencias:
            for adv in advertencias:
                messages.warning(request, adv)
        if partidos_creados:
            messages.success(
                request,
                f"Se han creado {len(partidos_creados)} partidos para la jornada {numero_jornada}."
            )

        return redirect('partido_single', torneo_id=torneo_id)

    # Obtener datos para renderizar el formulario
    jornadas = Partido.objects.filter(torneo=torneo).values('jornada').distinct().order_by('jornada')
    numero_jornada = jornadas.count() + 1
    jugadores = Jugador.objects.filter(
        # ranking__torneo=torneo,
        # ranking__activo=True
    ).distinct().order_by('apellido', 'nombre')


    canchas = Cancha.objects.all()

    return render(request, 'partido_single.html', {
        'torneo': torneo,
        'numero_jornada': numero_jornada,
        'jugadores': jugadores,
        'canchas': canchas,
        'jornadas': jornadas,
    })

#-----------------------------------------------------------------------------------
#partido Doble 106
def jornada_detalle(request, torneo_id, jornada):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    if torneo.tipo_juego in ['Doble', 'Mixto']:
        partidos = Partido.objects.filter(torneo=torneo, jornada=jornada).select_related(
            'equipo1__jugador1', 'equipo1__jugador2',
            'equipo2__jugador1', 'equipo2__jugador2',
            'cancha', 'resultado'
        )
        equipos = Equipo.objects.filter(torneo=torneo).select_related('jugador1', 'jugador2').order_by('jugador1__apellido')
        canchas = Cancha.objects.all()

        return render(request, 'jornada_detalle.html', {
            'torneo': torneo,
            'jornada': jornada,
            'partidos': partidos,
            'equipos': equipos,
            'canchas': canchas,
        })

    else:
        partidos = Partido.objects.filter(torneo=torneo, jornada=jornada).select_related(
            'jugador1', 'jugador2', 'cancha', 'resultado'
        )
        jugadores = Jugador.objects.all().order_by('apellido', 'nombre')
        # jugadores = Jugador.objects.filter(ranking__torneo=torneo, ranking__activo=True).distinct().order_by('apellido', 'nombre')
        canchas = Cancha.objects.all()

        return render(request, 'jornada_detalle.html', {
            'torneo': torneo,
            'jornada': jornada,
            'partidos': partidos,
            'jugadores': jugadores,
            'canchas': canchas,
        })

#-----------------------------------------------------------------------------------
from django.core.paginator import Paginator

def listar_partidos(request):
    torneo_id = request.GET.get('torneo', '')
    search_fecha = request.GET.get('fecha', '')

    # Carga optimizada con select_related para evitar problemas con None
    partidos = Partido.objects.select_related(
        'torneo', 'cancha__sede',
        'jugador1', 'jugador2',
        'equipo1__jugador1', 'equipo1__jugador2',
        'equipo2__jugador1', 'equipo2__jugador2',
        'resultado__ganador_jugador', 'resultado__ganador_equipo'
    ).all()

    if torneo_id:
        partidos = partidos.filter(torneo_id=torneo_id)

    if search_fecha:
        partidos = partidos.filter(fecha=search_fecha)

    partidos = partidos.order_by('-fecha', '-hora')

    # Paginación (si la estás usando, ajustá si querés más por página)
    paginator = Paginator(partidos, 20)
    page_number = request.GET.get("page")
    page_obj = paginator.get_page(page_number)

    return render(request, 'listar_partidos.html', {
        'page_obj': page_obj,
        'torneos': Torneo.objects.all(),
        'torneo_id': torneo_id,
        'search_fecha': search_fecha,
    })



    
@csrf_exempt
def validar_partido_existente(request, torneo_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            jugador1_id = data.get('jugador1')
            jugador2_id = data.get('jugador2')
            fecha = data.get('fecha')
            hora = data.get('hora')
            cancha = data.get('cancha')

            if not jugador1_id or not jugador2_id:
                return JsonResponse({'success': False, 'message': 'Faltan jugadores.'}, status=400)

            ya_existe = Partido.objects.filter(
                torneo_id=torneo_id
            ).filter(
                Q(jugador1_id=jugador1_id, jugador2_id=jugador2_id) |
                Q(jugador1_id=jugador2_id, jugador2_id=jugador1_id)
            ).exists()

            if ya_existe:
                return JsonResponse({'success': False, 'message': 'Estos jugadores ya han jugado en este torneo.'})
            
            return JsonResponse({'success': True, 'message': 'El partido es válido.'})

        except json.JSONDecodeError:
            return JsonResponse({'success': False, 'message': 'Error en el formato de los datos.'}, status=400)
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)}, status=500)

    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)

#@csrf_exempt
#def validar_partido(request, torneo_id):
    #if request.method == 'POST':
       # torneo = get_object_or_404(Torneo, id=torneo_id)
      #  data = json.loads(request.body)

      #  jugador1 = data.get('jugador1')
       # jugador2 = data.get('jugador2')
        #fecha_str = data.get('fecha')
        #hora_str = data.get('hora')
        #cancha_id = data.get('cancha')

        #errors = []

        # Parse de fecha
        #try:
           # fecha_obj = date.fromisoformat(fecha_str)
        #except ValueError:
            # fallback dd/mm/yyyy
            #try:
                #day, month, year = fecha_str.split('/')
                #fecha_obj = date(int(year), int(month), int(day))
            #except:
               # errors.append(f"Fecha '{fecha_str}' inválida. Usa YYYY-MM-DD o DD/MM/YYYY")

        # Parse de hora
        #if not errors:
            #try:
               # hora_obj = datetime.strptime(hora_str, '%H:%M').time()
            #except ValueError:
                #errors.append(f"La hora '{hora_str}' no es válida. Usa HH:MM 24h.")

        # Validaciones si no hay errores de parsing
        #if not errors:
            #if Partido.objects.filter(
             #   torneo=torneo
           # ).filter(
             #   Q(jugador1_id=jugador1, jugador2_id=jugador2) |
              #  Q(jugador1_id=jugador2, jugador2_id=jugador1)
           # ).exists():
              #  errors.append("Los jugadores seleccionados ya jugaron entre sí en este torneo.")

           # if Partido.objects.filter(
               # torneo=torneo,
              #  fecha=fecha_obj,
              #  hora=hora_obj,
              #  cancha_id=cancha_id
            #).exists():
               # errors.append(f"Ya existe un partido en {fecha_str} {hora_str} - Cancha {cancha_id}.")

       # if errors:
          #  return JsonResponse({'errors': errors}, status=400)
       # else:
           # return JsonResponse({'message': 'Validación exitosa'}, status=200)

   # return JsonResponse({'error': 'Método no permitido'}, status=405)


def tiene_categoria_doble(self):
    return self.categorias.filter(tipo_juego__iexact="Doble").exists()



from .models import Cancha, Sede
@csrf_exempt
def abm_cancha(request):
    if request.method == 'GET':
        sedes = Sede.objects.all()
        return render(request, 'abm_cancha.html', {'sedes': sedes})

    elif request.method == 'POST':
        cancha_num = request.POST.get('cancha')
        sede_id = request.POST.get('sede')

        if not cancha_num or not sede_id:
            return JsonResponse({'success': False, 'error': 'Faltan datos'})

        # 💥 Verificar si ya existe la combinación número + sede
        if Cancha.objects.filter(cancha=cancha_num, sede_id=sede_id).exists():
            return JsonResponse({
                'success': False,
                'error': 'Ya existe una cancha con ese número en la misma sede.'
            })

        try:
            Cancha.objects.create(
                cancha=cancha_num,
                sede_id=sede_id
            )
            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

def listado_canchas(request):
    search = request.GET.get('search', '').strip()
    qs = Cancha.objects.all().order_by('cancha')

    if search:
        condiciones = Q()
        if search.isdigit():
            condiciones |= Q(cancha=int(search))
        condiciones |= Q(sede__nombre__icontains=search)
        qs = qs.filter(condiciones)

    paginator = Paginator(qs, 30)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'listado_canchas.html', {
        'canchas': page_obj,
        'page_obj': page_obj,
        'filtros': {
            'search': search,
        }
    })


#Maneja la  vista de ver la jornada 

@csrf_exempt
def eliminar_partido(request, partido_id):
    if request.method == 'POST':
        partido = get_object_or_404(Partido, id=partido_id)
        try:
            partido.delete()
            return JsonResponse({'success': True, 'message': 'Partido eliminado exitosamente.'})
        except Exception as e:
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido.'}, status=405)

@csrf_exempt
def modificar_partido(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        partido_id = data.get('partido_id')
        partido = Partido.objects.get(id=partido_id)
        resultado = ResultadoPartido.objects.filter(partido=partido).first()

        # Revertir ranking anterior
        # if resultado and resultado.ganador_jugador:
        #     revertir_ranking_single(resultado)

        if not resultado:
            resultado = ResultadoPartido(partido=partido)

        resultado.set1_jugador1 = int(data.get('set1_jugador1', 0))
        resultado.set2_jugador1 = int(data.get('set2_jugador1', 0))
        resultado.set3_jugador1 = int(data.get('set3_jugador1', 0))

        resultado.set1_jugador2 = int(data.get('set1_jugador2', 0))
        resultado.set2_jugador2 = int(data.get('set2_jugador2', 0))
        resultado.set3_jugador2 = int(data.get('set3_jugador2', 0))

        # Definir ganador
        sets_j1 = contar_sets_ganados(
            resultado.set1_jugador1, resultado.set1_jugador2,
            resultado.set2_jugador1, resultado.set2_jugador2,
            resultado.set3_jugador1, resultado.set3_jugador2
        )
        sets_j2 = contar_sets_ganados(
            resultado.set1_jugador2, resultado.set1_jugador1,
            resultado.set2_jugador2, resultado.set2_jugador1,
            resultado.set3_jugador2, resultado.set3_jugador1
        )

        if sets_j1 > sets_j2:
            resultado.ganador_jugador = partido.jugador1
        elif sets_j2 > sets_j1:
            resultado.ganador_jugador = partido.jugador2
        else:
            resultado.ganador_jugador = None  # Empate o error

        # resultado.save()
        # actualizar_ranking_manual(resultado)

        return JsonResponse({'status': 'ok'})


"""

@receiver(post_save, sender=ResultadoPartido)
def actualizar_ranking(sender, instance, **kwargs):
    if not instance.ganador_jugador:
        return  # No hacer nada si no hay ganador asignado

    from ranking.models import Ranking  # por si no está arriba

    partido = instance.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()

    jugador1 = partido.jugador1
    jugador2 = partido.jugador2

    # Obtengo ranking de ambos jugadores
    ranking_j1, _ = Ranking.objects.get_or_create(jugador=jugador1, torneo=torneo, categoria=categoria)
    ranking_j2, _ = Ranking.objects.get_or_create(jugador=jugador2, torneo=torneo, categoria=categoria)

    # 🔄 Revertir resultado anterior si existe
    try:
        resultado_anterior = ResultadoPartido.objects.get(partido=partido)
        if resultado_anterior and resultado_anterior.id == instance.id and resultado_anterior.ganador_jugador:
            ganador_ant = resultado_anterior.ganador_jugador
            perdedor_ant = jugador2 if ganador_ant == jugador1 else jugador1

            sets_ganados_ant = sum([
                resultado_anterior.set1_jugador1 > resultado_anterior.set1_jugador2,
                resultado_anterior.set2_jugador1 > resultado_anterior.set2_jugador2,
                resultado_anterior.set3_jugador1 > resultado_anterior.set3_jugador2,
            ])
            sets_perdidos_ant = 3 - sets_ganados_ant

            games_j1_ant = resultado_anterior.set1_jugador1 + resultado_anterior.set2_jugador1
            games_j2_ant = resultado_anterior.set1_jugador2 + resultado_anterior.set2_jugador2

            # El set 3 no suma en games
            if resultado_anterior.set3_jugador1 > 0 or resultado_anterior.set3_jugador2 > 0:
                pass  # No sumar games del set 3

            # Ranking del ganador anterior
            ranking_ganador_ant = Ranking.objects.get(jugador=ganador_ant, torneo=torneo)
            ranking_perdedor_ant = Ranking.objects.get(jugador=perdedor_ant, torneo=torneo)

            # Revertir cambios
            ranking_ganador_ant.pg -= 1
            ranking_ganador_ant.sets -= (sets_ganados_ant - sets_perdidos_ant)
            ranking_ganador_ant.games -= (games_j1_ant - games_j2_ant)
            ranking_ganador_ant.puntaje_total_categoria -= 100
            ranking_ganador_ant.save()

            ranking_perdedor_ant.pp -= 1
            ranking_perdedor_ant.sets -= (sets_perdidos_ant - sets_ganados_ant)
            ranking_perdedor_ant.games -= (games_j2_ant - games_j1_ant)
            ranking_perdedor_ant.puntaje_total_categoria += 50
            ranking_perdedor_ant.save()
    except ResultadoPartido.DoesNotExist:
        pass

    # ✅ Calcular nuevo resultado
    ganador = instance.ganador_jugador
    perdedor = jugador2 if ganador == jugador1 else jugador1

    sets_j1 = sum([
        instance.set1_jugador1 > instance.set1_jugador2,
        instance.set2_jugador1 > instance.set2_jugador2,
        instance.set3_jugador1 > instance.set3_jugador2,
    ])
    sets_j2 = 3 - sets_j1

    games_j1 = instance.set1_jugador1 + instance.set2_jugador1
    games_j2 = instance.set1_jugador2 + instance.set2_jugador2
    # No sumar set 3 en games
    # if instance.set3_jugador1 > 0 or instance.set3_jugador2 > 0:
    #     (no se suman los games del set 3)

    if ganador == jugador2:
        sets_ganador, sets_perdedor = sets_j2, sets_j1
        games_ganador, games_perdedor = games_j2, games_j1
        ranking_ganador = ranking_j2
        ranking_perdedor = ranking_j1
    else:
        sets_ganador, sets_perdedor = sets_j1, sets_j2
        games_ganador, games_perdedor = games_j1, games_j2
        ranking_ganador = ranking_j1
        ranking_perdedor = ranking_j2

    # ✅ Aplicar nuevo resultado
    ranking_ganador.pg += 1
    ranking_ganador.sets += (sets_ganador - sets_perdedor)
    ranking_ganador.games += (games_ganador - games_perdedor)
    ranking_ganador.puntaje_total_categoria += 100
    ranking_ganador.save()

    ranking_perdedor.pp += 1
    ranking_perdedor.sets += (sets_perdedor - sets_ganador)
    ranking_perdedor.games += (games_perdedor - games_ganador)
    ranking_perdedor.puntaje_total_categoria -= 50
    ranking_perdedor.save()

    print(f"♻️ Ranking modificado - {ganador.nombre} ganó. Cambios aplicados correctamente.")
"""
    
    
def vista_partidos(request, torneo_id):
    torneo = Torneo.objects.get(id=torneo_id)
    partidos = Partido.objects.filter(torneo=torneo)  # Solo los partidos no terminados

    return render(request, 'partidos.html', {"torneo": torneo, "partidos": partidos})


def guardar_jornada(request, torneo_id):
    """ Guarda todos los partidos de un torneo en el historial de jornada y los elimina de la vista actual """
    
    if request.method == "POST":
        try:
            torneo = Torneo.objects.get(id=torneo_id)
            partidos = Partido.objects.filter(torneo=torneo)

            if not partidos.exists():
                return JsonResponse({"success": False, "message": "No hay partidos para guardar."})

            # 🔥 Crear una nueva jornada en el historial
            jornada = HistorialJornada.objects.create(torneo=torneo, fecha=date.today())
            jornada.partidos.set(partidos)  # Asociar los partidos terminados
            jornada.save()

            # 🔥 Eliminar los partidos de la vista principal
            partidos.delete()

            return JsonResponse({"success": True, "message": "Jornada guardada y eliminada correctamente."})
        except Exception as e:
            return JsonResponse({"success": False, "message": str(e)})

    return JsonResponse({"success": False, "message": "Método no permitido."})


def historial_jornada(request):
    # Asegurar que los partidos están bien relacionados
    jornadas = HistorialJornada.objects.prefetch_related('partidos__jugador1', 'partidos__jugador2', 'partidos__cancha')

    # Debug: Mostrar en la consola qué se está trayendo
    for jornada in jornadas:
        print(f"📅 Jornada {jornada.fecha} - Torneo: {jornada.torneo.nombre}")
        print(f"📝 Número de partidos en la jornada: {jornada.partidos.count()}")

    return render(request, 'historial_jornada.html', {"jornadas": jornadas})

def historial_publico(request, torneo_id=None):
    # 1) Obtengo todos los torneos para el sidebar
    torneos = Torneo.objects.all().order_by('nombre')
    # print("Total de torneos:", torneos.count())

    # 2) Base de datos: resultados con sus partidos relacionados
    resultados = ResultadoPartido.objects.select_related(
        'partido__torneo',
        'partido__cancha',
        'partido__equipo1',
        'partido__equipo2',
        'partido__jugador1',
        'partido__jugador2',
        'ganador_jugador',
        'ganador_equipo',
    )

    # 3) Si pasaron un torneo_id, filtro por ese torneo
    torneo_actual = None
    if torneo_id:
        torneo_actual = get_object_or_404(Torneo, id=torneo_id)
        resultados = resultados.filter(partido__torneo=torneo_actual)

    # 4) Filtro opcional por fecha (YYYY-MM-DD)
    fecha = request.GET.get('fecha')
    if fecha:
        resultados = resultados.filter(partido__fecha=fecha)

    # 5) Ordeno y pagino (12 por página)
    resultados = resultados.order_by('-partido__fecha', '-partido__hora')
    paginator = Paginator(resultados, 20)
    page_obj = paginator.get_page(request.GET.get('page'))

    # 6) Renderizo plantilla pública
    return render(request, 'historial_publico.html', {
        'torneos': torneos,
        'torneo_actual': torneo_actual,
        'page_obj': page_obj,
        'search_fecha': fecha or '',
    })


#filtrar por jugador los partidos 
from django.shortcuts import render
from .models import Partido, Torneo, Jugador
from django.core.paginator import Paginator

def historial_partidos(request):
    torneo_id = request.GET.get('torneo')
    jugador_id = request.GET.get('jugador')
    search_fecha = request.GET.get('fecha')

    partidos = Partido.objects.all()

    if torneo_id:
        partidos = partidos.filter(torneo_id=torneo_id)
    
    if jugador_id:
        partidos = partidos.filter(jugador1_id=jugador_id) | partidos.filter(jugador2_id=jugador_id)

    if search_fecha:
        partidos = partidos.filter(fecha=search_fecha)

    paginator = Paginator(partidos, 10)  # 10 partidos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    context = {
        'torneos': Torneo.objects.all(),
        'jugadores': Jugador.objects.all(),
        'page_obj': page_obj,
        'torneo_id': torneo_id,
        'jugador_id': jugador_id,
        'search_fecha': search_fecha,
    }
    
    return render(request, 'historial_partidos.html', context)




@csrf_exempt
def guardar_partido(request):
    if request.method == "POST":
        data = json.loads(request.body)
        partido = Partido.objects.get(id=data["partido_id"])
        partido.resultado.set1_jugador1 = data["set1_jugador1"]
        partido.resultado.set2_jugador1 = data["set2_jugador1"]
        partido.resultado.set3_jugador1 = data["set3_jugador1"]
        partido.resultado.set1_jugador2 = data["set1_jugador2"]
        partido.resultado.set2_jugador2 = data["set2_jugador2"]
        partido.resultado.set3_jugador2 = data["set3_jugador2"]
        partido.resultado.save()
        return JsonResponse({"success": True})

@csrf_exempt
def borrar_partido(request):
    if request.method == "POST":
        data = json.loads(request.body)
        Partido.objects.filter(id=data["partido_id"]).delete()
        return JsonResponse({"success": True})
    
    


from .models import Torneo

def vista_admin(request):
    torneos = Torneo.objects.all().order_by('-fecha_inicio')  # o como prefieras ordenarlos
    return render(request, 'abm_torneo.html', {
        'torneos': torneos,
        # ...otros datos si los necesitás...
    })



#--------------------------------------------------------------------------------------------------------------
# Inicio Carga masiva Cancha 100
def carga_masiva_cancha(request):
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        print("📥 Archivos recibidos:", request.FILES)
        try:
            excel_file = request.FILES['archivo_excel']
            df = pd.read_excel(excel_file, engine='openpyxl')

            print("🧩 Columnas detectadas:", df.columns.tolist())

            for _, row in df.iterrows():
                numero_cancha = int(row['cancha'])

                # Verificar si ya existe
                if not Cancha.objects.filter(cancha=numero_cancha).exists():
                    Cancha.objects.create(cancha=numero_cancha)

            return JsonResponse({'exito': True})
        except Exception as e:
            print("❌ Error al procesar archivo:", str(e))
            return JsonResponse({'exito': False, 'error': str(e)})

    return JsonResponse({'exito': False, 'error': 'Método no permitido'})

# Fin Carga masiva 100
#--------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------
# Inicio Carga Masiva de Torneo 103
def carga_masiva_torneos(request):
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        try:
            excel_file = request.FILES['archivo_excel']
            df = pd.read_excel(excel_file, engine='openpyxl')

            for _, row in df.iterrows():
                nombre = row['nombre']
                fecha_inicio = pd.to_datetime(row['fecha_inicio']).date()
                fecha_fin = pd.to_datetime(row['fecha_fin']).date() if not pd.isna(row['fecha_fin']) else None
                tipo = row['tipo']

                torneo, creado = Torneo.objects.get_or_create(
                    nombre=nombre,
                    fecha_inicio=fecha_inicio,
                    defaults={
                        'fecha_fin': fecha_fin,
                        'tipo': tipo
                    }
                )

                # Si ya existía, actualiza
                if not creado:
                    torneo.fecha_fin = fecha_fin
                    torneo.tipo = tipo
                    torneo.save()

                # Procesar categorías
                categorias_str = str(row['categorias'])
                for cat_str in categorias_str.split(';'):
                    try:
                        nivel, edad, tipo_juego = cat_str.strip().split('-')
                        categoria = Categoria.objects.get(nivel=nivel, edad=int(edad), tipo_juego=tipo_juego)
                        TorneoCategoria.objects.get_or_create(torneo=torneo, categoria=categoria)
                    except Exception as e:
                        print(f"❌ Error con categoría '{cat_str}' en torneo '{nombre}': {e}")

            return JsonResponse({'exito': True})
        except Exception as e:
            print("❌ Error general al procesar torneos:", str(e))
            return JsonResponse({'exito': False, 'error': str(e)})

    return JsonResponse({'exito': False, 'error': 'Método no permitido'})


# Inicio Carga Masiva de Torneo 103
#--------------------------------------------------------------------------------------------------------------
from django.db.models import F, Value
from django.db.models.functions import Coalesce

def listado_jugadores_master(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    if torneo.tipo_juego in ['Doble', 'Mixto']:
        # Mostrar equipos
        equipos = Equipo.objects.filter(
            rankingequipo__torneo=torneo
        ).annotate(
            puntaje=Coalesce(F('rankingequipo__puntaje_total_categoria'), Value(0)),
            activo=Coalesce(F('rankingequipo__activo'), Value(False))
        ).select_related('jugador1', 'jugador2').distinct().order_by('-puntaje')

        return render(request, 'listado_jugadores_master.html', {
            'torneo': torneo,
            'equipos': equipos,
            'es_doble': True
        })

    else:
        # Mostrar jugadores
        jugadores = Jugador.objects.filter(
            ranking__torneo=torneo
        ).annotate(
            puntaje=Coalesce(F('ranking__puntaje_total_categoria'), Value(0)),
            activo=Coalesce(F('ranking__activo'), Value(False))
        ).distinct().order_by('-puntaje')

        return render(request, 'listado_jugadores_master.html', {
            'torneo': torneo,
            'jugadores': jugadores,
            'es_doble': False
        })

@csrf_exempt
@csrf_exempt
def modificar_partido_doble(request):
    if request.method == 'POST':
        data = json.loads(request.body)

        partido_id = data.get('partido_id')
        partido = Partido.objects.get(id=partido_id)
        resultado = ResultadoPartido.objects.filter(partido=partido).first()

        # Revertir ranking anterior
        # if resultado and resultado.ganador_equipo:
        #     revertir_ranking_doble(resultado)

        if not resultado:
            resultado = ResultadoPartido(partido=partido)

        resultado.set1_equipo1 = int(data.get('set1_jugador1', 0))
        resultado.set2_equipo1 = int(data.get('set2_jugador1', 0))
        resultado.set3_equipo1 = int(data.get('set3_jugador1', 0))

        resultado.set1_equipo2 = int(data.get('set1_jugador2', 0))
        resultado.set2_equipo2 = int(data.get('set2_jugador2', 0))
        resultado.set3_equipo2 = int(data.get('set3_jugador2', 0))

        # Calcular sets ganados ignorando el set 3 si no se jugó
        sets_eq1 = contar_sets_ganados(
            resultado.set1_equipo1, resultado.set1_equipo2,
            resultado.set2_equipo1, resultado.set2_equipo2,
            resultado.set3_equipo1, resultado.set3_equipo2
        )
        sets_eq2 = contar_sets_ganados(
            resultado.set1_equipo2, resultado.set1_equipo1,
            resultado.set2_equipo2, resultado.set2_equipo1,
            resultado.set3_equipo2, resultado.set3_equipo1
        )

        if sets_eq1 > sets_eq2:
            resultado.ganador_equipo = partido.equipo1
        elif sets_eq2 > sets_eq1:
            resultado.ganador_equipo = partido.equipo2
        else:
            resultado.ganador_equipo = None  # Empate o error

        # resultado.save()
        # actualizar_ranking_manual_equipos(resultado)

        return JsonResponse({'status': 'ok'})


from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from reportlab.platypus import Table, TableStyle, Paragraph, SimpleDocTemplate, Spacer, Image
from reportlab.lib.enums import TA_CENTER


def generar_pdf_partidos_por_fecha(request):
    fecha_str = request.GET.get("fecha")
    sede_id = request.GET.get("sede_id")
    sede = get_object_or_404(Sede, id=sede_id)

    if not fecha_str or not sede_id:
        return HttpResponse("Fecha o sede no proporcionada", status=400)

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        sede_id = int(sede_id)
    except ValueError:
        return HttpResponse("Parámetros inválidos", status=400)

    # ✅ Traer partidos de todas las sedes (para verificar mismo día o días consecutivos)
    rango_fechas = [fecha - timedelta(days=1), fecha, fecha + timedelta(days=1)]
    partidos_global = Partido.objects.select_related(
        'torneo', 'cancha__sede',
        'jugador1', 'jugador2',
        'equipo1__jugador1', 'equipo1__jugador2',
        'equipo2__jugador1', 'equipo2__jugador2'
    ).filter(
        fecha__in=rango_fechas
    ).order_by('fecha', 'hora')

    # ✅ Filtrar solo los partidos de la sede actual para mostrar
    partidos_sede = partidos_global.filter(
        cancha__sede__id=sede_id,
        fecha=fecha   # <-- FIX: asegura que solo se incluya la fecha seleccionada
    )

    if not partidos_sede.exists():
        return HttpResponse("No hay partidos para la fecha y sede seleccionadas", status=404)

    # Detectar jugadores con partidos consecutivos o más de uno en el mismo día
    jugadores_partidos = {}
    for p in partidos_global:  # se analiza GLOBALMENTE
        jugadores = []
        if p.torneo.tipo_juego == 'Single':
            if p.jugador1: jugadores.append(p.jugador1)
            if p.jugador2: jugadores.append(p.jugador2)
        else:
            if p.equipo1:
                if p.equipo1.jugador1: jugadores.append(p.equipo1.jugador1)
                if p.equipo1.jugador2: jugadores.append(p.equipo1.jugador2)
            if p.equipo2:
                if p.equipo2.jugador1: jugadores.append(p.equipo2.jugador1)
                if p.equipo2.jugador2: jugadores.append(p.equipo2.jugador2)

        for j in jugadores:
            jugadores_partidos.setdefault(j.dni, []).append(p.fecha)

    jugadores_marcados = set()
    for jugador_dni, fechas in jugadores_partidos.items():
        fechas_ordenadas = sorted(fechas)

        # Caso 1: más de un partido el mismo día
        conteo_por_fecha = {}
        for f in fechas_ordenadas:
            conteo_por_fecha[f] = conteo_por_fecha.get(f, 0) + 1
            if conteo_por_fecha[f] > 1:
                jugadores_marcados.add(jugador_dni)

        # Caso 2: partidos en días consecutivos
        for i in range(len(fechas_ordenadas) - 1):
            if (fechas_ordenadas[i + 1] - fechas_ordenadas[i]).days == 1:
                jugadores_marcados.add(jugador_dni)

    # Función para formatear nombres
    def formatear_nombre(jugador):
        if not jugador:
            return "SIN ASIGNAR"
        nombre = f"{jugador.apellido.upper()} {jugador.nombre.capitalize()}"
        if jugador.dni in jugadores_marcados:
            return f"<font color='green'><b>{nombre}*</b></font>"
        return nombre

    styles = getSampleStyleSheet()
    estilo_celda = ParagraphStyle(
        'CeldaTabla',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=9,
        leading=11,
    )

    partidos = []
    for p in partidos_sede:  # mostramos solo sede actual
        torneo = p.torneo
        tipo = torneo.tipo_juego

        if tipo == 'Single':
            jugador1 = formatear_nombre(p.jugador1)
            jugador2 = formatear_nombre(p.jugador2)
            nombres = f"{jugador1}<br/><b><font size=9 >VS</font></b><br/>{jugador2}"
        else:
            equipo1_j1 = formatear_nombre(p.equipo1.jugador1 if p.equipo1 else None)
            equipo1_j2 = formatear_nombre(p.equipo1.jugador2 if p.equipo1 else None)
            equipo2_j1 = formatear_nombre(p.equipo2.jugador1 if p.equipo2 else None)
            equipo2_j2 = formatear_nombre(p.equipo2.jugador2 if p.equipo2 else None)

            equipo1 = f"{equipo1_j1} / <br/>{equipo1_j2}"
            equipo2 = f"{equipo2_j1} / <br/>{equipo2_j2}"

            nombres = f"{equipo1}<br/><b><font size=9 >VS</font></b><br/>{equipo2}"


        # Buscar resultado si existe
        resultado = ResultadoPartido.objects.filter(partido=p).first()
        resultado_texto = ""
        if resultado:
            if tipo == 'Single':
                sets = [
                    f"{resultado.set1_jugador1}-{resultado.set1_jugador2}",
                    f"{resultado.set2_jugador1}-{resultado.set2_jugador2}",
                    f"{resultado.set3_jugador1}-{resultado.set3_jugador2}"
                ]
            else:
                sets = [
                    f"{resultado.set1_equipo1}-{resultado.set1_equipo2}",
                    f"{resultado.set2_equipo1}-{resultado.set2_equipo2}",
                    f"{resultado.set3_equipo1}-{resultado.set3_equipo2}"
                ]
            sets_filtrados = [s for s in sets if s not in ("0-0", "None-None", "None-0", "0-None", "None-None")]
            if any("-" in s and s != "0-0" for s in sets_filtrados):
                resultado_texto = "<br/><font size=10 color='red'><b>Resultado:</b> " + " / ".join(sets_filtrados) + "</font>"

            if tipo == 'Single' and resultado.ganador_jugador:
                ganador_nombre = formatear_nombre(resultado.ganador_jugador)
            elif tipo != 'Single' and resultado.ganador_equipo:
                eq = resultado.ganador_equipo
                ganador_nombre = f"{formatear_nombre(eq.jugador1)}/{formatear_nombre(eq.jugador2)}"
            else:
                ganador_nombre = "Sin definir"

            resultado_texto += f"<br/><font size=10><b>Ganador:</b> {ganador_nombre}</font>"

        detalle = Paragraph(
            f"<font size=12 color='red'><b>{torneo.nombre}</b></font><br/>"
            f"<font size=11><b>{nombres}</b></font>{resultado_texto}",
            estilo_celda
        )

        partidos.append({
            'hora': p.hora,
            'cancha': p.cancha.cancha,
            'detalle': detalle,
        })

    canchas = sorted(set(p['cancha'] for p in partidos))
    horarios = sorted(set(p['hora'] for p in partidos))

    data = [['HORA'] + [f'Cancha {c}' for c in canchas]]
    for hora in horarios:
        fila = [hora.strftime('%H:%M')]
        for cancha in canchas:
            partido = next((p['detalle'] for p in partidos if p['hora'] == hora and p['cancha'] == cancha), '')
            fila.append(partido)
        data.append(fila)

    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer,
        pagesize=landscape(A4),
        leftMargin=1 * cm,
        rightMargin=1 * cm,
        topMargin=2 * cm,
        bottomMargin=1.5 * cm
    )

    story = []

    # Logo
    # Logos lado a lado
    from reportlab.platypus import Table

    try:
        logo_apur = Image(ruta_imagen, width=3 * cm, height=1.5 * cm)
    except:
        logo_apur = Paragraph("[APUR NO ENCONTRADO]", styles["Normal"])

    try:
        ruta_french = os.path.join(settings.BASE_DIR, 'static', 'imagenes', 'logo_french_clay.png')
        logo_french = Image(ruta_french, width=2.5 * cm, height=1.5 * cm)
    except:
        logo_french = Paragraph("[FRENCH CLAY NO ENCONTRADO]", styles["Normal"])

    tabla_logos = Table(
        [[logo_apur, logo_french]],
        colWidths=[5*cm, 5*cm]  # ancho de columnas ajustable
    )
    tabla_logos.setStyle(TableStyle([
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('BOTTOMPADDING', (0, 0), (-1, -1), 0),
        ('TOPPADDING', (0, 0), (-1, -1), 0),
    ]))

    story.append(tabla_logos)


    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("Liga Abierta APUR-FRENCH CLAY ", styles["Title"]))

    # Día de la semana
    dia_semana = fecha.strftime("%A")
    dias_es = {
        "Monday": "Lunes", "Tuesday": "Martes", "Wednesday": "Miércoles",
        "Thursday": "Jueves", "Friday": "Viernes",
        "Saturday": "Sábado", "Sunday": "Domingo"
    }
    dia_semana_es = dias_es.get(dia_semana, dia_semana)

    story.append(Paragraph(
        f'<para align="center"><font size=18>Fecha: {dia_semana_es} {fecha.strftime("%d/%m/%Y")}</font></para>',
        styles["Normal"]
    ))

    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f'<para align="center"><font size=18><b>Sede: {sede.nombre}</b></font></para>', styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    row_heights = [2.5 * cm] + [4 * cm for _ in horarios]
    table = Table(data, colWidths=[6 * cm] + [6 * cm for _ in canchas], rowHeights=row_heights)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
        ('TOPPADDING', (0, 0), (-1, -1), 6),   # más aire arriba
        ('BOTTOMPADDING', (0, 0), (-1, -1), 6) # más aire abajo
    ]))

    story.append(table)

    # Leyenda
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(
        "<font size=11 color='green'><b>* Jugadores en verde: juegan más de un partido el mismo día o en días consecutivos (en cualquier sede o tipo de juego)</b></font>",
        styles["Normal"]
    ))

    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = (
        f'attachment; filename="liga_{sede.nombre.replace(" ", "_")}_{dia_semana_es}_{fecha.strftime("%d-%m-%Y")}.pdf"'
    )
    response.write(pdf)
    return response


def abm_sede(request):
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            Sede.objects.create(nombre=nombre)
            return JsonResponse({'success': True})
        else:
            return JsonResponse({'success': False, 'error': 'Nombre vacío'})
    
    return render(request, 'abm_sede.html')

def listado_sedes(request):
    search = request.GET.get('search', '')

    qs = Sede.objects.all().order_by('nombre')
    if search:
        qs = qs.filter(nombre__icontains=search)

    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'listado_sedes.html', {
        'sedes': page_obj,
        'page_obj': page_obj,
        'filtros': {
            'search': search or '',
        }
    })


def formulario_pdf_fecha_sede(request):
    sedes = Sede.objects.all()
    return render(request, "torneo/pdf_seleccion_fecha.html", {
        'sedes': sedes
    })
    

@csrf_exempt
def validar_partido_fecha_hora_cancha(request):
    if request.method == 'POST':
        data = json.loads(request.body)
        fecha = data.get('fecha')
        hora = data.get('hora')
        cancha_id = data.get('cancha_id')

        conflicto = Partido.objects.filter(
            fecha=fecha,
            hora=hora,
            cancha_id=cancha_id
        ).exists()

        return JsonResponse({'ocupado': conflicto})
    


def eliminar_sede(request, sede_id):
    sede = get_object_or_404(Sede, id=sede_id)
    sede.delete()
    messages.success(request, f'Sede "{sede.nombre}" eliminada correctamente.')
    return redirect('listado_sedes')


def eliminar_cancha(request, cancha_id):
    cancha = get_object_or_404(Cancha, id=cancha_id)
    cancha.delete()
    return redirect('listado_canchas')  # Cambiá esto si tu vista se llama diferente



def editar_sede(request, sede_id):
    sede = get_object_or_404(Sede, id=sede_id)
    if request.method == 'POST':
        nombre = request.POST.get('nombre', '').strip()
        if nombre:
            sede.nombre = nombre
            sede.save()
            messages.success(request, f'Sede "{nombre}" editada correctamente.')
        else:
            messages.error(request, 'El nombre no puede estar vacío.')
        return redirect('listado_sedes')



   