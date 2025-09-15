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
from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.admin.views.decorators import staff_member_required
from django.contrib import messages
from .models import Torneo

# ---- Helpers simples para ascensos/descensos por torneo (archivo JSON) ----
import os, json
from django.conf import settings

FILE_PATH = os.path.join(settings.BASE_DIR, 'ascensos_descensos.json')

def _read_movs():
    if not os.path.exists(FILE_PATH):
        return {"ascensos": {}, "descensos": {}}
    with open(FILE_PATH, 'r', encoding='utf-8') as f:
        return json.load(f)

def _write_movs(data):
    with open(FILE_PATH, 'w', encoding='utf-8') as f:
        json.dump(data, f, indent=2, ensure_ascii=False)

def get_ascensos(torneo_id, default=0):
    data = _read_movs()
    return int(data.get("ascensos", {}).get(str(torneo_id), default))

def set_ascensos(torneo_id, value):
    data = _read_movs()
    data.setdefault("ascensos", {})[str(torneo_id)] = int(value)
    _write_movs(data)

def get_descensos(torneo_id, default=0):
    data = _read_movs()
    return int(data.get("descensos", {}).get(str(torneo_id), default))

def set_descensos(torneo_id, value):
    data = _read_movs()
    data.setdefault("descensos", {})[str(torneo_id)] = int(value)
    _write_movs(data)
# ---------------------------------------------------------------------------



def contar_sets_ganados(set1_a, set1_b, set2_a, set2_b, set3_a, set3_b):
    sets_ganados = 0
    if set1_a != 0 or set1_b != 0:
        if set1_a > set1_b:
            sets_ganados += 1
    if set2_a != 0 or set2_b != 0:
        if set2_a > set2_b:
            sets_ganados += 1
    if set3_a != 0 or set3_b != 0:
        if set3_a > set3_b:
            sets_ganados += 1
    return sets_ganados

# no se usa más 12/8
def ranking_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    ranking = Ranking.objects.filter(torneo=torneo).annotate(
        games=F('pg') - (F('pj') - F('pg'))  # Games ganados - Games perdidos
    ).order_by('-puntaje_total_categoria')  # Ordenar por puntaje

    return render(request, 'ranking.html', {'torneo': torneo, 'ranking': ranking})

def ver_ranking(request, torneo_id):
    # Obtener torneo actual
    if torneo_id == 0:
        torneo_actual = Torneo.objects.first()
    else:
        torneo_actual = get_object_or_404(Torneo, id=torneo_id)

    # Valores (sin tocar BD)
    ascensos_val  = get_ascensos(torneo_actual.id, default=0) if torneo_actual else 0
    descensos_val = get_descensos(torneo_actual.id, default=0) if torneo_actual else 0

    # Calcular ranking (lista de diccionarios)
    ranking_list = calcular_ranking(torneo_actual.id, request.user) if torneo_actual else []

    # Separar jugadores activos y eliminados
    ranking_activos = []
    ranking_eliminados = []

    for j in ranking_list:
        # Determinar estado según tipo de torneo
        if torneo_actual.tipo_juego in ["Doble", "Mixto"]:
            estados = [j["equipo"].jugador1.estado, j["equipo"].jugador2.estado]
        else:
            estados = [j["jugador"].estado]

        if "DEL" in estados:
            ranking_eliminados.append(j)  # Jugador eliminado va al final
        else:
            ranking_activos.append(j)  # Jugadores activos/inactivos van arriba

    # Unir nuevamente, activos primero y eliminados al final
    ranking_ordenado = ranking_activos + ranking_eliminados

    # Obtener lista de torneos para el dropdown
    torneos = Torneo.objects.all().order_by("nombre")
    
    # 🔒 Ocultar “no visibles” según BD (sin tocar flujo de persistencia)
    if torneo_actual:
        if torneo_actual.tipo_juego in ("Doble", "Mixto"):
            invisibles = set(
                RankingEquipo.objects
                .filter(torneo=torneo_actual, activo=False)
                .values_list("equipo_id", flat=True)     # <- PK de Equipo
            )
            ranking_ordenado = [r for r in ranking_ordenado if (r.get("equipo") and r["equipo"].pk not in invisibles)]
        else:
            invisibles = set(
                Ranking.objects
                .filter(torneo=torneo_actual, activo=False)
                .values_list("jugador_id", flat=True)
            )
            ranking_ordenado = [r for r in ranking_ordenado if (r.get("jugador") and r["jugador"].pk not in invisibles)]


    torneos = Torneo.objects.all().order_by("nombre")

    torneos_destino = Torneo.objects.none()
    if torneo_actual:
        torneos_destino = (
            Torneo.objects
            .filter(
                tipo_juego=torneo_actual.tipo_juego, 
                tipo=torneo_actual.tipo,
            )
            .exclude(id=torneo_actual.id)
            .order_by('nombre')
        )

    # Renderizar template pasando ranking ya ordenado
    return render(request, "ranking.html", {
        "torneo_actual": torneo_actual,
        "ranking": ranking_ordenado,
        "torneos": torneos,
        "ascensos_val": ascensos_val,
        "descensos_val": descensos_val,
        "torneos_destino": torneos_destino,
    })


