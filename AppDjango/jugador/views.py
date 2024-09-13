from django.shortcuts import render, redirect
from .models import Jugador, Categoria

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
    jugadores = Jugador.objects.all()
    return render(request, 'listado_jugadores.html', {'jugadores': jugadores})
