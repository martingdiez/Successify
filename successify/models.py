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
    name = models.CharField(max_length=100)
    date_added = models.DateTimeField(auto_now_add=True)
    es_fijo = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Categorías de gastos'

    def __str__(self):
        """Devuelve una representación del modelo como cadena."""
        return self.name

class Gasto(models.Model):
    categoria = models.ForeignKey(CategoríaGasto, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    
    name = models.CharField(max_length=50)
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

        self.gastomes_set.filter(mes__cerrado=False).update(nombre=self.name)

    def __str__(self):
        return self.name

class GastoMes(models.Model):
    gasto = models.ForeignKey(Gasto, on_delete=models.SET_NULL, null=True)
    mes = models.ForeignKey(Mes, on_delete=models.CASCADE)
    
    nombre = models.CharField(max_length=50, null=True, blank=True)
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
            self.nombre = self.gasto.name

        super().save(*args, **kwargs)

        #Genera codigo fecha/gasto
        if not self.codigo:
            self.codigo = f"{self.mes.codigo}{self.gasto.codigo}"
            super().save(update_fields=["codigo"])

    def __str__(self):
        return f"{self.codigo}: {self.monto}"
    
#INGRESOS

class CategoriaIngreso(models.Model):
    """Una categoría de ingreso de dinero"""
    name = models.CharField(max_length=100)
    date_added = models.DateTimeField(auto_now_add=True)
    es_fijo = models.BooleanField(default=False)

    class Meta:
        verbose_name_plural = 'Categorías de ingresos'
    
    def __str__(self):
        return self.name
    
class Ingreso(models.Model):
    categoria = models.ForeignKey(CategoriaIngreso, on_delete=models.CASCADE)
    owner = models.ForeignKey(User, on_delete=models.CASCADE)
    name = models.CharField(max_length=50)
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
        return self.name
    
class IngresoMes(models.Model):
    ingreso = models.ForeignKey(Ingreso, on_delete=models.SET_NULL, null=True)
    mes = models.ForeignKey(Mes, on_delete=models.CASCADE)

    nombre = models.CharField(max_length=50, null=True, blank=True)
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
            self.nombre = self.ingreso.name
        
        super().save(*args, **kwargs)
        #Genera codigo fecha/ingreso
        if not self.codigo:
            self.codigo = f"{self.mes.codigo}{self.ingreso.codigo}"
            super().save(update_fields=["codigo"])

    def __str__(self):
        return f"{self.codigo}: {self.monto}"