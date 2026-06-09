#!/usr/bin/env python3
"""
Renueva el periodo online de la web app en PythonAnywhere (free tier).

El free tier expira a los 3 meses; el unico modo de renovar es apretar el boton
"Run until 3 months from today" en la pestaña Web. No hay API para esto, asi que
automatizamos un browser headless.

Credenciales por variables de entorno (GitHub Secrets):
  PA_USERNAME, PA_PASSWORD

Salidas:
  exit 0  -> boton apretado, o ya estaba lejos de expirar (nada que hacer)
  exit 1  -> fallo real (login fallido, pagina inesperada)
"""
import os
import sys
import re
from playwright.sync_api import sync_playwright, TimeoutError as PWTimeout

USER = os.environ.get("PA_USERNAME", "").strip()
PASS = os.environ.get("PA_PASSWORD", "")

if not USER or not PASS:
    print("ERROR: faltan PA_USERNAME / PA_PASSWORD en el entorno", file=sys.stderr)
    sys.exit(1)


def main():
    with sync_playwright() as p:
        browser = p.chromium.launch()
        page = browser.new_page()
        page.set_default_timeout(30000)

        # --- Login ---
        page.goto("https://www.pythonanywhere.com/login/")
        page.fill("#id_auth-username", USER)
        page.fill("#id_auth-password", PASS)
        # Enviar el form con Enter en el campo password (evita ambiguedad de botones).
        page.press("#id_auth-password", "Enter")
        page.wait_for_load_state("networkidle")

        if "/login/" in page.url:
            page.screenshot(path="pa_login_fail.png", full_page=True)
            print("ERROR: el login no avanzo (¿password incorrecta o 2FA activo?)",
                  file=sys.stderr)
            browser.close()
            sys.exit(1)
        print(f"Login OK -> {page.url}")

        # El path /user/{username}/ es case-sensitive: tomar el username canonico
        # del redirect post-login en vez de adivinar la capitalizacion.
        m_user = re.search(r"/user/([^/]+)/", page.url)
        canon = m_user.group(1) if m_user else USER

        # --- Pestaña Web ---
        page.goto(f"https://www.pythonanywhere.com/user/{canon}/webapps/")
        page.wait_for_load_state("networkidle")

        body = page.inner_text("body")
        if "Access Denied" in body or "not authorized" in body:
            page.screenshot(path="pa_web_tab.png", full_page=True)
            print(f"ERROR: 403 en /user/{canon}/webapps/ — path/username incorrecto",
                  file=sys.stderr)
            browser.close()
            sys.exit(1)

        # Escanear todos los clickables y buscar el boton de renovacion por etiqueta.
        candidates = page.locator("button, input[type=submit], a[href]")
        target = None
        hit_label = ""
        labels = []
        for i in range(candidates.count()):
            el = candidates.nth(i)
            try:
                label = (el.inner_text(timeout=1000) or "").strip()
            except Exception:
                label = ""
            if not label:
                label = (el.get_attribute("value") or "").strip()
            if label:
                labels.append(label)
            if re.search(r"(run until|3 months|extend|until 3 months)", label, re.I):
                target = el
                hit_label = label
                break

        if target is not None:
            target.scroll_into_view_if_needed()
            target.click()
            page.wait_for_load_state("networkidle")
            print(f"OK -> periodo renovado (boton: '{hit_label}').")
            page.screenshot(path="pa_web_tab.png", full_page=True)
            browser.close()
        else:
            m = (re.search(r"disabled on\s+([0-9A-Za-z ,]+)", body, re.I)
                 or re.search(r"expire[sd]? on\s+([0-9A-Za-z ,]+)", body, re.I))
            cuando = m.group(1).strip() if m else "fecha no detectada"
            print(f"ERROR: no encontre el boton de renovacion. Expira: {cuando}.",
                  file=sys.stderr)
            print("Clickables vistos: " + " | ".join(labels[:50]), file=sys.stderr)
            page.screenshot(path="pa_web_tab.png", full_page=True)
            browser.close()
            sys.exit(1)


if __name__ == "__main__":
    try:
        main()
    except PWTimeout as e:
        print(f"ERROR: timeout esperando la pagina: {e}", file=sys.stderr)
        sys.exit(1)