def calcular_ranking(torneo_id, user=None):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    # Participantes según tipo de torneo
    if torneo.tipo_juego in ["Doble", "Mixto"]:
        participantes = torneo.equipos.all()
    else:
        participantes = Jugador.objects.filter(jugador_torneos__torneo=torneo)

    # Inicializar estructura
    ranking_data = {}
    for p in participantes:
        ranking_data[p.pk] = {  # <-- usar pk en vez de id
            "equipo": p if torneo.tipo_juego in ["Doble", "Mixto"] else None,
            "jugador": p if torneo.tipo_juego not in ["Doble", "Mixto"] else None,
            "pj": 0,
            "pg": 0,
            "pp": 0,
            "sets": 0,
            "games": 0,
            "puntaje_total_categoria": 0,
        }

    def calcular_sets_ganados(resultado, es_doble):
        sets_ganados_equipo1 = 0
        sets_ganados_equipo2 = 0
        if not resultado:
            return 0, 0

        if es_doble:
            sets = [
                (resultado.set1_equipo1, resultado.set1_equipo2),
                (resultado.set2_equipo1, resultado.set2_equipo2),
                (resultado.set3_equipo1, resultado.set3_equipo2),
            ]
        else:
            sets = [
                (resultado.set1_jugador1, resultado.set1_jugador2),
                (resultado.set2_jugador1, resultado.set2_jugador2),
                (resultado.set3_jugador1, resultado.set3_jugador2),
            ]

        for s1, s2 in sets:
            if s1 is None or s2 is None:
                continue
            if s1 > s2:
                sets_ganados_equipo1 += 1
            elif s2 > s1:
                sets_ganados_equipo2 += 1

        return sets_ganados_equipo1, sets_ganados_equipo2

    def calcular_games_ganados(resultado, es_doble):
        """
        Devuelve (games_sum_first2_for_side1, games_sum_first2_for_side2)
        NOTA: NO incluye el tercer set en la suma; el ajuste +1/-1 se aplicará
        después en el bucle principal según la regla definida.
        """
        if not resultado:
            return 0, 0

        if es_doble:
            games1 = sum(v or 0 for v in [
                resultado.set1_equipo1,
                resultado.set2_equipo1,
            ])
            games2 = sum(v or 0 for v in [
                resultado.set1_equipo2,
                resultado.set2_equipo2,
            ])
        else:
            games1 = sum(v or 0 for v in [
                resultado.set1_jugador1,
                resultado.set2_jugador1,
            ])
            games2 = sum(v or 0 for v in [
                resultado.set1_jugador2,
                resultado.set2_jugador2,
            ])
        return games1, games2

    partidos = torneo.partido_set.all()
    es_doble = torneo.tipo_juego in ["Doble", "Mixto"]
     # Filtrar solo partidos que tengan ganador definido
    partidos_con_ganador = []
    for partido in partidos:
        resultado = getattr(partido, 'resultado', None)
        if not resultado:
            continue

        if es_doble:
            if getattr(resultado, "ganador_equipo", None) is not None:
                partidos_con_ganador.append(partido)
        else:
            if getattr(resultado, "ganador_jugador", None) is not None:
                partidos_con_ganador.append(partido)

    # Reemplazar la lista original de partidos por los filtrados
    partidos = partidos_con_ganador

    # Si no hay partidos con ganador, se retorna lista vacía
    if not partidos:
        return []

    for partido in partidos:
        resultado = getattr(partido, 'resultado', None)
        if not resultado:
            continue

        if es_doble:
            p1 = partido.equipo1
            p2 = partido.equipo2
        else:
            p1 = partido.jugador1
            p2 = partido.jugador2

        if p1 is None or p2 is None:
            continue

        # NUEVO: agregar participantes faltantes automáticamente
        for p in [p1, p2]:
            if p.pk not in ranking_data:
                ranking_data[p.pk] = {
                    "equipo": p if es_doble else None,
                    "jugador": p if not es_doble else None,
                    "pj": 0,
                    "pg": 0,
                    "pp": 0,
                    "sets": 0,
                    "games": 0,
                    "puntaje_total_categoria": 0,
                }
                print(f"[INFO] Nuevo participante detectado y agregado: {p} (pk={p.pk})")

        # Partidos jugados
        ranking_data[p1.pk]["pj"] += 1
        ranking_data[p2.pk]["pj"] += 1

        # Sets ganados (esta función ya cuenta correctamente los 3 sets)
        sets1, sets2 = calcular_sets_ganados(resultado, es_doble)
        ranking_data[p1.pk]["sets"] += (sets1 - sets2)
        ranking_data[p2.pk]["sets"] += (sets2 - sets1)

        # ----- GAMES: base (solo primeros 2 sets) -----
        games_base1, games_base2 = calcular_games_ganados(resultado, es_doble)
        base_diff = games_base1 - games_base2

        # Detectar si hubo tercer set
        if es_doble:
            set3_1 = resultado.set3_equipo1
            set3_2 = resultado.set3_equipo2
        else:
            set3_1 = resultado.set3_jugador1
            set3_2 = resultado.set3_jugador2

        third_played = (
            set3_1 is not None and set3_2 is not None
            and (set3_1 > 0 or set3_2 > 0)
        )

        # Bonus según regla: si hubo tercer set, +1 al ganador del partido, -1 al perdedor.
        bonus = 0
        if third_played:
            if sets1 > sets2:
                bonus = 1
            elif sets2 > sets1:
                bonus = -1
            # si empate improbable, bonus=0

        final_diff = base_diff + bonus

        # Aplicar diferencia final a ambos participantes (simétrico)
        ranking_data[p1.pk]["games"] += final_diff
        ranking_data[p2.pk]["games"] += -final_diff

        # Ganados, perdidos y puntaje (por sets)
        if sets1 > sets2:
            ranking_data[p1.pk]["pg"] += 1
            ranking_data[p2.pk]["pp"] += 1
            ranking_data[p1.pk]["puntaje_total_categoria"] += 100
            ranking_data[p2.pk]["puntaje_total_categoria"] -= 50
        else:
            ranking_data[p2.pk]["pg"] += 1
            ranking_data[p1.pk]["pp"] += 1
            ranking_data[p2.pk]["puntaje_total_categoria"] += 100
            ranking_data[p1.pk]["puntaje_total_categoria"] -= 50


    # Ordenar ranking por puntaje (los que no jugaron van al final)
    # ranking_list = sorted(
    #     ranking_data.values(),
    #     key=lambda x: (x["pj"] == 0, -x["puntaje_total_categoria"])
    # )
    ranking_list = sorted(
        ranking_data.values(),
        key=lambda x: (
            x["pj"] == 0,                       # los que no jugaron al final
            -x["puntaje_total_categoria"],      # 1) puntaje (desc)
            -x["pj"],                           # 2) partidos jugados (desc)
            -x["pg"],                           # 3) partidos ganados (desc)
            x["pp"],                            # 4) partidos perdidos (asc -> menos pérdidas mejor)
            -x["sets"],                         # 5) sets (desc)
            -x["games"]                         # 6) games (desc) <-- desempate final
        )
    )
    
    # Guarda en base de datos
    if user and user.is_authenticated and user.is_staff:
        guardar_ranking_en_modelos(torneo, ranking_list)

    return ranking_list

