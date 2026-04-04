from django.contrib import admin
from django.urls import path
from django.contrib.auth import views as auth_views
from django.conf import settings
from django.conf.urls.static import static

from gestion.views import (
    dashboard,
    detalle_ficha,
    actualizar_ficha,
    nuevo_ingreso,
    editar_datos_recepcion,
    crear_usuario,
    generar_pdf_ingreso,
    inventario,
    reportes_ganancias,
    gestion_usuarios,
    eliminar_usuario,
    generar_pdf_stock_total,
    generar_pdf_pedidos,
    eliminar_repuesto,
    eliminar_cliente,
    eliminar_ficha,
    papelera_fichas,
    restaurar_ficha,
    eliminar_permanente_ficha,
    editar_repuesto,
    eliminar_registro_reporte,
    reenviar_email_ingreso,
)

urlpatterns = [
    path('admin/', admin.site.urls),
    # --- AUTENTICACIÓN ---
    path('login/', auth_views.LoginView.as_view(), name='login'),
    path('logout/', auth_views.LogoutView.as_view(), name='logout'),
    # --- GESTIÓN DE USUARIOS (PERSONAL) ---
    path('usuarios/', gestion_usuarios, name='gestion_usuarios'),
    path('crear-usuario/', crear_usuario, name='crear_usuario'),
    path('usuarios/eliminar/<int:user_id>/', eliminar_usuario, name='eliminar_usuario'),
    # --- SISTEMA DE FICHAS (CORE) ---
    path('', dashboard, name='dashboard'),
    path('nuevo-ingreso/', nuevo_ingreso, name='nuevo_ingreso'),
    path('ficha/<int:ficha_id>/', detalle_ficha, name='detalle_ficha'),
    path('ficha/<int:ficha_id>/actualizar/', actualizar_ficha, name='actualizar_ficha'),
    path('ficha/<int:ficha_id>/editar-recepcion/', editar_datos_recepcion, name='editar_datos_recepcion'),
    path('ficha/<int:ficha_id>/pdf/', generar_pdf_ingreso, name='pdf_ingreso'),
    path('ficha/<int:ficha_id>/reenviar-email/', reenviar_email_ingreso, name='reenviar_email_ingreso'),
    path('ficha/eliminar/<int:ficha_id>/', eliminar_ficha, name='eliminar_ficha'),
    # --- PAPELERA Y BORRADOS ---
    path('papelera/', papelera_fichas, name='papelera_fichas'),
    path('papelera/restaurar/<int:ficha_id>/', restaurar_ficha, name='restaurar_ficha'),
    path('papelera/eliminar-definitivo/<int:ficha_id>/', eliminar_permanente_ficha, name='eliminar_definitivo'),
    # --- INVENTARIO Y STOCK ---
    path('inventario/', inventario, name='inventario'),
    path('inventario/editar/<int:repuesto_id>/', editar_repuesto, name='editar_repuesto'),
    path('inventario/eliminar/<int:repuesto_id>/', eliminar_repuesto, name='eliminar_repuesto'),
    path('inventario/total/', generar_pdf_stock_total, name='pdf_stock_total'),
    path('inventario/pedidos/', generar_pdf_pedidos, name='pdf_pedidos'),
    # --- CLIENTES ---
    path('cliente/eliminar/<int:cliente_id>/', eliminar_cliente, name='eliminar_cliente'),
    # --- REPORTES Y FINANZAS ---
    path('reportes/', reportes_ganancias, name='reportes'),
    path('reportes/eliminar/<int:ficha_id>/', eliminar_registro_reporte, name='eliminar_registro_reporte'),
]

if settings.DEBUG:
    urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)