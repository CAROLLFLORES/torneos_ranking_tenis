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
from django.http import JsonResponse
from torneo.models import Partido, HistorialJornada, Torneo
from django.db.models.signals import post_save
from django.dispatch import receiver
from ranking.models import Ranking
from .models import HistorialJornada

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

                        # VALIDACIÓN: Evitar equipos repetidos
                        equipo_existente = Equipo.objects.filter(
                            torneo=torneo,
                            jugador1=jugador1,
                            jugador2=jugador2
                        ).exists() or Equipo.objects.filter(
                            torneo=torneo,
                            jugador1=jugador2,
                            jugador2=jugador1
                        ).exists()

                        if equipo_existente:
                            messages.error(request, 'Este equipo ya fue creado.')
                        else:
                            Equipo.objects.create(
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
            
    # Pasar mensajes como contexto para el modal
    all_messages = [m.message for m in messages.get_messages(request)]

    return render(request, 'asociar_equipos.html', {
        'torneo': torneo,
        'jugadores_disponibles': jugadores_disponibles,
        'equipos_asociados': equipos_asociados,
        'all_messages': all_messages,  # Pasamos los mensajes al contexto
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


from datetime import datetime, date

def guardar_fecha(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    if request.method == 'POST':
        print("Datos recibidos en POST:", request.POST)  # Depuración
        
        numero_jornada = request.POST.get('numero_jornada')
        jugadores1 = request.POST.getlist('jugador1[]')
        jugadores2 = request.POST.getlist('jugador2[]')
        fechas = request.POST.getlist('fecha[]')
        horas = request.POST.getlist('hora[]')
        canchas = request.POST.getlist('cancha[]')

        print("Jugadores 1:", jugadores1)  # Depuración
        print("Jugadores 2:", jugadores2)  # Depuración
        print("Fechas:", fechas)           # Depuración
        print("Horas:", horas)             # Depuración
        print("Canchas:", canchas)         # Depuración

        partidos_creados = []

        for i in range(len(fechas)):
            try:
                # Crear el partido
                partido = Partido(
                    torneo=torneo,
                    jornada=numero_jornada,
                    jugador1_id=jugadores1[i],
                    jugador2_id=jugadores2[i],
                    fecha=date.fromisoformat(fechas[i]),
                    hora=datetime.strptime(horas[i], '%H:%M').time(),
                    cancha_id=canchas[i]
                )
                partido.save()
                partidos_creados.append(partido)

            except Exception as e:
                print(f"Error al guardar el partido en la fila {i + 1}: {str(e)}")  # Depuración

        if partidos_creados:
            messages.success(request, f"Se guardaron {len(partidos_creados)} partidos correctamente.")

        return redirect('partido_single', torneo_id=torneo.id)

    return redirect('partido_single', torneo_id=torneo.id)

#esto agregrue para el guardado de resultaultado por partidofrom django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from .models import Partido, ResultadoPartido

@csrf_exempt
def guardar_resultados(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            print("📩 Datos recibidos en la API:", data)  # 👀 Depuración

            partido_id = data.get('partido_id')
            partido = Partido.objects.get(id=partido_id)

            resultado, created = ResultadoPartido.objects.get_or_create(partido=partido)

            resultado.set1_jugador1 = int(data.get('set1_jugador1') or 0)
            resultado.set2_jugador1 = int(data.get('set2_jugador1') or 0)
            resultado.set3_jugador1 = int(data.get('set3_jugador1') or 0)
            resultado.set1_jugador2 = int(data.get('set1_jugador2') or 0)
            resultado.set2_jugador2 = int(data.get('set2_jugador2') or 0)
            resultado.set3_jugador2 = int(data.get('set3_jugador2') or 0)
            
            ganador_dni = data.get('ganador_dni')

            print(f"Ganador DNI recibido: {ganador_dni}")  # 👀 Depuración

            if ganador_dni:
                try:
                    ganador_jugador = Jugador.objects.get(dni=int(ganador_dni))  # 🔹 Convertimos a entero
                    resultado.ganador_jugador = ganador_jugador  # 🔹 Guardamos como objeto Jugador
                    print(f"✅ Guardando ganador con DNI {ganador_dni}")
                except Jugador.DoesNotExist:
                    print(f"⚠ Jugador con DNI {ganador_dni} no encontrado.")
                    resultado.ganador_jugador = None
            else:
                resultado.ganador_jugador = None
                print("⚠ No se recibió un ganador válido.")

            resultado.save()
            print("✅ Resultado guardado correctamente.")

            return JsonResponse({'success': True, 'message': 'Resultado guardado correctamente.'})
        except ValueError as e:
            print(f"❌ Error de valor: {e}")  # 👀 Debugging
            return JsonResponse({'success': False, 'message': 'Error en los datos numéricos.'})
        except Exception as e:
            print(f"❌ Error inesperado: {e}")  # 👀 Debugging
            return JsonResponse({'success': False, 'message': str(e)})
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)


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
    jugadores = Jugador.objects.filter(jugador_torneos__torneo=torneo).order_by('apellido', 'nombre')
    canchas = Cancha.objects.all()

    return render(request, 'partido_single.html', {
        'torneo': torneo,
        'numero_jornada': numero_jornada,
        'jugadores': jugadores,
        'canchas': canchas,
        'jornadas': jornadas,
    })



def jornada_detalle(request, torneo_id, jornada):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    partidos = Partido.objects.filter(torneo=torneo, jornada=jornada).select_related('jugador1', 'jugador2', 'cancha')
    
    return render(request, 'jornada_detalle.html', {
        'torneo': torneo,
        'jornada': jornada,
        'partidos': partidos,
    })

def listar_partidos(request):
    torneo_id = request.GET.get('torneo', '')  # Captura el torneo seleccionado
    search_fecha = request.GET.get('fecha', '')  # Captura la fecha seleccionada

    # Obtener todos los partidos
    partidos = Partido.objects.all()

    # Aplicar filtros si se selecciona un torneo o una fecha
    if torneo_id:
        partidos = partidos.filter(torneo_id=torneo_id)

    if search_fecha:
        partidos = partidos.filter(fecha=search_fecha)

    # Ordenar por fecha de manera descendente
    partidos = partidos.order_by('-fecha')

    return render(request, 'listar_partidos.html', {
        'page_obj': partidos,  # Enviar partidos filtrados
        'torneos': Torneo.objects.all(),  # Enviar la lista de torneos
        'torneo_id': torneo_id,  # Para mantener el torneo seleccionado en el HTML
        'search_fecha': search_fecha,  # Para mantener la fecha seleccionada en el HTML
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



def abm_cancha(request):
    if request.method == "POST":
        numero_cancha = request.POST.get("cancha")

        # 🟠 Verifica si la cancha ya existe
        if Cancha.objects.filter(cancha=numero_cancha).exists():
            return JsonResponse({"success": False, "errors": "La cancha ya existe."})

        # 🟠 Crea la nueva cancha
        Cancha.objects.create(cancha=numero_cancha)
        return JsonResponse({"success": True})  # ✅ Respuesta JSON exitosa

    return render(request, "abm_cancha.html")


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
            partido = Partido.objects.get(id=partido_id)

            partido.fecha = data['fecha']
            partido.hora = data['hora']
            partido.save()

            resultado, created = ResultadoPartido.objects.get_or_create(partido=partido)
            resultado.set1_jugador1 = data.get('set1_jugador1', 0)
            resultado.set2_jugador1 = data.get('set2_jugador1', 0)
            resultado.set3_jugador1 = data.get('set3_jugador1', 0)
            resultado.set1_jugador2 = data.get('set1_jugador2', 0)
            resultado.set2_jugador2 = data.get('set2_jugador2', 0)
            resultado.set3_jugador2 = data.get('set3_jugador2', 0)
            resultado.ganador_jugador_id = data.get('ganador', None)

            resultado.save()

            return JsonResponse({'success': True})
        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)})
    
    return JsonResponse({'success': False, 'message': 'Método no permitido'}, status=405)




@receiver(post_save, sender=Partido)
def actualizar_ranking(sender, instance, **kwargs):
    """ Actualiza el ranking cuando se guarda un partido con resultado """

    # Verificamos que el partido tenga un ganador guardado
    if instance.ganador and instance.perdedor:
        torneo = instance.torneo
        categoria = instance.categoria
        ganador = instance.ganador  # 🔥 Ya lo tienes guardado
        perdedor = instance.perdedor  # 🔥 Ya lo tienes guardado

        # 🔥 ACTUALIZAR RANKING DEL GANADOR 🔥
        ranking_ganador, created = Ranking.objects.get_or_create(
            jugador=ganador,
            torneo=torneo,
            categoria=categoria,
            defaults={"posicion": 0, "pj": 0, "pg": 0, "puntaje_total": 0}
        )
        ranking_ganador.pj += 1
        ranking_ganador.pg += 1
        ranking_ganador.puntaje_total += 100  # ✅ SUMA 100 PUNTOS
        ranking_ganador.save()

        # 🔥 ACTUALIZAR RANKING DEL PERDEDOR 🔥
        ranking_perdedor, created = Ranking.objects.get_or_create(
            jugador=perdedor,
            torneo=torneo,
            categoria=categoria,
            defaults={"posicion": 0, "pj": 0, "pg": 0, "puntaje_total": 0}
        )
        ranking_perdedor.pj += 1
        ranking_perdedor.puntaje_total -= 50  # ❌ RESTA 50 PUNTOS
        ranking_perdedor.save()

        print(f"🏆 Ranking de {torneo.nombre} actualizado: {ganador.nombre} (+100) | {perdedor.nombre} (-50)")


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
    
    
def procesar_ascenso(request):
    if request.method == 'POST':
        cantidad = int(request.POST.get('cantidad_jugadores', 0))
        aplicar_a = request.POST.get('aplicar_a')
        torneo_id = request.POST.get('torneo_id')

        # Acá podés aplicar la lógica que desees
        if aplicar_a == 'todos':
            # Aplica ascenso a todos los torneos
            # lógica para múltiples torneos...
            messages.success(request, f'Se ascendieron {cantidad} jugadores en todos los torneos.')
        else:
            # Aplica ascenso a uno solo
            # lógica para torneo_id específico...
            messages.success(request, f'Se ascendieron {cantidad} jugadores en el torneo seleccionado.')

        return redirect('admin_menu')  # o donde quieras redirigir

    return redirect('admin_menu')  # por si entran por GET

from .models import Torneo

def vista_admin(request):
    torneos = Torneo.objects.all().order_by('-fecha_inicio')  # o como prefieras ordenarlos
    return render(request, 'abm_torneo.html', {
        'torneos': torneos,
        # ...otros datos si los necesitás...
    })