def guardar_ranking_en_modelos(torneo, ranking_list):
    categoria_default = torneo.torneo_categorias.first().categoria
    with transaction.atomic():
        for pos, data in enumerate(ranking_list, start=1):
            if torneo.tipo_juego in ["Doble", "Mixto"]:
                RankingEquipo.objects.update_or_create(
                    torneo=torneo,
                    equipo=data["equipo"],
                    defaults={
                        "posicion": pos,
                        "pj": data["pj"],
                        "pg": data["pg"],
                        "pp": data["pp"],
                        "sets": data["sets"],
                        "games": data["games"],
                        "puntaje_total_categoria": data["puntaje_total_categoria"],
                        "categoria": categoria_default,
                        "bimestre": 0,
                        "anio": 0,
                        #"activo": True,
                    }
                )
            else:
                Ranking.objects.update_or_create(
                    torneo=torneo,
                    jugador=data["jugador"],
                    defaults={
                        "posicion": pos,
                        "pj": data["pj"],
                        "pg": data["pg"],
                        "pp": data["pp"],
                        "sets": data["sets"],
                        "games": data["games"],
                        "puntaje_total_categoria": data["puntaje_total_categoria"],
                        "categoria": categoria_default,
                        "bimestre": 0,
                        "anio": 0,
                        #"activo": True,
                    }
                )


