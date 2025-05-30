from django.shortcuts import render, get_object_or_404, redirect

# Create your views here.
from django.db.models.signals import post_save
from django.dispatch import receiver
from torneo.models import ResultadoPartido, MasterJugador, Equipo
from ranking.models import Ranking, Torneo, Jugador, RankingEquipo
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import Sum, F
from torneo.models import TorneoJugador, MasterJugador
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json
from django.contrib import messages
from django.http import HttpResponseBadRequest





def ranking_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    ranking = Ranking.objects.filter(torneo=torneo).annotate(
        games=F('pg') - (F('pj') - F('pg'))  # Games ganados - Games perdidos
    ).order_by('-puntaje_total_categoria')  # Ordenar por puntaje

    return render(request, 'ranking.html', {'torneo': torneo, 'ranking': ranking})


def ver_ranking(request, torneo_id):
    torneo_actual = get_object_or_404(Torneo, id=torneo_id)
    #esta parte se anulo, ya que lo de abajo lo que hace es agrupar por mismo estilo de torneo
    #torneos_en_curso = Torneo.objects.all()
    torneos_en_curso = Torneo.objects.filter(
        tipo_juego=torneo_actual.tipo_juego,
        categorias__in=torneo_actual.categorias.all()
    ).exclude(id=torneo_actual.id).distinct()


    if torneo_actual.tipo_juego == "Doble":

        ranking = RankingEquipo.objects.filter(
            torneo=torneo_actual,
            activo=True
        ).select_related('equipo__jugador1', 'equipo__jugador2').order_by(
            '-puntaje_total_categoria'
        )
    else:
        ranking = Ranking.objects.filter(
            torneo=torneo_actual,
            activo=True
        ).select_related('jugador').order_by(
            '-puntaje_total_categoria', '-games'
        )

    master_creado = MasterJugador.objects.filter(torneo=torneo_actual).exists()
    master_cantidad = MasterJugador.objects.filter(torneo=torneo_actual).count()

    return render(request, 'ranking.html', {
        'torneo_actual': torneo_actual,
        'torneos_en_curso': torneos_en_curso,
        'ranking': ranking,
        'master_creado': master_creado,
        'master_cantidad': master_cantidad
    })





