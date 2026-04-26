from django.shortcuts import render, redirect
from django.contrib.auth import login
from django.contrib.auth.forms import UserCreationForm, UserChangeForm

def register(request):
    """Registra un nuevo usuario"""
    if request.method != 'POST':
        #Muestra un formulario de registro en blanco
        form = UserCreationForm()
    else:
        #Procesa un formulario cumplimentado
        form = UserCreationForm(data=request.POST)
        if form.is_valid():
            new_user = form.save()
            #Inicia la sesión del usuario y lo redirige a la página de inicio
            login(request, new_user)
            return redirect('successify:index')
    #Muestra un formulario en blanco o no válido
    context = {'form':form}
    return render(request, 'registration/register.html', context)