# def ver_ranking(request, torneo_id):
#     torneo_actual = get_object_or_404(Torneo, id=torneo_id)

#     if torneo_actual.tipo_juego == "Doble" or torneo_actual.tipo_juego == "Mixto":
        
#         # 👇 Este bloque asegura que todos los equipos tengan un ranking aunque no hayan jugado
#         for equipo in torneo_actual.equipos.all():
#             RankingEquipo.objects.get_or_create(
#                 equipo=equipo,
#                 torneo=torneo_actual,
#                 categoria=torneo_actual.categorias.first(),
#                 anio=torneo_actual.fecha_inicio.year,
#                 bimestre=1,
#                 defaults={
#                     'pj': 0, 'pg': 0, 'pp': 0, 'sets': 0, 'games': 0,
#                     'puntaje_total_categoria': 0, 'puntaje_acumulador': 0, 'activo': True
#                 }
#             )

#         ranking = RankingEquipo.objects.filter(
#             torneo=torneo_actual,
#             activo=True
#         ).select_related('equipo__jugador1', 'equipo__jugador2').order_by(
#             '-puntaje_total_categoria'
#         )

#     else:
#         ranking = Ranking.objects.filter(
#             torneo=torneo_actual,
#             activo=True
#         ).select_related('jugador').order_by(
#             '-puntaje_total_categoria', '-games'
#         )

#     master_creado = MasterJugador.objects.filter(torneo=torneo_actual).exists()
#     master_cantidad = MasterJugador.objects.filter(torneo=torneo_actual).count()

#     return render(request, 'ranking.html', {
#         'torneo_actual': torneo_actual,
#         'ranking': ranking,
#         'master_creado': master_creado,
#         'master_cantidad': master_cantidad
#     })

