from django import forms
from .models import Jugador

class JugadorForm(forms.ModelForm):
    class Meta:
        model = Jugador
        fields = ['nombre', 'apellido', 'dni', 'sexo']
        widgets = {
            'dni': forms.HiddenInput(),  # Ocultar el campo DNI en el formulario
        }
