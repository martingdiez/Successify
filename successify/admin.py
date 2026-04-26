from django.contrib import admin
from .models import CategoríaGasto,Gasto, CategoriaIngreso,Ingreso,Mes,GastoMes,IngresoMes

#Registre modelos aquí
admin.site.register(CategoríaGasto)

@admin.register(Gasto)
class GastoAdmin(admin.ModelAdmin):
    exclude = ("codigo",)
    readonly_fields = ("codigo",)

@admin.register(GastoMes)
class GastoMesAdmin(admin.ModelAdmin):
    exclude = ("codigo",)
    readonly_fields = ("codigo",)

admin.site.register(CategoriaIngreso)

@admin.register(Ingreso)
class IngresoAdmin(admin.ModelAdmin):
    exclude = ("codigo",)
    readonly_fields = ("codigo",)

@admin.register(IngresoMes)
class IngresoMesAdmin(admin.ModelAdmin):
    exclude = ("codigo",)
    readonly_fields = ("codigo",)

    
admin.site.register(Mes)