def actualizar_ranking(sender, instance, **kwargs):
    from ranking.models import Ranking  # por si no está arriba

    partido = instance.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()
    
    jugador1 = partido.jugador1
    jugador2 = partido.jugador2

    # Obtengo ranking de ambos jugadores
    ranking_j1, _ = Ranking.objects.get_or_create(jugador=jugador1, torneo=torneo, categoria=categoria)
    ranking_j2, _ = Ranking.objects.get_or_create(jugador=jugador2, torneo=torneo, categoria=categoria)

    # 🔄 Revertir resultado anterior si existe
    try:
        resultado_anterior = ResultadoPartido.objects.get(partido=partido)
        if resultado_anterior and resultado_anterior.id == instance.id and resultado_anterior.ganador_jugador:
            ganador_ant = resultado_anterior.ganador_jugador
            perdedor_ant = jugador2 if ganador_ant == jugador1 else jugador1

            sets_ganados_ant = sum([
                resultado_anterior.set1_jugador1 > resultado_anterior.set1_jugador2,
                resultado_anterior.set2_jugador1 > resultado_anterior.set2_jugador2,
                resultado_anterior.set3_jugador1 > resultado_anterior.set3_jugador2,
            ])
            sets_perdidos_ant = 3 - sets_ganados_ant

            games_j1_ant = resultado_anterior.set1_jugador1 + resultado_anterior.set2_jugador1
            games_j2_ant = resultado_anterior.set1_jugador2 + resultado_anterior.set2_jugador2

            # El set 3 no suma en games
            if resultado_anterior.set3_jugador1 > 0 or resultado_anterior.set3_jugador2 > 0:
                pass  # No sumar games del set 3

            # Ranking del ganador anterior
            ranking_ganador_ant = Ranking.objects.get(jugador=ganador_ant, torneo=torneo)
            ranking_perdedor_ant = Ranking.objects.get(jugador=perdedor_ant, torneo=torneo)

            # Revertir cambios
            ranking_ganador_ant.pg -= 1
            ranking_ganador_ant.sets -= (sets_ganados_ant - sets_perdidos_ant)
            ranking_ganador_ant.games -= (games_j1_ant - games_j2_ant)
            ranking_ganador_ant.puntaje_total_categoria -= 100
            ranking_ganador_ant.save()

            ranking_perdedor_ant.pp -= 1
            ranking_perdedor_ant.sets -= (sets_perdidos_ant - sets_ganados_ant)
            ranking_perdedor_ant.games -= (games_j2_ant - games_j1_ant)
            ranking_perdedor_ant.puntaje_total_categoria += 50
            ranking_perdedor_ant.save()
    except ResultadoPartido.DoesNotExist:
        pass

    # ✅ Calcular nuevo resultado
    ganador = instance.ganador_jugador
    perdedor = jugador2 if ganador == jugador1 else jugador1

    sets_j1 = sum([
        instance.set1_jugador1 > instance.set1_jugador2,
        instance.set2_jugador1 > instance.set2_jugador2,
        instance.set3_jugador1 > instance.set3_jugador2,
    ])
    sets_j2 = 3 - sets_j1

    games_j1 = instance.set1_jugador1 + instance.set2_jugador1
    games_j2 = instance.set1_jugador2 + instance.set2_jugador2
    # No sumar set 3 en games
    # if instance.set3_jugador1 > 0 or instance.set3_jugador2 > 0:
    #     (no se suman los games del set 3)

    if ganador == jugador2:
        sets_ganador, sets_perdedor = sets_j2, sets_j1
        games_ganador, games_perdedor = games_j2, games_j1
        ranking_ganador = ranking_j2
        ranking_perdedor = ranking_j1
    else:
        sets_ganador, sets_perdedor = sets_j1, sets_j2
        games_ganador, games_perdedor = games_j1, games_j2
        ranking_ganador = ranking_j1
        ranking_perdedor = ranking_j2

    # ✅ Aplicar nuevo resultado
    ranking_ganador.pg += 1
    ranking_ganador.sets += sets_ganador
    ranking_ganador.games += (games_ganador - games_perdedor)
    ranking_ganador.puntaje_total_categoria += 100
    ranking_ganador.save()

    ranking_perdedor.pp += 1
    ranking_perdedor.sets += sets_perdedor
    ranking_perdedor.games += (games_perdedor - games_ganador)
    ranking_perdedor.puntaje_total_categoria -= 50
    ranking_perdedor.save()

    print(f"♻️ Ranking modificado - {ganador.nombre} ganó. Cambios aplicados correctamente.")


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
        jugadores_ids = json.loads(request.POST.get('jugadores_json') or request.POST.get('equipos_json') or '[]')
        torneo_destino_id = request.POST.get('torneo_destino')
        torneo_origen_id = request.POST.get('torneo_origen')

        torneo_origen = Torneo.objects.get(id=torneo_origen_id)

        if jugadores_ids and torneo_destino_id and torneo_origen_id:
            if torneo_origen.tipo_juego in ['Doble', 'Mixto']:
                ascender_equipos(jugadores_ids, torneo_origen_id, torneo_destino_id)
            else:
                ascender_jugadores(jugadores_ids, torneo_origen_id, torneo_destino_id)
            return redirect('abm_torneo')

    return redirect('abm_torneo')


from django.views.decorators.http import require_POST

@require_POST
def seleccionar_master(request):
    jugadores_ids = json.loads(request.POST.get('jugadores_json', '[]'))
    torneo_id = request.POST.get('torneo_origen')
    cantidad = len(jugadores_ids)

    if not jugadores_ids or not torneo_id:
        messages.error(request, "Debes seleccionar jugadores y un torneo.")
        return redirect('ver_ranking', torneo_id=torneo_id)

    torneo = get_object_or_404(Torneo, id=torneo_id)

    MasterJugador.objects.filter(torneo=torneo).delete()

    for pos, dni in enumerate(jugadores_ids, start=1):
        jugador = get_object_or_404(Jugador, dni=dni)
        ranking = Ranking.objects.filter(torneo=torneo, jugador=jugador).first()
        if ranking:
            MasterJugador.objects.create(
                torneo=torneo,
                jugador=jugador,
                categoria=ranking.categoria,
                posicion=pos
            )

    seleccionados = MasterJugador.objects.filter(torneo=torneo).select_related('jugador')

    return render(request, 'master_torneos.html', {
        'torneo': torneo,
        'seleccionados': seleccionados,
        'cantidad': cantidad
    })


def master_torneos(request, torneo_id, cantidad):
    torneo = get_object_or_404(Torneo, id=torneo_id)
    cantidad = int(cantidad)

    rankings = Ranking.objects.filter(torneo=torneo).order_by('-puntaje_total_categoria')[:cantidad]

    MasterJugador.objects.filter(torneo=torneo).delete()

    for idx, ranking in enumerate(rankings, start=1):
        MasterJugador.objects.create(
            torneo=torneo,
            jugador=ranking.jugador,
            categoria=ranking.categoria,
            posicion=idx
        )

    seleccionados = MasterJugador.objects.filter(torneo=torneo).select_related('jugador')

    return render(request, 'master_torneos.html', {
        'torneo': torneo,
        'seleccionados': seleccionados,
        'cantidad': cantidad
    })

