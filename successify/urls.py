"""Define patrones de url para successify"""

from django.urls import path
from . import views

app_name = 'successify'
urlpatterns = [
    
    #Core

    #Index
    path('', views.index, name='index'),
    #Página resumen
    path('resumen/', views.resumen, name='resumen'),
    #Vista mes en modo panel con movimiento anexado
    path('mes/<str:codigo_mes>/<str:codigo_movimiento>/', views.mes, name='mes'),
    #Vista mes en modo panel, sin movimiento anexado
    path('panelmes/<str:codigo_mes>/', views.mes, name='mes_simple'),
    #Cambiar estado mes
    path('cambiar-estado-mes/<str:codigo>/', views.cambiar_estado_mes, name='cambiar_estado_mes'),
    #Página que muestra el balance del mes en curso
    path('balance/',views.balance, name='balance'),

    ### GASTOS

    #Categorías de gastos
    path('categorias_de_gastos/', views.categorias_de_gastos,name='categorias_de_gastos'),
    #Gastos, ordenados por categoría(descendente)
    path('gastos/',views.gastos, name='gastos'),
    #Gasto individual
    path('gasto/<str:codigo>/',views.gasto, name='gasto'),
    #Añadir un gasto nuevo
    path('nuevo_gasto/', views.nuevo_gasto, name='nuevo_gasto'),
    #Añadir gastomes desde la página gastos
    path('nuevo_gasto_mes/<str:codigo>', views.nuevo_gasto_mes, name='nuevo_gasto_mes'),
    #Editar un gasto
    path('editar_gasto/<str:codigo>/', views.editar_gasto, name='editar_gasto'),    
    #Eliminar GastoMes
    path('eliminar_gastomes/<str:codigo_gastomes>/', views.eliminar_gastomes, name='eliminar_gastomes'),
    #Eliminar un gasto
    path('eliminar_gasto/<str:codigo>',views.eliminar_gasto, name='eliminar_gasto'),
    
    ### INGRESOS

    #Categorías de ingresos
    path('categorias_de_ingresos/', views.categorias_de_ingresos,name='categorias_de_ingresos'),
    #Ingresos, ordenados por categoría(descendente)
    path('ingresos/',views.ingresos,name='ingresos'),
    #Individual
    path('ingreso/<str:codigo>/',views.ingreso, name='ingreso'),   
    #Añadir un ingreso nuevo
    path('nuevo_ingreso', views.nuevo_ingreso,name='nuevo_ingreso'),
    #Añadir ingresomes desde la página de ingresos
    path('nuevo_ingreso_mes/<str:codigo>', views.nuevo_ingreso_mes, name='nuevo_ingreso_mes'),
    #Editar un ingreso
    path('editar_ingreso/<str:codigo>/',views.editar_ingreso,name='editar_ingreso'),
    #Eliminar IngresoMes
    path('eliminar_ingresomes/<str:codigo_ingresomes>/', views.eliminar_ingresomes, name='eliminar_ingresomes'), 
    #Eliminar un ingreso
    path('eliminar_ingreso/<str:codigo>', views.eliminar_ingreso, name='eliminar_ingreso'),




]

