from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse
from .models import CategoríaGasto, Gasto, CategoriaIngreso, Ingreso, Mes, GastoMes, IngresoMes
from datetime import date
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
from .forms import GastoForm, IngresoForm
from django.http import Http404
import json
from django.forms import modelformset_factory



MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }


def index(request):
    """La página de inicio para Successus"""
    return render(request, 'successify/index.html')

def mes(request, codigo_mes, codigo_movimiento):
    """Vista completa de toda la información de un mes"""
    
    # 1. Buscamos el mes específico por su código.
    mes_obj = get_object_or_404(Mes, codigo=codigo_mes, owner=request.user)
    nombre_mes = MESES_ES.get(mes_obj.month,"random")
    
    # 2. Buscamos los registros que pertenecen a ese mes
    ingresos_mes = IngresoMes.objects.filter(mes=mes_obj)
    gastos_mes = GastoMes.objects.filter(mes=mes_obj)
    
    # 3. Calculamos totales
    total_ingresos = sum(i.monto for i in ingresos_mes)
    total_gastos = sum(g.monto for g in gastos_mes)

    context = {
        'mes': mes_obj,
        'nombre_mes':nombre_mes,
        'gastos_mes': gastos_mes,
        'total_gastos': total_gastos,
        'ingresos_mes': ingresos_mes,
        'total_ingresos': total_ingresos,
        'balance': total_ingresos - total_gastos,
        'codigo_movimiento': codigo_movimiento,
    }

    # Nota: El primer argumento de render es el nombre del ARCHIVO .html
    return render(request, 'successify/mes_panel.html', context)


def categorias_de_gastos(request):
    """La página que muestra todas las categorías de gastos"""
    categorias = CategoríaGasto.objects.order_by('date_added')
    context = {'categorias':categorias}

    return render(request, 'successify/categorias_de_gastos.html', context)

@login_required
def gastos(request):
    """La página que muestra todos los gastos"""                
    today = date.today()
    
    gastos_fijos = Gasto.objects.filter(
        owner=request.user,categoria__name='Gastos Fijos').order_by('-presupuesto')
    
    gastos_esporadicos = Gasto.objects.filter(
        owner=request.user, categoria__name='Gastos Esporádicos').order_by('-presupuesto')
    
    context = {'gastos_fijos':gastos_fijos,
               'gastos_esporadicos':gastos_esporadicos,
                "year": today.year,
                "month": today.month,
    }

    return render(request, 'successify/gastos.html', context)

@login_required
def gasto(request,codigo):
    """Página que muestra un gasto en específico"""
    gasto = get_object_or_404(Gasto,codigo=codigo,owner=request.user)
    gasto_form = GastoForm(instance=gasto)
    # Traer todos los GastoMes de este gasto
    qs = GastoMes.objects.filter(gasto=gasto).order_by('mes__year', 'mes__month')

    try:
        year_focal = int(request.GET.get('year', date.today().year))
    except ValueError:
        year_focal = date.today().year

    fecha_central = date(year_focal, date.today().month, 1)

    meses_rango = []
    inicio = fecha_central - relativedelta(months=3)

    for i in range(12):
        fecha_iterada = inicio + relativedelta(months=i)       
        mes_obj, _ = Mes.objects.get_or_create(
            owner=request.user, 
            year=fecha_iterada.year, 
            month=fecha_iterada.month
        )
        
        # Usamos .first() para que no de error si no existe aún
        gasto_mes = GastoMes.objects.filter(gasto=gasto, mes=mes_obj).first()
        
        nombre_mes = MESES_ES[fecha_iterada.month]

        if gasto_mes:        
            meses_rango.append({
                'nombre': nombre_mes, # Ene 2026
                'mes_obj': mes_obj,
                'gasto_mes': gasto_mes,
                'es_actual': fecha_iterada.month == date.today().month and fecha_iterada.year == date.today().year
            })
        
        else:
            meses_rango.append({ 
            'nombre': nombre_mes, # Ene 2026
            'mes_obj': mes_obj,
            'gasto_mes': gasto_mes,
            'es_actual': fecha_iterada.month == date.today().month and fecha_iterada.year == date.today().year
            })

    
    context={'gasto':gasto,
            'gasto_form':gasto_form,
            'codigo':gasto.codigo,
            'meses_rango':meses_rango,
            'year_actual': year_focal,
            'year_prev': year_focal - 1,
            'year_next': year_focal + 1,    
    }

    return render(request, 'successify/gasto.html', context)

