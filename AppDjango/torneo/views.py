
# 05/04/2025 - Agrego ID Carga masiva Cancha 100 y Carga Masiva de Torneo 103
# 05/04/2025 - Se esta poniendo en funcionamiento el doble y mixto 104
# 05/04/2025 - Se crear partido Doble 106


# views.py
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import TorneoForms
from .models import Torneo, TorneoCategoria, TorneoJugador, Partido, Equipo, Cancha
from jugador.models import Categoria, Jugador
from django.core.paginator import Paginator
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




def abm_torneo(request):
    all_categorias = Categoria.objects.all()
    categoria_id = request.GET.get('categoria')
    search_query = request.GET.get('search')
    

    torneos = Torneo.objects.all().order_by('-id')

    if categoria_id:
        torneos = torneos.filter(categorias__id=categoria_id)

    if search_query:
        torneos = torneos.filter(nombre__icontains=search_query)

    paginator = Paginator(torneos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    sedes = Sede.objects.all()  # 🔥 ESTA LÍNEA CREA LA VARIABLE


    return render(request, 'abm_torneo.html', {
        'page_obj': page_obj,
        'all_categorias': all_categorias,
        'categoria_id': categoria_id,
        'search': search_query,
        'sedes': sedes,  # 👈 este es el que faltaba antes

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
                return redirect('abm_torneo')
            except IntegrityError:
                messages.error(request, 'Error: Ya existe una relación entre este torneo y una de las categorías seleccionadas.')
            except Exception as e:
                messages.error(request, f'Error al crear el torneo: {e}')
        else:
            messages.error(request, 'Por favor, corrige los errores en el formulario.')
    else:
        form = TorneoForms()
    
    torneos = Torneo.objects.all().order_by('-fecha_inicio').prefetch_related('categorias')
    paginator = Paginator(torneos, 10)
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
    search = request.GET.get('search', '')  # Captura la búsqueda

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
    if search:
        jugadores_disponibles = jugadores_disponibles.filter(
            Q(nombre__icontains=search) | Q(apellido__icontains=search)
        )

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
        'search': search  # ✅ Asegurate de devolverlo al template
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
    es_doble = torneo.categorias.filter(tipo_juego__iexact='Doble').exists()

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
            jugadores1 = request.POST.getlist('jugador1[]')  # estos son en realidad equipos
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

        if torneo.tipo_juego in ['Doble', 'Mixto']:
            return redirect('partido_doble', torneo_id=torneo.id)
        else:
            return redirect('partido_single', torneo_id=torneo.id)

    return redirect('partido_doble' if torneo.tipo_juego in ['Doble', 'Mixto'] else 'partido_single', torneo_id=torneo.id)


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
                post_save.disconnect(actualizar_ranking, sender=ResultadoPartido)

                resultado.save()

                post_save.connect(actualizar_ranking, sender=ResultadoPartido)

                # ✅ Revertir si es edición
                if es_edicion:
                    if es_doble:
                        revertir_ranking_doble(resultado_original)
                    else:
                        revertir_ranking_single(resultado_original)

                # ✅ Aplicar resultado nuevo
                if es_doble:
                    actualizar_ranking_manual_equipos(resultado)
                else:
                    actualizar_ranking_manual(resultado)

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
        ranking__torneo=torneo,
        ranking__activo=True
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

    if torneo.tipo_juego in ['Doble', 'Mixto']:  # <- corregido aquí
        partidos = Partido.objects.filter(torneo=torneo, jornada=jornada).select_related(
            'equipo1__jugador1', 'equipo1__jugador2',
            'equipo2__jugador1', 'equipo2__jugador2',
            'cancha', 'resultado'
        )
    else:
        partidos = Partido.objects.filter(torneo=torneo, jornada=jornada).select_related(
            'jugador1', 'jugador2', 'cancha', 'resultado'
        )

    return render(request, 'jornada_detalle.html', {
        'torneo': torneo,
        'jornada': jornada,
        'partidos': partidos,
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
    canchas = Cancha.objects.all()
    return render(request, 'listado_canchas.html', {'canchas': canchas})


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
def modificar_partido(request, partido_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            partido = get_object_or_404(Partido, id=partido_id)
            resultado = get_object_or_404(ResultadoPartido, partido=partido)

            jugador1 = partido.jugador1
            jugador2 = partido.jugador2
            torneo = partido.torneo
            categoria = torneo.categorias.first()

            # 🔁 Obtener datos anteriores antes de modificarlos
            sets_anteriores_j1 = sum([
                resultado.set1_jugador1 > resultado.set1_jugador2,
                resultado.set2_jugador1 > resultado.set2_jugador2,
                resultado.set3_jugador1 > resultado.set3_jugador2,
            ])
            sets_anteriores_j2 = 3 - sets_anteriores_j1

            games_anteriores_j1 = resultado.set1_jugador1 + resultado.set2_jugador1
            games_anteriores_j2 = resultado.set1_jugador2 + resultado.set2_jugador2

            if resultado.set3_jugador1 > 0 or resultado.set3_jugador2 > 0:
                games_anteriores_j1 += 0  # no se suman games
                games_anteriores_j2 += 0

            ranking_j1 = Ranking.objects.get(jugador=jugador1, torneo=torneo)
            ranking_j2 = Ranking.objects.get(jugador=jugador2, torneo=torneo)

            # 🔄 Revertir puntos anteriores
            ranking_j1.pj -= 1
            ranking_j2.pj -= 1

            if resultado.ganador_jugador == jugador1:
                ranking_j1.pg -= 1
                ranking_j2.pp -= 1
                ranking_j1.puntaje_total_categoria -= 100
                ranking_j2.puntaje_total_categoria += 50
            elif resultado.ganador_jugador == jugador2:
                ranking_j2.pg -= 1
                ranking_j1.pp -= 1
                ranking_j2.puntaje_total_categoria -= 100
                ranking_j1.puntaje_total_categoria += 50

            ranking_j1.sets -= (sets_anteriores_j1 - sets_anteriores_j2)
            ranking_j2.sets -= (sets_anteriores_j2 - sets_anteriores_j1)
            ranking_j1.games -= (games_anteriores_j1 - games_anteriores_j2)
            ranking_j2.games -= (games_anteriores_j2 - games_anteriores_j1)

            ranking_j1.save()
            ranking_j2.save()

            # ✅ Guardar nuevos datos del resultado
            resultado.set1_jugador1 = data.get('set1_jugador1', 0)
            resultado.set2_jugador1 = data.get('set2_jugador1', 0)
            resultado.set3_jugador1 = data.get('set3_jugador1', 0)
            resultado.set1_jugador2 = data.get('set1_jugador2', 0)
            resultado.set2_jugador2 = data.get('set2_jugador2', 0)
            resultado.set3_jugador2 = data.get('set3_jugador2', 0)

            ganador_dni = data.get('ganador')
            if ganador_dni:
                resultado.ganador_jugador = Jugador.objects.get(dni=ganador_dni)
            else:
                resultado.ganador_jugador = None

            resultado.save()

            # 🔁 Calcular nuevos sets y games
            sets_j1 = sum([
                resultado.set1_jugador1 > resultado.set1_jugador2,
                resultado.set2_jugador1 > resultado.set2_jugador2,
                resultado.set3_jugador1 > resultado.set3_jugador2,
            ])
            sets_j2 = 3 - sets_j1

            games_j1 = resultado.set1_jugador1 + resultado.set2_jugador1
            games_j2 = resultado.set1_jugador2 + resultado.set2_jugador2

            if resultado.set3_jugador1 > 0 or resultado.set3_jugador2 > 0:
                # set 3 no suma games
                pass

            # ✅ Aplicar nueva suma
            ranking_j1.pj += 1
            ranking_j2.pj += 1

            if resultado.ganador_jugador == jugador1:
                ranking_j1.pg += 1
                ranking_j2.pp += 1
                ranking_j1.puntaje_total_categoria += 100
                ranking_j2.puntaje_total_categoria -= 50
            elif resultado.ganador_jugador == jugador2:
                ranking_j2.pg += 1
                ranking_j1.pp += 1
                ranking_j2.puntaje_total_categoria += 100
                ranking_j1.puntaje_total_categoria -= 50

            ranking_j1.sets += (sets_j1 - sets_j2)
            ranking_j2.sets += (sets_j2 - sets_j1)
            ranking_j1.games += (games_j1 - games_j2)
            ranking_j2.games += (games_j2 - games_j1)

            ranking_j1.save()
            ranking_j2.save()

            return JsonResponse({'success': True})
        
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)



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
def modificar_partido_doble(request, partido_id):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            partido = get_object_or_404(Partido, id=partido_id)
            resultado = get_object_or_404(ResultadoPartido, partido=partido)
            torneo = partido.torneo
            categoria = torneo.categorias.first()

            equipo1 = partido.equipo1
            equipo2 = partido.equipo2

            # Revertir ranking anterior
            ranking1 = RankingEquipo.objects.get(torneo=torneo, equipo=equipo1, categoria=categoria)
            ranking2 = RankingEquipo.objects.get(torneo=torneo, equipo=equipo2, categoria=categoria)

            sets_ant_1 = sum([
                resultado.set1_equipo1 > resultado.set1_equipo2,
                resultado.set2_equipo1 > resultado.set2_equipo2,
                resultado.set3_equipo1 > resultado.set3_equipo2,
            ])
            sets_ant_2 = 3 - sets_ant_1

            games_1 = resultado.set1_equipo1 + resultado.set2_equipo1
            games_2 = resultado.set1_equipo2 + resultado.set2_equipo2

            if resultado.ganador_equipo == equipo1:
                ranking1.pg -= 1
                ranking2.pp -= 1
                ranking1.puntaje_total_categoria -= 100
                ranking2.puntaje_total_categoria += 50
            elif resultado.ganador_equipo == equipo2:
                ranking2.pg -= 1
                ranking1.pp -= 1
                ranking2.puntaje_total_categoria -= 100
                ranking1.puntaje_total_categoria += 50

            ranking1.pj -= 1
            ranking2.pj -= 1
            ranking1.sets -= (sets_ant_1 - sets_ant_2)
            ranking2.sets -= (sets_ant_2 - sets_ant_1)
            ranking1.games -= (games_1 - games_2)
            ranking2.games -= (games_2 - games_1)

            ranking1.save()
            ranking2.save()

            # Guardar nuevos sets
            resultado.set1_equipo1 = int(data.get('set1_equipo1') or 0)
            resultado.set2_equipo1 = int(data.get('set2_equipo1') or 0)
            resultado.set3_equipo1 = int(data.get('set3_equipo1') or 0)
            resultado.set1_equipo2 = int(data.get('set1_equipo2') or 0)
            resultado.set2_equipo2 = int(data.get('set2_equipo2') or 0)
            resultado.set3_equipo2 = int(data.get('set3_equipo2') or 0)

            ganador_equipo_id = data.get('ganador_equipo_id')
            if ganador_equipo_id:
                resultado.ganador_equipo = Equipo.objects.get(id=ganador_equipo_id)
            else:
                resultado.ganador_equipo = None

            resultado.save()

            # Aplicar ranking nuevo
            nuevo_ganador = resultado.ganador_equipo
            nuevo_perdedor = equipo2 if nuevo_ganador == equipo1 else equipo1

            sets_ganador = sum([
                resultado.set1_equipo1 > resultado.set1_equipo2,
                resultado.set2_equipo1 > resultado.set2_equipo2,
                resultado.set3_equipo1 > resultado.set3_equipo2,
            ]) if nuevo_ganador == equipo1 else sum([
                resultado.set1_equipo2 > resultado.set1_equipo1,
                resultado.set2_equipo2 > resultado.set2_equipo1,
                resultado.set3_equipo2 > resultado.set3_equipo1,
            ])
            sets_perdedor = 3 - sets_ganador

            games_ganador = (resultado.set1_equipo1 + resultado.set2_equipo1) if nuevo_ganador == equipo1 else (
                            resultado.set1_equipo2 + resultado.set2_equipo2)
            games_perdedor = (resultado.set1_equipo2 + resultado.set2_equipo2) if nuevo_ganador == equipo1 else (
                            resultado.set1_equipo1 + resultado.set2_equipo1)

            ranking_ganador = RankingEquipo.objects.get(torneo=torneo, equipo=nuevo_ganador, categoria=categoria)
            ranking_perdedor = RankingEquipo.objects.get(torneo=torneo, equipo=nuevo_perdedor, categoria=categoria)

            ranking_ganador.pj += 1
            ranking_ganador.pg += 1
            ranking_ganador.sets += (sets_ganador - sets_perdedor)
            ranking_ganador.games += (games_ganador - games_perdedor)
            ranking_ganador.puntaje_total_categoria += 100

            ranking_perdedor.pj += 1
            ranking_perdedor.pp += 1
            ranking_perdedor.sets += (sets_perdedor - sets_ganador)
            ranking_perdedor.games += (games_perdedor - games_ganador)
            ranking_perdedor.puntaje_total_categoria -= 50

            ranking_ganador.save()
            ranking_perdedor.save()

            return JsonResponse({'success': True})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})

    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)


from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from io import BytesIO
from reportlab.platypus import Table, TableStyle, Paragraph, SimpleDocTemplate, Spacer, Image
from reportlab.lib.enums import TA_CENTER

def generar_pdf_partidos_por_fecha(request):
    fecha_str = request.GET.get("fecha")
    sede_id = request.GET.get("sede_id")
    sede = Sede.objects.get(id=sede_id)

    if not fecha_str or not sede_id:
        return HttpResponse("Fecha o sede no proporcionada", status=400)

    try:
        fecha = datetime.strptime(fecha_str, "%Y-%m-%d").date()
        sede_id = int(sede_id)
    except ValueError:
        return HttpResponse("Parámetros inválidos", status=400)

    partidos_qs = Partido.objects.select_related(
        'torneo', 'cancha__sede',
        'jugador1', 'jugador2',
        'equipo1__jugador1', 'equipo1__jugador2',
        'equipo2__jugador1', 'equipo2__jugador2'
    ).filter(
        fecha=fecha,
        cancha__sede__id=sede_id
    ).order_by('hora')

    if not partidos_qs.exists():
        return HttpResponse("No hay partidos para la fecha y sede seleccionadas", status=404)

    styles = getSampleStyleSheet()
    estilo_celda = ParagraphStyle(
        'CeldaTabla',
        parent=styles['Normal'],
        alignment=TA_CENTER,
        fontSize=9,
        leading=11,
    )

    partidos = []
    for p in partidos_qs:
        torneo = p.torneo
        tipo = torneo.tipo_juego

        if tipo == 'Single':
            nombres = f"{p.jugador1.apellido} vs {p.jugador2.apellido}"
        else:
            nombres = f"{p.equipo1.jugador1.apellido}/{p.equipo1.jugador2.apellido} vs {p.equipo2.jugador1.apellido}/{p.equipo2.jugador2.apellido}"

        detalle = Paragraph(
            f"<font size=12><b>{nombres}</b></font><br/><font size=9>{torneo.nombre} - {tipo}</font>",
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
    try:
        logo = Image("static/imagenes/apur.png", width=4 * cm, height=2 * cm)
        story.append(logo)
    except:
        story.append(Paragraph("[LOGO NO ENCONTRADO]", styles["Normal"]))

    story.append(Spacer(1, 0.3 * cm))
    story.append(Paragraph("LIGA", styles["Title"]))
    story.append(Paragraph(f'<para align="center"><font size=20>Fecha: {fecha.strftime("%d/%m/%Y")}</font></para>', styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))
    story.append(Paragraph(f'<para align="center"><font size=20><b>Sede: {sede.nombre}</b></font></para>', styles["Normal"]))
    story.append(Spacer(1, 0.5 * cm))

    row_heights = [1.5 * cm] + [2.5 * cm for _ in horarios]
    table = Table(data, colWidths=[3.5 * cm] + [6 * cm for _ in canchas], rowHeights=row_heights)

    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.lightgrey),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.black),
        ('FONTNAME', (0, 0), (-1, -1), 'Helvetica'),
        ('FONTSIZE', (0, 0), (-1, -1), 10),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('VALIGN', (0, 0), (-1, -1), 'MIDDLE'),
    ]))

    story.append(table)
    doc.build(story)

    pdf = buffer.getvalue()
    buffer.close()

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'attachment; filename="liga_{fecha}.pdf"'
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
    sedes = Sede.objects.filter(nombre__icontains=search).order_by('nombre')
    return render(request, 'listado_sedes.html', {'sedes': sedes})



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
