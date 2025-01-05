from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import TorneoForms
from .models import Torneo, TorneoCategoria, TorneoJugador, Partido , Equipo,Cancha
from jugador.models import Categoria
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from jugador.models import Jugador
import random
from django.http import JsonResponse
from django.utils import timezone
from django.db.models import Q
from django.views.decorators.csrf import csrf_exempt
import json


def abm_torneo(request):
    # Manejo del filtro por categoría
    categoria_id = request.GET.get('categoria')
    search_query = request.GET.get('search', '')
    
    if categoria_id:
        torneos = Torneo.objects.filter(categorias__id=categoria_id).distinct().prefetch_related('categorias')
    elif search_query:
        torneos = Torneo.objects.filter(nombre__icontains=search_query).prefetch_related('categorias')
    else:
        torneos = Torneo.objects.all().order_by('-fecha_inicio').prefetch_related('categorias')  # Prefetch categorías
    
    paginator = Paginator(torneos, 10)  # Muestra 10 torneos por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)
    
    all_categorias = Categoria.objects.all()  # Obtiene todas las categorías para el filtro
    
    return render(request, 'abm_torneo.html', {
        'page_obj': page_obj,
        'all_categorias': all_categorias,
        'categoria_id': categoria_id,  # Cambiado de 'categoria' a 'categoria_id'
        'search': search_query,
    })

def crear_torneo(request):
    if request.method == 'POST':
        form = TorneoForms(request.POST)
        if form.is_valid():
            categorias = form.cleaned_data['categorias']  # Obtiene las categorías seleccionadas
            try:
                with transaction.atomic():  # Inicia una transacción atómica
                    torneo = form.save()  # Guarda el Torneo
                    for categoria in categorias:
                        # Usa get_or_create para evitar duplicados
                        TorneoCategoria.objects.get_or_create(torneo=torneo, categoria=categoria)
                messages.success(request, 'Torneo creado exitosamente.')
                return redirect('abm_torneo')  # Redirige a la lista de torneos
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
                    torneo = form.save()  # Guarda el Torneo
                    torneo.categorias.clear()  # Borra todas las relaciones existentes
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
    
    #acomode para que muestre ordenado alfabeticamente de apellido y nombre
    # Filtrar jugadores disponibles según el tipo de torneo
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
        jugadores_dni = request.POST.getlist('jugadores')  # Jugadores a asociar
        jugadores_seleccionados_dni = request.POST.getlist('jugadores_seleccionados')  # Jugadores a desasociar

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

    # Filtrar jugadores disponibles según el tipo de torneo
    jugadores_disponibles = Jugador.objects.none()
    if torneo.tipo == 'F':
        jugadores_disponibles = Jugador.objects.filter(sexo='F').order_by('apellido', 'nombre')
    elif torneo.tipo == 'M':
        jugadores_disponibles = Jugador.objects.filter(sexo='M').order_by('apellido', 'nombre')
    elif torneo.tipo == 'Mixto':
        jugadores_disponibles = Jugador.objects.filter(sexo__in=['F', 'M']).order_by('apellido', 'nombre')

    # Obtener equipos ya asociados al torneo
    equipos_asociados = Equipo.objects.filter(torneo=torneo).select_related('jugador1', 'jugador2')

    if request.method == 'POST':
        action = request.POST.get('action')
        equipos_seleccionados = request.POST.getlist('equipos')  # Equipos creados enviados desde el formulario
        jugador1_id = request.POST.get('jugador1')
        jugador2_id = request.POST.get('jugador2')

        try:
            with transaction.atomic():
                # Crear equipo nuevo
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

                # Asociar equipos creados al torneo
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

                # Desasociar equipos del torneo
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

    # Verifica si alguna categoría del torneo es de dobles
    es_doble = any("doble" in categoria.tipo_juego.lower() for categoria in categorias)

    if es_doble:
        return redirect('asociar_equipos', id=torneo.id)  # Cambia torneo_id a id
    else:
        return redirect('asociar_jugadores', id=torneo.id)  # Sin cambios
    
    
def redirigir_partidos(request, torneo_id):
    # Obtén el torneo
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    # Verifica si el torneo tiene una categoría de tipo doble
    es_doble = torneo.categorias.filter(tipo_juego__iexact="Doble").exists()

    if es_doble:
        # Redirige al template de partidos para torneos dobles
        return redirect('partido_doble', torneo_id=torneo.id)
    else:
        # Redirige al template de partidos para torneos singles
        return redirect('partido_single', torneo_id=torneo.id)
    
