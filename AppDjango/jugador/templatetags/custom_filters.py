from django import template

register = template.Library()

@register.filter
def formatear_categoria(categoria):
    return f"{categoria.nivel}-{categoria.edad}-{categoria.tipo_juego}"