def listado_masters(request):
    from torneo.models import MasterJugador, Torneo

    # Trae solo torneos que tengan al menos un MasterJugador
    torneos = Torneo.objects.filter(masterjugador__isnull=False).distinct()

    return render(request, 'listado_masters.html', {
        'torneos': torneos
    })



def ascender_equipos(equipos_ids, torneo_origen_id, torneo_destino_id):
    torneo_origen = Torneo.objects.get(id=torneo_origen_id)
    torneo_destino = Torneo.objects.get(id=torneo_destino_id)

    with transaction.atomic():
        for equipo_id in equipos_ids:
            equipo = Equipo.objects.get(id=equipo_id)

            ranking_origen = RankingEquipo.objects.filter(torneo=torneo_origen, equipo=equipo).first()
            if ranking_origen:
                ranking_origen.activo = False
                ranking_origen.save()

            ranking_destino, creado = RankingEquipo.objects.get_or_create(
                torneo=torneo_destino,
                equipo=equipo,
                defaults={
                    'categoria': ranking_origen.categoria,
                    'anio': ranking_origen.anio,
                    'bimestre': ranking_origen.bimestre,
                    'pj': 0, 'pg': 0, 'pp': 0, 'games': 0, 'sets': 0,
                    'puntaje_total_categoria': 0,
                    'puntaje_acumulador': 0,
                    'activo': True
                }
            )
            if not creado:
                ranking_destino.activo = True
                ranking_destino.save()



def actualizar_ranking_manual(resultado):
    partido = resultado.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()
    anio = torneo.fecha_inicio.year
    bimestre = 1  # ajustar según lógica

    jugador1 = partido.jugador1
    jugador2 = partido.jugador2
    ganador = resultado.ganador_jugador

    if not ganador:
        return

    perdedor = jugador2 if ganador == jugador1 else jugador1

    # Obtener o crear rankings
    ranking_j1, _ = Ranking.objects.get_or_create(
        jugador=jugador1, torneo=torneo, categoria=categoria,
        anio=anio, bimestre=bimestre,
        defaults={'pj': 0, 'pg': 0, 'pp': 0, 'sets': 0, 'games': 0,
                  'puntaje_total_categoria': 0, 'puntaje_acumulador': 0, 'activo': True}
    )
    ranking_j2, _ = Ranking.objects.get_or_create(
        jugador=jugador2, torneo=torneo, categoria=categoria,
        anio=anio, bimestre=bimestre,
        defaults={'pj': 0, 'pg': 0, 'pp': 0, 'sets': 0, 'games': 0,
                  'puntaje_total_categoria': 0, 'puntaje_acumulador': 0, 'activo': True}
    )

    # 🔁 REVERSIÓN SI YA HABÍA UN RESULTADO GUARDADO
    resultado_previo = ResultadoPartido.objects.filter(partido=partido).first()
    if resultado_previo and resultado_previo.id == resultado.id and resultado_previo.ganador_jugador:
        ganador_ant = resultado_previo.ganador_jugador
        perdedor_ant = jugador2 if ganador_ant == jugador1 else jugador1

        sets_ganados_ant = sum([
            resultado_previo.set1_jugador1 > resultado_previo.set1_jugador2,
            resultado_previo.set2_jugador1 > resultado_previo.set2_jugador2,
            resultado_previo.set3_jugador1 > resultado_previo.set3_jugador2,
        ])
        sets_perdidos_ant = 3 - sets_ganados_ant

        games_j1_ant = resultado_previo.set1_jugador1 + resultado_previo.set2_jugador1
        games_j2_ant = resultado_previo.set1_jugador2 + resultado_previo.set2_jugador2

        if resultado_previo.set3_jugador1 > 0 or resultado_previo.set3_jugador2 > 0:
            pass  # set 3 no suma en games

        ranking_ganador_ant = Ranking.objects.get(jugador=ganador_ant, torneo=torneo)
        ranking_perdedor_ant = Ranking.objects.get(jugador=perdedor_ant, torneo=torneo)

        ranking_ganador_ant.pj -= 1
        ranking_ganador_ant.pg -= 1
        ranking_ganador_ant.sets -= (sets_ganados_ant - sets_perdidos_ant)
        ranking_ganador_ant.games -= (games_j1_ant - games_j2_ant)
        ranking_ganador_ant.puntaje_total_categoria -= 100
        ranking_ganador_ant.save()

        ranking_perdedor_ant.pj -= 1
        ranking_perdedor_ant.pp -= 1
        ranking_perdedor_ant.sets -= (sets_perdidos_ant - sets_ganados_ant)
        ranking_perdedor_ant.games -= (games_j2_ant - games_j1_ant)
        ranking_perdedor_ant.puntaje_total_categoria += 50
        ranking_perdedor_ant.save()

    # ✅ APLICAR NUEVO RESULTADO
    sets_j1 = sum([
        resultado.set1_jugador1 > resultado.set1_jugador2,
        resultado.set2_jugador1 > resultado.set2_jugador2,
        resultado.set3_jugador1 > resultado.set3_jugador2,
    ])
    sets_j2 = 3 - sets_j1

    games_j1 = resultado.set1_jugador1 + resultado.set2_jugador1
    games_j2 = resultado.set1_jugador2 + resultado.set2_jugador2

    # Incrementar valores correctamente
    ranking_j1.pj += 1
    ranking_j2.pj += 1

    if ganador == jugador1:
        ranking_j1.pg += 1
        ranking_j2.pp += 1
        ranking_j1.puntaje_total_categoria += 100
        ranking_j2.puntaje_total_categoria -= 50
    else:
        ranking_j2.pg += 1
        ranking_j1.pp += 1
        ranking_j2.puntaje_total_categoria += 100
        ranking_j1.puntaje_total_categoria -= 50

    ranking_j1.sets += sets_j1
    ranking_j2.sets += sets_j2
    ranking_j1.games += (games_j1 - games_j2)
    ranking_j2.games += (games_j2 - games_j1)

    ranking_j1.save()
    ranking_j2.save()



