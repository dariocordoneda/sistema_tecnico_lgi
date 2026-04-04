import os
from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse
from django.db.models import Q, Sum, F
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import User
from django.conf import settings
from django.core.mail import send_mail, EmailMultiAlternatives
from django.utils import timezone
from django.contrib.staticfiles.finders import find
import openpyxl
from django.utils.timezone import make_aware
from datetime import datetime

from .models import Cliente, Equipo, Ficha, FotoFicha, Repuesto
from .forms import RegistroUsuarioForm

from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import A4
from reportlab.lib.units import cm
from reportlab.lib import colors
from django.contrib.staticfiles.storage import staticfiles_storage


# --- HELPER: EMAIL HTML LGI ---
def _build_email_html(cliente, equipo, ficha):
    fecha = ficha.fecha_ingreso.strftime('%d/%m/%Y') if ficha.fecha_ingreso else ''
    return f"""<!DOCTYPE html>
<html lang="es">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1.0"></head>
<body style="margin:0;padding:0;background:#1a1a1a;font-family:Arial,sans-serif;">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#1a1a1a;padding:24px 16px;">
<tr><td align="center">
<table width="560" cellpadding="0" cellspacing="0" style="background:#ffffff;border-radius:12px;overflow:hidden;max-width:560px;width:100%;">
  <tr><td style="background:#111111;padding:28px 32px;">
    <table cellpadding="0" cellspacing="0"><tr>
      <td style="vertical-align:middle;padding-right:14px;">
        <table cellpadding="0" cellspacing="0"><tr><td style="width:48px;height:48px;background:#D4A017;text-align:center;vertical-align:middle;font-size:11px;font-weight:900;color:#111;letter-spacing:-1px;">LGI</td></tr></table>
      </td>
      <td style="vertical-align:middle;">
        <div style="font-size:20px;font-weight:700;color:#D4A017;letter-spacing:3px;text-transform:uppercase;line-height:1;">LGI ELECTRÓNICS</div>
        <div style="font-size:11px;color:#888;letter-spacing:2px;text-transform:uppercase;margin-top:3px;">Servicio Técnico Profesional</div>
      </td>
    </tr></table>
  </td></tr>
  <tr><td style="background:#D4A017;padding:10px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="font-size:12px;font-weight:700;color:#111;letter-spacing:2px;text-transform:uppercase;">Aviso de Ingreso</td>
      <td align="right"><span style="background:#111;color:#D4A017;font-size:12px;font-weight:700;padding:4px 12px;border-radius:4px;letter-spacing:1px;">#{ficha.codigo_compuesto}</span></td>
    </tr></table>
  </td></tr>
  <tr><td style="padding:28px 32px;">
    <p style="margin:0 0 18px;font-size:15px;color:#222;">Hola <strong>{cliente.nombre_apellido}</strong>,</p>
    <p style="margin:0 0 20px;font-size:14px;color:#444;line-height:1.7;">Hemos registrado el ingreso de tu equipo en nuestro sistema. A continuación encontrás los datos de tu orden:</p>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
    <tr><td style="background:#f8f8f8;border:1px solid #eee;border-left:4px solid #D4A017;border-radius:6px;padding:18px 20px;">
      <table width="100%" cellpadding="0" cellspacing="0" style="font-size:13px;">
        <tr><td style="color:#888;padding:5px 0;width:130px;">Orden Nro</td><td style="color:#111;font-weight:700;padding:5px 0;">#{ficha.codigo_compuesto}</td></tr>
        <tr><td style="color:#888;padding:5px 0;">Equipo</td><td style="color:#111;padding:5px 0;">{equipo.marca_modelo} / {equipo.identificador}</td></tr>
        <tr><td style="color:#888;padding:5px 0;vertical-align:top;">Falla reportada</td><td style="color:#111;padding:5px 0;">{ficha.falla_cliente}</td></tr>
        <tr><td style="color:#888;padding:5px 0;">Fecha de ingreso</td><td style="color:#111;padding:5px 0;">{fecha}</td></tr>
      </table>
    </td></tr></table>
    <table width="100%" cellpadding="0" cellspacing="0" style="margin:0 0 24px;">
    <tr><td style="background:#111;border-radius:6px;padding:16px 20px;">
      <table cellpadding="0" cellspacing="0"><tr>
        <td style="vertical-align:top;padding-right:12px;"><div style="width:20px;height:20px;background:#D4A017;border-radius:50%;text-align:center;line-height:20px;font-size:12px;font-weight:700;color:#111;">!</div></td>
        <td style="font-size:13px;color:#ccc;line-height:1.6;">Te avisaremos por <strong style="color:#D4A017;">WhatsApp</strong> cuando tu equipo esté listo para retirar. Asegurate de tener guardado el número: <strong style="color:#ffffff;">3624-605132</strong></td>
      </tr></table>
    </td></tr></table>
    <p style="margin:0 0 8px;font-size:13px;color:#666;line-height:1.6;">Podés comunicarte con nosotros de <strong>Lun a Vier de 8hs a 20hs</strong> al <strong>3624-605132</strong>.</p>
    <p style="margin:0;font-size:12px;color:#999;line-height:1.6;">Recordatorio legal: Transcurridos los 90 días de la notificación de retiro, el equipo se considerará en abandono (Art. 2587 CCCN).</p>
  </td></tr>
  <tr><td style="background:#111;padding:18px 32px;">
    <table width="100%" cellpadding="0" cellspacing="0"><tr>
      <td style="font-size:11px;color:#555;line-height:1.6;">Resistencia, Chaco<br><a href="https://lgi-electronics.netlify.app" style="color:#D4A017;text-decoration:none;">lgi-electronics.netlify.app</a></td>
      <td align="right" style="font-size:10px;color:#444;font-style:italic;line-height:1.6;">Casilla automática.<br>No respondas este correo.</td>
    </tr></table>
  </td></tr>
</table>
</td></tr></table>
</body></html>"""


