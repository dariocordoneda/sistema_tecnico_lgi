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

        # Buscar el boton de renovacion por texto (puede ser button, a o input)
        renew = page.locator(
            "text=/Run until 3 months from today/i"
        ).or_(page.locator("input[value*='3 months' i]"))

        if renew.count() > 0:
            renew.first.click()
            page.wait_for_load_state("networkidle")
            print("OK -> periodo renovado (boton apretado).")
        else:
            # Sin boton = todavia lejos de expirar; no es un error.
            txt = page.inner_text("body")
            m = re.search(r"expire[sd]? on\s+([0-9A-Za-z ,\-]+)", txt, re.I)
            cuando = m.group(1).strip() if m else "fecha no detectada"
            print(f"Sin boton de renovacion visible — app vigente (expira: {cuando}).")

        page.screenshot(path="pa_web_tab.png", full_page=True)
        browser.close()


if __name__ == "__main__":
    try:
        main()
    except PWTimeout as e:
        print(f"ERROR: timeout esperando la pagina: {e}", file=sys.stderr)
        sys.exit(1)
