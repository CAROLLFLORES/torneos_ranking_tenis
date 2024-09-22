from django.shortcuts import render, redirect , get_object_or_404
from .models import Jugador, Categoria

def jugador_detalle(request, jugador_id):
    jugador = get_object_or_404(Jugador, id=jugador_id)
    return render(request, 'datos_jugador.html', {'jugador': jugador})


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
    
    jugadores = jugadores.order_by('apellido')  # Ordenar alfabéticamente
    
    return render(request, 'listado_jugadores.html', {'jugadores': jugadores})

# views.py

def datos_jugador(request, dni):
    jugador = get_object_or_404(Jugador, dni=dni)  # Corregido el parámetro
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


#Begin - 22/09/2024 -Franco Corbalan 'Agrego Funcionalidad de categoria'
def abm_categoria(request):
    if request.method == "POST":
        c_nivel = request.POST.get("nivel")
        c_edad = request.POST.get("edad")
        c_tipo_juego = request.POST.get("tipo_juego")
        
        try:
            categoria_existente= Categoria.objects.filter(nivel=c_nivel, edad=c_edad, tipo_juego=c_tipo_juego).exists()
            
            if categoria_existente:
                return render(request, "error_page.html", {"error": "La categoría ya existe."})
            else:
                categoria = Categoria(nivel=c_nivel, 
                                        edad=c_edad, 
                                        tipo_juego=c_tipo_juego)
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
#End - 22/09/2024 -Franco Corbalan 'Agrego Funcionalidad de categoria'

def borrar_jugador(request, jugador_dni):
    jugador = get_object_or_404(Jugador, dni=jugador_dni)
    jugador.delete()  # Eliminar el jugador
    return redirect('borrado_exitoso', jugador_dni=jugador_dni)  # Asegúrate de que este parámetro sea el correcto


def borrado_exitoso(request, jugador_dni):
    return render(request, 'borrado_exitoso.html', {'jugador_dni': jugador_dni})
