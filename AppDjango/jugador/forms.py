from django import forms
from .models import Jugador

from django import forms
from .models import Jugador, Categoria

class JugadorForm(forms.ModelForm):
    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        widget=forms.CheckboxSelectMultiple,  # Cambia el widget según cómo quieras mostrar las opciones (checkboxes o dropdown)
        required=True,  # Haz que sea obligatorio o no según tus necesidades
        label="Categorías",  # Etiqueta personalizada para el campo
    )

    class Meta:
        model = Jugador
        fields = ['nombre', 'apellido', 'dni', 'sexo', 'categorias']  # Incluye las categorías
        widgets = {
            'dni': forms.HiddenInput(),  # Ocultar el campo DNI en el formulario
        }