# no se usa más 12/8
def actualizar_ranking(sender, instance, **kwargs):
    from ranking.models import Ranking
    partido = instance.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()
    
    jugador1 = partido.jugador1
    jugador2 = partido.jugador2

    # Ranking de ambos jugadores
    ranking_j1, _ = Ranking.objects.get_or_create(jugador=jugador1, torneo=torneo, categoria=categoria)
    ranking_j2, _ = Ranking.objects.get_or_create(jugador=jugador2, torneo=torneo, categoria=categoria)

    # 🔄 Revertir resultado anterior si existe
    try:
        resultado_anterior = ResultadoPartido.objects.get(partido=partido)
        if resultado_anterior and resultado_anterior.id == instance.id and resultado_anterior.ganador_jugador:
            ganador_ant = resultado_anterior.ganador_jugador
            perdedor_ant = jugador2 if ganador_ant == jugador1 else jugador1

            sets_ganados_ant = contar_sets_ganados(
                resultado_anterior.set1_jugador1, resultado_anterior.set1_jugador2,
                resultado_anterior.set2_jugador1, resultado_anterior.set2_jugador2,
                resultado_anterior.set3_jugador1, resultado_anterior.set3_jugador2
            )
            sets_perdidos_ant = contar_sets_ganados(
                resultado_anterior.set1_jugador2, resultado_anterior.set1_jugador1,
                resultado_anterior.set2_jugador2, resultado_anterior.set2_jugador1,
                resultado_anterior.set3_jugador2, resultado_anterior.set3_jugador1
            )

            games_j1_ant = resultado_anterior.set1_jugador1 + resultado_anterior.set2_jugador1
            games_j2_ant = resultado_anterior.set1_jugador2 + resultado_anterior.set2_jugador2

            ranking_ganador_ant = Ranking.objects.get(jugador=ganador_ant, torneo=torneo)
            ranking_perdedor_ant = Ranking.objects.get(jugador=perdedor_ant, torneo=torneo)

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

    sets_j1 = contar_sets_ganados(
        instance.set1_jugador1, instance.set1_jugador2,
        instance.set2_jugador1, instance.set2_jugador2,
        instance.set3_jugador1, instance.set3_jugador2
    )
    sets_j2 = contar_sets_ganados(
        instance.set1_jugador2, instance.set1_jugador1,
        instance.set2_jugador2, instance.set2_jugador1,
        instance.set3_jugador2, instance.set3_jugador1
    )

    games_j1 = instance.set1_jugador1 + instance.set2_jugador1
    games_j2 = instance.set1_jugador2 + instance.set2_jugador2

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

    ranking_ganador.pg += 1
    ranking_ganador.sets += sets_ganador
    ranking_ganador.games += (games_ganador - games_perdedor)
    ranking_ganador.puntaje_total_categoria += 100
    ranking_ganador.save()

    ranking_perdedor.pp += 1
    ranking_perdedor.sets += (sets_perdedor - sets_ganador)
    ranking_perdedor.games += (games_perdedor - games_ganador)
    ranking_perdedor.puntaje_total_categoria -= 50
    ranking_perdedor.save()

    print(f"♻️ Ranking modificado - {ganador.nombre} ganó. Cambios aplicados correctamente.")


# no se usa mas!
def ranking_general(request, torneo_id=None):
    torneos = Torneo.objects.all()
    contexto = {'torneos': torneos}

    if torneo_id:
        torneo_actual = get_object_or_404(Torneo, id=torneo_id)

        # Decide qué modelo de ranking usar según el tipo de torneo
        if torneo_actual.tipo_juego in ("Doble", "Mixto"):
            # Asegura que aparezcan equipos sin partidos jugados
            for equipo in torneo_actual.equipos.all():
                RankingEquipo.objects.get_or_create(
                    equipo=equipo,
                    torneo=torneo_actual,
                    categoria=torneo_actual.categorias.first(),
                    anio=torneo_actual.fecha_inicio.year,
                    bimestre=1,
                    defaults={'pj':0,'pg':0,'pp':0,'sets':0,'games':0,
                              'puntaje_total_categoria':0,'puntaje_acumulador':0,'activo':True}
                )
            ranking = RankingEquipo.objects.filter(
                torneo=torneo_actual, activo=True
            ).order_by('-puntaje_total_categoria')
        else:
            ranking = Ranking.objects.filter(
                torneo=torneo_actual, activo=True
            ).order_by('-puntaje_total_categoria','-games')

        # Otros torneos para el modal de ascenso/descenso
        torneos_en_curso = Torneo.objects.filter(
            tipo_juego=torneo_actual.tipo_juego,
            categorias__in=torneo_actual.categorias.all()
        ).exclude(id=torneo_actual.id).distinct()

        contexto.update({
            'torneo_actual': torneo_actual,
            'ranking': ranking,
            'torneos_en_curso': torneos_en_curso
        })

    return render(request, 'ranking_general.html', contexto)


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
            return redirect('ver_ranking', torneo_id=torneo_origen.id)

    return redirect('ver_ranking', torneo_id=torneo_origen.id)

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

                # ✅ inscribir en el torneo destino para que se vea en el ranking
            if hasattr(torneo_destino, "equipos"):
                if not torneo_destino.equipos.filter(pk=equipo.pk).exists():
                    torneo_destino.equipos.add(equipo)

