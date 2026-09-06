#!/usr/bin/env python3
"""Autorización única para obtener el refresh token de Gmail (ámbito gmail.send, y nada más).

Se ejecuta UNA vez en el ordenador de la persona cuya cuenta enviará los correos (hace falta navegador).
Requisitos previos, en https://console.cloud.google.com :
  1. Crear un proyecto (p. ej. "Quantum informes").
  2. APIs y servicios → Biblioteca → habilitar "Gmail API".
  3. APIs y servicios → Pantalla de consentimiento OAuth → tipo "Interno" (solo posible con Google Workspace).
     Si la cuenta es un Gmail personal, el tipo es "Externo" y hay que publicar la app: en modo "Prueba" el
     refresh token caduca a los 7 días.
  4. APIs y servicios → Credenciales → Crear credenciales → ID de cliente OAuth → tipo "Aplicación de escritorio".
     Copiar el ID de cliente y el secreto.

Uso:
  python3 gmail_auth.py --client-id XXX.apps.googleusercontent.com --client-secret YYY
Al terminar imprime las cuatro variables de entorno que hay que dar de alta en el entorno de Claude Code.
"""
import argparse, http.server, json, secrets, threading, urllib.parse, urllib.request, webbrowser

SCOPE = "https://www.googleapis.com/auth/gmail.send"
PORT = 8765


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--client-id", required=True)
    ap.add_argument("--client-secret", required=True)
    a = ap.parse_args()
    redirect = f"http://localhost:{PORT}/"
    state = secrets.token_urlsafe(16)
    url = "https://accounts.google.com/o/oauth2/v2/auth?" + urllib.parse.urlencode({
        "client_id": a.client_id, "redirect_uri": redirect, "response_type": "code", "scope": SCOPE,
        "access_type": "offline", "prompt": "consent", "state": state})
    code = {}

    class H(http.server.BaseHTTPRequestHandler):
        def do_GET(self):
            q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query)
            if q.get("state", [""])[0] == state and "code" in q:
                code["v"] = q["code"][0]
                self.send_response(200); self.end_headers()
                self.wfile.write("Autorización recibida. Puedes cerrar esta pestaña.".encode())
            else:
                self.send_response(400); self.end_headers()
        def log_message(self, *args):
            pass

    srv = http.server.HTTPServer(("localhost", PORT), H)
    threading.Thread(target=srv.handle_request, daemon=True).start()
    print("Abriendo el navegador para autorizar (solo permiso de ENVIAR correo)…")
    webbrowser.open(url)
    print("Si no se abre, copia esta URL en el navegador:\n", url)
    while "v" not in code:
        pass
    data = urllib.parse.urlencode({"code": code["v"], "client_id": a.client_id, "client_secret": a.client_secret,
                                   "redirect_uri": redirect, "grant_type": "authorization_code"}).encode()
    with urllib.request.urlopen("https://oauth2.googleapis.com/token", data=data, timeout=30) as r:
        tok = json.load(r)
    if "refresh_token" not in tok:
        raise SystemExit("Google no devolvió refresh_token. Repite con prompt=consent o revoca el acceso previo en myaccount.google.com/permissions.")
    with urllib.request.urlopen(urllib.request.Request("https://gmail.googleapis.com/gmail/v1/users/me/profile",
                                headers={"Authorization": f"Bearer {tok['access_token']}"}), timeout=30) as r:
        me = json.load(r)["emailAddress"]
    print("\nListo. Variables de entorno para el entorno de Claude Code (Settings → Environments):\n")
    print(f"GMAIL_CLIENT_ID={a.client_id}")
    print(f"GMAIL_CLIENT_SECRET={a.client_secret}")
    print(f"GMAIL_REFRESH_TOKEN={tok['refresh_token']}")
    print(f"GMAIL_SENDER={me}")


if __name__ == "__main__":
    main()
