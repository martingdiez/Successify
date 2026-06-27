from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError


#MES

class Mes(models.Model):
    owner = models.ForeignKey(User, on_delete=models.CASCADE)

    year = models.IntegerField()
    month = models.IntegerField()

    cerrado = models.BooleanField(default=False)
    codigo = models.CharField(max_length=20,
                              blank=True, editable=False)

    class Meta:
        verbose_name_plural = "Meses"
        unique_together = ("owner", "year", "month")

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        #Genera codigo con fecha
        if not self.codigo:

            self.codigo = f"{str(self.year)[-2:]}{self.month:02d}"
            super().save(update_fields=["codigo"])

    def __str__(self):
        return f"{self.codigo}"

# GASTOS
class CategoríaGasto(models.Model):
    """Una categoría de egreso de dinero"""
    nombre = models.CharField(max_length=100)
    date_added = models.DateTimeField(auto_now_add=True)
    es_fijo = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Categorías de gastos'

    def __str__(self):
        """Devuelve una representación del modelo como cadena."""
        return self.nombre

class Gasto(models.Model):
    categoria = models.ForeignKey(CategoríaGasto, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    
    nombre = models.CharField(max_length=50)
    codigo = models.CharField(max_length=20, unique=True,
                            blank=True, editable=False)

    presupuesto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        
        if not self.codigo:
            self.codigo = f"G{self.id}"
            super().save(update_fields=["codigo"])

        self.gastomes_set.filter(mes__cerrado=False).update(nombre=self.nombre, categoria=self.categoria.nombre)

    def __str__(self):
        return self.nombre

class GastoMes(models.Model):
    gasto = models.ForeignKey(Gasto, on_delete=models.SET_NULL, null=True)
    mes = models.ForeignKey(Mes, on_delete=models.CASCADE)
    
    nombre = models.CharField(max_length=50, null=True, blank=True)
    categoria = models.CharField(max_length=50, null=True, blank=True)

    codigo = models.CharField(max_length=20, unique=True,
                               blank=True, editable=False)    
    
    
    monto = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("gasto", "mes")
    
    def save(self, *args, **kwargs):

        #pk = Primary Key. Sirve para saber si estoy editando o creando
        if self.pk and self.mes.cerrado:
            raise ValidationError(
                "No se puede modificar un registro de un mes cerrado.")

        if self.gasto:
            self.nombre = self.gasto.nombre
            self.categoria = self.gasto.categoria.nombre

        super().save(*args, **kwargs)

        #Genera codigo fecha/gasto
        if not self.codigo:
            self.codigo = f"{self.mes.codigo}{self.gasto.codigo}"
            super().save(update_fields=["codigo"])

    def actualizar_monto_por_subgastos(self):
        """
        Si tiene subgastos, suma todos sus montos y actualiza el campo 'monto'.
        Si se eliminan todos los subgastos, mantiene su monto actual o pasa a 0.
        """
        # Obtenemos todos los subgastos relacionados usando el 'related_name'
        subgastos_qs = self.subgastos.all()
        
        if subgastos_qs.exists():
            # Sumamos todos los montos de sus hijos
            total = sum(subgasto.monto for subgasto in subgastos_qs)
            self.monto = total
            # Guardamos únicamente el campo monto para no disparar validaciones infinitas
            super().save(update_fields=['monto'])

    def __str__(self):
        return f"{self.codigo}: {self.monto}"
    
class SubGastoMes(models.Model):
    gasto_mes = models.ForeignKey(GastoMes, on_delete=models.CASCADE, related_name='subgastos')
    nombre = models.CharField(max_length=100, default="Sin registro")
    monto = models.DecimalField(max_digits=10, decimal_places=2, default=0.00)

    def save(self, *args, **kwargs):
        # Validación de mes cerrado heredada del padre
        if self.gasto_mes.mes.cerrado:
            raise ValidationError("No se puede modificar un subregistro de un mes cerrado.")
        
        # Forzar el límite máximo de 3 subgastos en el backend al crear uno nuevo
        if not self.pk and self.gasto_mes.subgastos.count() >= 3:
            raise ValidationError("Un gasto mensual no puede tener más de 3 subregistros.")
        
        super().save(*args, **kwargs)
        # Una vez guardado el subgasto, actualizamos el monto del GastoMes padre
        self.gasto_mes.actualizar_monto_por_subgastos()

    def delete(self, *args, **kwargs):
        if self.gasto_mes.mes.cerrado:
            raise ValidationError("No se puede eliminar un subregistro de un mes cerrado.")
        
        gasto_mes_padre = self.gasto_mes
        super().delete(*args, **kwargs)
        # Al eliminar, también recalculamos el monto del padre
        gasto_mes_padre.actualizar_monto_por_subgastos()

    def __str__(self):
        return f"{self.nombre}: {self.monto} (Padre: {self.gasto_mes.codigo})"


#INGRESOS

class CategoriaIngreso(models.Model):
    """Una categoría de ingreso de dinero"""
    nombre = models.CharField(max_length=100)
    date_added = models.DateTimeField(auto_now_add=True)
    es_fijo = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Categorías de ingresos'
    
    def __str__(self):
        return self.nombre
    
class Ingreso(models.Model):
    categoria = models.ForeignKey(CategoriaIngreso, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    nombre = models.CharField(max_length=50)
    codigo = models.CharField(max_length=20, unique=True,
                               blank=True, editable=False)

    presupuesto = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)

        if not self.codigo:
            self.codigo = f"I{self.id}"
            super().save(update_fields=["codigo"])


    def __str__(self):
        return self.nombre
    
class IngresoMes(models.Model):
    ingreso = models.ForeignKey(Ingreso, on_delete=models.SET_NULL, null=True)
    mes = models.ForeignKey(Mes, on_delete=models.CASCADE)

    nombre = models.CharField(max_length=50, null=True, blank=True)
    categoria = models.CharField(max_length=50, null=True, blank=True)

    codigo = models.CharField(max_length=20, unique=True, 
                              blank=True, editable=False)

    monto = models.DecimalField(max_digits=10, decimal_places=2)

    class Meta:
        unique_together = ("ingreso", "mes")

    def save(self, *args, **kwargs):

        if self.pk and self.mes.cerrado:
            raise ValidationError(
                "No se puede modificar un registro de un mes cerrado.")
        
        if self.ingreso:
            self.nombre = self.ingreso.nombre
            self.categoria = self.ingreso.categoria.nombre
        
        super().save(*args, **kwargs)
        #Genera codigo fecha/ingreso
        if not self.codigo:
            self.codigo = f"{self.mes.codigo}{self.ingreso.codigo}"
            super().save(update_fields=["codigo"])

    def __str__(self):
        return f"{self.codigo}: {self.monto}"


# Test de sincronización de Successify