@login_required
def nuevo_gasto(request):
    """Añade un nuevo gasto"""
    if request.method != 'POST':
        #No se enviaron datos, crea un formulario en blanco
        form = GastoForm()
    
    else:
        #Datos POST enviados, procesa datos
        form = GastoForm(data=request.POST)
        if form.is_valid():
            nuevo_gasto = form.save(commit=False)
            nuevo_gasto.owner = request.user
            nuevo_gasto.save()
            return redirect('successify:gasto', codigo=nuevo_gasto.codigo)
    
    #Muestra un formulario en blanco o no válido
    context = {'form': form}
    return render(request, 'successify/nuevo_gasto.html',context)

@login_required
@require_POST
def nuevo_gasto_mes(request, codigo):
    """Crea un GastoMes desde la página de gasto"""
    gasto = get_object_or_404(Gasto, codigo=codigo, owner=request.user)

    #Obtenemos los datos del formulario
    monto = request.POST.get('monto')
    year = request.POST.get('year')
    month = request.POST.get('month')

    if monto and year and month:
        mes_obj, _ = Mes.objects.get_or_create(
            owner = request.user,
            year=int(year),
            month=int(month),
        )

        if mes_obj.cerrado:
            messages.error(request, f"El mes {mes_obj} está cerrado y no permite nuevos registros.")
            return redirect(f"{reverse('successify:gasto', args=[gasto.codigo])}?year={year}")

        GastoMes.objects.update_or_create(
            mes = mes_obj,
            gasto=gasto,
            defaults={'monto': monto}
        )
    
        return redirect(f"{reverse('successify:gasto', args=[gasto.codigo])}?year={year}")

def eliminar_gastomes(request, codigo_gastomes):
    # Buscamos por el owner del mes para seguridad
    gastomes = get_object_or_404(GastoMes, codigo=codigo_gastomes, mes__owner=request.user)
    
    # Datos para volver atrás
    year = gastomes.mes.year
    # Si el gasto existe usamos su código, si no, volvemos al resumen
    redirect_url = reverse('successify:resumen')
    
    if gastomes.gasto:
        redirect_url = f"{reverse('successify:gasto', args=[gastomes.gasto.codigo])}?year={year}"

    if gastomes.mes.cerrado:
        messages.error(request, "No se puede eliminar un registro de un mes cerrado.")
        return redirect(redirect_url)

    if request.method == 'POST':       
        gastomes.delete()
        messages.success(request, "Registro eliminado correctamente.")
        return redirect(redirect_url)


@login_required
@transaction.atomic
def editar_gasto(request, codigo):
    gasto = get_object_or_404(Gasto, codigo=codigo, owner=request.user)

    if request.method == 'POST':
        gasto_form = GastoForm(instance=gasto, data=request.POST)

        if gasto_form.is_valid():
            gasto_form.save()
            return redirect('successify:gasto', codigo=gasto.codigo)
    else:
        gasto_form = GastoForm(instance=gasto)


    context = {
        'gasto': gasto,
        'gasto_form': gasto_form,
        'codigo':gasto.codigo,
        }
    
    return render(request, 'successify/gasto.html', context)

@login_required
def eliminar_gasto(request, codigo):
    """Elimina un gasto"""
    gasto = get_object_or_404(
        Gasto,
        codigo=codigo,
        owner=request.user
    )

    redirect_url = reverse('successify:resumen')

    if request.method == 'POST':

        GastoMes.objects.filter(
            gasto=gasto,
            mes__cerrado=False,
            owner=request.user).delete()

        gasto.delete()
        return redirect('successify:gastos')

def categorias_de_ingresos(request):
    """La página que muestra todas las categorías de ingresos"""
    categorias = CategoriaIngreso.objects.order_by('date_added')

    context = {'categorias':categorias}

    return render(request, 'successify/categorias_de_ingresos.html',context)

@login_required
def ingresos(request):
    """La página que muestra todos los gastos"""  
    today = date.today()              
    ingresos = Ingreso.objects.filter(owner=request.user).order_by('categoria')
    context = {'ingresos':ingresos,
               'year':today.year,
               'month':today.month
    }

    return render(request, 'successify/ingresos.html', context)

