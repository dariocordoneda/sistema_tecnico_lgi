import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum, F
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail
from django.utils import timezone
from django.contrib.staticfiles.finders import find
import openpyxl 
from django.utils.timezone import make_aware
from datetime import datetime

# Modelos y Formularios
from .models import Cliente, Equipo, Ficha, FotoFicha, Repuesto
from .forms import RegistroUsuarioForm 

# ReportLab (PDF)
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from django.contrib.staticfiles.storage import staticfiles_storage

# --- 1. SEGURIDAD ---
def es_admin(user):
    """Solo el Superusuario tiene acceso a funciones críticas."""
    return user.is_authenticated and user.is_superuser

# --- 2. GESTIÓN DE USUARIOS ---
@login_required
@user_passes_test(es_admin)
def gestion_usuarios(request):
    usuarios = User.objects.all().order_by('-is_superuser', 'username')
    return render(request, 'gestion/usuarios.html', {'usuarios': usuarios})

@login_required
@user_passes_test(es_admin)
def crear_usuario(request):
    if request.method == 'POST':
        form = RegistroUsuarioForm(request.POST)
        if form.is_valid():
            user = form.save(commit=False)
            if form.cleaned_data.get('es_administrador'):
                user.is_staff = True
                user.is_superuser = True
            else:
                user.is_staff = False
                user.is_superuser = False
            user.save()
            return redirect('gestion_usuarios')
    else:
        form = RegistroUsuarioForm()
    return render(request, 'registration/crear_usuario.html', {'form': form})

@login_required
@user_passes_test(es_admin)
def eliminar_usuario(request, user_id):
    if request.user.id == user_id:
        return redirect('gestion_usuarios')
    usuario = get_object_or_404(User, id=user_id)
    usuario.delete()
    return redirect('gestion_usuarios')

# --- 3. DASHBOARD Y FICHAS ---
@login_required
def dashboard(request):
    fichas = Ficha.objects.filter(eliminado=False).order_by('-fecha_ingreso')
    busqueda = request.GET.get('buscar')
    filtro_estado = request.GET.get('estado')
    
    if filtro_estado:
        fichas = fichas.filter(estado=filtro_estado)
    if busqueda:
        fichas = fichas.filter(
            Q(equipo__cliente__nombre_apellido__icontains=busqueda) |
            Q(equipo__marca_modelo__icontains=busqueda) |
            Q(equipo__identificador__icontains=busqueda)
        )

    stats = {
        'total': Ficha.objects.filter(eliminado=False).count(),
        'ingresados': Ficha.objects.filter(estado='ING', eliminado=False).count(),
        'diagnostico': Ficha.objects.filter(estado='DIA', eliminado=False).count(),
        'reparando': Ficha.objects.filter(estado='REP', eliminado=False).count(),
        'listos': Ficha.objects.filter(estado='LST', eliminado=False).count(),
        'abandonados': Ficha.objects.filter(estado='ABD', eliminado=False).count(),
    }
    return render(request, 'gestion/dashboard.html', {'fichas': fichas, 'stats': stats})

@login_required
def detalle_ficha(request, ficha_id):
    ficha = get_object_or_404(Ficha, id=ficha_id)
    repuestos = Repuesto.objects.filter(cantidad__gt=0) | Repuesto.objects.filter(id=ficha.repuesto_stock_id)
    return render(request, 'gestion/detalle.html', {
        'ficha': ficha, 
        'repuestos_disponibles': repuestos.distinct()
    })