# no se usa más 12/8
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
       # 🔁 REVERSIÓN SI YA HABÍA UN RESULTADO GUARDADO DISTINTO
    try:
        resultado_previo = ResultadoPartido.objects.get(pk=resultado.pk)
        if resultado_previo.ganador_jugador and resultado_previo.ganador_jugador != ganador:
            ganador_ant = resultado_previo.ganador_jugador
            perdedor_ant = jugador2 if ganador_ant == jugador1 else jugador1

            sets_ganados_ant = contar_sets_ganados(
                resultado_previo.set1_jugador1, resultado_previo.set1_jugador2,
                resultado_previo.set2_jugador1, resultado_previo.set2_jugador2,
                resultado_previo.set3_jugador1, resultado_previo.set3_jugador2
            )
            sets_perdidos_ant = contar_sets_ganados(
                resultado_previo.set1_jugador2, resultado_previo.set1_jugador1,
                resultado_previo.set2_jugador2, resultado_previo.set2_jugador1,
                resultado_previo.set3_jugador2, resultado_previo.set3_jugador1
            )

            games_j1_ant = resultado_previo.set1_jugador1 + resultado_previo.set2_jugador1
            games_j2_ant = resultado_previo.set1_jugador2 + resultado_previo.set2_jugador2

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
    except ResultadoPartido.DoesNotExist:
        pass


    # ✅ APLICAR NUEVO RESULTADO
    sets_j1 = contar_sets_ganados(
        resultado.set1_jugador1, resultado.set1_jugador2,
        resultado.set2_jugador1, resultado.set2_jugador2,
        resultado.set3_jugador1, resultado.set3_jugador2
    )
    sets_j2 = contar_sets_ganados(
        resultado.set1_jugador2, resultado.set1_jugador1,
        resultado.set2_jugador2, resultado.set2_jugador1,
        resultado.set3_jugador2, resultado.set3_jugador1
    )

    games_j1 = resultado.set1_jugador1 + resultado.set2_jugador1
    games_j2 = resultado.set1_jugador2 + resultado.set2_jugador2

    # Incrementar valores correctamente
   # Solo sumar PJ si no había ganador previo (primer carga de resultado)
    # Determinar si es nuevo resultado o edición
    # ✅ Sumar PJ solo si no había otro resultado ya guardado para este partido
    es_nuevo = not ResultadoPartido.objects.filter(partido=partido).exclude(pk=resultado.pk).exists()

    if es_nuevo:
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

    # ✅ Games por diferencia (sin duplicar)
    ranking_j1.games += (games_j1 - games_j2)
    ranking_j2.games += (games_j2 - games_j1)

    if ganador == jugador1:
        ranking_j1.sets += sets_j1
        ranking_j2.sets += (sets_j2 - sets_j1)
    else:
        ranking_j2.sets += sets_j2
        ranking_j1.sets += (sets_j1 - sets_j2)

    ranking_j1.save()
    ranking_j2.save()

