from django import template

register = template.Library()

@register.filter
def formatear_categoria(categoria):
    return f"{categoria.tipo_juego}-{categoria.genero}-{categoria.nivel}-{categoria.edad}"

# nuevo
@register.filter
def estado_class(estado):
    # Usalo con jugador.estado
    return 'estado-inactivo' if estado == 'INA' else ''
