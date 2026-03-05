from django.db import models
from django.contrib.auth.models import User
from PIL import Image
import os

# 1. Tabla de Clientes
class Cliente(models.Model):
    nombre_apellido = models.CharField(max_length=200)
    dni = models.CharField(max_length=20, unique=True)
    telefono = models.CharField(max_length=20)
    email = models.EmailField()

    def __str__(self):
        return f"{self.id:04d} - {self.nombre_apellido}"

# 2. Tabla de Equipos
class Equipo(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE, related_name='equipos')
    tipo = models.CharField(max_length=50) # Celular, Notebook, etc.
    marca_modelo = models.CharField(max_length=100)
    identificador = models.CharField(max_length=50, help_text="IMEI o Número de Serie")
    password = models.CharField(max_length=50, blank=True, null=True)

    def __str__(self):
        return f"{self.marca_modelo} ({self.identificador})"

# 3. Tabla de Stock de Repuestos
class Repuesto(models.Model):
    nombre = models.CharField(max_length=100)
    descripcion = models.TextField(blank=True)
    cantidad = models.IntegerField(default=0)
    stock_minimo = models.IntegerField(default=2)
    precio_costo = models.DecimalField(max_digits=10, decimal_places=2)
    precio_venta_sugerido = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.nombre} ({self.cantidad} unidades)"

    @property
    def necesita_reposicion(self):
        return self.cantidad <= self.stock_minimo

# 4. Tabla de Fichas de Reparación
class Ficha(models.Model):
    ESTADOS = [
        ('ING', 'Ingresado'),
        ('DIA', 'En Diagnóstico'),
        ('APR', 'Esperando Aprobación'),
        ('REP', 'En Reparación'),
        ('LST', 'Reparado'),
        ('NRE', 'No Reparado'),
        ('REJ', 'Presupuesto Rechazado'),
        ('ENT', 'Entregado'),
        ('ABD', 'Abandonado'),
    ]
    
    equipo = models.ForeignKey(Equipo, on_delete=models.CASCADE)
    tecnico = models.ForeignKey(User, on_delete=models.SET_NULL, null=True)
    estado = models.CharField(max_length=3, choices=ESTADOS, default='ING')
    falla_cliente = models.TextField()
    obs_recepcion = models.TextField(help_text="Estado físico y accesorios")
    
    # --- CAMPOS PARA LA PAPELERA (BORRADO LÓGICO) ---
    eliminado = models.BooleanField(default=False) 
    fecha_eliminacion = models.DateTimeField(null=True, blank=True)
    
    # Campo para vincular un repuesto principal del stock directamente
    repuesto_stock = models.ForeignKey(Repuesto, on_delete=models.SET_NULL, null=True, blank=True, related_name='fichas_asignadas')
    
    # Costos consolidados para facturación rápida
    costo_repuesto = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    costo_mo = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    resumen_trabajo = models.TextField(blank=True)
    
    fecha_ingreso = models.DateTimeField(auto_now_add=True)

    @property
    def codigo_compuesto(self):
        return f"{self.equipo.cliente.id:04d}-{self.id:04d}"

    def __str__(self):
        # Si está eliminada, agregamos el prefijo visual
        prefix = "[ELIMINADA] " if self.eliminado else ""
        return f"{prefix}{self.codigo_compuesto} - {self.equipo.marca_modelo}"

# 5. Detalle de Repuestos Usados
class RepuestoUtilizado(models.Model):
    ficha = models.ForeignKey(Ficha, on_delete=models.CASCADE, related_name='repuestos_usados')
    repuesto = models.ForeignKey(Repuesto, on_delete=models.CASCADE)
    cantidad = models.IntegerField(default=1)
    precio_al_momento = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.repuesto.nombre} en Ficha {self.ficha.id}"

# 6. Tabla de Fotos
class FotoFicha(models.Model):
    ficha = models.ForeignKey(Ficha, on_delete=models.CASCADE, related_name='fotos')
    imagen = models.ImageField(upload_to='fotos/%Y/%m/%d/')
    descripcion = models.CharField(max_length=100, blank=True)

    def save(self, *args, **kwargs):
        super().save(*args, **kwargs)
        if self.imagen:
            img = Image.open(self.imagen.path)
            if img.height > 1080 or img.width > 1080:
                output_size = (1080, 1080)
                img.thumbnail(output_size)
                img.save(self.imagen.path, quality=80, optimize=True)