@login_required
def actualizar_ficha(request, ficha_id):
    ficha = get_object_or_404(Ficha, id=ficha_id)
    if request.method == 'POST':
        ficha.estado = request.POST.get('estado')
        ficha.costo_mo = request.POST.get('costo_mo') or 0
        ficha.resumen_trabajo = request.POST.get('resumen_trabajo')
        
        repuesto_id = request.POST.get('repuesto_seleccionado')
        if repuesto_id:
            nuevo_repuesto = get_object_or_404(Repuesto, id=repuesto_id)
            if ficha.repuesto_stock != nuevo_repuesto:
                if ficha.repuesto_stock:
                    ficha.repuesto_stock.cantidad += 1
                    ficha.repuesto_stock.save()
                nuevo_repuesto.cantidad -= 1
                nuevo_repuesto.save()
                ficha.repuesto_stock = nuevo_repuesto
                ficha.costo_repuesto = nuevo_repuesto.precio_venta_sugerido
        else:
            if ficha.repuesto_stock:
                ficha.repuesto_stock.cantidad += 1
                ficha.repuesto_stock.save()
                ficha.repuesto_stock = None
        
        if request.POST.get('costo_repuesto'):
            ficha.costo_repuesto = request.POST.get('costo_repuesto')
        ficha.save()
    return redirect('detalle_ficha', ficha_id=ficha_id)

@login_required
def editar_datos_recepcion(request, ficha_id):
    ficha = get_object_or_404(Ficha, id=ficha_id)
    if request.method == 'POST':
        cliente = ficha.equipo.cliente
        cliente.nombre_apellido = request.POST.get('nombre_cliente')
        cliente.telefono = request.POST.get('telefono_cliente')
        cliente.email = request.POST.get('email_cliente')
        cliente.save()
        
        equipo = ficha.equipo
        equipo.marca_modelo = request.POST.get('marca_modelo')
        equipo.identificador = request.POST.get('identificador')
        equipo.password = request.POST.get('password')
        equipo.save()
    return redirect('detalle_ficha', ficha_id=ficha_id)

@login_required
def nuevo_ingreso(request):
    clientes = Cliente.objects.all().order_by('nombre_apellido')
    cliente_id = request.GET.get('cliente_id')
    cliente_seleccionado = get_object_or_404(Cliente, id=cliente_id) if cliente_id else None

    if request.method == 'POST':
        if cliente_seleccionado:
            cliente = cliente_seleccionado
            cliente.telefono = request.POST.get('telefono')
            cliente.email = request.POST.get('email')
            cliente.save()
        else:
            cliente = Cliente.objects.create(
                nombre_apellido=request.POST.get('nombre_apellido'),
                dni=request.POST.get('dni'),
                telefono=request.POST.get('telefono'),
                email=request.POST.get('email')
            )
        
        equipo = Equipo.objects.create(
            cliente=cliente,
            marca_modelo=request.POST.get('marca_modelo'),
            identificador=request.POST.get('identificador'),
            password=request.POST.get('password')
        )
        
        ficha = Ficha.objects.create(
            equipo=equipo, falla_cliente=request.POST.get('falla_cliente'),
            obs_recepcion=request.POST.get('obs_recepcion'), estado='ING'
        )
        
        for f in request.FILES.getlist('fotos'):
            FotoFicha.objects.create(ficha=ficha, imagen=f)

        if cliente.email:
            try:
                asunto = f"Aviso de Ingreso #{ficha.codigo_compuesto} - LGI Electrónics"
                cuerpo = (
                    f"Hola {cliente.nombre_apellido},\n\n"
                    f"Este es un aviso automático de LGI Electrónics. Hemos registrado el ingreso de tu equipo en nuestro sistema:\n\n"
                    f"- Orden Nro: {ficha.codigo_compuesto}\n"
                    f"- Equipo: {equipo.marca_modelo} / {equipo.identificador}\n"
                    f"- Falla reportada: {ficha.falla_cliente}\n\n"
                    f"Te notificaremos por medio de Whatsapp al numero telefonico informado en la orden cuando el equipo pase a estado 'LISTO'.\n\n"
                    f"Ante cualquier duda/consulta se puede comunicar al tel: 3624-605132 Lun-Vier de 8hs a 20hs.\n\n"
                    f"Recordatorio legal: Transcurridos los 90 días de la notificación de retiro, el equipo se considerará en abandono (Art. 2587 CCCN).\n\n"
                    f"LGI Electrónics - Servicio Técnico Profesional.\n"
                    f"---\n"
                    f"Por favor, no respondas a este correo ya que es una casilla automática."
                )
                send_mail(asunto, cuerpo, settings.DEFAULT_FROM_EMAIL, [cliente.email])
            except: pass 

        return redirect('dashboard')
    return render(request, 'gestion/nuevo_ingreso.html', {'clientes': clientes, 'cliente_sel': cliente_seleccionado})