def _build_email_texto(cliente, equipo, ficha):
    return (
        f"Hola {cliente.nombre_apellido},\n\n"
        f"Este es un aviso automático de LGI Electrónics. Hemos registrado el ingreso de tu equipo:\n\n"
        f"- Orden Nro: {ficha.codigo_compuesto}\n"
        f"- Equipo: {equipo.marca_modelo} / {equipo.identificador}\n"
        f"- Falla reportada: {ficha.falla_cliente}\n\n"
        f"Te notificaremos por WhatsApp cuando el equipo esté LISTO.\n\n"
        f"Consultas: 3624-605132 | Lun-Vier 8hs a 20hs.\n\n"
        f"Recordatorio: Transcurridos 90 días de la notificación de retiro, el equipo se considerará en abandono (Art. 2587 CCCN).\n\n"
        f"LGI Electrónics - Servicio Técnico Profesional.\n"
        f"---\nCasilla automática, no respondas este correo."
    )


def _enviar_email_lgi(cliente, equipo, ficha):
    asunto = f"Aviso de Ingreso #{ficha.codigo_compuesto} - LGI Electrónics"
    texto = _build_email_texto(cliente, equipo, ficha)
    html = _build_email_html(cliente, equipo, ficha)
    msg = EmailMultiAlternatives(asunto, texto, settings.DEFAULT_FROM_EMAIL, [cliente.email])
    msg.attach_alternative(html, "text/html")
    msg.send()


# --- 1. SEGURIDAD ---
def es_admin(user):
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
        cliente.nombre_apellido = request.POST.get('nombre_apellido')
        cliente.telefono = request.POST.get('telefono')
        cliente.email = request.POST.get('email')
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
                _enviar_email_lgi(cliente, equipo, ficha)
            except:
                pass

        return redirect('dashboard')
    return render(request, 'gestion/nuevo_ingreso.html', {'clientes': clientes, 'cliente_sel': cliente_seleccionado})