def partido_doble(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    equipos = Equipo.objects.filter(torneo=torneo).select_related('jugador1', 'jugador2')
    
    return render(request, 'partido_doble.html', {
        'torneo': torneo,
        'equipos': equipos,
    })

def guardar_fecha(request, torneo_id):
    if request.method == 'POST':
        # Procesar los datos enviados en el formulario
        print(f"Datos recibidos: {request.POST}")
        # Aquí puedes guardar la información de la fecha, partidos, etc.
        
        # Redirigir a la misma página para cargar la siguiente fecha
        return redirect('partido_single', torneo_id=torneo_id)
    else:
        return JsonResponse({'error': 'Método no permitido'}, status=405)

def partido_single(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    
    if request.method == 'POST':
        numero_jornada = request.POST.get('numero_jornada')  # Obtener el número de jornada del input
        jugadores1 = request.POST.getlist('jugador1[]')
        jugadores2 = request.POST.getlist('jugador2[]')
        fechas = request.POST.getlist('fecha[]')
        horas = request.POST.getlist('hora[]')
        canchas = request.POST.getlist('cancha[]')

        advertencias = []  # Lista para almacenar mensajes de advertencia
        partidos_creados = []  # Para registrar los partidos creados
        
        for jugador1, jugador2, fecha, hora, cancha in zip(jugadores1, jugadores2, fechas, horas, canchas):
            # Validación 1: Verificar si los jugadores ya jugaron entre sí
            if Partido.objects.filter(
                torneo=torneo
            ).filter(
                (Q(jugador1_id=jugador1, jugador2_id=jugador2) | 
                 Q(jugador1_id=jugador2, jugador2_id=jugador1))
            ).exists():
                advertencias.append(f"Los jugadores con IDs {jugador1} y {jugador2} ya han jugado entre sí en este torneo.")
            
            # Validación 2: Verificar si la fecha, hora y cancha ya están ocupadas
            if Partido.objects.filter(
                torneo=torneo,
                fecha=fecha,
                hora=hora,
                cancha_id=cancha
            ).exists():
                advertencias.append(f"Ya existe un partido programado el {fecha} a las {hora} en la Cancha {cancha}.")
            else:
                # Crear el partido si no hay conflictos
                partido = Partido.objects.create(
                    torneo=torneo,
                    jugador1_id=jugador1,
                    jugador2_id=jugador2,
                    fecha=fecha,
                    hora=hora,
                    cancha_id=cancha,
                    jornada=numero_jornada
                )
                partidos_creados.append(partido)
        
        # Mostrar advertencias o mensaje de éxito
        if advertencias:
            for advertencia in advertencias:
                messages.warning(request, advertencia)
        if partidos_creados:
            messages.success(request, f"Se han guardado {len(partidos_creados)} partidos para la jornada número {numero_jornada}.")

        return redirect('partido_single', torneo_id=torneo_id)

    # Determinar el número de jornada
    numero_jornada = Partido.objects.filter(torneo=torneo).values('jornada').distinct().count() + 1
    
    # Obtener jugadores y canchas disponibles
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
        fecha = data.get('fecha')
        hora = data.get('hora')
        cancha = data.get('cancha')

        errors = []

        # Validación 1: Verificar si los jugadores ya jugaron entre sí
        if Partido.objects.filter(
            torneo=torneo
        ).filter(
            (Q(jugador1_id=jugador1, jugador2_id=jugador2) |
             Q(jugador1_id=jugador2, jugador2_id=jugador1))
        ).exists():
            errors.append(f"Los jugadores seleccionados ya jugaron entre sí en este torneo.")

        # Validación 2: Verificar si la fecha, hora y cancha ya están ocupadas
        if Partido.objects.filter(
            torneo=torneo,
            fecha=fecha,
            hora=hora,
            cancha_id=cancha
        ).exists():
            errors.append(f"Ya existe un partido programado el {fecha} a las {hora} en la Cancha {cancha}.")

        # Devolver resultado
        if errors:
            return JsonResponse({'errors': errors}, status=400)
        else:
            return JsonResponse({'message': 'Validación exitosa'}, status=200)

    return JsonResponse({'error': 'Método no permitido'}, status=405)

def tiene_categoria_doble(self):
        """
        Verifica si alguna de las categorías asociadas al torneo es de tipo 'Doble'.
        """
        return self.categorias.filter(tipo_juego__iexact="Doble").exists()







#Cancha 




def abm_cancha(request):
    if request.method == "POST":
        try:
            numero_cancha = request.POST.get("cancha")
            
            # Validar si el número de cancha ya existe
            if Cancha.objects.filter(cancha=numero_cancha).exists():
                messages.error(request, f"La cancha número {numero_cancha} ya está registrada.")
            else:
                # Crear y guardar la nueva cancha
                nueva_cancha = Cancha(cancha=numero_cancha)
                nueva_cancha.save()
                messages.success(request, f"La cancha número {numero_cancha} fue guardada exitosamente.")
                
            return redirect('abm_cancha')  # Redirige de nuevo a la página de ABM Cancha

        except Exception as e:
            messages.error(request, f"Error al intentar guardar la cancha: {e}")
    return render(request, 'abm_cancha.html')

    
def listado_canchas(request):
    canchas = Cancha.objects.all()  # Obtener todas las canchas de la base de datos
    return render(request, 'listado_canchas.html', {'canchas': canchas})
