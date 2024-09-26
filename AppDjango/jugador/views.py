from django.shortcuts import render, redirect, get_object_or_404
from .models import Jugador, Categoria, JugadorCategoria
from django.urls import reverse
from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import Q  # Asegúrate de importar Q para las búsquedas

def jugador_detalle(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)
    return render(request, 'datos_jugador.html', {'jugador': jugador})

def CrearJugador(request):
    categorias = Categoria.objects.all()  # Obtén todas las categorías para el contexto

    if request.method == "POST":
        j_nombre = request.POST.get("nombre")
        j_apellido = request.POST.get("apellido")
        j_dni = request.POST.get("dni")
        j_sexo = request.POST.get("sexo")
        categorias_seleccionadas = request.POST.getlist("categorias")  # Obtener categorías seleccionadas

        try:
            jugador = Jugador(
                nombre=j_nombre,
                apellido=j_apellido,
                dni=j_dni,
                sexo=j_sexo
            )
            jugador.save()
            
                   
           
            messages.success(request, "Jugador creado exitosamente.")
            return redirect('guardar_jugador')  # Redirige al menú de administración después de guardar

        except Exception as e:
            messages.error(request, f"Error al crear jugador: {e}")
            return render(request, "admin_carga_jugador.html", {"categorias": categorias})

    return render(request, "admin_carga_jugador.html", {"categorias": categorias})

def guardar_jugador(request):
    return render(request, "guardar_jugador.html")


def modificar_jugador(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)
    
    if request.method == "POST":
        jugador.nombre = request.POST.get("nombre")
        jugador.apellido = request.POST.get("apellido")
        jugador.sexo = request.POST.get("sexo")
        # Guarda los cambios en la base de datos
        jugador.save()
        return redirect('listado_jugadores')  # Redirige a la lista de jugadores después de modificar

    # Si no es un POST, no necesitas devolver nada en este caso
    return redirect('listado_jugadores')  # Asegúrate de redirigir si la solicitud no es POST




def datos_jugador(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)
    return render(request, 'datos_jugador.html', {'jugador': jugador})

def busqueda_jugador(request):
    nombre = request.GET.get('nombre', '')
    apellido = request.GET.get('apellido', '')
    accion = request.GET.get('accion', '')

    if accion == 'ver' and apellido:
        try:
            jugador = Jugador.objects.get(apellido=apellido)
            return redirect('datos_jugador', dni=jugador.dni)  # Cambiado a dni
        except Jugador.DoesNotExist:
            return render(request, 'listado_jugadores.html', {'error': 'Jugador no encontrado.'})

    jugadores = Jugador.objects.all()
    if nombre:
        jugadores = jugadores.filter(nombre__icontains=nombre)
    if apellido:
        jugadores = jugadores.filter(apellido__icontains=apellido)

    jugadores = jugadores.order_by('apellido', 'nombre')

    return render(request, 'listado_jugadores.html', {'jugadores': jugadores})

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

def borrar_jugador(request, dni):
    try:
        jugador = get_object_or_404(Jugador, dni=dni)
        jugador.delete()
        messages.success(request, f"Se ha eliminado  '{jugador.nombre}' exitosamente")
        return redirect('borrado_exitoso', jugador_dni=dni)

    except Jugador.DoesNotExist:
        messages.error(request, f"error al eliminar el jugador, no existe")
        return redirect(reverse('listado_jugadores'))
    
def borrado_exitoso(request, jugador_dni):
    return render(request, 'borrado_exitoso.html', {'jugador_dni': jugador_dni})


def listado_jugadores(request):
    search = request.GET.get('search', '')
    sexo_filter = request.GET.get('sexo', '')


    # Filtrar jugadores por nombre o apellido
    jugadores = Jugador.objects.all()
    if search:
        jugadores = jugadores.filter(nombre__icontains=search) | jugadores.filter(apellido__icontains=search)

    # Filtrar por sexo
    if sexo_filter:
        jugadores = jugadores.filter(sexo=sexo_filter)

    # Paginación
    paginator = Paginator(jugadores, 20)  # Muestra 20 jugadores por página
    page_number = request.GET.get('page')
    page_obj = paginator.get_page(page_number)

    return render(request, 'listado_jugadores.html', {'jugadores': page_obj, 'search': search, 'sexo': sexo_filter})