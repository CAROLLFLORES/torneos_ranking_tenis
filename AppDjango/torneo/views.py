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
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json
from datetime import datetime, date, time

# NUEVO import para parsear fechas/horas
from datetime import datetime, date, time

def abm_torneo(request):
    categoria_id = request.GET.get('categoria')
    search_query = request.GET.get('search', '')
    
    if categoria_id:
        torneos = Torneo.objects.filter(categorias__id=categoria_id).distinct().prefetch_related('categorias')
    elif search_query:
        torneos = Torneo.objects.filter(nombre__icontains=search_query).prefetch_related('categorias')
    else:
        torneos = Torneo.objects.all().order_by('-fecha_inicio').prefetch_related('categorias')
    
    paginator = Paginator(torneos, 10)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    all_categorias = Categoria.objects.all()
    
    return render(request, 'abm_torneo.html', {
        'page_obj': page_obj,
        'all_categorias': all_categorias,
        'categoria_id': categoria_id,
        'search': search_query,
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
    return render(request, 'abm_torneo.html', {
        'form': form,
        'page_obj': page_obj,
        'all_categorias': all_categorias,
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
                    torneo = form.save()
                    torneo.categorias.clear()
                    for categoria in categorias:
                        TorneoCategoria.objects.get_or_create(torneo=torneo, categoria=categoria)
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
    
    if torneo.tipo == 'F':
        jugadores_disponibles = Jugador.objects.filter(sexo='F').exclude(jugador_torneos__torneo=torneo).order_by('apellido', 'nombre')
    elif torneo.tipo == 'M':
        jugadores_disponibles = Jugador.objects.filter(sexo='M').exclude(jugador_torneos__torneo=torneo).order_by('apellido', 'nombre')
    elif torneo.tipo == 'Mixto':
        jugadores_disponibles = Jugador.objects.filter(sexo__in=['F', 'M']).exclude(jugador_torneos__torneo=torneo).order_by('apellido', 'nombre')
    else:
        jugadores_disponibles = Jugador.objects.none()

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
    })


def asociar_equipos(request, id):
    torneo = get_object_or_404(Torneo, id=id)
    jugadores_disponibles = Jugador.objects.none()
    if torneo.tipo == 'F':
        jugadores_disponibles = Jugador.objects.filter(sexo='F').order_by('apellido', 'nombre')
    elif torneo.tipo == 'M':
        jugadores_disponibles = Jugador.objects.filter(sexo='M').order_by('apellido', 'nombre')
    elif torneo.tipo == 'Mixto':
        jugadores_disponibles = Jugador.objects.filter(sexo__in=['F', 'M']).order_by('apellido', 'nombre')

    equipos_asociados = Equipo.objects.filter(torneo=torneo).select_related('jugador1', 'jugador2')

    if request.method == 'POST':
        action = request.POST.get('action')
        equipos_seleccionados = request.POST.getlist('equipos')
        jugador1_id = request.POST.get('jugador1')
        jugador2_id = request.POST.get('jugador2')

        try:
            with transaction.atomic():
                if action == "crear_equipo":
                    if jugador1_id and jugador2_id and jugador1_id != jugador2_id:
                        jugador1 = Jugador.objects.get(dni=jugador1_id)
                        jugador2 = Jugador.objects.get(dni=jugador2_id)
                        Equipo.objects.get_or_create(
                            jugador1=jugador1,
                            jugador2=jugador2,
                            torneo=torneo
                        )
                        messages.success(request, 'Equipo creado exitosamente.')
                    else:
                        messages.error(request, 'Selecciona dos jugadores distintos para crear un equipo.')

                elif action == "asociar":
                    if equipos_seleccionados:
                        for equipo_str in equipos_seleccionados:
                            jugador1_id, jugador2_id = equipo_str.split('-')
                            jugador1 = Jugador.objects.get(dni=jugador1_id)
                            jugador2 = Jugador.objects.get(dni=jugador2_id)
                            Equipo.objects.get_or_create(
                                jugador1=jugador1,
                                jugador2=jugador2,
                                torneo=torneo
                            )
                        messages.success(request, 'Equipos guardados exitosamente en la base de datos.')

                elif action == "desasociar":
                    if equipos_seleccionados:
                        equipos = Equipo.objects.filter(id__in=equipos_seleccionados, torneo=torneo)
                        equipos.delete()
                        messages.success(request, 'Equipos desasociados exitosamente del torneo.')

            return redirect('asociar_equipos', id=torneo.id)

        except IntegrityError:
            messages.error(request, 'Ocurrió un error con la base de datos.')
        except Exception as e:
            messages.error(request, f'Error al procesar la solicitud: {e}')

    return render(request, 'asociar_equipos.html', {
        'torneo': torneo,
        'jugadores_disponibles': jugadores_disponibles,
        'equipos_asociados': equipos_asociados,
    })


def redirigir_inscripcion(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    categorias = torneo.categorias.all()
    es_doble = any("doble" in categoria.tipo_juego.lower() for categoria in categorias)
    if es_doble:
        return redirect('asociar_equipos', id=torneo.id)
    else:
        return redirect('asociar_jugadores', id=torneo.id)


def redirigir_partidos(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    es_doble = torneo.categorias.filter(tipo_juego__iexact="Doble").exists()
    if es_doble:
        return redirect('partido_doble', torneo_id=torneo.id)
    else:
        return redirect('partido_single', torneo_id=torneo.id)


def partido_doble(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    equipos = Equipo.objects.filter(torneo=torneo).select_related('jugador1', 'jugador2')
    
    return render(request, 'partido_doble.html', {
        'torneo': torneo,
        'equipos': equipos,
    })


def guardar_fecha(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    if request.method == 'POST':
        numero_jornada = request.POST.get('numero_jornada')
        jugadores1 = request.POST.getlist('jugador1[]')
        jugadores2 = request.POST.getlist('jugador2[]')
        fechas = request.POST.getlist('fecha[]')
        horas = request.POST.getlist('hora[]')
        canchas = request.POST.getlist('cancha[]')

        errores = []
        partidos_creados = []

        for i in range(len(fechas)):
            try:
                # Validar jugadores
                jugador1_id = jugadores1[i]
                jugador2_id = jugadores2[i]
                if not jugador1_id or not jugador2_id:
                    errores.append(f"Fila {i + 1}: Ambos jugadores deben estar seleccionados.")
                    continue
                if jugador1_id == jugador2_id:
                    errores.append(f"Fila {i + 1}: Un jugador no puede enfrentarse a sí mismo.")
                    continue

                # Validar fecha
                try:
                    fecha_obj = date.fromisoformat(fechas[i])
                except ValueError:
                    errores.append(f"Fila {i + 1}: Fecha '{fechas[i]}' no válida. Usa el formato YYYY-MM-DD.")
                    continue

                # Validar hora
                try:
                    hora_obj = datetime.strptime(horas[i], '%H:%M').time()
                except ValueError:
                    errores.append(f"Fila {i + 1}: Hora '{horas[i]}' no válida. Usa el formato HH:MM.")
                    continue

                # Validar cancha
                cancha_id = canchas[i]
                if not cancha_id:
                    errores.append(f"Fila {i + 1}: La cancha debe estar seleccionada.")
                    continue

                # Verificar conflictos de programación
                if Partido.objects.filter(
                    torneo=torneo, fecha=fecha_obj, hora=hora_obj, cancha_id=cancha_id
                ).exists():
                    errores.append(f"Fila {i + 1}: Ya existe un partido en la fecha y hora seleccionada.")
                    continue

                # Crear el partido
                partido = Partido(
                    torneo=torneo,
                    jornada=numero_jornada,
                    jugador1_id=jugador1_id,
                    jugador2_id=jugador2_id,
                    fecha=fecha_obj,
                    hora=hora_obj,
                    cancha_id=cancha_id
                )
                partido.save()
                partidos_creados.append(partido)

            except Exception as e:
                errores.append(f"Fila {i + 1}: Error inesperado: {str(e)}")

        # Mostrar mensajes al usuario
        if errores:
            for error in errores:
                messages.error(request, error)
        if partidos_creados:
            messages.success(request, f"Se guardaron {len(partidos_creados)} partidos correctamente.")

        return redirect('partido_single', torneo_id=torneo.id)

    return redirect('partido_single', torneo_id=torneo.id)


def partido_single(request, torneo_id):
    """
    Similar a guardar_fecha, pero para un solo form.
    También parseamos la fecha/hora por si el usuario teclea DD/MM/YYYY o HH:MM con AM/PM.
    """
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    if request.method == 'POST':
        numero_jornada = request.POST.get('numero_jornada')
        jugadores1 = request.POST.getlist('jugador1[]')
        jugadores2 = request.POST.getlist('jugador2[]')
        fechas = request.POST.getlist('fecha[]')
        horas = request.POST.getlist('hora[]')
        canchas = request.POST.getlist('cancha[]')

        advertencias = []
        partidos_creados = []
        
        for jugador1, jugador2, fecha_str, hora_str, cancha_id in zip(
            jugadores1, jugadores2, fechas, horas, canchas
        ):
            # 1) Parse FECHA
            try:
                fecha_obj = date.fromisoformat(fecha_str)  # YYYY-MM-DD
            except ValueError:
                # Intentar dd/mm/yyyy
                try:
                    day, month, year = fecha_str.split('/')
                    fecha_obj = date(int(year), int(month), int(day))
                except:
                    messages.warning(
                        request,
                        f"La fecha '{fecha_str}' no es válida. Formato esperado: YYYY-MM-DD o DD/MM/YYYY"
                    )
                    continue

            # 2) Parse HORA
            try:
                hora_obj = datetime.strptime(hora_str, '%H:%M').time()
            except ValueError:
                messages.warning(
                    request,
                    f"La hora '{hora_str}' no es válida. Usa formato HH:MM (24h)."
                )
                continue

            # Validación 1: Verificar si ya jugaron entre sí
            if Partido.objects.filter(torneo=torneo).filter(
                Q(jugador1_id=jugador1, jugador2_id=jugador2) |
                Q(jugador1_id=jugador2, jugador2_id=jugador1)
            ).exists():
                advertencias.append(f"Jugadores {jugador1} y {jugador2} ya jugaron entre sí en este torneo.")
            
            # Validación 2: Verificar fecha/hora/cancha ocupadas
            if Partido.objects.filter(
                torneo=torneo, fecha=fecha_obj, hora=hora_obj, cancha_id=cancha_id
            ).exists():
                advertencias.append(f"Ya existe un partido en {fecha_obj} {hora_obj} en la Cancha {cancha_id}.")
            else:
                # Crear
                p = Partido.objects.create(
                    torneo=torneo,
                    jugador1_id=jugador1,
                    jugador2_id=jugador2,
                    fecha=fecha_obj,
                    hora=hora_obj,
                    cancha_id=cancha_id,
                    jornada=numero_jornada
                )
                partidos_creados.append(p)
        
        if advertencias:
            for adv in advertencias:
                messages.warning(request, adv)
        if partidos_creados:
            messages.success(
                request,
                f"Se han guardado {len(partidos_creados)} partidos para la jornada {numero_jornada}."
            )

        return redirect('partido_single', torneo_id=torneo_id)

    numero_jornada = Partido.objects.filter(torneo=torneo).values('jornada').distinct().count() + 1
    jugadores = Jugador.objects.filter(jugador_torneos__torneo=torneo).order_by('apellido', 'nombre')
    canchas = Cancha.objects.all()

    return render(request, 'partido_single.html', {
        'torneo': torneo,
        'numero_jornada': numero_jornada,
        'jugadores': jugadores,
        'canchas': canchas,
    })


@csrf_exempt
def validar_partido(request, torneo_id):
    if request.method == 'POST':
        torneo = get_object_or_404(Torneo, id=torneo_id)
        data = json.loads(request.body)

        jugador1 = data.get('jugador1')
        jugador2 = data.get('jugador2')
        fecha_str = data.get('fecha')
        hora_str = data.get('hora')
        cancha_id = data.get('cancha')

        errors = []

        # Parse de fecha
        try:
            fecha_obj = date.fromisoformat(fecha_str)
        except ValueError:
            # fallback dd/mm/yyyy
            try:
                day, month, year = fecha_str.split('/')
                fecha_obj = date(int(year), int(month), int(day))
            except:
                errors.append(f"Fecha '{fecha_str}' inválida. Usa YYYY-MM-DD o DD/MM/YYYY")

        # Parse de hora
        if not errors:
            try:
                hora_obj = datetime.strptime(hora_str, '%H:%M').time()
            except ValueError:
                errors.append(f"La hora '{hora_str}' no es válida. Usa HH:MM 24h.")

        # Validaciones si no hay errores de parsing
        if not errors:
            if Partido.objects.filter(
                torneo=torneo
            ).filter(
                Q(jugador1_id=jugador1, jugador2_id=jugador2) |
                Q(jugador1_id=jugador2, jugador2_id=jugador1)
            ).exists():
                errors.append("Los jugadores seleccionados ya jugaron entre sí en este torneo.")

            if Partido.objects.filter(
                torneo=torneo,
                fecha=fecha_obj,
                hora=hora_obj,
                cancha_id=cancha_id
            ).exists():
                errors.append(f"Ya existe un partido en {fecha_str} {hora_str} - Cancha {cancha_id}.")

        if errors:
            return JsonResponse({'errors': errors}, status=400)
        else:
            return JsonResponse({'message': 'Validación exitosa'}, status=200)

    return JsonResponse({'error': 'Método no permitido'}, status=405)


def tiene_categoria_doble(self):
    return self.categorias.filter(tipo_juego__iexact="Doble").exists()


def abm_cancha(request):
    if request.method == "POST":
        try:
            numero_cancha = request.POST.get("cancha")
            if Cancha.objects.filter(cancha=numero_cancha).exists():
                messages.error(request, f"La cancha número {numero_cancha} ya está registrada.")
            else:
                nueva_cancha = Cancha(cancha=numero_cancha)
                nueva_cancha.save()
                messages.success(request, f"La cancha número {numero_cancha} fue guardada exitosamente.")
                
            return redirect('abm_cancha')
        except Exception as e:
            messages.error(request, f"Error al intentar guardar la cancha: {e}")
    return render(request, 'abm_cancha.html')


def listado_canchas(request):
    canchas = Cancha.objects.all()
    return render(request, 'listado_canchas.html', {'canchas': canchas})
