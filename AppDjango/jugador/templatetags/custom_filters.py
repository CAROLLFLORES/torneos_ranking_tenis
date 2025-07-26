from django import template

register = template.Library()

@register.filter
def formatear_categoria(categoria):
    return f"{categoria.tipo_juego}-{categoria.genero}-{categoria.nivel}-{categoria.edad}"