@login_required
def ingreso(request, codigo):
    """Página que muestra un ingreso en específico"""
    ingreso = get_object_or_404(Ingreso,codigo=codigo,owner=request.user)
    ingreso_form = IngresoForm(instance=ingreso)

    try:
        yearl_focal = int(request.GET.get('year',date.today().year))
    except ValueError:
        yearl_focal = date.today().year

    fecha_central = date(yearl_focal,date.today().month, 1)

    meses_rango = []
    inicio = fecha_central - relativedelta(months=3)

    for i in range(12):
        fecha_iterada = inicio + relativedelta(months=i)
        # Buscar (o asegurar que exista) el objeto Mes en la DB
        # Esto es vital para que IngresoMes tenga a donde apuntar
        mes_obj, _ = Mes.objects.get_or_create(
            owner = request.user,
            year=fecha_iterada.year,
            month=fecha_iterada.month,
        )

        # Buscar el IngresoMes para este gasto en este mes
        # Usamos .first() para que no de error si no existe aún
        ingreso_mes = IngresoMes.objects.filter(ingreso=ingreso, mes=mes_obj).first()
        
        nombre_mes_frontend = MESES_ES[fecha_iterada.month]

        if ingreso_mes:
            meses_rango.append({
                'nombre' : nombre_mes_frontend, #Ene 2026
                'mes_obj': mes_obj,
                'ingreso_mes':ingreso_mes,
                'es_actual': fecha_iterada.month == date.today().month and fecha_iterada.year == date.today().year,
                })

        else:
            meses_rango.append({
                'nombre': nombre_mes_frontend,
                'mes_obj':mes_obj,
                'ingreso_mes':ingreso_mes,
                'es_actual' : fecha_iterada.month == date.today().month and fecha_iterada.year == date.today().year,
                })
            
    context={'ingreso':ingreso,
             'ingreso_form':ingreso_form,
             'codigo':ingreso.codigo,
             'meses_rango':meses_rango,
             'year_actual':yearl_focal,
             'year_prev':yearl_focal -1,
             'year_next':yearl_focal +1,
    }

    return render(request, 'successify/ingreso.html', context)

@login_required
def nuevo_ingreso(request):
    """Añade un nuevo ingreso"""
    if request.method != 'POST':
        #No se enviaron datos, crea un formulario en blanco
        form = IngresoForm()
    
    else:
        #Datos POST enviados, procesa datos
        form = IngresoForm(data=request.POST)
        if form.is_valid():
            nuevo_ingreso = form.save(commit=False)
            nuevo_ingreso.owner = request.user
            nuevo_ingreso.save()
            return redirect('successify:ingreso',codigo=nuevo_ingreso.codigo)
    
    #Muestra un formulario en blanco o no válido
    context = {'form': form}
    return render(request,'successify/nuevo_ingreso.html', context)

@login_required
@require_POST
def nuevo_ingreso_mes(request,codigo):
    """Crea un IngresoMes desde la pagina de ingreso"""
    ingreso=get_object_or_404(Ingreso,codigo=codigo, owner=request.user)

    #Obtenemos los datos del formulario
    monto = request.POST.get('monto')
    year = request.POST.get('year')
    month = request.POST.get('month')  

    if monto and year and month:
        mes_obj, _ = Mes.objects.get_or_create(
            owner=request.user,
            year=int(year),
            month=int(month),
        )

        IngresoMes.objects.update_or_create(
            mes=mes_obj,
            ingreso=ingreso,
            defaults={'monto':monto}
        )

        return redirect(f"{reverse('successify:ingreso', args=[ingreso.codigo])}?year={year}")

def eliminar_ingresomes(request,codigo_ingresomes):
    """Elimina un IngresoMes"""
    ingresomes=get_object_or_404(IngresoMes,codigo=codigo_ingresomes, ingreso__owner=request.user)
    codigo_ingreso = ingresomes.ingreso.codigo
    año_del_ingresomes = ingresomes.mes.year

    if request.method == 'POST':
        ingresomes.delete()
        return redirect(f"{reverse('successify:ingreso', args=[codigo_ingreso])}?year={año_del_ingresomes}")

    context = {
        'ingresomes':ingresomes,
        'ingreso':ingresomes.ingreso
        }

    return render(request, 'successify/eliminar_ingresomes.html', context)

@login_required
@transaction.atomic
def editar_ingreso(request, codigo):
    ingreso = get_object_or_404(Ingreso, codigo=codigo, owner=request.user)
    
    if request.method=='POST':
        ingreso_form=IngresoForm(instance=ingreso, data=request.POST)

        if ingreso_form.is_valid():
            ingreso_form.save()
            return redirect('successify:ingreso',codigo=ingreso.codigo)

    else:
        ingreso_form = IngresoForm(instance=ingreso)

    context = {
        'ingreso':ingreso,
        'ingreso_form':ingreso_form,
        'codigo':codigo,
        }
    
    return render(request,'successify/ingreso.html', context)

@login_required
def eliminar_ingreso(request, codigo):
    """Eliminar un ingreso"""
    ingreso = get_object_or_404(
        Ingreso,
        codigo=codigo,
        owner=request.user,
    )

    if request.method == 'POST':
        ingreso.delete()
        return redirect('successify:ingresos')
    
    return render(request, 'successify/eliminar_ingreso.html',{'ingreso':ingreso})

def get_or_create_mes(user, year, month):
    mes, created = Mes.objects.get_or_create(
        owner=user,
        year=year,
        month=month
    )
    
    return mes

