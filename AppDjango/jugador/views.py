from django.shortcuts import render, redirect, get_object_or_404
from .models import Jugador,Categoria,JugadorCategoria
from torneo.models import TorneoJugador, Partido, Torneo
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q
from .forms import JugadorForm

def jugador_detalle(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)
    return render(request, 'datos_jugador.html', {'jugador': jugador})

def CrearJugador(request):
    if request.method == "POST":
        form = JugadorForm(request.POST)
        if form.is_valid():
            jugador = form.save()
            messages.success(request, "Jugador creado exitosamente.")
            return redirect('guardar_jugador')
        else:
            messages.error(request, "Error en el formulario. Revisa los datos ingresados.")
    else:
        form = JugadorForm()
    return render(request, "admin_carga_jugador.html", {"form": form})

def guardar_jugador(request):
    return render(request, "guardar_jugador.html")

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

    # Filtrar jugadores por nombre o apellido
    jugadores = Jugador.objects.all()
    if search:
        jugadores = jugadores.filter(Q(nombre__icontains=search) | Q(apellido__icontains=search))

    # Filtrar por sexo
    if sexo_filter:
        jugadores = jugadores.filter(sexo=sexo_filter)

    # Paginación
    paginator = Paginator(jugadores, 20)  # Muestra 20 jugadores por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    # Pasar todas las categorías al contexto
    todas_categorias = Categoria.objects.all()

    return render(request, 'listado_jugadores.html', {
        'jugadores': page_obj,
        'todas_categorias': todas_categorias,
        'search': search,
        'sexo': sexo_filter
    })


def datos_jugador(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)

    # 🔹 Obtener los torneos en los que está inscrito el jugador
    torneos = Torneo.objects.filter(torneo_jugadores__jugador=jugador).distinct()

    # 🔹 Obtener los partidos en los que ha jugado el jugador
    partidos = Partido.objects.filter(
        (Q(jugador1=jugador) | Q(jugador2=jugador))
    ).select_related('torneo').order_by('-fecha')

    return render(request, 'datos_jugador.html', {
        'jugador': jugador,
        'torneos': torneos,
        'partidos': partidos,
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

def borrar_jugador(request, dni):
    try:
        jugador = get_object_or_404(Jugador, dni=dni)
        jugador.delete()
        messages.success(request, f"Se ha eliminado '{jugador.nombre}' exitosamente.")
        return redirect('borrado_exitoso', jugador_dni=dni)

    except Jugador.DoesNotExist:
        messages.error(request, "Error al eliminar el jugador, no existe.")
        return redirect(reverse('listado_jugadores'))
    
def borrado_exitoso(request, jugador_dni):
    return render(request, 'borrado_exitoso.html', {'jugador_dni': jugador_dni})

def abm_categoria(request):
    if request.method == "POST":
        c_nivel = request.POST.get("nivel")
        c_edad = request.POST.get("edad")
        c_tipo_juego = request.POST.get("tipo_juego")
        
        try:
            categoria_existente = Categoria.objects.filter(nivel=c_nivel, edad=c_edad, tipo_juego=c_tipo_juego).exists()
            
            if categoria_existente:
                return render(request, "error_page.html", {"error": "La categoría ya existe."})
            else:
                categoria = Categoria(nivel=c_nivel, edad=c_edad, tipo_juego=c_tipo_juego)
                categoria.save()
                return redirect('exito_categoria')  
        except Exception as e:
            print(f"Error al crear categoría: {e}")
            return render(request, "error_page.html", {"error": str(e)})
    
    return render(request, "abm_categoria.html")

def exito_categoria(request):
    return render(request, "exito_categoria.html")

def listado_categorias(request):
    categorias = Categoria.objects.all()
    return render(request, 'listados_categorias.html', {'categorias': categorias})

def eliminar_categoria(request, id_categoria):
    categoria = get_object_or_404(Categoria, id_categoria=id_categoria)
    categoria.delete()
    return redirect('listados_categorias')


