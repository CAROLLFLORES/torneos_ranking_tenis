from django import forms
from .models import Jugador, Categoria

class JugadorForm(forms.ModelForm):
    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        widget=forms.CheckboxSelectMultiple,
        required=True
    )

    class Meta:
        model = Jugador
        fields = ['nombre', 'apellido', 'dni', 'sexo', 'categorias']