# --- 4. INVENTARIO ---
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
    fecha_inicio = request.GET.get('fecha_inicio')
    fecha_fin = request.GET.get('fecha_fin')

    fichas = Ficha.objects.filter(estado='ENT', eliminado=False).order_by('-fecha_ingreso')

    if fecha_inicio and fecha_fin and fecha_inicio != 'None' and fecha_fin != 'None':
        try:
            fichas = fichas.filter(fecha_ingreso__range=[fecha_inicio, f"{fecha_fin} 23:59:59"])
        except:
            pass

    if 'exportar' in request.GET:
        response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
        response['Content-Disposition'] = 'attachment; filename="Reporte_Ganancias_LGI.xlsx"'
        wb = openpyxl.Workbook()
        ws = wb.active
        ws.title = "Ganancias"
        ws.append(['Fecha Ingreso', 'Código', 'Cliente', 'Equipo', 'Mano de Obra', 'Repuesto', 'Total'])
        for f in fichas:
            mo = f.costo_mo or 0
            rep = f.costo_repuesto or 0
            ws.append([
                f.fecha_ingreso.strftime('%d/%m/%Y') if f.fecha_ingreso else '',
                f.codigo_compuesto, f.equipo.cliente.nombre_apellido,
                f.equipo.marca_modelo, mo, rep, mo + rep
            ])
        wb.save(response)
        return response

    total_mo = fichas.aggregate(Sum('costo_mo'))['costo_mo__sum'] or 0
    total_rep = fichas.aggregate(Sum('costo_repuesto'))['costo_repuesto__sum'] or 0
    total_ingresos = total_mo + total_rep
    count = fichas.count()
    promedio = total_ingresos / count if count > 0 else 0

    return render(request, 'gestion/reportes.html', {
        'fichas': fichas, 'total_mo': total_mo,
        'total_repuestos_venta': total_rep, 'total_ingresos': total_ingresos,
        'fichas_count': count, 'promedio': round(promedio, 2),
        'fecha_inicio': fecha_inicio if fecha_inicio != 'None' else '',
        'fecha_fin': fecha_fin if fecha_fin != 'None' else ''
    })

@login_required
@user_passes_test(es_admin)
def eliminar_registro_reporte(request, ficha_id):
    if not request.user.is_superuser:
        return HttpResponse("No tenés permisos para eliminar registros contables.", status=403)
    ficha = get_object_or_404(Ficha, id=ficha_id)
    ficha.eliminado = True
    ficha.fecha_eliminacion = timezone.now()
    ficha.save()
    return redirect('reportes')

