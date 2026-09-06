#!/usr/bin/env python3
"""Envía el informe por Microsoft Graph con una aplicación de Azure (permiso de aplicación Mail.Send).

Requiere que la política de red del entorno de Claude Code permita graph.microsoft.com y login.microsoftonline.com.

Credenciales por variables de entorno (se definen en el entorno de Claude Code, nunca en el repo):
  GRAPH_TENANT_ID, GRAPH_CLIENT_ID, GRAPH_CLIENT_SECRET  -> registro de aplicación en Entra ID (Azure AD)
  GRAPH_SENDER                                           -> buzón del tenant desde el que se envía (p. ej. informes@globaleye.es)

Registro en https://entra.microsoft.com  (Identidad → Aplicaciones → Registros de aplicaciones):
  1. Nuevo registro, p. ej. "Quantum informes". Copiar Id. de aplicación (cliente) e Id. de directorio (inquilino).
  2. Certificados y secretos → Nuevo secreto de cliente. Copiar el valor (solo se muestra una vez).
  3. Permisos de API → Agregar → Microsoft Graph → Permisos de aplicación → Mail.Send → Conceder consentimiento de administrador.
  4. Recomendado: limitar la app a un solo buzón con una política de acceso a aplicaciones de Exchange Online
     (New-ApplicationAccessPolicy -AppId <cliente> -PolicyScopeGroupId <grupo con el buzón remitente> -AccessRight RestrictAccess).

Uso:
  send_mail_graph.py --to a@x.es --cc b@y.es,c@y.es --subject "Asunto" --body cuerpo.txt --attach informe.pdf [--attach otro.pdf]
"""
import argparse, base64, json, mimetypes, os, sys, urllib.parse, urllib.request
from pathlib import Path

MAX_INLINE = 3 * 1024 * 1024  # Graph admite adjuntos inline hasta 3 MB por fichero; los informes pesan < 0,5 MB


def access_token():
    need = ["GRAPH_TENANT_ID", "GRAPH_CLIENT_ID", "GRAPH_CLIENT_SECRET", "GRAPH_SENDER"]
    missing = [k for k in need if not os.environ.get(k)]
    if missing:
        sys.exit(f"Faltan variables de entorno: {', '.join(missing)}")
    url = f"https://login.microsoftonline.com/{os.environ['GRAPH_TENANT_ID']}/oauth2/v2.0/token"
    data = urllib.parse.urlencode({
        "client_id": os.environ["GRAPH_CLIENT_ID"], "client_secret": os.environ["GRAPH_CLIENT_SECRET"],
        "scope": "https://graph.microsoft.com/.default", "grant_type": "client_credentials"}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=30) as r:
        return json.load(r)["access_token"]


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True); ap.add_argument("--cc", default="")
    ap.add_argument("--subject", required=True); ap.add_argument("--body", required=True)
    ap.add_argument("--attach", action="append", default=[])
    a = ap.parse_args()
    rcpt = lambda s: [{"emailAddress": {"address": x.strip()}} for x in s.split(",") if x.strip()]
    attachments = []
    for f in a.attach:
        p = Path(f)
        if not p.is_file():
            sys.exit(f"No existe el adjunto: {f}")
        if p.stat().st_size > MAX_INLINE:
            sys.exit(f"Adjunto mayor de 3 MB, requiere sesión de carga: {f}")
        attachments.append({"@odata.type": "#microsoft.graph.fileAttachment", "name": p.name,
                            "contentType": mimetypes.guess_type(p.name)[0] or "application/octet-stream",
                            "contentBytes": base64.b64encode(p.read_bytes()).decode()})
    payload = {"message": {"subject": a.subject,
                           "body": {"contentType": "Text", "content": Path(a.body).read_text(encoding="utf-8")},
                           "toRecipients": rcpt(a.to), "ccRecipients": rcpt(a.cc), "attachments": attachments},
               "saveToSentItems": True}
    url = f"https://graph.microsoft.com/v1.0/users/{urllib.parse.quote(os.environ['GRAPH_SENDER'])}/sendMail"
    req = urllib.request.Request(url, data=json.dumps(payload).encode(),
                                 headers={"Authorization": f"Bearer {access_token()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            ok = r.status
    except urllib.error.HTTPError as e:
        sys.exit(f"Graph devolvió {e.code}: {e.read().decode()[:400]}")
    print(f"Enviado ({ok}). para={a.to} cc={a.cc} adjuntos={[Path(f).name for f in a.attach]}")


if __name__ == "__main__":
    main()
