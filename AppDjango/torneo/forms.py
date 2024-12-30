# torneo/forms.py

from django import forms
from .models import Torneo
from jugador.models import Categoria  # Asegúrate de importar correctamente desde la app jugador

class TorneoForms(forms.ModelForm):
    categorias = forms.ModelMultipleChoiceField(
        queryset=Categoria.objects.all(),
        widget=forms.SelectMultiple(attrs={'class': 'form-control'}),  # Cambia a Select si quieres que sea un solo seleccionable
        label="Categorías"
    )
    tipo = forms.ChoiceField(
        choices=Torneo.TIPO_CHOICES,
        required=True,
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    
    class Meta:
        model = Torneo
        fields = ['nombre', 'fecha_inicio', 'fecha_fin', 'categorias', 'tipo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'form-control', 'placeholder': 'Nombre del Torneo'}),
            'fecha_inicio': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'fecha_fin': forms.DateInput(attrs={'class': 'form-control', 'type': 'date'}),
            'categorias': forms.Select(attrs={'class': 'form-control'}),
            'tipo': forms.Select(attrs={'class': 'form-control'}),
        }
