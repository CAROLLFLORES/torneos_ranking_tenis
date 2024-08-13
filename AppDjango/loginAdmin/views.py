from django.shortcuts import render

# Create your views here.
# MVC = modelo vista controlador  -> hay acciones (metodos)
# MVT = modelo vista template -> hay acciones (metodos)

from django.http import HttpResponse

def admin_login(request):
    return render(request, 'admin_login.html')

def index(request):
    return HttpResponse("probando")

def admin_menu(request):
    return render(request, "admin_menu.html")

def admin_carga_jugador(request):
    return render(request, "admin_carga_jugador.html")

def admin_datos_jugador(request):
    return render(request, "admin_datos_jugador.html")
"""
#solo hice esta parte para crear la funcion de alta jugador falta relacionarlo a la bdd y dar alta en models
def alta_jugador(request, nombre, apellido, edad, genero, categoria, dni):
    jugador = Jugador{
        nombre= nombre,
        apellido= apellido,
        #etc
    }
    jugador.save()
    
    return HttpResponse("alta jugador ok")
    
se hace uno para salvar los datos

def save_jugador(request):
    if request.method=="GET":
        nombre =request.GET ["nombre"]
        apellido=request.GET["apellido"]

        jugador = Jugador{
        nombre= nombre,
        apellido= apellido,
        #etc
    }
        jugador.save()
        return HttpResponse("alta jugador ok")
    
    else:
        return 
         return HttpResponse("no se ha podido cargar jugador")
         
         
     para sacar un dato de la bdd
    def dato(request):
        dato = Jugador.objects.get(parametro)
    
    return HttpResponse("mostrar jugador ok")
    
    
    modificar
    def editar_jugador(request, apellido):
        jugador =Jugador.objects.get(parametro)
        jugador.nombre = parametro
        etc
        
        jugador.save()
        return HttpResponse("editado jugador ok")
    
    
    mostrar listado de todos los objetos de una tabla
    def jugador(request):
        jugador=Jugador.objects.all() o order.by("nobmre")
        
        return render(request, "nombre.html"), (
            "jugador": jugador
        ))
        
borrar 
def borrar_jugador(request, nombre):
    jugador=Jugador.objects.get(nombre)
    jugador.delete()
    
    return redirect("nombre de la pagina que redirijo luego de borrar")
    
    filtros tambien tengo 
    jugador.objects.filter(nombre="ejemplo")
    
    """