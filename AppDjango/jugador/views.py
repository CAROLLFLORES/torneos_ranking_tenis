#  5/04/2025 se realizo el agregar el id Carga masiva categoria 101 y Carga Masiva de Jugadores 102


from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q
from django.http import JsonResponse, HttpResponse
from django.contrib.auth.decorators import login_required, user_passes_test
from django.utils import timezone

from .models import Jugador, Categoria, JugadorCategoria, EstadoJugador
from torneo.models import TorneoJugador, Partido, Torneo, Equipo

from .forms import JugadorForm
from loginAdmin.views import es_admin

from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet

import pandas as pd
from io import BytesIO
from collections import defaultdict
from ranking.models import Ranking, RankingEquipo


def jugador_detalle(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)
    return render(request, 'datos_jugador.html', {'jugador': jugador})


@login_required
@user_passes_test(es_admin)
def CrearJugador(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        apellido = request.POST.get("apellido")

        if Jugador.objects.filter(nombre__iexact=nombre, apellido__iexact=apellido).exists():
            messages.warning(request, "⚠️ El jugador ya existe en la base de datos.")
            return redirect("admin_carga_jugador")

        form = JugadorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            messages.success(request, "✅ Jugador creado correctamente.")
            return redirect("admin_carga_jugador")
        else:
            messages.error(request, "❌ Error al crear el jugador. Revisá los campos.")
    else:
        form = JugadorForm()

    return render(request, "admin_carga_jugador.html", {"form": form})

@login_required
@user_passes_test(es_admin)
def guardar_jugador(request):
    return render(request, "guardar_jugador.html")

@login_required
@user_passes_test(es_admin)
def modificar_jugador(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)
    if request.method == "POST":
        nombre = request.POST.get('nombre')
        apellido = request.POST.get('apellido')
        sexo = request.POST.get('sexo')
        categorias_ids = request.POST.getlist('categorias[]')  # checkboxes del modal
        estado = request.POST.get('estado', jugador.estado)    # ACT/INA/DEL

        # Datos base
        jugador.nombre = nombre
        jugador.apellido = apellido
        jugador.sexo = sexo
        jugador.estado = estado

        # Si no está borrado, limpiamos fecha_baja (por si reactivaron)
        if estado != EstadoJugador.BORRADO:
            jugador.fecha_baja = None

        jugador.save()

        # Actualizar categorías
        jugador.categorias.clear()
        for categoria_id in categorias_ids:
            categoria = get_object_or_404(Categoria, id_categoria=categoria_id)
            JugadorCategoria.objects.get_or_create(jugador=jugador, categoria=categoria)

        messages.success(request, "Jugador actualizado exitosamente.")
        return redirect('listado_jugadores')

    return render(request, 'modificar_jugador.html', {'jugador': jugador})


def listado_jugadores(request):
    search = request.GET.get('search', '').strip()
    sexo_filter = request.GET.get('sexo', '').strip()
    categoria_filter = request.GET.get('categoria', '').strip()
    estado_filter = request.GET.get('estado', '').strip()  # ACT/INA/DEL (opcional)

    
    # Solo el admin puede listar BORRADOS
    if estado_filter == EstadoJugador.BORRADO and not (request.user.is_authenticated and request.user.is_staff):
        estado_filter = ''  # ignora intento de ver DEL si no es admin

    # Base del queryset:
    if estado_filter == EstadoJugador.BORRADO and (request.user.is_authenticated and request.user.is_staff):
        jugadores_qs = Jugador.objects.all().order_by('apellido', 'nombre')   # incluir DEL
    else:
        jugadores_qs = Jugador.objects.visibles().order_by('apellido', 'nombre')  # oculta DEL

    # Filtros
    if search:
        jugadores_qs = jugadores_qs.filter(Q(nombre__icontains=search) | Q(apellido__icontains=search))
    if sexo_filter:
        jugadores_qs = jugadores_qs.filter(sexo=sexo_filter)
    if categoria_filter:
        jugadores_qs = jugadores_qs.filter(categorias__id_categoria=categoria_filter)
    if estado_filter:
        jugadores_qs = jugadores_qs.filter(estado=estado_filter)

    jugadores_qs = jugadores_qs.distinct()

    paginator = Paginator(jugadores_qs, 15)
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    todas_categorias = Categoria.objects.all().order_by('nivel')

    return render(request, 'listado_jugadores.html', {
        'jugadores': page_obj,
        'todas_categorias': todas_categorias,
        'filtros': {
            'search': search,
            'sexo': sexo_filter,
            'categoria': categoria_filter,
            'estado': estado_filter,
        }
    })



def datos_jugador(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)

    torneos = Torneo.objects.filter(
        Q(torneo_jugadores__jugador=jugador) |
        Q(equipos__jugador1=jugador) |
        Q(equipos__jugador2=jugador)
    ).distinct()

    torneos_data = []
    for torneo in torneos:
        ranking = None
        puesto = None
        categoria = torneo.categorias.first()

        if torneo.tipo_juego in ["Doble", "Mixto"]:
            equipos = Equipo.objects.filter(
                torneo=torneo
            ).filter(
                Q(jugador1=jugador) | Q(jugador2=jugador)
            )

            for equipo in equipos:
                ranking = RankingEquipo.objects.filter(
                    torneo=torneo,
                    equipo=equipo
                ).order_by('-anio', '-bimestre', '-id_ranking_equipo').last()

                if ranking:
                    categoria = ranking.categoria or categoria
                    puesto = ranking.posicion if ranking.posicion and ranking.posicion > 0 else RankingEquipo.objects.filter(
                        torneo=torneo,
                        categoria=categoria
                    ).filter(
                        puntaje_total_categoria__gt=ranking.puntaje_total_categoria
                    ).count() + 1
                    break  

            torneos_data.append({
                'id': torneo.id,
                'torneo': torneo,
                'nombre': torneo.nombre,
                'categoria': categoria,
                'fecha': torneo.fecha_inicio,
                'ranking': ranking,
                'puesto': puesto,
            })

        else:
            ranking = Ranking.objects.filter(
                torneo=torneo,
                jugador=jugador
            ).order_by('-anio', '-bimestre', '-id_ranking').last()

            if ranking:
                categoria = ranking.categoria or categoria
                puesto = ranking.posicion if ranking.posicion and ranking.posicion > 0 else Ranking.objects.filter(
                    torneo=torneo,
                    categoria=categoria
                ).filter(
                    puntaje_total_categoria__gt=ranking.puntaje_total_categoria
                ).count() + 1

            torneos_data.append({
                'id': torneo.id,
                'torneo': torneo,
                'nombre': torneo.nombre,
                'categoria': categoria,
                'fecha': torneo.fecha_inicio,
                'ranking': ranking,
                'puesto': puesto,
            })

    partidos = Partido.objects.filter(
        Q(jugador1=jugador) | Q(jugador2=jugador) |
        Q(equipo1__jugador1=jugador) | Q(equipo1__jugador2=jugador) |
        Q(equipo2__jugador1=jugador) | Q(equipo2__jugador2=jugador)
    ).select_related(
        'torneo', 'resultado',
        'equipo1__jugador1', 'equipo1__jugador2',
        'equipo2__jugador1', 'equipo2__jugador2'
    ).order_by('-fecha')

    partidos_por_nombre = defaultdict(list)
    for partido in partidos:
        partidos_por_nombre[partido.torneo.nombre].append(partido)

    return render(request, 'datos_jugador.html', {
        'jugador': jugador,
        'torneos_data': torneos_data,
        'partidos_agrupados': partidos_por_nombre.items(),
    })

def busqueda_jugador(request):
    nombre = request.GET.get('nombre', '')
    apellido = request.GET.get('apellido', '')
    accion = request.GET.get('accion', '')

    if accion == 'ver' and apellido:
        try:
            jugador = Jugador.objects.get(apellido=apellido)
            return redirect('datos_jugador', dni=jugador.dni)  # Usar dni para redirigir
        except Jugador.DoesNotExist:
            return render(request, 'listado_jugadores.html', {'error': 'Jugador no encontrado.'})

    jugadores = Jugador.objects.all()
    if nombre:
        jugadores = jugadores.filter(nombre__icontains=nombre)
    if apellido:
        jugadores = jugadores.filter(apellido__icontains=apellido)

    jugadores = jugadores.order_by('apellido', 'nombre')

    return render(request, 'listado_jugadores.html', {'jugadores': jugadores})


@login_required
@user_passes_test(es_admin)
def borrar_jugador(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)
    jugador.estado = EstadoJugador.BORRADO
    jugador.fecha_baja = timezone.now().date()
    jugador.save(update_fields=['estado', 'fecha_baja'])
    messages.success(request, f"🗑️ Se marcó '{jugador.apellido}, {jugador.nombre}' como BORRADO.")
    return redirect('listado_jugadores')

    
@login_required
@user_passes_test(es_admin)
def borrado_exitoso(request, jugador_dni):
    return render(request, 'borrado_exitoso.html', {'jugador_dni': jugador_dni})


@login_required
@user_passes_test(es_admin)
def abm_categoria(request):
    if request.method == "POST":
        c_nivel = request.POST.get("nivel")
        c_edad = request.POST.get("edad")
        c_tipo_juego = request.POST.get("tipo_juego")
        c_genero = request.POST.get("genero")  # ✅ NUEVO

        try:
            categoria_existente = Categoria.objects.filter(
                nivel=c_nivel,
                edad=c_edad,
                tipo_juego=c_tipo_juego,
                genero=c_genero  # ✅ VALIDAMOS también por género
            ).exists()

            if categoria_existente:
                return JsonResponse({"success": False, "errors": "La categoría ya existe."})
            else:
                Categoria.objects.create(
                    nivel=c_nivel,
                    edad=c_edad,
                    tipo_juego=c_tipo_juego,
                    genero=c_genero  # ✅ AHORA SE GUARDA
                )
                return JsonResponse({"success": True})  # ✅ Éxito
        except Exception as e:
            print(f"Error al crear categoría: {e}")
            return JsonResponse({"success": False, "errors": str(e)})

    return render(request, "abm_categoria.html")

@login_required
@user_passes_test(es_admin)
def exito_categoria(request):
    return render(request, "exito_categoria.html")

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger

@login_required
@user_passes_test(es_admin)
def listado_categorias(request):
    qs = Categoria.objects.all().order_by('nivel')

    # Obtener filtros del GET
    tipo_juego = request.GET.get('tipo_juego')
    genero = request.GET.get('genero')
    nivel = request.GET.get('nivel')
    edad = request.GET.get('edad')

    # Filtros acumulativos
    if tipo_juego:
        qs = qs.filter(tipo_juego=tipo_juego)
    if genero:
        qs = qs.filter(genero=genero)
    if nivel:
        qs = qs.filter(nivel=nivel)
    if edad:
        qs = qs.filter(edad=edad)

    paginator = Paginator(qs, 50)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    return render(request, 'listados_categorias.html', {
        'categorias': page_obj,
        'page_obj': page_obj,
        'filtros': {
            'tipo_juego': tipo_juego or '',
            'genero': genero or '',
            'nivel': nivel or '',
            'edad': edad or '',
        }
    })

@login_required
@user_passes_test(es_admin)
def eliminar_categoria(request, id_categoria):
    categoria = get_object_or_404(Categoria, id_categoria=id_categoria)
    categoria.delete()
    return redirect('listados_categorias')

@login_required
@user_passes_test(es_admin)
def editar_categoria(request, id_categoria):
    categoria = get_object_or_404(Categoria, id_categoria=id_categoria)

    if request.method == "POST":
        nivel = request.POST.get('nivel')
        edad = request.POST.get('edad')
        tipo_juego = request.POST.get('tipo_juego')
        genero = request.POST.get('genero')

        categoria.nivel = nivel
        categoria.edad = edad
        categoria.tipo_juego = tipo_juego
        categoria.genero = genero
        categoria.save()

        messages.success(request, "Categoría actualizada exitosamente.")
        return redirect('listados_categorias')  # Asegurate que este nombre de vista sea correcto

    # En este caso no se debería llegar con GET porque es desde un modal
    return redirect('listados_categorias')

#para generar pdf

@login_required
@user_passes_test(es_admin)
def exportar_jugadores_pdf(request):
    # Filtros desde la URL
    search = request.GET.get("search", "").strip()
    sexo = request.GET.get("sexo", "").strip()
    categoria = request.GET.get("categoria", "").strip()
    estado = request.GET.get("estado", "").strip()  # opcional

    # Base: visibles (oculta borrados)
    jugadores = Jugador.objects.visibles()

    if search:
        jugadores = jugadores.filter(Q(nombre__icontains=search) | Q(apellido__icontains=search))
    if sexo:
        jugadores = jugadores.filter(sexo=sexo)
    if categoria:
        jugadores = jugadores.filter(categorias__id_categoria=categoria)
    if estado:
        jugadores = jugadores.filter(estado=estado)

    # PDF
    buffer = BytesIO()
    c = canvas.Canvas(buffer, pagesize=A4)
    width, height = A4
    y = height - 40

    # Encabezados
    c.setFont("Helvetica-Bold", 14)
    c.drawString(100, y, "Listado de Jugadores")
    y -= 30

    # Columnas
    c.setFont("Helvetica-Bold", 10)
    c.drawString(40, y, "Apellido")
    c.drawString(150, y, "Nombre")
    c.drawString(250, y, "Sexo")
    c.drawString(300, y, "Categorías")
    y -= 20

    # Contenido
    c.setFont("Helvetica", 10)
    for jugador in jugadores:
        if y < 60:
            c.showPage()
            y = height - 40

        categorias = ", ".join([
            f"{c.tipo_juego}-{c.genero}-{c.nivel}-{c.edad}" for c in jugador.categorias.all()
        ]) or "Sin categoría"

        c.setFont("Helvetica", 10)
        c.drawString(40, y, jugador.apellido.upper())
        c.drawString(150, y, jugador.nombre.capitalize())
        c.drawString(250, y, jugador.sexo)

        # 👇 CATEGORÍAS: achicamos y dividimos en varias líneas si es largo
        c.setFont("Helvetica", 8)
        max_line_length = 70  # Ajustable: ancho máximo de cada línea
        lines = [categorias[i:i+max_line_length] for i in range(0, len(categorias), max_line_length)]
        for i, line in enumerate(lines):
            c.drawString(300, y - (i * 10), line)

        y -= 20 + (10 * (len(lines) - 1))  # Ajustamos el y según las líneas extra

    c.showPage()
    c.save()
    buffer.seek(0)
    return HttpResponse(buffer, content_type="application/pdf")

#--------------------------------------------------------------------------------------------------------------
#Carga masiva categoria 101
@login_required
@user_passes_test(es_admin)
def carga_masiva_categoria(request):
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        print(" Archivos recibidos:", request.FILES)
        try:
            excel_file = request.FILES['archivo_excel']
            df = pd.read_excel(excel_file, engine='openpyxl')

            print("🧩 Columnas detectadas:", df.columns.tolist())

            for _, row in df.iterrows():
                Categoria.objects.create(
                    nivel=str(row.get('nivel', 'Sin nivel')),
                    edad=str(row.get('edad', '0')),           # <- string
                    tipo_juego=str(row.get('tipo_juego', 'Sin tipo')),
                    genero=str(row.get('genero', 'Sin tipo')) # por si está la columna
                )

            return JsonResponse({'exito': True})
        except Exception as e:
            print("❌ Error al procesar archivo:", str(e))
            return JsonResponse({'exito': False, 'error': str(e)})

    return JsonResponse({'exito': False, 'error': 'Método no permitido'})
#--------------------------------------------------------------------------------------------------------------

#--------------------------------------------------------------------------------------------------------------
#Carga Masiva de Jugadores 102
@login_required
@user_passes_test(es_admin)
def carga_masiva_jugadores(request):
    if request.method == 'POST' and request.FILES.get('archivo_excel'):
        try:
            excel_file = request.FILES['archivo_excel']
            df = pd.read_excel(excel_file, engine='openpyxl')

            for _, row in df.iterrows():
                nombre = str(row.get('nombre', '')).strip()
                apellido = str(row.get('apellido', '')).strip()
                sexo = str(row.get('sexo', '')).strip()

                if not nombre or not apellido or not sexo:
                    continue  # fila incompleta

                # Verificar si ya existe (esto puede crear duplicados si hay homónimos)
                jugador, creado = Jugador.objects.get_or_create(
                    nombre=nombre,
                    apellido=apellido,
                    sexo=sexo
                )

                # Procesar categorías (separadas por ';')
                categorias_str = str(row.get('categorias', '')).strip()
                if categorias_str and categorias_str.lower() != 'nan':
                    for cat_str in categorias_str.split(';'):
                        cat_str = cat_str.strip()
                        if not cat_str:
                            continue

                        # Formatos soportados:
                        # 1) nivel-edad-tipo_juego-genero
                        # 2) nivel-edad-tipo_juego  (genero por defecto 'Sin tipo')
                        partes = [p.strip() for p in cat_str.split('-')]
                        try:
                            if len(partes) == 4:
                                nivel, edad, tipo_juego, genero = partes
                            elif len(partes) == 3:
                                nivel, edad, tipo_juego = partes
                                genero = 'Sin tipo'
                            else:
                                print(f"❌ Formato de categoría desconocido: '{cat_str}'")
                                continue

                            categoria = Categoria.objects.get(
                                nivel=nivel, edad=str(edad), tipo_juego=tipo_juego, genero=genero
                            )
                            JugadorCategoria.objects.get_or_create(jugador=jugador, categoria=categoria)
                        except Categoria.DoesNotExist:
                            print(f"❌ No existe la categoría: {cat_str}")
                        except Exception as e:
                            print(f"❌ Error con categoría '{cat_str}': {e}")

            return JsonResponse({'exito': True})
        except Exception as e:
            print("❌ Error general al procesar jugadores:", str(e))
            return JsonResponse({'exito': False, 'error': str(e)})

    return JsonResponse({'exito': False, 'error': 'Método no permitido'})
#--------------------------------------------------------------------------------------------------------------