# --- 4. INVENTARIO (CON BUSCADOR Y EDICIÓN) ---
@login_required
def inventario(request):
    busqueda = request.GET.get('buscar')
    repuestos = Repuesto.objects.all().order_by('nombre')
    
    if busqueda:
        repuestos = repuestos.filter(Q(nombre__icontains=busqueda))

    if request.method == 'POST':
        if not request.user.is_superuser:
             return HttpResponse("No tenés permiso para crear repuestos", status=403)
             
        Repuesto.objects.create(
            nombre=request.POST.get('nombre'),
            cantidad=request.POST.get('cantidad'),
            precio_costo=request.POST.get('precio_costo'),
            precio_venta_sugerido=request.POST.get('precio_venta'),
            stock_minimo=request.POST.get('stock_minimo', 2)
        )
        return redirect('inventario')
    
    return render(request, 'gestion/inventario.html', {'repuestos': repuestos, 'busqueda': busqueda})

@login_required
@user_passes_test(es_admin)
def editar_repuesto(request, repuesto_id):
    repuesto = get_object_or_404(Repuesto, id=repuesto_id)
    if request.method == 'POST':
        repuesto.nombre = request.POST.get('nombre')
        repuesto.cantidad = request.POST.get('cantidad')
        repuesto.precio_costo = request.POST.get('precio_costo')
        repuesto.precio_venta_sugerido = request.POST.get('precio_venta')
        repuesto.stock_minimo = request.POST.get('stock_minimo')
        repuesto.save()
        return redirect('inventario')
    return render(request, 'gestion/editar_repuesto.html', {'repuesto': repuesto})

@login_required
@user_passes_test(es_admin)
def eliminar_repuesto(request, repuesto_id):
    repuesto = get_object_or_404(Repuesto, id=repuesto_id)
    repuesto.delete()
    return redirect('inventario')

# --- 5. PAPELERA ---
@login_required
@user_passes_test(es_admin)
def eliminar_ficha(request, ficha_id):
    ficha = get_object_or_404(Ficha, id=ficha_id)
    ficha.eliminado = True
    ficha.fecha_eliminacion = timezone.now()
    ficha.save()
    return redirect('dashboard')

@login_required
@user_passes_test(es_admin)
def papelera_fichas(request):
    fichas_borradas = Ficha.objects.filter(eliminado=True).order_by('-fecha_eliminacion')
    return render(request, 'gestion/papelera.html', {'fichas': fichas_borradas})

@login_required
@user_passes_test(es_admin)
def restaurar_ficha(request, ficha_id):
    ficha = get_object_or_404(Ficha, id=ficha_id)
    ficha.eliminado = False
    ficha.fecha_eliminacion = None
    ficha.save()
    return redirect('papelera_fichas')

@login_required
@user_passes_test(es_admin)
def eliminar_permanente_ficha(request, ficha_id):
    ficha = get_object_or_404(Ficha, id=ficha_id)
    ficha.delete()
    return redirect('papelera_fichas')

@login_required
@user_passes_test(es_admin)
def eliminar_cliente(request, cliente_id):
    cliente = get_object_or_404(Cliente, id=cliente_id)
    cliente.delete()
    return redirect('dashboard')

