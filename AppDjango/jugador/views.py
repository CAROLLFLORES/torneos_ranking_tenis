#  5/04/2025 se realizo el agregar el id Carga masiva categoria 101 y Carga Masiva de Jugadores 102

from django.core.paginator import Paginator, EmptyPage, PageNotAnInteger
from django.shortcuts import render, redirect, get_object_or_404
from .models import Jugador,Categoria,JugadorCategoria
from torneo.models import TorneoJugador, Partido, Torneo
from django.urls import reverse
from django.contrib import messages
from django.db.models import Q
from .forms import JugadorForm
from django.http import JsonResponse
from django.http import HttpResponse
from reportlab.lib.pagesizes import A4
from reportlab.pdfgen import canvas
from reportlab.lib import colors
from reportlab.platypus import Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from jugador.models import Jugador, Categoria
from django.http import JsonResponse
import pandas as pd
from django.contrib.auth.decorators import login_required, user_passes_test
from loginAdmin.views import es_admin
from io import BytesIO
from collections import defaultdict
from ranking.models import Ranking, RankingEquipo
from .models import Jugador  # solo Jugador está en jugador.models
from torneo.models import Torneo, Partido, Equipo  # estos están en torneo

def jugador_detalle(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)
    return render(request, 'datos_jugador.html', {'jugador': jugador})


@login_required
@user_passes_test(es_admin)
def CrearJugador(request):
    if request.method == "POST":
        nombre = request.POST.get("nombre")
        apellido = request.POST.get("apellido")

        # 🔍 Verificar si ya existe un jugador con el mismo nombre y apellido
        if Jugador.objects.filter(nombre__iexact=nombre, apellido__iexact=apellido).exists():
            return JsonResponse({"success": False, "errors": "El jugador ya existe en la base de datos."})

        form = JugadorForm(request.POST, request.FILES)
        if form.is_valid():
            form.save()
            return JsonResponse({"success": True})  # ✅ Respuesta exitosa
        else:
            return JsonResponse({"success": False, "errors": form.errors})  # ❌ Errores de validación

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
        categorias_ids = request.POST.getlist('categorias[]')  # Captura las categorías seleccionadas

        jugador.nombre = nombre
        jugador.apellido = apellido
        jugador.sexo = sexo
        jugador.save()

        # Actualizar las categorías
        jugador.categorias.clear()  # Elimina las categorías anteriores
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

    jugadores_qs = Jugador.objects.all().order_by('apellido', 'nombre')

    if search:
        jugadores_qs = jugadores_qs.filter(
            Q(nombre__icontains=search) | Q(apellido__icontains=search)
        )

    if sexo_filter:
        jugadores_qs = jugadores_qs.filter(sexo=sexo_filter)

    if categoria_filter:
        jugadores_qs = jugadores_qs.filter(categorias__id_categoria=categoria_filter)

    # Evita duplicados si un jugador está en varias categorías
    jugadores_qs = jugadores_qs.distinct()

    paginator = Paginator(jugadores_qs, 50)
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
        }
    })


def datos_jugador(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)

    # 🔹 Torneos en los que participa
    torneos = Torneo.objects.filter(
        Q(torneo_jugadores__jugador=jugador) |
        Q(equipos__jugador1=jugador) |
        Q(equipos__jugador2=jugador)
    ).distinct()

    torneos_data = []
    for torneo in torneos:
        if torneo.tipo_juego in ["Doble", "Mixto"]:
            equipo = Equipo.objects.filter(
                torneo=torneo
            ).filter(
                Q(jugador1=jugador) | Q(jugador2=jugador)
            ).first()

            ranking = None
            puesto = None
            if equipo:
                ranking = RankingEquipo.objects.filter(
                    torneo=torneo,
                    equipo=equipo
                ).order_by('-anio', '-bimestre', '-id_ranking_equipo').first()

                if ranking:
                    if ranking.posicion and ranking.posicion > 0:
                        puesto = ranking.posicion
                    else:
                        puesto = RankingEquipo.objects.filter(
                            torneo=torneo,
                            categoria=ranking.categoria
                        ).filter(
                            puntaje_total_categoria__gt=ranking.puntaje_total_categoria
                        ).count() + 1

            torneos_data.append({
                'torneo': torneo,
                'nombre': torneo.nombre,
                'categoria': ranking.categoria if ranking else torneo.categorias.first(),
                'fecha': torneo.fecha_inicio,
                'ranking': ranking,
                'puesto': puesto,
            })

        else:  # Torneo individual
            ranking = Ranking.objects.filter(
                torneo=torneo,
                jugador=jugador
            ).order_by('-anio', '-bimestre', '-id_ranking').first()

            puesto = None
            if ranking:
                if ranking.posicion and ranking.posicion > 0:
                    puesto = ranking.posicion
                else:
                    puesto = Ranking.objects.filter(
                        torneo=torneo,
                        categoria=ranking.categoria
                    ).filter(
                        puntaje_total_categoria__gt=ranking.puntaje_total_categoria
                    ).count() + 1

            torneos_data.append({
                'torneo': torneo,
                'nombre': torneo.nombre,
                'categoria': ranking.categoria if ranking else torneo.categorias.first(),
                'fecha': torneo.fecha_inicio,
                'ranking': ranking,
                'puesto': puesto,
            })

    # 🔹 Partidos jugados
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
    try:
        jugador = get_object_or_404(Jugador, dni=dni)
        jugador.delete()
        messages.success(request, f"Se ha eliminado '{jugador.nombre}' exitosamente.")
        return redirect('borrado_exitoso', jugador_dni=dni)

    except Jugador.DoesNotExist:
        messages.error(request, "Error al eliminar el jugador, no existe.")
        return redirect(reverse('listado_jugadores'))
    
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
    search = request.GET.get("search", "")
    sexo = request.GET.get("sexo", "")
    categoria = request.GET.get("categoria", "")

    # Filtrado
    jugadores = Jugador.objects.all()
    if search:
        jugadores = jugadores.filter(nombre__icontains=search) | jugadores.filter(apellido__icontains=search)
    if sexo:
        jugadores = jugadores.filter(sexo=sexo)
    if categoria:
        jugadores = jugadores.filter(categorias__id_categoria=categoria)

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
                    nivel=row['nivel'],
                    edad=int(row['edad']),
                    tipo_juego=row['tipo_juego']
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
                nombre = row['nombre']
                apellido = row['apellido']
                sexo = row['sexo']

                # Verificar si ya existe
                jugador, creado = Jugador.objects.get_or_create(
                    nombre=nombre,
                    apellido=apellido,
                    sexo=sexo
                )

                # Procesar categorías (separadas por ;)
                categorias_str = str(row['categorias'])  # Asegurar string
                for cat_str in categorias_str.split(';'):
                    try:
                        nivel, edad, tipo_juego = cat_str.strip().split('-')
                        categoria = Categoria.objects.get(nivel=nivel, edad=int(edad), tipo_juego=tipo_juego)
                        JugadorCategoria.objects.get_or_create(jugador=jugador, categoria=categoria)
                    except Exception as e:
                        print(f"❌ Categoría inválida para jugador {nombre} {apellido}: {cat_str} ({e})")

            return JsonResponse({'exito': True})
        except Exception as e:
            print("❌ Error general al procesar jugadores:", str(e))
            return JsonResponse({'exito': False, 'error': str(e)})

    return JsonResponse({'exito': False, 'error': 'Método no permitido'})
#--------------------------------------------------------------------------------------------------------------