@login_required
def generar_pdf_ingreso(request, ficha_id):
    ficha = get_object_or_404(Ficha, id=ficha_id)
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = f'inline; filename="Orden_{ficha.codigo_compuesto}.pdf"'

    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    # Colores de marca
    GOLD   = colors.HexColor('#D4A017')
    BLACK  = colors.HexColor('#111111')
    DARK   = colors.HexColor('#1a1a1a')
    GRAY   = colors.HexColor('#555555')
    LGRAY  = colors.HexColor('#dddddd')
    WHITE  = colors.white

    margin = 1.5 * cm

    # ── HEADER NEGRO ──────────────────────────────────────
    header_h = 2.8 * cm
    p.setFillColor(BLACK)
    p.rect(0, height - header_h, width, header_h, fill=1, stroke=0)

    # Logo — ocupa el lado izquierdo completo (ya contiene el texto de marca)
    logo_path = find('img/logo.png')
    if logo_path:
        try:
            p.drawImage(logo_path, margin, height - header_h + 0.15 * cm,
                        width=7 * cm, height=2.5 * cm,
                        preserveAspectRatio=True, mask='auto')
        except:
            pass

    # Número de orden (derecha del header)
    p.setFillColor(GOLD)
    p.setFont("Helvetica-Bold", 18)
    p.drawRightString(width - margin, height - 1.4 * cm, f"#{ficha.codigo_compuesto}")
    p.setFillColor(GRAY)
    p.setFont("Helvetica", 7.5)
    p.drawRightString(width - margin, height - 2.1 * cm, "ORDEN DE TRABAJO")

    # ── BANDA DORADA ──────────────────────────────────────
    banda_y = height - header_h - 0.75 * cm
    p.setFillColor(GOLD)
    p.rect(0, banda_y, width, 0.75 * cm, fill=1, stroke=0)
    p.setFillColor(BLACK)
    p.setFont("Helvetica-Bold", 8)
    p.drawString(margin, banda_y + 0.22 * cm, "COMPROBANTE DE RECEPCIÓN DE EQUIPO")
    fecha_str = ficha.fecha_ingreso.strftime('%d/%m/%Y') if ficha.fecha_ingreso else ''
    p.drawRightString(width - margin, banda_y + 0.22 * cm, fecha_str)

    # ── FUNCIÓN HELPER: dibuja sección con borde dorado izquierdo ──
    def draw_section(y_top, rows, section_h):
        """rows = lista de (label, valor)"""
        p.setFillColor(GOLD)
        p.rect(margin, y_top - section_h, 0.18 * cm, section_h, fill=1, stroke=0)
        p.setStrokeColor(LGRAY)
        p.setLineWidth(0.3)
        p.rect(margin + 0.18 * cm, y_top - section_h,
               width - 2 * margin - 0.18 * cm, section_h, fill=0, stroke=1)
        row_h = section_h / len(rows)
        for i, (lbl, val) in enumerate(rows):
            ry = y_top - (i + 0.72) * row_h
            p.setFillColor(GRAY)
            p.setFont("Helvetica-Bold", 7.5)
            p.drawString(margin + 0.5 * cm, ry, lbl.upper())
            p.setFillColor(BLACK)
            p.setFont("Helvetica", 10)
            p.drawString(margin + 0.5 * cm + 3.5 * cm, ry, str(val))
            if i < len(rows) - 1:
                p.setStrokeColor(LGRAY)
                p.setLineWidth(0.3)
                p.line(margin + 0.4 * cm, ry - 0.25 * cm,
                       width - margin - 0.2 * cm, ry - 0.25 * cm)

    # ── SECCIÓN CLIENTE ───────────────────────────────────
    y = banda_y - 0.4 * cm
    p.setFillColor(GRAY)
    p.setFont("Helvetica-Bold", 7)
    p.drawString(margin + 0.4 * cm, y - 0.02 * cm, "DATOS DEL CLIENTE")
    y -= 0.35 * cm

    cliente_rows = [
        ("Nombre",   ficha.equipo.cliente.nombre_apellido),
        ("Teléfono", ficha.equipo.cliente.telefono),
        ("Email",    ficha.equipo.cliente.email or "—"),
    ]
    sec_h = 2.8 * cm
    draw_section(y, cliente_rows, sec_h)
    y -= sec_h + 0.45 * cm

    # ── SECCIÓN EQUIPO ────────────────────────────────────
    p.setFillColor(GRAY)
    p.setFont("Helvetica-Bold", 7)
    p.drawString(margin + 0.4 * cm, y - 0.02 * cm, "DATOS DEL EQUIPO")
    y -= 0.35 * cm

    equipo_rows = [
        ("Modelo",    ficha.equipo.marca_modelo),
        ("IMEI / SN", ficha.equipo.identificador or "—"),
        ("Falla",     ficha.falla_cliente),
    ]
    if ficha.obs_recepcion:
        equipo_rows.append(("Estética", ficha.obs_recepcion))

    sec_h2 = len(equipo_rows) * 0.95 * cm
    draw_section(y, equipo_rows, sec_h2)
    y -= sec_h2 + 0.45 * cm

    # ── SECCIÓN TÉRMINOS ──────────────────────────────────
    p.setFillColor(GRAY)
    p.setFont("Helvetica-Bold", 7)
    p.drawString(margin + 0.4 * cm, y - 0.02 * cm, "TÉRMINOS Y CONDICIONES")
    y -= 0.35 * cm

    terminos_h = 3.2 * cm
    p.setFillColor(GOLD)
    p.rect(margin, y - terminos_h, 0.18 * cm, terminos_h, fill=1, stroke=0)
    p.setStrokeColor(LGRAY)
    p.setLineWidth(0.3)
    p.rect(margin + 0.18 * cm, y - terminos_h,
           width - 2 * margin - 0.18 * cm, terminos_h, fill=0, stroke=1)

    lineas = [
        "1. El presupuesto tiene una validez de 10 días corridos.",
        "2. La garantía es de 90 días sobre el trabajo realizado.",
        "3. Transcurridos 90 días del aviso de retiro, el equipo se considera en abandono (Art. 2587 CCCN).",
        "4. Es OBLIGATORIO presentar este comprobante para retirar el equipo.",
        "5. LGI Electrónics no se responsabiliza por la pérdida de datos en el equipo.",
    ]
    ty = y - 0.45 * cm
    for linea in lineas:
        p.setFillColor(GRAY)
        p.setFont("Helvetica", 7.8)
        p.drawString(margin + 0.5 * cm, ty, linea)
        ty -= 0.5 * cm

    y -= terminos_h + 0.6 * cm

    # ── FIRMAS ────────────────────────────────────────────
    firma_y = 3.2 * cm
    p.setStrokeColor(colors.HexColor('#aaaaaa'))
    p.setLineWidth(0.5)
    p.line(margin, firma_y, margin + 6 * cm, firma_y)
    p.line(width - margin - 6 * cm, firma_y, width - margin, firma_y)
    p.setFillColor(GRAY)
    p.setFont("Helvetica", 8)
    p.drawCentredString(margin + 3 * cm, firma_y - 0.4 * cm, "Firma del Cliente")
    p.drawCentredString(width - margin - 3 * cm, firma_y - 0.4 * cm, "LGI Electrónics")

    # ── FOOTER NEGRO ──────────────────────────────────────
    footer_h = 1 * cm
    p.setFillColor(BLACK)
    p.rect(0, 0, width, footer_h, fill=1, stroke=0)
    p.setFillColor(GOLD)
    p.setFont("Helvetica-Bold", 7)
    p.drawCentredString(width / 2, 0.38 * cm, "LGI ELECTRÓNICS  —  Resistencia, Chaco  —  Tel: 3624-605132  —  lgi-electronics.netlify.app")

    p.showPage()
    p.save()
    return response

