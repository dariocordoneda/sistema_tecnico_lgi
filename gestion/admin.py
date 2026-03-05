from django.contrib import admin
from .models import Cliente, Equipo, Ficha, FotoFicha
from django.shortcuts import redirect

# Esto permite cargar fotos directamente dentro de la ficha sin salir de la pantalla
class FotoFichaInline(admin.TabularInline):
    model = FotoFicha
    extra = 3 # Te da 3 espacios para subir fotos de una

@admin.register(Ficha)
class FichaAdmin(admin.ModelAdmin):
    # Qué columnas ver en el listado principal
    list_display = ('codigo_compuesto', 'get_cliente', 'equipo', 'estado', 'fecha_ingreso')
    list_filter = ('estado', 'fecha_ingreso')
    search_fields = ('equipo__marca_modelo', 'equipo__cliente__nombre_apellido', 'id')
    inlines = [FotoFichaInline]

    def get_cliente(self, obj):
        return obj.equipo.cliente.nombre_apellido
    get_cliente.short_description = 'Cliente'
    
    def response_add(self, request, obj, post_url_continue=None):
        return redirect('/') # Redirige al Dashboard nuestro después de guardar

    def response_change(self, request, obj):
        return redirect('/') # Redirige al Dashboard después de editar

admin.site.register(Cliente)
admin.site.register(Equipo)