@login_required
def balance(request):
    """Calcula el balance mensual usando Mes, GastoMes e IngresoMes"""
    today = date.today()
    year = request.GET.get("year")
    month = request.GET.get("month")

    try:
        year = int(year)
    except (TypeError, ValueError):
        year = today.year

    try:
        month = int(month)
        if month < 1 or month > 12:
            month = today.month
    except (TypeError, ValueError):
        month = today.month

    balances_anuales = []

    for m in range(1, 13):

        mes_obj = get_or_create_mes(request.user, year, m)

        gastos_fijos = GastoMes.objects.filter(
            mes=mes_obj,
            gasto__categoria__es_fijo=True
        ).aggregate(Sum("monto"))["monto__sum"] or 0

        gastos_esporadicos = GastoMes.objects.filter(
            mes=mes_obj,
            gasto__categoria__es_fijo=False
        ).aggregate(Sum("monto"))["monto__sum"] or 0

        ingresos_fijos = IngresoMes.objects.filter(
            mes=mes_obj,
            ingreso__categoria__es_fijo=True
        ).aggregate(Sum("monto"))["monto__sum"] or 0

        ingresos_esporadicos = IngresoMes.objects.filter(
            mes=mes_obj,
            ingreso__categoria__es_fijo=False
        ).aggregate(Sum("monto"))["monto__sum"] or 0

        total_ingresos = ingresos_fijos + ingresos_esporadicos
        total_gastos = gastos_fijos + gastos_esporadicos

        balances_anuales.append({
            "mes": m,
            "ingresos": total_ingresos,
            "gastos": total_gastos,
            "balance": total_ingresos - total_gastos,
        })

    mes_actual_data = balances_anuales[month - 1]

    # Navegación meses/años
    prev_month, prev_year = (month-1, year) if month > 1 else (12, year-1)
    next_month, next_year = (month+1, year) if month < 12 else (1, year+1)

    labels = [f"Mes {item['mes']}" for item in balances_anuales]
    balances = [float(item.get("balance", 0)) for item in balances_anuales]

    context = {
        "year": year,
        "month": month,
        "balances_anuales": balances_anuales,
        "total_ingresos": mes_actual_data["ingresos"],
        "total_gastos": mes_actual_data["gastos"],
        "balance_mes": mes_actual_data["balance"],
        "prev_month": prev_month,
        "prev_month_year": prev_year,
        "next_month": next_month,
        "next_month_year": next_year,
        "context_labels": json.dumps(labels),
        "context_balances": json.dumps(balances),
    }

    return render(request, "successify/balance.html", context)

def resumen(request):
    """Lista todos los ingresos, gastos"""
    gastos_fijos = Gasto.objects.filter(owner=request.user, categoria__name = 'Gastos Fijos').order_by('-presupuesto')
    gastos_esporadicos = Gasto.objects.filter(owner=request.user, categoria__name = 'Gastos Esporádicos').order_by('-presupuesto') 
    ingresos_fijos = Ingreso.objects.filter(owner=request.user, categoria__name = 'Ingresos Fijos').order_by('-presupuesto')
    ingresos_esporadicos = Ingreso.objects.filter(owner=request.user, categoria__name = 'Ingresos Esporadicos').order_by('-presupuesto')



    today = date.today()
    mes_actual = today.month
    año_actual = today.year

    codigo_mes = f"{str(año_actual)[-2:]}{mes_actual:02d}"

    mes = Mes.objects.filter(codigo=codigo_mes).first()

    #Sumo todos los gastos dentro del mes en curso
    gastos_mes = GastoMes.objects.filter(mes=mes)
    total_gasto_mes = 0

    for gasto_mes in gastos_mes:
        total_gasto_mes += gasto_mes.monto

    #Sumo todos los ingresos dentro del mes en curso
    ingresos_mes = IngresoMes.objects.filter(mes=mes)
    total_ingreso_mes = 0

    for ingreso_mes in ingresos_mes:
        total_ingreso_mes += ingreso_mes.monto
    
    balance = total_ingreso_mes - total_gasto_mes

    context = {
        'gastos_fijos':gastos_fijos,
        'gastos_esporadicos':gastos_esporadicos,
        'ingresos_fijos':ingresos_fijos,
        'ingresos_esporadicos':ingresos_esporadicos,
        'total_gasto_mes':total_gasto_mes,
        'total_ingreso_mes':total_ingreso_mes,
        'mes':mes,
        'balance':balance,
    }

    return render(request, 'successify/resumen.html', context)


#FUNCIONES

def cambiar_estado_mes(request, codigo):
    if request.method == 'POST':
        mes_obj = get_object_or_404(Mes, codigo=codigo, owner=request.user)
        mes_obj.cerrado = not mes_obj.cerrado # Si está abierto lo cierra, y viceversa
        mes_obj.save()
        messages.success(request, f"Mes {'cerrado' if mes_obj.cerrado else 'abierto'} correctamente.")
    return redirect(request.META.get('HTTP_REFERER', 'successify:resumen'))