@login_required
@user_passes_test(es_admin)
def generar_pdf_pedidos(request):
    repuestos_bajo_stock = Repuesto.objects.filter(cantidad__lte=F('stock_minimo'))

    if request.method == 'POST':
        ids_seleccionados = request.POST.getlist('items_seleccionados')
        if not ids_seleccionados:
            return redirect('pdf_pedidos')

        response = HttpResponse(content_type='application/pdf')
        response['Content-Disposition'] = 'attachment; filename="Pedido_Repuestos_LGI.pdf"'
        p = canvas.Canvas(response, pagesize=A4)
        width, height = A4

        GOLD  = colors.HexColor('#D4A017')
        BLACK = colors.HexColor('#111111')
        GRAY  = colors.HexColor('#555555')
        LGRAY = colors.HexColor('#dddddd')
        FGRAY = colors.HexColor('#f8f8f8')
        margin = 1.5 * cm

        def draw_header_pedido(canvas_obj):
            header_h = 2.8 * cm
            canvas_obj.setFillColor(BLACK)
            canvas_obj.rect(0, height - header_h, width, header_h, fill=1, stroke=0)
            logo_path = find('img/logo.png')
            if logo_path:
                try:
                    canvas_obj.drawImage(logo_path, margin, height - header_h + 0.15 * cm,
                                         width=7 * cm, height=2.5 * cm,
                                         preserveAspectRatio=True, mask='auto')
                except:
                    pass
            canvas_obj.setFillColor(GOLD)
            canvas_obj.setFont("Helvetica-Bold", 13)
            canvas_obj.drawRightString(width - margin, height - 1.5 * cm, "ORDEN DE COMPRA")
            canvas_obj.setFillColor(GRAY)
            canvas_obj.setFont("Helvetica", 7.5)
            canvas_obj.drawRightString(width - margin, height - 2.1 * cm,
                                       f"PEDIDO DE REPUESTOS — {timezone.now().strftime('%d/%m/%Y')}")
            banda_y = height - header_h - 0.75 * cm
            canvas_obj.setFillColor(GOLD)
            canvas_obj.rect(0, banda_y, width, 0.75 * cm, fill=1, stroke=0)
            canvas_obj.setFillColor(BLACK)
            canvas_obj.setFont("Helvetica-Bold", 8)
            canvas_obj.drawString(margin, banda_y + 0.22 * cm, "DETALLE DE REPUESTOS A REPONER")
            return banda_y

        banda_y = draw_header_pedido(p)

        # Cabecera de tabla
        tabla_y = banda_y - 0.5 * cm
        col_cant = 3.5 * cm
        tabla_w  = width - 2 * margin

        p.setFillColor(FGRAY)
        p.rect(margin + 0.18 * cm, tabla_y - 0.6 * cm, tabla_w - 0.18 * cm, 0.6 * cm, fill=1, stroke=0)
        p.setFillColor(GOLD)
        p.rect(margin, tabla_y - 0.6 * cm, 0.18 * cm, 0.6 * cm, fill=1, stroke=0)
        p.setStrokeColor(LGRAY); p.setLineWidth(0.3)
        p.rect(margin + 0.18 * cm, tabla_y - 0.6 * cm, tabla_w - 0.18 * cm, 0.6 * cm, fill=0, stroke=1)
        p.setFillColor(GRAY); p.setFont("Helvetica-Bold", 7.5)
        p.drawString(margin + 0.5 * cm, tabla_y - 0.38 * cm, "REPUESTO / INSUMO")
        p.drawCentredString(width - margin - col_cant / 2, tabla_y - 0.38 * cm, "CANTIDAD")

        y = tabla_y - 0.6 * cm
        alternado = False

        for r_id in ids_seleccionados:
            repuesto = get_object_or_404(Repuesto, id=r_id)
            cantidad_final = request.POST.get(f'cantidad_{r_id}', 1)
            row_h = 0.85 * cm

            if y - row_h < 1.2 * cm:
                p.setStrokeColor(LGRAY); p.setLineWidth(0.3)
                p.line(margin + 0.18 * cm, y, width - margin, y)
                p.showPage()
                banda_y = draw_header_pedido(p)
                y = banda_y - 0.5 * cm - 0.6 * cm
                alternado = False

            if alternado:
                p.setFillColor(colors.HexColor('#f8f8f8'))
                p.rect(margin + 0.18 * cm, y - row_h, tabla_w - 0.18 * cm, row_h, fill=1, stroke=0)

            p.setFillColor(GOLD)
            p.rect(margin, y - row_h, 0.18 * cm, row_h, fill=1, stroke=0)
            p.setStrokeColor(LGRAY); p.setLineWidth(0.3)
            p.line(margin + 0.18 * cm, y - row_h, width - margin, y - row_h)
            p.line(margin, y, width - margin, y)
            p.line(width - margin - col_cant, y - row_h, width - margin - col_cant, y)
            p.rect(margin + 0.18 * cm, y - row_h, tabla_w - 0.18 * cm, row_h, fill=0, stroke=1)

            p.setFillColor(BLACK); p.setFont("Helvetica", 10)
            p.drawString(margin + 0.5 * cm, y - 0.55 * cm, repuesto.nombre)

            p.setFillColor(GOLD); p.setFont("Helvetica-Bold", 12)
            p.drawCentredString(width - margin - col_cant / 2, y - 0.55 * cm, f"× {cantidad_final}")

            y -= row_h
            alternado = not alternado

        # Footer
        footer_h = 0.8 * cm
        p.setFillColor(BLACK)
        p.rect(0, 0, width, footer_h, fill=1, stroke=0)
        p.setFillColor(GOLD); p.setFont("Helvetica-Bold", 7)
        p.drawCentredString(width / 2, 0.28 * cm,
                            "LGI ELECTRÓNICS  —  Resistencia, Chaco  —  Tel: 3624-605132  —  lgi-electronics.netlify.app")

        p.save()
        return response

    return render(request, 'gestion/preparar_pedido.html', {'repuestos_bajo_stock': repuestos_bajo_stock})