# no se usa más 12/8
def actualizar_ranking_manual_equipos(resultado):
    partido = resultado.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()
    anio = torneo.fecha_inicio.year
    bimestre = 1  # ajustar según lógica

    equipo1 = partido.equipo1
    equipo2 = partido.equipo2
    ganador = resultado.ganador_equipo

    if not ganador:
        return

    perdedor = equipo2 if ganador == equipo1 else equipo1

    # Obtener o crear rankings
    ranking_eq1, _ = RankingEquipo.objects.get_or_create(
        equipo=equipo1, torneo=torneo, categoria=categoria,
        anio=anio, bimestre=bimestre,
        defaults={'pj': 0, 'pg': 0, 'pp': 0, 'sets': 0, 'games': 0,
                  'puntaje_total_categoria': 0, 'puntaje_acumulador': 0, 'activo': True}
    )
    ranking_eq2, _ = RankingEquipo.objects.get_or_create(
        equipo=equipo2, torneo=torneo, categoria=categoria,
        anio=anio, bimestre=bimestre,
        defaults={'pj': 0, 'pg': 0, 'pp': 0, 'sets': 0, 'games': 0,
                  'puntaje_total_categoria': 0, 'puntaje_acumulador': 0, 'activo': True}
    )

    # Reversión solo si ya había ganador y fue distinto
    try:
        resultado_previo = ResultadoPartido.objects.get(pk=resultado.pk)
        if resultado_previo.ganador_equipo and resultado_previo.ganador_equipo != ganador:
            ganador_ant = resultado_previo.ganador_equipo
            perdedor_ant = equipo2 if ganador_ant == equipo1 else equipo1

            sets_ganados_ant = contar_sets_ganados(
                resultado_previo.set1_equipo1, resultado_previo.set1_equipo2,
                resultado_previo.set2_equipo1, resultado_previo.set2_equipo2,
                resultado_previo.set3_equipo1, resultado_previo.set3_equipo2
            )
            sets_perdidos_ant = contar_sets_ganados(
                resultado_previo.set1_equipo2, resultado_previo.set1_equipo1,
                resultado_previo.set2_equipo2, resultado_previo.set2_equipo1,
                resultado_previo.set3_equipo2, resultado_previo.set3_equipo1
            )

            games_eq1_ant = resultado_previo.set1_equipo1 + resultado_previo.set2_equipo1
            games_eq2_ant = resultado_previo.set1_equipo2 + resultado_previo.set2_equipo2

            ranking_ganador_ant = RankingEquipo.objects.get(equipo=ganador_ant, torneo=torneo)
            ranking_perdedor_ant = RankingEquipo.objects.get(equipo=perdedor_ant, torneo=torneo)

            ranking_ganador_ant.pj -= 1
            ranking_ganador_ant.pg -= 1
            ranking_ganador_ant.sets -= (sets_ganados_ant - sets_perdidos_ant)
            ranking_ganador_ant.games -= (games_eq1_ant - games_eq2_ant)
            ranking_ganador_ant.puntaje_total_categoria -= 100
            ranking_ganador_ant.save()

            ranking_perdedor_ant.pj -= 1
            ranking_perdedor_ant.pp -= 1
            ranking_perdedor_ant.sets -= (sets_perdidos_ant - sets_ganados_ant)
            ranking_perdedor_ant.games -= (games_eq2_ant - games_eq1_ant)
            ranking_perdedor_ant.puntaje_total_categoria += 50
            ranking_perdedor_ant.save()
    except ResultadoPartido.DoesNotExist:
        pass

    # Nuevo resultado actual
    sets_eq1 = contar_sets_ganados(
        resultado.set1_equipo1, resultado.set1_equipo2,
        resultado.set2_equipo1, resultado.set2_equipo2,
        resultado.set3_equipo1, resultado.set3_equipo2
    )
    sets_eq2 = contar_sets_ganados(
        resultado.set1_equipo2, resultado.set1_equipo1,
        resultado.set2_equipo2, resultado.set2_equipo1,
        resultado.set3_equipo2, resultado.set3_equipo1
    )

    games_eq1 = resultado.set1_equipo1 + resultado.set2_equipo1
    games_eq2 = resultado.set1_equipo2 + resultado.set2_equipo2

    # Solo sumar PJ si antes no había ganador
    es_nuevo = not ResultadoPartido.objects.filter(partido=partido).exclude(pk=resultado.pk).exists()


    if es_nuevo:
        ranking_eq1.pj += 1
        ranking_eq2.pj += 1


    if ganador == equipo1:
        ranking_eq1.pg += 1
        ranking_eq2.pp += 1
        ranking_eq1.puntaje_total_categoria += 100
        ranking_eq2.puntaje_total_categoria -= 50
    else:
        ranking_eq2.pg += 1
        ranking_eq1.pp += 1
        ranking_eq2.puntaje_total_categoria += 100
        ranking_eq1.puntaje_total_categoria -= 50

    ranking_eq1.games += (games_eq1 - games_eq2)
    ranking_eq2.games += (games_eq2 - games_eq1)

    if ganador == equipo1:
        ranking_eq1.sets += sets_eq1
        ranking_eq2.sets += (sets_eq2 - sets_eq1)
    else:
        ranking_eq2.sets += sets_eq2
        ranking_eq1.sets += (sets_eq1 - sets_eq2)

    ranking_eq1.save()
    ranking_eq2.save()

