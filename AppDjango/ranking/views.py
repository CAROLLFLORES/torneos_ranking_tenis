from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from django.db.models.signals import post_save
from django.dispatch import receiver
from torneo.models import ResultadoPartido
from ranking.models import Ranking, Torneo, Jugador
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, F
from torneo.models import TorneoJugador
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib import messages




def ranking_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    ranking = Ranking.objects.filter(torneo=torneo).annotate(
        games=F('pg') - (F('pj') - F('pg'))  # Games ganados - Games perdidos
    ).order_by('-puntaje_total_categoria')  # Ordenar por puntaje

    return render(request, 'ranking.html', {'torneo': torneo, 'ranking': ranking})



def ver_ranking(request, torneo_id):
    torneo_actual = get_object_or_404(Torneo, id=torneo_id)
    torneos_en_curso = Torneo.objects.all()  # 🔥 Mostrar todos los torneos disponibles

    ranking = Ranking.objects.filter(
    torneo=torneo_actual,
    activo=True  # 👈 Solo jugadores visibles
    ).select_related('jugador').order_by(
        '-puntaje_total_categoria', '-games'
    )


    return render(request, 'ranking.html', {
        'torneo_actual': torneo_actual,  # ✅ Asegura que este contexto esté en la plantilla
        'torneos_en_curso': torneos_en_curso,
        'ranking': ranking
    })



@receiver(post_save, sender=ResultadoPartido)
def actualizar_ranking(sender, instance, **kwargs):
    partido = instance.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()
    ganador = instance.ganador_jugador

    if not ganador:
        print(f"⚠ No hay ganador en el resultado del partido {partido.id}")
        return

    perdedor = partido.jugador1 if partido.jugador1 != ganador else partido.jugador2

    if not perdedor:
        print(f"⚠ No se identificó al perdedor del partido {partido.id}")
        return

    # ✅ ESTO VA FUERA del if
    sets_j1 = int(instance.set1_jugador1 > instance.set1_jugador2) + \
              int(instance.set2_jugador1 > instance.set2_jugador2) + \
              int(instance.set3_jugador1 > instance.set3_jugador2)

    sets_j2 = int(instance.set1_jugador2 > instance.set1_jugador1) + \
              int(instance.set2_jugador2 > instance.set2_jugador1) + \
              int(instance.set3_jugador2 > instance.set3_jugador1)

    games_j1 = instance.set1_jugador1 + instance.set2_jugador1
    games_j2 = instance.set1_jugador2 + instance.set2_jugador2

    if ganador == partido.jugador2:
        sets_ganador, sets_perdedor = sets_j2, sets_j1
        games_ganador, games_perdedor = games_j2, games_j1
    else:
        sets_ganador, sets_perdedor = sets_j1, sets_j2
        games_ganador, games_perdedor = games_j1, games_j2

    ranking_ganador, _ = Ranking.objects.get_or_create(
        jugador=ganador, torneo=torneo, categoria=categoria,
        defaults={"pj": 0, "pg": 0, "pp": 0, "sets": 0, "games": 0, "puntaje_total_categoria": 0}
    )
    ranking_ganador.pj += 1
    ranking_ganador.pg += 1
    ranking_ganador.sets += (sets_ganador - sets_perdedor)
    ranking_ganador.games += (games_ganador - games_perdedor)
    ranking_ganador.puntaje_total_categoria += 100
    ranking_ganador.save()

    ranking_perdedor, _ = Ranking.objects.get_or_create(
        jugador=perdedor, torneo=torneo, categoria=categoria,
        defaults={"pj": 0, "pg": 0, "pp": 0, "sets": 0, "games": 0, "puntaje_total_categoria": 0}
    )
    ranking_perdedor.pj += 1
    ranking_perdedor.pp += 1
    ranking_perdedor.sets += (sets_perdedor - sets_ganador)
    ranking_perdedor.games += (games_perdedor - games_ganador)
    ranking_perdedor.puntaje_total_categoria -= 50
    ranking_perdedor.save()

    print(f"✅ Ranking actualizado: {ganador.nombre} (sets: +{sets_ganador - sets_perdedor}, games: +{games_ganador - games_perdedor})")

def ranking_general(request):
    torneos = Torneo.objects.all()  # 🔹 Obtener todos los torneos
    return render(request, 'ranking_general.html', {'torneos': torneos})


def ascender_jugadores(jugadores_dni, torneo_origen_id, torneo_destino_id):
    torneo_origen = Torneo.objects.get(id=torneo_origen_id)
    torneo_destino = Torneo.objects.get(id=torneo_destino_id)

    with transaction.atomic():
        for jugador_dni in jugadores_dni:
            jugador = Jugador.objects.get(dni=jugador_dni)  # ✅ CAMBIO CLAVE

            ranking_origen = Ranking.objects.filter(torneo=torneo_origen, jugador=jugador).first()
            if not ranking_origen:
                continue

            ranking_origen.activo = False
            ranking_origen.save()

            ranking_destino = Ranking.objects.filter(
                torneo=torneo_destino, jugador=jugador
            ).first()

            if ranking_destino:
                ranking_destino.activo = True
                ranking_destino.save()
                print(f"✅ Activado nuevamente en torneo {torneo_destino.nombre} → jugador {jugador.nombre}")



            else:
                Ranking.objects.create(
                    torneo=torneo_destino,
                    jugador=jugador,
                    categoria=ranking_origen.categoria,
                    anio=ranking_origen.anio,
                    bimestre=ranking_origen.bimestre,
                    pj=0, pg=0, pp=0, games=0, sets=0,
                    puntaje_total_categoria=0,
                    puntaje_acumulador=0,
                    activo=True
                )

            TorneoJugador.objects.get_or_create(torneo=torneo_destino, jugador=jugador)

            
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

        return redirect('abm_torneo')  # o donde quieras redirigir

    return redirect('abm_torneo')  # por si entran por GET
     
@csrf_exempt       
def confirmar_ascenso_final(request):
    if request.method == 'POST':
        jugadores_ids = json.loads(request.POST.get('jugadores_json', '[]'))
        torneo_destino_id = request.POST.get('torneo_destino')
        torneo_origen_id = request.POST.get('torneo_origen')

        if jugadores_ids and torneo_destino_id and torneo_origen_id:
            ascender_jugadores(jugadores_ids, torneo_origen_id, torneo_destino_id)
            return redirect('abm_torneo')  # ✅ Redirige al menú de torneos

        return redirect('admin_menu')  # fallback por si algo falla

    return redirect('admin_menu')
