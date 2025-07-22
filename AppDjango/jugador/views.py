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
    search = request.GET.get('search', '')
    sexo_filter = request.GET.get('sexo', '')
    categoria_filter = request.GET.get('categoria', '')

    # 🔹 Filtrar jugadores por nombre, apellido, sexo y categoría
    jugadores = Jugador.objects.all().order_by('apellido', 'nombre')


    if search:
        jugadores = jugadores.filter(
            Q(nombre__icontains=search) | Q(apellido__icontains=search)
        )

    if sexo_filter:
        jugadores = jugadores.filter(sexo=sexo_filter)

    if categoria_filter:
        jugadores = jugadores.filter(categorias__id_categoria=categoria_filter)

    # 🔹 Paginación
    paginator = Paginator(jugadores, 100)  # 20 jugadores por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # 🔹 Obtener todas las categorías para el selector
    todas_categorias = Categoria.objects.all()

    return render(request, 'listado_jugadores.html', {
        'jugadores': page_obj,
        'todas_categorias': todas_categorias,
        'search': search,
        'sexo': sexo_filter,
        'categoria_seleccionada': categoria_filter
    })

from collections import defaultdict
def datos_jugador(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)

    # 🔹 Torneos en los que está inscrito
    torneos = Torneo.objects.filter(torneo_jugadores__jugador=jugador).distinct()
    from ranking.models import Ranking

    torneos_data = []

    for torneo in torneos:
        ranking = Ranking.objects.filter(
            torneo=torneo,
            jugador=jugador,
            activo=True
        ).first()

        if ranking:
            todos_rankings = Ranking.objects.filter(
                torneo=torneo,
                bimestre=ranking.bimestre,
                anio=ranking.anio,
                categoria=ranking.categoria,
                activo=True
            ).order_by('-puntaje_total_categoria')

            posicion = None
            for i, r in enumerate(todos_rankings, start=1):
                if r.jugador == jugador:
                    posicion = i
                    break

            torneos_data.append({
                'nombre': torneo.nombre,
                'categoria': ranking.categoria,
                'fecha': torneo.fecha_inicio,
                'ranking': posicion,
                'puntaje': ranking.puntaje_total_categoria,
            })
        else:
            torneos_data.append({
                'nombre': torneo.nombre,
                'categoria': torneo.categorias.first(),  # fallback si no tiene ranking
                'fecha': torneo.fecha_inicio,
                'ranking': None,
                'puntaje': None,
            })

    # 🔹 Partidos jugados por el jugador
    partidos = Partido.objects.filter(
        Q(jugador1=jugador) | Q(jugador2=jugador)
    ).select_related('torneo').order_by('-fecha')

    # 🔸 Agrupar los partidos por nombre del torneo
    from collections import defaultdict
    partidos_por_nombre = defaultdict(list)
    for partido in partidos:
        nombre = partido.torneo.nombre
        partidos_por_nombre[nombre].append(partido)

    return render(request, 'datos_jugador.html', {
        'jugador': jugador,
        'torneos': torneos,
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
        
        try:
            categoria_existente = Categoria.objects.filter(nivel=c_nivel, edad=c_edad, tipo_juego=c_tipo_juego).exists()
            
            if categoria_existente:
                return JsonResponse({"success": False, "errors": "La categoría ya existe."})
            else:
                Categoria.objects.create(nivel=c_nivel, edad=c_edad, tipo_juego=c_tipo_juego)
                return JsonResponse({"success": True})  # ✅ Respuesta JSON exitosa
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
    paginator = Paginator(qs, 10)
    page_number = request.GET.get('page')
    try:
        page_obj = paginator.page(page_number)
    except PageNotAnInteger:
        page_obj = paginator.page(1)
    except EmptyPage:
        page_obj = paginator.page(paginator.num_pages)

    # PASAMOS 'categorias' = page_obj, y también page_obj para la paginación
    return render(request, 'listados_categorias.html', {
        'categorias': page_obj,
        'page_obj': page_obj,
    })


@login_required
@user_passes_test(es_admin)
def eliminar_categoria(request, id_categoria):
    categoria = get_object_or_404(Categoria, id_categoria=id_categoria)
    categoria.delete()
    return redirect('listados_categorias')

#para generar pdf

@login_required
@user_passes_test(es_admin)
def exportar_jugadores_pdf(request):
    # 🟡 1️⃣ Captura los filtros
    search = request.GET.get('search', '')
    sexo_filter = request.GET.get('sexo', '')
    categoria_filter = request.GET.get('categoria', '')

    # 🟡 2️⃣ Filtra los jugadores según los parámetros recibidos
    jugadores = Jugador.objects.all()

    if search:
        jugadores = jugadores.filter(
            Q(nombre__icontains=search) | Q(apellido__icontains=search)
        )
    if sexo_filter:
        jugadores = jugadores.filter(sexo=sexo_filter)
    if categoria_filter:
        jugadores = jugadores.filter(categorias__id_categoria=categoria_filter)

    # 🟡 3️⃣ Obtiene la categoría seleccionada
    categoria_nombre = "Todas"
    if categoria_filter:
        categoria_obj = Categoria.objects.filter(id_categoria=categoria_filter).first()
        if categoria_obj:
            categoria_nombre = f"{categoria_obj.nivel} - {categoria_obj.tipo_juego} - {categoria_obj.edad} años"

    sexo_nombre = "Todos"
    if sexo_filter == "M":
        sexo_nombre = "Masculino"
    elif sexo_filter == "F":
        sexo_nombre = "Femenino"

    # 🟡 4️⃣ Genera el PDF
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="listado_jugadores.pdf"'

    c = canvas.Canvas(response, pagesize=A4)
    c.setTitle('Listado de Jugadores')

    # 🟠 5️⃣ Títulos
    c.setFont("Helvetica-Bold", 14)
    c.drawString(200, 800, "Listado de Jugadores")

    c.setFont("Helvetica", 11)
    c.drawString(100, 780, f"Categoría: {categoria_nombre}")
    c.drawString(100, 765, f"Género: {sexo_nombre}")

    # 🟠 6️⃣ Genera la tabla de jugadores con categorías
    jugadores = jugadores.prefetch_related('categorias')
    data = [["Apellido", "Nombre", "Sexo", "Categorías"]]

    for jugador in jugadores:
        categorias = ", ".join([f"{c.nivel}-{c.tipo_juego}" for c in jugador.categorias.all()])
        data.append([
            jugador.apellido.upper(),
            jugador.nombre.capitalize(),
            "Masculino" if jugador.sexo == "M" else "Femenino",
            categorias if categorias else "Sin categoría"
        ])

    # 🟠 7️⃣ Estilo de la tabla
    table = Table(data, colWidths=[100, 100, 100])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.orange),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 10),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black),
    ]))

    # 🟡 8️⃣ Coloca la tabla en el PDF
    table.wrapOn(c, 400, 600)
    table.drawOn(c, 100, 650 - len(data) * 20)

    # 🟠 9️⃣ Cierra el PDF
    c.save()

    return response

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