# --- 6. REPORTES Y PDF ---
@login_required
@user_passes_test(es_admin)
def reportes_ganancias(request):
    # 1. Capturamos las fechas
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')
    
    fichas = Ficha.objects.filter(estado='ENT', eliminado=False).order_by('-fecha_ingreso')

    # Validación: Solo filtramos si AMBAS fechas tienen contenido y no son "None" o vacías
    if fecha_inicio and fecha_fin and fecha_inicio != 'None' and fecha_fin != 'None':
        try:
            fichas = fichas.filter(fecha_ingreso__range=[fecha_inicio, f"{fecha_fin} 23:59:59"])
        except ValidationError:
            # Si el formato de fecha es basura, no filtramos nada para evitar el crash
            pass

    # 2. Exportación a Excel
    if 'exportar' in request.GET:
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Reporte_Ganancias_LGI.xlsx"'
        
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Ganancias"
        
        # Cabeceras
        ws.append(['Fecha Ingreso', 'Código', 'Cliente', 'Equipo', 'Mano de Obra', 'Repuesto', 'Total'])
        
        for f in fichas:
            # Usamos getattr o or 0 para evitar errores si algún costo es None en la DB
            mo = f.costo_mo or 0
            rep = f.costo_repuesto or 0
            ws.append([
                f.fecha_ingreso.strftime('%d/%m/%Y') if f.fecha_ingreso else '',
                f.codigo_compuesto,
                f.equipo.cliente.nombre_apellido,
                f.equipo.marca_modelo,
                mo,
                rep,
                mo + rep
            ])
            
        wb.save(response)
        return response

    # ... (Resto de tu lógica de cálculos: total_mo, total_rep, promedio, etc.)
    # Asegurate de pasar 'fichas' (el queryset) al context para el template
    
    # Cálculos rápidos
    total_mo = fichas.aggregate(Sum('costo_mo'))['costo_mo__sum'] or 0
    total_rep = fichas.aggregate(Sum('costo_repuesto'))['costo_repuesto__sum'] or 0
    total_ingresos = total_mo + total_rep
    count = fichas.count()
    promedio = total_ingresos / count if count > 0 else 0

    return render(request, 'gestion/reportes.html', {
        'fichas': fichas,
        'total_mo': total_mo, 
        'total_repuestos_venta': total_rep,
        'total_ingresos': total_ingresos, 
        'fichas_count': count,
        'promedio': round(promedio, 2),
        'fecha_inicio': fecha_inicio if fecha_inicio != 'None' else '',
        'fecha_fin': fecha_fin if fecha_fin != 'None' else ''
    })
    
 
@login_required
@user_passes_test(es_admin)
def eliminar_registro_reporte(request, ficha_id):
    """
    Elimina (borrado lógico) una ficha desde el panel de reportes.
    Solo accesible por el usuario root/superuser.
    """
    # Verificación extra de seguridad
    if not request.user.is_superuser:
        return HttpResponse("No tenés permisos para eliminar registros contables.", status=403)
    
    # Obtenemos la ficha o tiramos 404 si no existe
    ficha = get_object_or_404(Ficha, id=ficha_id)
    
    # Aplicamos borrado lógico para que no aparezca en ganancias ni dashboard
    ficha.eliminado = True
    ficha.fecha_eliminacion = timezone.now()
    ficha.save()
    
    # Redirigimos de vuelta a la página de reportes
    return redirect('reportes')