# no se usa más 12/8
def revertir_ranking_single(resultado):
    partido = resultado.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()

    jugador1 = partido.jugador1
    jugador2 = partido.jugador2
    ganador = resultado.ganador_jugador

    if not ganador:
        return

    perdedor = jugador2 if ganador == jugador1 else jugador1

    ranking_j1 = Ranking.objects.get(jugador=jugador1, torneo=torneo)
    ranking_j2 = Ranking.objects.get(jugador=jugador2, torneo=torneo)

    sets_ganados = contar_sets_ganados(
        resultado.set1_jugador1, resultado.set1_jugador2,
        resultado.set2_jugador1, resultado.set2_jugador2,
        resultado.set3_jugador1, resultado.set3_jugador2
    )
    sets_perdidos = contar_sets_ganados(
        resultado.set1_jugador2, resultado.set1_jugador1,
        resultado.set2_jugador2, resultado.set2_jugador1,
        resultado.set3_jugador2, resultado.set3_jugador1
    )

    games_j1 = resultado.set1_jugador1 + resultado.set2_jugador1
    games_j2 = resultado.set1_jugador2 + resultado.set2_jugador2

    ranking_ganador = Ranking.objects.get(jugador=ganador, torneo=torneo)
    ranking_perdedor = Ranking.objects.get(jugador=perdedor, torneo=torneo)

    ranking_ganador.pg -= 1
    ranking_ganador.sets -= (sets_ganados - sets_perdidos)
    ranking_ganador.games -= (games_j1 - games_j2)
    ranking_ganador.puntaje_total_categoria -= 100
    ranking_ganador.save()

    ranking_perdedor.pp -= 1
    ranking_perdedor.sets -= (sets_perdidos - sets_ganados)
    ranking_perdedor.games -= (games_j2 - games_j1)
    ranking_perdedor.puntaje_total_categoria += 50
    ranking_perdedor.save()

# no se usa más 12/8
def revertir_ranking_doble(resultado):
    partido = resultado.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()
    anio = torneo.fecha_inicio.year
    bimestre = 1  # ajustar según lógica real

    equipo1 = partido.equipo1
    equipo2 = partido.equipo2
    ganador = resultado.ganador_equipo

    if not ganador:
        return

    perdedor = equipo2 if ganador == equipo1 else equipo1

    ranking_eq1 = RankingEquipo.objects.get(equipo=equipo1, torneo=torneo)
    ranking_eq2 = RankingEquipo.objects.get(equipo=equipo2, torneo=torneo)

    sets_ganados = contar_sets_ganados(
        resultado.set1_equipo1, resultado.set1_equipo2,
        resultado.set2_equipo1, resultado.set2_equipo2,
        resultado.set3_equipo1, resultado.set3_equipo2
    )
    sets_perdidos = contar_sets_ganados(
        resultado.set1_equipo2, resultado.set1_equipo1,
        resultado.set2_equipo2, resultado.set2_equipo1,
        resultado.set3_equipo2, resultado.set3_equipo1
    )

    games_eq1 = resultado.set1_equipo1 + resultado.set2_equipo1
    games_eq2 = resultado.set1_equipo2 + resultado.set2_equipo2

    ranking_ganador = RankingEquipo.objects.get(equipo=ganador, torneo=torneo)
    ranking_perdedor = RankingEquipo.objects.get(equipo=perdedor, torneo=torneo)

    ranking_ganador.pg -= 1
    ranking_ganador.sets -= (sets_ganados - sets_perdidos)
    ranking_ganador.games -= (games_eq1 - games_eq2)
    ranking_ganador.puntaje_total_categoria -= 100
    ranking_ganador.save()

    ranking_perdedor.pp -= 1
    ranking_perdedor.sets -= (sets_perdidos - sets_ganados)
    ranking_perdedor.games -= (games_eq2 - games_eq1)
    ranking_perdedor.puntaje_total_categoria += 50
    ranking_perdedor.save()



@staff_member_required
def actualizar_ascensos(request, torneo_id):
    torneo = get_object_or_404(Torneo, pk=torneo_id)
    if request.method == 'POST':
        try:
            nuevo = int(request.POST.get('ascensos', '0'))
            if nuevo < 0: raise ValueError
            set_ascensos(torneo.id, nuevo)
            messages.success(request, f"Ascienden actualizado a {nuevo} para {torneo.nombre}.")
        except ValueError:
            messages.error(request, "Ingresá un número válido (0 o mayor).")
    return redirect('ver_ranking', torneo_id=torneo.id)

@staff_member_required
def actualizar_descensos(request, torneo_id):
    torneo = get_object_or_404(Torneo, pk=torneo_id)
    if request.method == 'POST':
        try:
            nuevo = int(request.POST.get('descensos', '0'))
            if nuevo < 0: raise ValueError
            set_descensos(torneo.id, nuevo)
            messages.success(request, f"Descienden actualizado a {nuevo} para {torneo.nombre}.")
        except ValueError:
            messages.error(request, "Ingresá un número válido (0 o mayor).")
    return redirect('ver_ranking', torneo_id=torneo.id)
