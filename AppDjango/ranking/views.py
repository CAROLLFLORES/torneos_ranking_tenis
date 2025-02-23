from django.shortcuts import render, get_object_or_404

# Create your views here.
from django.db.models.signals import post_save
from django.dispatch import receiver
from torneo.models import ResultadoPartido
from ranking.models import Ranking, Torneo
from django.core.paginator import Paginator



from django.db.models import Sum, F

def ranking_torneo(request, torneo_id):
    torneo = get_object_or_404(Torneo, id=torneo_id)

    ranking = Ranking.objects.filter(torneo=torneo).annotate(
        games=F('pg') - (F('pj') - F('pg'))  # Games ganados - Games perdidos
    ).order_by('-puntaje_total_categoria')  # Ordenar por puntaje

    return render(request, 'ranking.html', {'torneo': torneo, 'ranking': ranking})



def ver_ranking(request, torneo_id):
    torneo_actual = get_object_or_404(Torneo, id=torneo_id)
    torneos_en_curso = Torneo.objects.all()  # 🔥 Mostrar todos los torneos disponibles

    ranking = Ranking.objects.filter(torneo=torneo_actual).select_related('jugador').order_by(
        '-puntaje_total_categoria', '-games'
    )

    return render(request, 'ranking.html', {
        'torneo_actual': torneo_actual,  # ✅ Asegura que este contexto esté en la plantilla
        'torneos_en_curso': torneos_en_curso,
        'ranking': ranking
    })




@receiver(post_save, sender=ResultadoPartido)
def actualizar_ranking(sender, instance, **kwargs):
    """ 🔥 Se ejecuta cuando se guarda un resultado de partido y actualiza el ranking """

    partido = instance.partido
    torneo = partido.torneo
    categoria = torneo.categorias.first()
    ganador = instance.ganador_jugador
    perdedor = partido.jugador1 if partido.jugador1 != ganador else partido.jugador2

    if not ganador or not perdedor:
        print(f"⚠ No se encontró un ganador o perdedor en partido {partido.id}")
        return

    # 🔹 Calcular Games ganados y perdidos por cada jugador
    games_ganador = instance.set1_jugador1 + instance.set2_jugador1 + instance.set3_jugador1
    games_perdedor = instance.set1_jugador2 + instance.set2_jugador2 + instance.set3_jugador2

    if ganador == partido.jugador2:  # Si el ganador es el jugador2, intercambiamos los valores
        games_ganador, games_perdedor = games_perdedor, games_ganador

    # 🔥 ACTUALIZAR RANKING DEL GANADOR 🔥
    ranking_ganador, created = Ranking.objects.get_or_create(
        jugador=ganador,
        torneo=torneo,
        categoria=categoria,
        defaults={"pj": 0, "pg": 0, "games": 0, "puntaje_total_categoria": 0}
    )
    ranking_ganador.pj += 1
    ranking_ganador.pg += 1
    ranking_ganador.games += (games_ganador - games_perdedor)  # 🔹 Sumar Games ganados menos perdidos
    ranking_ganador.puntaje_total_categoria += 100
    ranking_ganador.save()

    # 🔥 ACTUALIZAR RANKING DEL PERDEDOR 🔥
    ranking_perdedor, created = Ranking.objects.get_or_create(
        jugador=perdedor,
        torneo=torneo,
        categoria=categoria,
        defaults={"pj": 0, "pg": 0, "games": 0, "puntaje_total_categoria": 0}
    )
    ranking_perdedor.pj += 1
    ranking_perdedor.games += (games_perdedor - games_ganador)  # 🔹 Sumar Games ganados menos perdidos
    ranking_perdedor.puntaje_total_categoria -= 50
    ranking_perdedor.save()

    print(f"🏆 Ranking actualizado: {ganador.nombre} (+{games_ganador - games_perdedor} Games) | {perdedor.nombre} (-{games_perdedor - games_ganador} Games)")


def ranking_general(request):
    torneos = Torneo.objects.all()  # 🔹 Obtener todos los torneos
    return render(request, 'ranking_general.html', {'torneos': torneos})