@login_required
def generar_pdf_ingreso(request, ficha_id):
    ficha = get_object_or_404(Ficha, id=ficha_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Orden_{ficha.codigo_compuesto}.pdf"'
    
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4
   # --- AJUSTE LOGO MAC DEFINITIVO ---
    # Si el Nav lo muestra, esta ruta es la que Django reconoce.
    # Usamos find() para obtener la ruta del sistema de archivos.
    logo_path = find('img/logo.png')
    
    if logo_path:
        try:
            # Dibujamos el logo. Al usar find() obtenemos la ruta absoluta que ReportLab necesita.
            p.drawImage(logo_path, 1.5 * cm, height - 11.3 * cm, width=6 * cm, preserveAspectRatio=True, mask='auto')
        except:
            pass
    # ----------------------------------
    # Encabezado Orden
    p.rect(width - 7.5 * cm, height - 3.2 * cm, 5.5 * cm, 1.6 * cm)
    p.setFont("Helvetica-Bold", 12)
    p.drawCentredString(width - 4.75 * cm, height - 2.2 * cm, "ORDEN DE TRABAJO")
    p.setFont("Helvetica-Bold", 16)
    p.drawCentredString(width - 4.75 * cm, height - 2.9 * cm, f"#{ficha.codigo_compuesto}")
    
    p.setFont("Helvetica", 10)
    p.drawRightString(width - 2 * cm, height - 4.2 * cm, "Resistencia, Chaco | Tel: 3624-605132")
    p.line(1.5 * cm, height - 4.5 * cm, width - 1.5 * cm, height - 4.5 * cm)
    
    # Datos Principales
    y = height - 6 * cm
    p.setFont("Helvetica-Bold", 11); p.drawString(2 * cm, y, "CLIENTE:"); p.setFont("Helvetica", 11); p.drawString(6 * cm, y, f"{ficha.equipo.cliente.nombre_apellido}")
    y -= 1 * cm
    p.setFont("Helvetica-Bold", 11); p.drawString(2 * cm, y, "EQUIPO:"); p.setFont("Helvetica", 11); p.drawString(6 * cm, y, f"{ficha.equipo.marca_modelo}")
    y -= 1 * cm
    p.setFont("Helvetica-Bold", 11); p.drawString(2 * cm, y, "IMEI / SN:"); p.setFont("Helvetica", 11); p.drawString(6 * cm, y, f"{ficha.equipo.identificador}")
    y -= 1 * cm
    p.setFont("Helvetica-Bold", 11); p.drawString(2 * cm, y, "FALLA:"); p.setFont("Helvetica", 11); p.drawString(6 * cm, y, f"{ficha.falla_cliente}")
    
    # RECUADRO DE TÉRMINOS AJUSTADO (Simetría mejorada)
    p.setStrokeColor(colors.black)
    p.rect(1.5 * cm, 4.5 * cm, width - 3 * cm, 4 * cm)
    p.setFont("Helvetica-Bold", 10); p.drawString(2 * cm, 8.1 * cm, "TÉRMINOS Y CONDICIONES:")
    
    text = p.beginText(2 * cm, 7.5 * cm); text.setFont("Helvetica", 10); text.setLeading(14)
    lineas = [
        "• El presupuesto tiene una validez de 10 días corridos.",
        "• La garantía es de 90 días sobre el trabajo realizado.",
        "• Transcurridos 90 días del aviso de retiro, el equipo se considera en abandono.",
        "• Es OBLIGATORIO presentar este comprobante para retirar el equipo.",
        "• LGI Electrónics no se responsabiliza por la pérdida de datos en el equipo."
    ]
    for l in lineas: text.textLine(l)
    p.drawText(text)
    
    # Firmas centradas
    p.line(2.5 * cm, 2.5 * cm, 8.5 * cm, 2.5 * cm); p.drawCentredString(5.5 * cm, 2 * cm, "Firma del Cliente")
    p.line(width - 8.5 * cm, 2.5 * cm, width - 2.5 * cm, 2.5 * cm); p.drawCentredString(width - 5.5 * cm, 2 * cm, "LGI Electrónics")
    
    p.showPage(); p.save()
    return response



@login_required
@user_passes_test(es_admin)
def generar_pdf_pedidos(request):
    """
    Mejora visual del PDF de pedidos respetando el flujo de selección previo
    en preparar_pedido.html.
    """
    # Recuperamos los repuestos bajo stock para la vista previa
    repuestos_bajo_stock = Repuesto.objects.filter(cantidad__lte=F('stock_minimo'))
    
    if request.method == 'POST':
        # Tomamos los ítems que vos marcaste en el checkbox del HTML
        ids_seleccionados = request.POST.getlist('items_seleccionados')
        
        if not ids_seleccionados:
            return redirect('pdf_pedidos')

        # Iniciamos la respuesta PDF
        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Pedido_Repuestos_LGI.pdf"'
        
        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4
        
        # --- DISEÑO PROFESIONAL (MEJORA SOLICITADA) ---
        # 1. Logo LGI
        logo_path = find('img/logo.png')
        if logo_path:
            try:
                p.drawImage(logo_path, 1.5 * cm, 18 * cm, width=5 * cm, preserveAspectRatio=True, mask='auto')
            except:
                pass

        # 2. Título y Fecha
        p.setFont("Helvetica-Bold", 16)
        p.drawString(10.5 * cm, 25.5 * cm, "ORDEN DE COMPRA / PEDIDO")
        
        p.setFont("Helvetica", 10)
        p.drawString(1.5 * cm, 24.7 * cm, f"Fecha de emisión: {timezone.now().strftime('%d/%m/%Y')}")
        
        # Línea de encabezado
        p.setStrokeColor(colors.black)
        p.setLineWidth(1)
        p.line(1.5 * cm, 24.5 * cm, width - 1.5 * cm, 24.5 * cm)
        
        # 3. Cabecera de Tabla
        y = 23.5 * cm
        p.setFont("Helvetica-Bold", 11)
        p.drawString(2 * cm, y, "DETALLE DEL REPUESTO / INSUMO")
        p.drawCentredString(width - 3 * cm, y, "CANTIDAD")
        
        y -= 0.8 * cm
        p.setFont("Helvetica", 11)
        
        # 4. Listado de repuestos seleccionados
        for r_id in ids_seleccionados:
            repuesto = get_object_or_404(Repuesto, id=r_id)
            # Obtenemos la cantidad que editaste manualmente en el HTML
            cantidad_final = request.POST.get(f'cantidad_{r_id}', 1)
            
            # Línea divisoria tenue
            p.setStrokeColor(colors.lightgrey)
            p.setLineWidth(0.5)
            p.line(1.5 * cm, y - 0.2 * cm, width - 1.5 * cm, y - 0.2 * cm)
            
            # Datos (Nombre y Cantidad)
            p.setStrokeColor(colors.black)
            p.drawString(2 * cm, y, repuesto.nombre)
            
            p.setFont("Helvetica-Bold", 12)
            p.drawCentredString(width - 3 * cm, y, f"x {cantidad_final}")
            p.setFont("Helvetica", 11)
            
            y -= 1 * cm
            
            # Control de fin de página
            if y < 3 * cm:
                p.showPage()
                y = 26 * cm
                p.setFont("Helvetica", 11)

        # 5. Pie de página fijo
        p.setStrokeColor(colors.black)
        p.setLineWidth(1)
        p.line(1.5 * cm, 2.5 * cm, width - 1.5 * cm, 2.5 * cm)
        
        p.setFont("Helvetica-Oblique", 9)
        p.drawCentredString(width/2, 2 * cm, "LGI Electrónics - Servicio Técnico Profesional - Resistencia, Chaco")
        
        p.save()
        return response

    # Retorno al template original con la variable exacta que usás
    return render(request, 'gestion/preparar_pedido.html', {'repuestos_bajo_stock': repuestos_bajo_stock})

@login_required
def generar_pdf_stock_total(request):
    """Planilla de control físico con formato de tabla profesional."""
    repuestos = Repuesto.objects.all().order_by('nombre')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Stock_Fisico.pdf"'
    p = canvas.Canvas(response, pagesize=A4); width, height = A4
    
    def encabezado(canvas_obj, pag):
        canvas_obj.setFont("Helvetica-Bold", 14)
        canvas_obj.drawString(1.5 * cm, height - 2 * cm, "PLANILLA DE CONTROL DE STOCK FÍSICO")
        canvas_obj.setFont("Helvetica", 9)
        canvas_obj.drawString(1.5 * cm, height - 2.5 * cm, f"Fecha: {timezone.now().strftime('%d/%m/%Y')} | Pág: {pag}")
        canvas_obj.line(1.5 * cm, height - 2.7 * cm, width - 1.5 * cm, height - 2.7 * cm)
        y_ini = height - 3.2 * cm
        canvas_obj.setFont("Helvetica-Bold", 10)
        canvas_obj.drawString(1.8 * cm, y_ini, "DESCRIPCIÓN")
        canvas_obj.drawCentredString(14 * cm, y_ini, "SISTEMA")
        canvas_obj.drawCentredString(17 * cm, y_ini, "REAL")
        return y_ini - 0.5 * cm

    y = encabezado(p, 1)
    pag = 1
    for r in repuestos:
        p.setFont("Helvetica", 9)
        p.drawString(1.8 * cm, y, r.nombre[:60])
        p.drawCentredString(14 * cm, y, str(r.cantidad))
        p.rect(15.5 * cm, y - 0.1 * cm, 3 * cm, 0.5 * cm)
        y -= 0.8 * cm
        if y < 2 * cm:
            p.showPage(); pag += 1; y = encabezado(p, pag)
            
    p.save(); return response
