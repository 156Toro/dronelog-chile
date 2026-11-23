from django import template

register = template.Library()


@register.filter
def campo(objeto, nombre):
    valor = getattr(objeto, nombre, "")
    if isinstance(valor, bool):
        return "Sí" if valor else "No"
    return "—" if valor in (None, "") else valor
