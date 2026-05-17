from django.forms import modelformset_factory
from django import forms
from .models import Gasto, Ingreso, IngresoMes, GastoMes

class GastoForm(forms.ModelForm):
    class Meta:
        model = Gasto
        fields = ['categoria', 'nombre', 'presupuesto']

class GastoMesForm(forms.ModelForm):
    model: GastoMes
    fields= ['mes','gasto','monto']
        
class IngresoForm(forms.ModelForm):
    class Meta:
        model = Ingreso
        fields = ['categoria', 'nombre', 'presupuesto']

class IngresoMesForm(forms.ModelForm):
    model: IngresoMes
    fields= ['mes','gasto','monto']