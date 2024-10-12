from django.shortcuts import render
from django.urls import reverse

# Create your views here.
def abm_torneo(request):
    return render(request, 'abm_torneo.html')