def actualizar_ranking_manual_equipos(resultado):
    partido = resultado.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()
    anio = torneo.fecha_inicio.year
    bimestre = 1  # Podés ajustar esto según tu lógica

    ganador = resultado.ganador_equipo
    if not ganador:
        return

    perdedor = partido.equipo2 if ganador == partido.equipo1 else partido.equipo1

    # Calcular sets ganados y perdidos
    sets_ganador = sum([
        resultado.set1_equipo1 > resultado.set1_equipo2,
        resultado.set2_equipo1 > resultado.set2_equipo2,
        resultado.set3_equipo1 > resultado.set3_equipo2,
    ]) if ganador == partido.equipo1 else sum([
        resultado.set1_equipo2 > resultado.set1_equipo1,
        resultado.set2_equipo2 > resultado.set2_equipo1,
        resultado.set3_equipo2 > resultado.set3_equipo1,
    ])
    sets_perdedor = 3 - sets_ganador

    games_ganador = (
        resultado.set1_equipo1 + resultado.set2_equipo1
        if ganador == partido.equipo1 else
        resultado.set1_equipo2 + resultado.set2_equipo2
    )
    games_perdedor = (
        resultado.set1_equipo2 + resultado.set2_equipo2
        if ganador == partido.equipo1 else
        resultado.set1_equipo1 + resultado.set2_equipo1
    )

    # Obtener o crear ranking
    ranking_ganador, _ = RankingEquipo.objects.get_or_create(
        torneo=torneo,
        equipo=ganador,
        categoria=categoria,
        anio=anio,
        bimestre=bimestre,
        defaults={
            'pj': 0, 'pg': 0, 'pp': 0, 'sets': 0, 'games': 0,
            'puntaje_total_categoria': 0, 'puntaje_acumulador': 0,
            'activo': True
        }
    )

    ranking_perdedor, _ = RankingEquipo.objects.get_or_create(
        torneo=torneo,
        equipo=perdedor,
        categoria=categoria,
        anio=anio,
        bimestre=bimestre,
        defaults={
            'pj': 0, 'pg': 0, 'pp': 0, 'sets': 0, 'games': 0,
            'puntaje_total_categoria': 0, 'puntaje_acumulador': 0,
            'activo': True
        }
    )

    # Aplicar cambios
    ranking_ganador.pj += 1
    ranking_ganador.pg += 1
    ranking_ganador.sets += (sets_ganador - sets_perdedor)
    ranking_ganador.games += (games_ganador - games_perdedor)
    ranking_ganador.puntaje_total_categoria += 100

    ranking_perdedor.pj += 1
    ranking_perdedor.pp += 1
    ranking_perdedor.sets += (sets_perdedor - sets_ganador)
    ranking_perdedor.games += (games_perdedor - games_ganador)
    ranking_perdedor.puntaje_total_categoria -= 50

    ranking_ganador.save()
    ranking_perdedor.save()


