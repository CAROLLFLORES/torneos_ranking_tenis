from django.shortcuts import render, redirect , get_object_or_404
from .models import Jugador, Categoria

def datos_jugador(request):
    return render(request, "datos_jugador.html")

def CrearJugador(request):
    if request.method == "POST":
        j_nombre = request.POST.get("nombre")
        j_apellido = request.POST.get("apellido")
        j_dni = request.POST.get("dni")
        j_sexo = request.POST.get("sexo")
        #j_categoria = request.POST.get("categoria")

        try:
            jugador = Jugador(
                nombre=j_nombre,
                apellido=j_apellido,
                dni=j_dni,
                sexo=j_sexo
            )
            jugador.save()

            #if j_categoria:
               # categoria = Categoria.objects.get(id_categoria=j_categoria)
               # jugador.categorias.add(categoria)

            return redirect('guardar_jugador')  # Redirige al menú de administración después de guardar

        except Exception as e:
            print(f"Error al crear jugador: {e}")
            return render(request, "error_page.html", {"error": str(e)})

    return render(request, "admin_carga_jugador.html")


def guardar_jugador(request):
    return render(request, "guardar_jugador.html")


def listado_jugadores(request):
    nombre = request.GET.get('nombre', '')
    apellido = request.GET.get('apellido', '')
    
    # Filtrar los jugadores según los parámetros de búsqueda
    jugadores = Jugador.objects.all()
    if nombre:
        jugadores = jugadores.filter(nombre__icontains=nombre)
    if apellido:
        jugadores = jugadores.filter(apellido__icontains=apellido)
    
    jugadores = jugadores.order_by('apellido', 'nombre')  # Ordenar alfabéticamente
    
    return render(request, 'listado_jugadores.html', {'jugadores': jugadores})

# views.py

def datos_jugador(request, jugador_id):
    jugador = get_object_or_404(Jugador, id=jugador_id)
    return render(request, 'datos_jugador.html', {'jugador': jugador})


def busqueda_jugador(request):
    nombre = request.GET.get('nombre', '')
    apellido = request.GET.get('apellido', '')
    accion = request.GET.get('accion', '')

    if accion == 'ver' and apellido:
        try:
            jugador = Jugador.objects.get(apellido=apellido)
            return redirect('datos_jugador', jugador_id=jugador.id)
        except Jugador.DoesNotExist:
            return render(request, 'listado_jugadores.html', {'error': 'Jugador no encontrado.'})
    
    jugadores = Jugador.objects.all()
    if nombre:
        jugadores = jugadores.filter(nombre__icontains=nombre)
    if apellido:
        jugadores = jugadores.filter(apellido__icontains=apellido)
    
    jugadores = jugadores.order_by('apellido', 'nombre')
    
    return render(request, 'listado_jugadores.html', {'jugadores': jugadores})

def datos_jugador(request, jugador_id):
    jugador = get_object_or_404(Jugador, id=jugador_id)
    return render(request, 'datos_jugador.html', {'jugador': jugador})