#!/usr/bin/env python3
"""Envía el informe por correo mediante la API de Gmail (solo necesita el ámbito gmail.send).

Credenciales por variables de entorno (se definen en el entorno de Claude Code, nunca en el repo):
  GMAIL_CLIENT_ID, GMAIL_CLIENT_SECRET, GMAIL_REFRESH_TOKEN  -> obtenidos una sola vez con gmail_auth.py
  GMAIL_SENDER                                               -> dirección desde la que se envía (la cuenta que autorizó)

Uso:
  send_mail.py --to a@x.es --cc b@y.es,c@y.es --subject "Asunto" --body cuerpo.txt --attach informe.pdf [--attach otro.pdf]
"""
import argparse, base64, json, mimetypes, os, sys, urllib.parse, urllib.request
from email.message import EmailMessage
from pathlib import Path

TOKEN_URL = "https://oauth2.googleapis.com/token"
SEND_URL = "https://gmail.googleapis.com/gmail/v1/users/me/messages/send"


def access_token():
    need = ["GMAIL_CLIENT_ID", "GMAIL_CLIENT_SECRET", "GMAIL_REFRESH_TOKEN", "GMAIL_SENDER"]
    missing = [k for k in need if not os.environ.get(k)]
    if missing:
        sys.exit(f"Faltan variables de entorno: {', '.join(missing)}")
    data = urllib.parse.urlencode({
        "client_id": os.environ["GMAIL_CLIENT_ID"],
        "client_secret": os.environ["GMAIL_CLIENT_SECRET"],
        "refresh_token": os.environ["GMAIL_REFRESH_TOKEN"],
        "grant_type": "refresh_token",
    }).encode()
    with urllib.request.urlopen(urllib.request.Request(TOKEN_URL, data=data), timeout=30) as r:
        return json.load(r)["access_token"]


def build(sender, to, cc, subject, body, attachments):
    msg = EmailMessage()
    msg["From"] = sender
    msg["To"] = ", ".join(to)
    if cc:
        msg["Cc"] = ", ".join(cc)
    msg["Subject"] = subject
    msg.set_content(body)
    for path in attachments:
        p = Path(path)
        ctype, _ = mimetypes.guess_type(p.name)
        maintype, subtype = (ctype or "application/octet-stream").split("/", 1)
        msg.add_attachment(p.read_bytes(), maintype=maintype, subtype=subtype, filename=p.name)
    return msg


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--to", required=True, help="destinatarios separados por coma")
    ap.add_argument("--cc", default="", help="copias separadas por coma")
    ap.add_argument("--subject", required=True)
    ap.add_argument("--body", required=True, help="fichero de texto con el cuerpo")
    ap.add_argument("--attach", action="append", default=[], help="adjunto (repetible)")
    a = ap.parse_args()
    to = [x.strip() for x in a.to.split(",") if x.strip()]
    cc = [x.strip() for x in a.cc.split(",") if x.strip()]
    for f in a.attach:
        if not Path(f).is_file():
            sys.exit(f"No existe el adjunto: {f}")
        if Path(f).stat().st_size > 20 * 1024 * 1024:
            sys.exit(f"Adjunto demasiado grande (>20 MB): {f}")
    msg = build(os.environ["GMAIL_SENDER"], to, cc, a.subject, Path(a.body).read_text(encoding="utf-8"), a.attach)
    raw = base64.urlsafe_b64encode(msg.as_bytes()).decode()
    req = urllib.request.Request(SEND_URL, data=json.dumps({"raw": raw}).encode(),
                                 headers={"Authorization": f"Bearer {access_token()}", "Content-Type": "application/json"})
    try:
        with urllib.request.urlopen(req, timeout=60) as r:
            res = json.load(r)
    except urllib.error.HTTPError as e:
        sys.exit(f"Gmail API devolvió {e.code}: {e.read().decode()[:400]}")
    print(f"Enviado. id={res.get('id')} para={to} cc={cc} adjuntos={[Path(f).name for f in a.attach]}")


if __name__ == "__main__":
    main()
