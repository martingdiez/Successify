from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.contrib.auth.decorators import login_required
from django.views.decorators.http import require_POST
from django.urls import reverse
from .models import CategoríaGasto, Gasto, CategoriaIngreso, Ingreso, Mes, GastoMes, IngresoMes, SubGastoMes
from datetime import date
from dateutil.relativedelta import relativedelta
from django.utils import timezone
from django.db.models import Sum
from django.db import transaction
from .forms import GastoForm, IngresoForm
from django.http import Http404
import json
from django.forms import ValidationError, modelformset_factory
from collections import defaultdict



MESES_ES = {
    1: 'Enero', 2: 'Febrero', 3: 'Marzo', 4: 'Abril',
    5: 'Mayo', 6: 'Junio', 7: 'Julio', 8: 'Agosto',
    9: 'Septiembre', 10: 'Octubre', 11: 'Noviembre', 12: 'Diciembre'
    }


def index(request):
    """La página de inicio para Successus"""
    return render(request, 'successify/index.html')

def mes(request, codigo_mes):
    """Vista completa e interactiva con estructura de árbol para un mes"""
    
    # 1. Recuperamos el mes
    mes_obj = get_object_or_404(Mes, codigo=codigo_mes, owner=request.user)
    nombre_mes = MESES_ES.get(mes_obj.month, "Misterioso")
    
    # 2. Capturamos el código del movimiento si viene por Query Parameter
    codigo_movimiento = request.GET.get('movimiento', None)
    
    # 3. Traemos los registros haciendo el JOIN exacto hacia la categoría
    ingresos_mes = IngresoMes.objects.filter(mes=mes_obj).select_related('ingreso__categoria')
    gastos_mes = GastoMes.objects.filter(mes=mes_obj).select_related('gasto__categoria')
    
    # 4. Calculamos totales globales
    total_ingresos = sum(i.monto for i in ingresos_mes)
    total_gastos = sum(g.monto for g in gastos_mes)
    
    # 5. Agrupamos Gastos por Categoría de forma segura
    gastos_por_categoria = defaultdict(list)
    for gm in gastos_mes:
        # Vamos directo al grano: GastoMes -> gasto -> categoria
        cat = gm.categoria
        gastos_por_categoria[cat].append(gm)
        
    arbol_gastos = []
    for categoria, lista_items in gastos_por_categoria.items():
        lista_items_ordenada = sorted(lista_items, key=lambda item: item.monto, reverse=True)

        subtotal = sum(item.monto for item in lista_items)
        arbol_gastos.append({
            'categoria': categoria,
            'items': lista_items_ordenada,
            'subtotal': subtotal
        })
        
    # 6. Agrupamos Ingresos por Categoría de forma segura
    ingresos_por_categoria = defaultdict(list)
    for im in ingresos_mes:
        # Vamos directo al grano: IngresoMes -> ingreso -> categoria
        cat = im.categoria
        ingresos_por_categoria[cat].append(im)
        
    arbol_ingresos = []
    for categoria, lista_items in ingresos_por_categoria.items():
        lista_items_ordenada = sorted(lista_items, key=lambda item: item.monto, reverse=True)

        subtotal = sum(item.monto for item in lista_items)
        arbol_ingresos.append({
            'categoria': categoria,
            'items': lista_items_ordenada,
            'subtotal': subtotal
        })

    context = {
        'mes': mes_obj,
        'nombre_mes': nombre_mes,
        'arbol_gastos': arbol_gastos,
        'total_gastos': total_gastos,
        'arbol_ingresos': arbol_ingresos,
        'total_ingresos': total_ingresos,
        'balance': total_ingresos - total_gastos,
        'codigo_movimiento': codigo_movimiento,
    }

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
        owner=request.user,categoria__nombre='Gastos Fijos').order_by('-presupuesto')
    
    gastos_esporadicos = Gasto.objects.filter(
        owner=request.user, categoria__nombre='Gastos Esporádicos').order_by('-presupuesto')
    
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


    meses_rango = []
    inicio = date(year_focal, 1, 1)


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

        subgastos = []
        if gasto_mes:
            # Traemos todos los subgastos asociados a este mes
            subgastos = gasto_mes.subgastos.all().order_by('id')

        if gasto_mes:        
            meses_rango.append({
                'nombre': nombre_mes, # Ene 2026
                'mes_obj': mes_obj,
                'gasto_mes': gasto_mes,
                'es_actual': fecha_iterada.month == date.today().month and fecha_iterada.year == date.today().year,
                'subgastos': subgastos
            })
        
        else:
            meses_rango.append({ 
            'nombre': nombre_mes, # Ene 2026
            'mes_obj': mes_obj,
            'gasto_mes': gasto_mes,
            'es_actual': fecha_iterada.month == date.today().month and fecha_iterada.year == date.today().year,
            'subgastos': subgastos
            })

    # Navegación
    prev_year = year_focal - 1
    next_year = year_focal + 1
    
    context={'gasto':gasto,
            'gasto_form':gasto_form,
            'codigo':gasto.codigo,
            'meses_rango':meses_rango,
            'year_actual': year_focal,
            'prev_year': prev_year,
            'next_year': next_year,    
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
def eliminar_subgasto(request, subgasto_id):
    """Elimina directamente un subgasto desde su botón de basurero rojo"""
    if request.method == "POST":
        subgasto = get_object_or_404(SubGastoMes, id=subgasto_id, gasto_mes__gasto__owner=request.user)
        
        # Validación de seguridad heredada
        if subgasto.gasto_mes.mes.cerrado:
            raise ValidationError("No se puede eliminar un subregistro de un mes cerrado.")
        
        codigo_gasto = subgasto.gasto_mes.gasto.codigo
        subgasto.delete() # Al borrarse, el método delete() que creamos ayer recalculará el total del padre automáticamente
        
        return redirect('successify:gasto', codigo=codigo_gasto)
    
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
    
    return render(request,'successify/gasto.html', context)

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
            ).delete()

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
        year_focal = int(request.GET.get('year',date.today().year))
    except ValueError:
        year_focal = date.today().year


    meses_rango = []
    inicio = date(year_focal, 1, 1)

    for i in range(12):
        fecha_iterada = inicio + relativedelta(months=i)
        # Buscar (o asegurar que exista) el objeto Mes en la DB
        # Esto es vital para que IngresoMes tenga a donde apuntar
        mes_obj, _ = Mes.objects.get_or_create(
            owner = request.user,
            year=fecha_iterada.year,
            month=fecha_iterada.month,
        )

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

    # Navegación
    prev_year = year_focal - 1
    next_year = year_focal + 1

    context={'ingreso':ingreso,
             'ingreso_form':ingreso_form,
             'codigo':ingreso.codigo,
             'meses_rango':meses_rango,
             'year_actual':year_focal,
             'prev_year':prev_year,
             'next_year':next_year,
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

        if mes_obj.cerrado:
            messages.error(request, f"El mes {mes_obj} está cerrado y no permite nuevos registros.")
            return redirect(f"{reverse('successify:ingreso', args=[ingreso.codigo])}?year={year}")

        IngresoMes.objects.update_or_create(
            mes=mes_obj,
            ingreso=ingreso,
            defaults={'monto':monto}
        )

        return redirect(f"{reverse('successify:ingreso', args=[ingreso.codigo])}?year={year}")

def eliminar_ingresomes(request,codigo_ingresomes):
    """Elimina un IngresoMes"""
    ingresomes=get_object_or_404(IngresoMes,codigo=codigo_ingresomes, mes__owner=request.user)

    # Datos para volver atrás
    year = ingresomes.mes.year
    # Si el ingreso existe usamos su código, si no, volvemos al resumen
    redirect_url = reverse('successify:resumen')

    if ingresomes.ingreso:
        redirect_url = f"{reverse('successify:ingreso', args=[ingresomes.ingreso.codigo])}?year={year}"

    if ingresomes.mes.cerrado:
        messages.error(request, "No se puede eliminar un registro de un mes cerrado.")
        return redirect(redirect_url)

    if request.method == 'POST':
        ingresomes.delete()
        messages.success(request,"Registro eliminado correctamente.")
        return redirect(redirect_url)

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
        'codigo':ingreso.codigo,
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

    redirect_url = reverse('successify:resumen')

    if request.method == 'POST':

        IngresoMes.objects.filter(
            ingreso=ingreso,
            mes__cerrado=False,
        ).delete()

        ingreso.delete()
        return redirect('successify:ingresos')


@login_required
def balance(request):
    today = date.today()
    year = int(request.GET.get("year", today.year))
    month = int(request.GET.get("month", today.month))

    data_nombres_mes = []
    data_ingresos = []
    data_gastos = []
    data_balances = []
    meses_cerrados = []
    codigos_meses = []

    for m in range(1, 13):
        mes_obj = get_or_create_mes(request.user, year, m)

        # aggregate devuelve un diccionario {'monto__sum': valor}
        total_gastos = GastoMes.objects.filter(
            mes=mes_obj
        ).aggregate(Sum("monto"))["monto__sum"] or 0

        total_ingresos = IngresoMes.objects.filter(
            mes=mes_obj
        ).aggregate(Sum("monto"))["monto__sum"] or 0

        # MESES_ES es tu diccionario de nombres de meses
        data_nombres_mes.append(MESES_ES.get(m, f"Mes {m}"))
        data_ingresos.append(float(total_ingresos))
        data_gastos.append(float(total_gastos))
        data_balances.append(float(total_ingresos - total_gastos))
        meses_cerrados.append(mes_obj.cerrado)
        codigos_meses.append(mes_obj.codigo)

    # Navegación
    prev_year = year - 1
    next_year = year + 1

    context = {
        "year": year,
        "month": month,
        "graph_data": json.dumps({
            "labels": data_nombres_mes,
            "ingresos": data_ingresos,
            "gastos": data_gastos,
            "balances": data_balances,
            "cerrados": meses_cerrados,
            "codigos": codigos_meses,
        }),
        "prev_year": prev_year,
        "next_year": next_year,
    }
    return render(request, "successify/balance.html", context)

def resumen(request):
    """Lista todos los ingresos, gastos"""
    gastos_fijos = Gasto.objects.filter(owner=request.user, categoria__nombre = 'Gastos Fijos').order_by('-presupuesto')
    gastos_esporadicos = Gasto.objects.filter(owner=request.user, categoria__nombre = 'Gastos Esporádicos').order_by('-presupuesto') 
    ingresos_fijos = Ingreso.objects.filter(owner=request.user, categoria__nombre = 'Ingresos Fijos').order_by('-presupuesto')
    ingresos_esporadicos = Ingreso.objects.filter(owner=request.user, categoria__nombre = 'Ingresos Esporadicos').order_by('-presupuesto')



    today = date.today()
    mes_actual = today.month
    año_actual = today.year

    codigo_mes = f"{str(año_actual)[-2:]}{mes_actual:02d}"

    mes = Mes.objects.filter(codigo=codigo_mes).first()

    #Sumo todos los gastos dentro del mes en curso
    gastos_mes = GastoMes.objects.filter(gasto__owner=request.user, mes=mes)
    total_gasto_mes = 0

    for gasto_mes in gastos_mes:
        total_gasto_mes += gasto_mes.monto

    #Sumo todos los ingresos dentro del mes en curso
    ingresos_mes = IngresoMes.objects.filter(ingreso__owner=request.user, mes=mes)
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

def get_or_create_mes(user, year, month):
    mes, created = Mes.objects.get_or_create(
        owner=user,
        year=year,
        month=month
    )
    
    return mes

def cambiar_estado_mes(request, codigo):
    if request.method == 'POST':
        mes_obj = get_object_or_404(Mes, codigo=codigo, owner=request.user)
        mes_obj.cerrado = not mes_obj.cerrado # Si está abierto lo cierra, y viceversa
        mes_obj.save()
        messages.success(request, f"Mes {'cerrado' if mes_obj.cerrado else 'abierto'} correctamente.")
    return redirect(request.META.get('HTTP_REFERER', 'successify:resumen'))

@login_required
def crear_subgasto_mes(request, gastomes_id):
    """Procesa el envío del formulario cuando el usuario decide guardar un subgasto nuevo"""
    if request.method == "POST":
        # Buscamos el GastoMes padre asegurando que pertenezca al usuario (a través del gasto)
        gasto_mes = get_object_or_404(GastoMes, id=gastomes_id, gasto__owner=request.user)
        
        nombre = request.POST.get('nombre', 'Sin registro').strip() or 'Sin registro'
        monto = request.POST.get('monto', '0.00')
        
        # El backend se encarga de validar el límite de 3 gracias al método save() que modificamos antes
        try:
            SubGastoMes.objects.create(
                gasto_mes=gasto_mes,
                nombre=nombre,
                monto=monto
            )
        except ValidationError:
            # Aquí podrías manejar un mensaje de error si excede los 3
            pass
            
        return redirect('successify:gasto', codigo=gasto_mes.gasto.codigo)

@login_required
def actualizar_subgasto(request, subgasto_id):
    """Actualiza o elimina (si borran el nombre/monto) un subgasto existente"""
    if request.method == "POST":
        subgasto = get_object_or_404(SubGastoMes, id=subgasto_id, gasto_mes__gasto__owner=request.user)
        
        nombre = request.POST.get('nombre', '').strip()
        monto = request.POST.get('monto', '0.00')
        
        # Si el usuario vacía el nombre o el monto, o si deseas un botón de eliminar, 
        # podemos interpretar un nombre vacío como una orden de eliminación
        if not nombre:
            subgasto.delete()
        else:
            subgasto.nombre = nombre
            subgasto.monto = monto
            subgasto.save()
            
        return redirect('successify:gasto', codigo=subgasto.gasto_mes.gasto.codigo)