def revertir_ranking_single(resultado_anterior):
    partido = resultado_anterior.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()
    jugador1 = partido.jugador1
    jugador2 = partido.jugador2

    ganador = resultado_anterior.ganador_jugador
    if not ganador:
        return  # No se había guardado un ganador

    perdedor = jugador2 if ganador == jugador1 else jugador1

    sets_ganador = sum([
        resultado_anterior.set1_jugador1 > resultado_anterior.set1_jugador2,
        resultado_anterior.set2_jugador1 > resultado_anterior.set2_jugador2,
        resultado_anterior.set3_jugador1 > resultado_anterior.set3_jugador2,
    ]) if ganador == jugador1 else sum([
        resultado_anterior.set1_jugador2 > resultado_anterior.set1_jugador1,
        resultado_anterior.set2_jugador2 > resultado_anterior.set2_jugador1,
        resultado_anterior.set3_jugador2 > resultado_anterior.set3_jugador1,
    ])
    sets_perdedor = 3 - sets_ganador

    games_ganador = (
        resultado_anterior.set1_jugador1 + resultado_anterior.set2_jugador1
        if ganador == jugador1 else
        resultado_anterior.set1_jugador2 + resultado_anterior.set2_jugador2
    )
    games_perdedor = (
        resultado_anterior.set1_jugador2 + resultado_anterior.set2_jugador2
        if ganador == jugador1 else
        resultado_anterior.set1_jugador1 + resultado_anterior.set2_jugador1
    )

    ranking_ganador = Ranking.objects.get(jugador=ganador, torneo=torneo, categoria=categoria)
    ranking_perdedor = Ranking.objects.get(jugador=perdedor, torneo=torneo, categoria=categoria)

    ranking_ganador.pg -= 1
    ranking_ganador.sets -= (sets_ganador)
    ranking_ganador.games -= (games_ganador - games_perdedor)
    ranking_ganador.puntaje_total_categoria -= 100
    ranking_ganador.pj -= 1

    ranking_perdedor.pp -= 1
    ranking_perdedor.sets -= (sets_perdedor)
    ranking_perdedor.games -= (games_perdedor - games_ganador)
    ranking_perdedor.puntaje_total_categoria += 50
    ranking_perdedor.pj -= 1

    ranking_ganador.save()
    ranking_perdedor.save()

def revertir_ranking_doble(resultado_anterior):
    partido = resultado_anterior.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()

    ganador = resultado_anterior.ganador_equipo
    if not ganador:
        return

    perdedor = partido.equipo2 if ganador == partido.equipo1 else partido.equipo1

    sets_ganador = sum([
        resultado_anterior.set1_equipo1 > resultado_anterior.set1_equipo2,
        resultado_anterior.set2_equipo1 > resultado_anterior.set2_equipo2,
        resultado_anterior.set3_equipo1 > resultado_anterior.set3_equipo2,
    ]) if ganador == partido.equipo1 else sum([
        resultado_anterior.set1_equipo2 > resultado_anterior.set1_equipo1,
        resultado_anterior.set2_equipo2 > resultado_anterior.set2_equipo1,
        resultado_anterior.set3_equipo2 > resultado_anterior.set3_equipo1,
    ])
    sets_perdedor = 3 - sets_ganador

    games_ganador = (
        resultado_anterior.set1_equipo1 + resultado_anterior.set2_equipo1
        if ganador == partido.equipo1 else
        resultado_anterior.set1_equipo2 + resultado_anterior.set2_equipo2
    )
    games_perdedor = (
        resultado_anterior.set1_equipo2 + resultado_anterior.set2_equipo2
        if ganador == partido.equipo1 else
        resultado_anterior.set1_equipo1 + resultado_anterior.set2_equipo1
    )

    ranking_ganador = RankingEquipo.objects.get(equipo=ganador, torneo=torneo, categoria=categoria)
    ranking_perdedor = RankingEquipo.objects.get(equipo=perdedor, torneo=torneo, categoria=categoria)

    ranking_ganador.pg -= 1
    ranking_ganador.sets -= (sets_ganador - sets_perdedor)
    ranking_ganador.games -= (games_ganador - games_perdedor)
    ranking_ganador.puntaje_total_categoria -= 100
    ranking_ganador.pj -= 1

    ranking_perdedor.pp -= 1
    ranking_perdedor.sets -= (sets_perdedor - sets_ganador)
    ranking_perdedor.games -= (games_perdedor - games_ganador)
    ranking_perdedor.puntaje_total_categoria += 50
    ranking_perdedor.pj -= 1

    ranking_ganador.save()
    ranking_perdedor.save()
