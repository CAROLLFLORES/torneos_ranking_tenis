from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from .forms import TorneoForms
from .models import Torneo, TorneoCategoria, TorneoJugador, Partido , Equipo
from jugador.models import Categoria
from django.core.paginator import Paginator
from django.views.decorators.http import require_POST
from django.db import transaction, IntegrityError
from jugador.models import Jugador
import random
from django.utils import timezone


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

    # Filtrar equipos disponibles según el tipo de torneo
    if torneo.tipo == 'F':
        jugadores_disponibles = Jugador.objects.filter(sexo='F').order_by('apellido', 'nombre')
    elif torneo.tipo == 'M':
        jugadores_disponibles = Jugador.objects.filter(sexo='M').order_by('apellido', 'nombre')
    elif torneo.tipo == 'Mixto':
        jugadores_disponibles = Jugador.objects.filter(sexo__in=['F', 'M']).order_by('apellido', 'nombre')
    else:
        jugadores_disponibles = Jugador.objects.none()

    # Obtener equipos ya asociados al torneo
    equipos_asociados = Equipo.objects.filter(torneo=torneo).select_related('jugador1', 'jugador2')

    if request.method == 'POST':
        action = request.POST.get('action')
        equipos_ids = request.POST.getlist('equipos')  # Equipos a asociar
        equipos_seleccionados_ids = request.POST.getlist('equipos_seleccionados')  # Equipos a desasociar
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

                elif action == "asociar":
                    if equipos_ids:
                        equipos = Equipo.objects.filter(id__in=equipos_ids)
                        for equipo in equipos:
                            equipo.torneo = torneo
                            equipo.save()
                        messages.success(request, 'Equipos asociados exitosamente al torneo.')

                elif action == "desasociar":
                    if equipos_seleccionados_ids:
                        equipos = Equipo.objects.filter(id__in=equipos_seleccionados_ids, torneo=torneo)
                        for equipo in equipos:
                            equipo.delete()
                        messages.success(request, 'Equipos desasociados exitosamente del torneo.')

            return redirect('asociar_equipos', torneo.id)

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
        return redirect('asociar_equipos', torneo_id=torneo.id)  # Redirige a asociar equipos
    else:
        return redirect('asociar_jugadores', id=torneo.id)  # Redirige a asociar jugadores


#def generar_partidos_torneo(request, id):
   # torneo = get_object_or_404(Torneo, id=id)

    # Aquí va la lógica para generar los partidos

    #return render(request, 'generar_partidos.html', {'torneo': torneo})


from django.shortcuts import render, get_object_or_404
from .models import Torneo, Jugador
def generar_partidos_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    jugadores_seleccionados = Jugador.objects.filter(
        jugador_torneos__torneo=torneo
    ).order_by('apellido', 'nombre')

    if request.method == 'POST':
        jugador1_ids = request.POST.getlist('jugador1[]')
        jugador2_ids = request.POST.getlist('jugador2[]')
        fechas = request.POST.getlist('fecha[]')
        horas = request.POST.getlist('hora[]')

        for j1, j2, fecha, hora in zip(jugador1_ids, jugador2_ids, fechas, horas):
            if j1 != j2:  # Evitar que un jugador juegue contra sí mismo
                Partido.objects.create(
                    torneo=torneo,
                    jugador1_id=j1,
                    jugador2_id=j2,
                    fecha=fecha,
                    hora=hora
                )
        return redirect('ver_caracteristicas_torneo', id=torneo.id)

    return render(request, 'generar_partidos_torneo.html', {
        'torneo': torneo,
        'jugadores_seleccionados': jugadores_seleccionados,
    })