@login_required
def generar_pdf_stock_total(request):
    repuestos = Repuesto.objects.all().order_by('nombre')
    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="Stock_Fisico.pdf"'
    p = canvas.Canvas(response, pagesize=A4)
    width, height = A4

    GOLD  = colors.HexColor('#D4A017')
    BLACK = colors.HexColor('#111111')
    GRAY  = colors.HexColor('#555555')
    LGRAY = colors.HexColor('#dddddd')
    FGRAY = colors.HexColor('#f8f8f8')
    margin = 1.5 * cm

    col_sistem = 3.5 * cm
    col_real   = 3.5 * cm
    tabla_w    = width - 2 * margin

    def draw_header_stock(canvas_obj, pag):
        header_h = 2.8 * cm
        canvas_obj.setFillColor(BLACK)
        canvas_obj.rect(0, height - header_h, width, header_h, fill=1, stroke=0)
        logo_path = find('img/logo.png')
        if logo_path:
            try:
                canvas_obj.drawImage(logo_path, margin, height - header_h + 0.15 * cm,
                                     width=7 * cm, height=2.5 * cm,
                                     preserveAspectRatio=True, mask='auto')
            except:
                pass
        canvas_obj.setFillColor(GOLD)
        canvas_obj.setFont("Helvetica-Bold", 13)
        canvas_obj.drawRightString(width - margin, height - 1.5 * cm, "CONTROL DE STOCK")
        canvas_obj.setFillColor(GRAY)
        canvas_obj.setFont("Helvetica", 7.5)
        canvas_obj.drawRightString(width - margin, height - 2.1 * cm,
                                   f"PLANILLA FÍSICA — {timezone.now().strftime('%d/%m/%Y')}  |  Pág: {pag}")
        banda_y = height - header_h - 0.75 * cm
        canvas_obj.setFillColor(GOLD)
        canvas_obj.rect(0, banda_y, width, 0.75 * cm, fill=1, stroke=0)
        canvas_obj.setFillColor(BLACK)
        canvas_obj.setFont("Helvetica-Bold", 8)
        canvas_obj.drawString(margin, banda_y + 0.22 * cm, "VERIFICACIÓN DE INVENTARIO FÍSICO")

        # Cabecera de columnas
        cab_y = banda_y - 0.5 * cm
        canvas_obj.setFillColor(FGRAY)
        canvas_obj.rect(margin + 0.18 * cm, cab_y - 0.6 * cm, tabla_w - 0.18 * cm, 0.6 * cm, fill=1, stroke=0)
        canvas_obj.setFillColor(GOLD)
        canvas_obj.rect(margin, cab_y - 0.6 * cm, 0.18 * cm, 0.6 * cm, fill=1, stroke=0)
        canvas_obj.setStrokeColor(LGRAY); canvas_obj.setLineWidth(0.3)
        canvas_obj.rect(margin + 0.18 * cm, cab_y - 0.6 * cm, tabla_w - 0.18 * cm, 0.6 * cm, fill=0, stroke=1)
        canvas_obj.setFillColor(GRAY); canvas_obj.setFont("Helvetica-Bold", 7.5)
        canvas_obj.drawString(margin + 0.5 * cm, cab_y - 0.38 * cm, "DESCRIPCIÓN DEL REPUESTO / INSUMO")
        canvas_obj.drawCentredString(width - margin - col_real - col_sistem / 2, cab_y - 0.38 * cm, "SISTEMA")
        canvas_obj.drawCentredString(width - margin - col_real / 2, cab_y - 0.38 * cm, "REAL")

        return cab_y - 0.6 * cm

    y = draw_header_stock(p, 1)
    pag = 1
    alternado = False

    for r in repuestos:
        row_h = 0.82 * cm
        if y - row_h < 1.2 * cm:
            # footer
            p.setFillColor(BLACK)
            p.rect(0, 0, width, 0.8 * cm, fill=1, stroke=0)
            p.setFillColor(GOLD); p.setFont("Helvetica-Bold", 7)
            p.drawCentredString(width / 2, 0.28 * cm,
                                "LGI ELECTRÓNICS  —  Resistencia, Chaco  —  Tel: 3624-605132")
            p.showPage()
            pag += 1
            y = draw_header_stock(p, pag)
            alternado = False

        if alternado:
            p.setFillColor(FGRAY)
            p.rect(margin + 0.18 * cm, y - row_h, tabla_w - 0.18 * cm, row_h, fill=1, stroke=0)

        p.setFillColor(GOLD)
        p.rect(margin, y - row_h, 0.18 * cm, row_h, fill=1, stroke=0)
        p.setStrokeColor(LGRAY); p.setLineWidth(0.3)
        p.line(margin + 0.18 * cm, y - row_h, width - margin, y - row_h)
        p.rect(margin + 0.18 * cm, y - row_h, tabla_w - 0.18 * cm, row_h, fill=0, stroke=1)

        # Líneas verticales separadoras
        p.line(width - margin - col_real - col_sistem, y - row_h,
               width - margin - col_real - col_sistem, y)
        p.line(width - margin - col_real, y - row_h,
               width - margin - col_real, y)

        # Datos
        p.setFillColor(BLACK); p.setFont("Helvetica", 9.5)
        p.drawString(margin + 0.5 * cm, y - 0.52 * cm, r.nombre[:55])

        p.setFillColor(GOLD); p.setFont("Helvetica-Bold", 11)
        p.drawCentredString(width - margin - col_real - col_sistem / 2, y - 0.52 * cm, str(r.cantidad))

        # Recuadro para anotar cantidad real
        box_w = 2.2 * cm; box_h = 0.5 * cm
        bx = width - margin - col_real / 2 - box_w / 2
        by = y - row_h / 2 - box_h / 2
        p.setStrokeColor(LGRAY); p.setLineWidth(0.5)
        p.setFillColor(colors.white)
        p.rect(bx, by, box_w, box_h, fill=1, stroke=1)

        y -= row_h
        alternado = not alternado

    # Footer última página
    p.setFillColor(BLACK)
    p.rect(0, 0, width, 0.8 * cm, fill=1, stroke=0)
    p.setFillColor(GOLD); p.setFont("Helvetica-Bold", 7)
    p.drawCentredString(width / 2, 0.28 * cm,
                        "LGI ELECTRÓNICS  —  Resistencia, Chaco  —  Tel: 3624-605132  —  lgi-electronics.netlify.app")
    p.save()
    return response


# --- 7. REENVÍO DE EMAIL ---
@login_required
def reenviar_email_ingreso(request, ficha_id):
    ficha = get_object_or_404(Ficha, id=ficha_id)
    cliente = ficha.equipo.cliente
    equipo = ficha.equipo

    if cliente.email:
        try:
            _enviar_email_lgi(cliente, equipo, ficha)
        except:
            pass

    return redirect('detalle_ficha', ficha_id=ficha_id)