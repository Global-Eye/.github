#!/usr/bin/env python3
"""Genera los informes de actividad Quantum (diario / semanal) como HTML A4 listo para PDF.

Uso:
  build.py dump  YYYY-MM-DD YYYY-MM-DD        -> volcado de commits por producto/día/persona (para redactar)
  build.py daily YYYY-MM-DD                   -> informe diario de esa fecha
  build.py weekly YYYY-MM-DD                  -> informe semanal terminando ese viernes
"""
import base64, csv, datetime as dt, json, math, re, sys
from collections import defaultdict
from pathlib import Path
from zoneinfo import ZoneInfo

SC = Path(__file__).parent
TZ = ZoneInfo("Europe/Madrid")

# ------------------------------------------------------------------ configuración
PRODUCTS = [
    dict(key="resi",       name="Quantum Resi",            color="#006BBC", repos=["quantum.resi.back", "quantum.resi.front"]),
    dict(key="crm",        name="Quantum CRM",             color="#EF7D00", repos=["quantum.crm.backend", "quantum.crm.frontend"]),
    dict(key="infra",      name="Quantum Infraestructuras", color="#0B8F7A", repos=["quantum.infraestructuras.backend", "quantum.infraestructuras.frontend"]),
    dict(key="identity",   name="Quantum Identity",        color="#6B4E9B", repos=["quantum.identityserver.backend", "quantum.identityserver.frontend"]),
    dict(key="team",       name="Quantum Team",            color="#B23A48", repos=["quantumteam", "quantumteam-app"]),
    dict(key="plataforma", name="Plataforma común",        color="#8A8F98", hatch=True, repos=["quantum.erp", "quantum.layout.lib", "quantum.auth.lib"]),
]
REPO2PROD = {r: p["key"] for p in PRODUCTS for r in p["repos"]}
PROD = {p["key"]: p for p in PRODUCTS}
REPO_LABEL = {
    "quantum.resi.back": "Resi · Backend", "quantum.resi.front": "Resi · Frontend",
    "quantum.crm.backend": "CRM · Backend", "quantum.crm.frontend": "CRM · Frontend",
    "quantum.infraestructuras.backend": "Infraestructuras · Backend", "quantum.infraestructuras.frontend": "Infraestructuras · Frontend",
    "quantum.identityserver.backend": "Identity · Backend", "quantum.identityserver.frontend": "Identity · Frontend",
    "quantumteam": "Team · Web", "quantumteam-app": "Team · App",
    "quantum.erp": "ERP (especificaciones)", "quantum.layout.lib": "Layout Lib", "quantum.auth.lib": "Auth Lib",
}
PEOPLE = {
    "ramonesteban78@gmail.com": "Ramón Esteban", "ramon@wantedforcode.com": "Ramón Esteban",
    "pedro@wantedforcode.com": "Pedro Rubio",
    "asicilia@globaleye.local": "Alejandro Sicilia", "elsici@yahoo.com": "Alejandro Sicilia", "elsici@gmail.com": "Alejandro Sicilia",
    "atorres@globaleye.es": "Ángel Torres",
    "jcarlosdev@outlook.es": "Juan Carlos Fuentes", "153505643+jcarlosdev71@users.noreply.github.com": "Juan Carlos Fuentes",
    "mirian@wantedforcode.com": "Mirian Trujillo",
    "ddomene@globaleye.es": "David Domene",
    "carlos@wantedforcode.com": "Carlos Bourque",
    "pcuervo@globaleye.local": "Pilar Cuervo",
}
BOT_RE = re.compile(r"copilot|dependabot|\[bot\]|noreply@github\.com$", re.I)
HOLIDAYS = {dt.date(2026, 1, 1), dt.date(2026, 1, 6), dt.date(2026, 4, 3), dt.date(2026, 5, 1), dt.date(2026, 8, 15),
            dt.date(2026, 10, 12), dt.date(2026, 11, 1), dt.date(2026, 12, 6), dt.date(2026, 12, 8), dt.date(2026, 12, 25)}
FIX_RE = re.compile(r"\b(fix|corr[ei]g|error|bug|arregl|solucion|no se (muestra|guarda)|incorrect|solapa|truncam|falta)", re.I)

INK, INK2, INK3, LINE, SURF, CARD = "#1D1D1F", "#6E6E73", "#AEAEB2", "#E5E5EA", "#FCFCFB", "#F5F5F7"
GOOD, WARN, BAD = "#1E8E5A", "#B7791F", "#C9443A"
MESES = ["enero", "febrero", "marzo", "abril", "mayo", "junio", "julio", "agosto", "septiembre", "octubre", "noviembre", "diciembre"]
DIAS = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"]
DIAS_C = ["L", "M", "X", "J", "V", "S", "D"]


def fecha_larga(d):
    return f"{DIAS[d.weekday()]}, {d.day} de {MESES[d.month-1]} de {d.year}"


def fecha_corta(d):
    return f"{d.day} {MESES[d.month-1][:3]}"


def is_business(d):
    return d.weekday() < 5 and d not in HOLIDAYS


def business_days_back(end, n):
    out, d = [], end
    while len(out) < n:
        if is_business(d):
            out.append(d)
        d -= dt.timedelta(days=1)
    return sorted(out)


# ------------------------------------------------------------------ datos
class Data:
    def __init__(self):
        self.work, self.merges = [], []
        with open(SC / "data/commits.tsv", encoding="utf-8") as f:
            for row in csv.reader(f, delimiter="\t", quoting=csv.QUOTE_NONE):
                if len(row) < 8:
                    continue
                repo, sha, aiso, email, name, onmain, ismerge, subj = row[:8]
                if repo not in REPO2PROD or BOT_RE.search(email) or BOT_RE.search(name):
                    continue
                t = dt.datetime.fromisoformat(aiso).astimezone(TZ)
                c = dict(repo=repo, prod=REPO2PROD[repo], sha=sha, t=t, d=t.date(), email=email,
                         who=PEOPLE.get(email, name), subj=subj, onmain=onmain == "1")
                if ismerge == "1":
                    m = re.match(r"Merge pull request #(\d+)", subj)
                    if m and c["onmain"]:
                        c["pr"] = int(m.group(1))
                        c["title"] = subj.split("\n")[0]
                        self.merges.append(c)
                else:
                    self.work.append(c)
        gh = json.loads((SC / "data/github.json").read_text(encoding="utf-8"))
        self.open_prs = gh["open_prs"]
        self.closed = []
        for repo, items in gh["closed_issues_since_0831"].items():
            for it in items:
                t = dt.datetime.fromisoformat(it["closed"].replace("Z", "+00:00")).astimezone(TZ)
                self.closed.append(dict(repo=repo, prod=REPO2PROD[repo], n=it["n"], title=it["title"], t=t, d=t.date()))

    # --- consultas básicas
    def work_in(self, d0, d1, prod=None, who=None):
        return [c for c in self.work if d0 <= c["d"] <= d1 and (prod is None or c["prod"] == prod) and (who is None or c["who"] == who)]

    def merges_in(self, d0, d1, prod=None):
        return [c for c in self.merges if d0 <= c["d"] <= d1 and (prod is None or c["prod"] == prod)]

    def closed_in(self, d0, d1, prod=None):
        return [c for c in self.closed if d0 <= c["d"] <= d1 and (prod is None or c["prod"] == prod)]

    def people_in(self, d0, d1):
        return sorted({c["who"] for c in self.work_in(d0, d1)})

    def hours(self, who, d):
        ts = sorted(c["t"] for c in self.work if c["d"] == d and c["who"] == who)
        if not ts:
            return 0.0
        span = (ts[-1] - ts[0]).total_seconds() / 3600 + 1.0
        return round(min(9.0, max(2.0, span)) * 2) / 2

    def prs_open_at(self, repos, ref):
        """PRs abiertos (no borrador, no bots) creados hasta la fecha de referencia."""
        out = []
        for r in repos:
            for pr in self.open_prs.get(r, []):
                if pr.get("draft") or BOT_RE.search(pr["user"]):
                    continue
                created = dt.datetime.fromisoformat(pr["created"].replace("Z", "+00:00")).astimezone(TZ).date()
                if created <= ref:
                    out.append((pr, (ref - created).days))
        return out

    def hours_range(self, who, d0, d1):
        return sum(self.hours(who, d0 + dt.timedelta(i)) for i in range((d1 - d0).days + 1))

    def trend(self, prod, end, days=30):
        return [len(self.work_in(end - dt.timedelta(days - 1 - i), end - dt.timedelta(days - 1 - i), prod)) for i in range(days)]

    def status(self, prod, d):
        if len(self.work_in(d - dt.timedelta(29), d, prod)) < 10:
            return ("esporádico", INK3, "Sin desarrollo activo")
        last5 = business_days_back(d, 5)
        n5 = sum(len(self.work_in(x, x, prod)) for x in last5)
        today = len(self.work_in(d, d, prod))
        if n5 == 0:
            return ("parado", BAD, "Sin actividad en 5 días laborables")
        if today == 0:
            return ("sin actividad", INK3, "Sin actividad hoy")
        delivered = [m.get("title", "") for m in self.merges_in(d, d, prod)] + [c["title"] for c in self.closed_in(d, d, prod)]
        if not delivered:
            return ("en curso", WARN, "Trabajo en curso, sin entregas cerradas hoy")
        if all(FIX_RE.search(t) for t in delivered):
            return ("mantenimiento", INK2, "Solo correcciones")
        return ("avanzando", GOOD, "Funcionalidad nueva entregada")

    def status_week(self, prod, d0, d1):
        if len(self.work_in(d1 - dt.timedelta(29), d1, prod)) < 10:
            return ("esporádico", INK3, "Sin desarrollo activo")
        n = len(self.work_in(d0, d1, prod))
        if n == 0:
            return ("parado", BAD, "Sin actividad esta semana")
        delivered = [m.get("title", "") for m in self.merges_in(d0, d1, prod)] + [c["title"] for c in self.closed_in(d0, d1, prod)]
        if not delivered:
            return ("en curso", WARN, "Trabajo en curso, sin entregas")
        if all(FIX_RE.search(t) for t in delivered):
            return ("mantenimiento", INK2, "Solo correcciones")
        return ("avanzando", GOOD, "Funcionalidad nueva entregada")

    def alerts(self, d0, d1):
        out = []
        ref = d1
        # productos parados
        for p in PRODUCTS:
            last5 = business_days_back(ref, 5)
            prior = len(self.work_in(ref - dt.timedelta(29), ref - dt.timedelta(7), p["key"]))
            if prior >= 10 and sum(len(self.work_in(x, x, p["key"])) for x in last5) == 0:
                last = max((c["d"] for c in self.work if c["prod"] == p["key"]), default=None)
                out.append(("bad", f"{p['name']}: sin actividad en los últimos 5 días laborables" + (f" (última: {fecha_corta(last)})" if last else "")))
        # personas que han desaparecido
        for who in self.people_in(ref - dt.timedelta(60), ref):
            prev = len(self.work_in(ref - dt.timedelta(45), ref - dt.timedelta(15), who=who))
            recent = len(self.work_in(ref - dt.timedelta(14), ref, who=who))
            if prev >= 8 and recent == 0:
                last = max(c["d"] for c in self.work if c["who"] == who)
                out.append(("warn", f"{who}: sin actividad desde el {fecha_corta(last)} (antes, {prev} registros en un mes)"))
        # dependencia de una sola persona
        for p in PRODUCTS:
            w = self.work_in(ref - dt.timedelta(29), ref, p["key"])
            if len(w) >= 20:
                cnt = defaultdict(int)
                for c in w:
                    cnt[c["who"]] += 1
                top, n = max(cnt.items(), key=lambda kv: kv[1])
                if n / len(w) >= 0.9:
                    out.append(("info", f"{p['name']}: el {round(100*n/len(w))} % del trabajo del último mes es de una sola persona ({top})"))
        # PRs abiertos > 7 días (agrupados: los 2 más antiguos + recuento)
        aged = []
        for repo in self.open_prs:
            for pr, age in self.prs_open_at([repo], ref):
                if age >= 7:
                    aged.append((age, repo, pr))
        aged.sort(key=lambda x: -x[0])
        for age, repo, pr in aged[:2]:
            t = re.sub(r"^\d+\s+", "", pr["title"])
            out.append(("warn", f"{REPO_LABEL[repo]}: PR #{pr['n']} lleva {age} días sin integrar — «{t[:48]}{'…' if len(t)>48 else ''}»"))
        if len(aged) > 2:
            out.append(("warn", f"Otros {len(aged)-2} PRs llevan más de una semana sin integrar ({', '.join(sorted({REPO_LABEL[r].split(' ·')[0] for _, r, _ in aged[2:]}))})."))
        return out


# ------------------------------------------------------------------ SVG helpers
def esc(s):
    return (s or "").replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def hatch_defs():
    return ('<defs><pattern id="hatch" width="6" height="6" patternUnits="userSpaceOnUse" patternTransform="rotate(45)">'
            f'<rect width="6" height="6" fill="#D9DBE0"/><line x1="0" y1="0" x2="0" y2="6" stroke="{INK3}" stroke-width="2"/></pattern></defs>')


def fill_for(p):
    return "url(#hatch)" if p.get("hatch") else p["color"]


def sparkline(values, color, w=420, h=34, hatch=False, highlight_last=True, weekend_mask=None):
    """Barras diarias finas (30 días). Fines de semana en gris muy claro."""
    n = len(values)
    mx = max(values) or 1
    gap = 2
    bw = (w - gap * (n - 1)) / n
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" height="{h}" xmlns="http://www.w3.org/2000/svg">']
    if hatch:
        out.append(hatch_defs())
    out.append(f'<line x1="0" y1="{h-0.5}" x2="{w}" y2="{h-0.5}" stroke="{LINE}" stroke-width="1"/>')
    for i, v in enumerate(values):
        x = i * (bw + gap)
        bh = 0 if v == 0 else max(3, (h - 6) * v / mx)
        if weekend_mask and weekend_mask[i]:
            out.append(f'<rect x="{x:.1f}" y="{h-3}" width="{bw:.1f}" height="2" fill="{LINE}"/>')
            continue
        f = ("url(#hatch)" if hatch else color)
        if highlight_last and i == n - 1:
            out.append(f'<rect x="{x:.1f}" y="{h-1-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2" fill="{f}"/>')
        else:
            out.append(f'<rect x="{x:.1f}" y="{h-1-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="2" fill="{f}" opacity="{0.45 if highlight_last else 1}"/>')
    out.append("</svg>")
    return "".join(out)


def bar_pair(v_today, v_avg, color, label, fmt=lambda x: f"{x:g}", w=136, hatch=False):
    """Dos barras horizontales finas: hoy (color) vs media 30 días (gris). Etiquetas directas."""
    mx = max(v_today, v_avg, 0.01)
    bw = w - 52
    out = [f'<svg viewBox="0 0 {w} 34" width="{w}" height="34" xmlns="http://www.w3.org/2000/svg">']
    if hatch:
        out.append(hatch_defs())
    out.append(f'<text x="0" y="10" font-size="9" fill="{INK2}" font-weight="500">{esc(label)}</text>')
    x0 = 0
    l1, l2 = bw * v_today / mx, bw * v_avg / mx
    out.append(f'<rect x="{x0}" y="14" width="{max(l1,2):.1f}" height="7" rx="3.5" fill="{"url(#hatch)" if hatch else color}"/>')
    out.append(f'<text x="{x0+max(l1,2)+5:.1f}" y="20.5" font-size="9.5" fill="{INK}" font-weight="600">{esc(fmt(v_today))}</text>')
    out.append(f'<rect x="{x0}" y="25" width="{max(l2,2):.1f}" height="4" rx="2" fill="{INK3}"/>')
    out.append(f'<text x="{x0+max(l2,2)+5:.1f}" y="29.5" font-size="8" fill="{INK2}">media {esc(fmt(v_avg))}</text>')
    out.append("</svg>")
    return "".join(out)


def timeline(rows, w=680, h_row=26, start_h=7, end_h=20):
    """Una fila por persona; puntos = commits (color producto), franja = primer→último; horas a la derecha."""
    left = 130
    right_w = 110
    plot = w - left - right_w
    H = 18 + h_row * len(rows) + 10
    out = [f'<svg viewBox="0 0 {w} {H}" width="100%" xmlns="http://www.w3.org/2000/svg">', hatch_defs()]
    def X(hour):
        return left + plot * (hour - start_h) / (end_h - start_h)
    for hh in range(start_h, end_h + 1):
        x = X(hh)
        out.append(f'<line x1="{x:.1f}" y1="14" x2="{x:.1f}" y2="{H-8}" stroke="{LINE}" stroke-width="{1 if hh%3==0 else 0.5}"/>')
        if hh % 3 == 0 or hh == end_h:
            out.append(f'<text x="{x:.1f}" y="9" font-size="8" fill="{INK3}" text-anchor="middle">{hh:02d}h</text>')
    for i, r in enumerate(rows):
        y = 18 + h_row * i + h_row / 2
        out.append(f'<text x="0" y="{y+3:.1f}" font-size="10.5" fill="{INK}" font-weight="500">{esc(r["who"])}</text>')
        if r["points"]:
            hs = [p[0] for p in r["points"]]
            x0, x1 = X(max(start_h, min(hs))), X(min(end_h, max(hs)))
            out.append(f'<rect x="{x0-4:.1f}" y="{y-7:.1f}" width="{max(8, x1-x0+8):.1f}" height="14" rx="7" fill="{INK}" opacity="0.06"/>')
            for hour, prodkey in r["points"]:
                if hour < start_h or hour > end_h:
                    continue
                p = PROD[prodkey]
                out.append(f'<circle cx="{X(hour):.1f}" cy="{y:.1f}" r="4.5" fill="{fill_for(p)}" stroke="{SURF}" stroke-width="2"/>')
        else:
            out.append(f'<text x="{left+6}" y="{y+3:.1f}" font-size="9" fill="{INK3}">sin registros</text>')
        out.append(f'<text x="{w-2}" y="{y+4:.1f}" font-size="13" fill="{INK}" font-weight="500" text-anchor="end">{r["hours"]:g} h</text>')
        out.append(f'<text x="{w-42}" y="{y+3.5:.1f}" font-size="8" fill="{INK3}" text-anchor="end">media {r["avg"]:g} h</text>')
    out.append("</svg>")
    return "".join(out)


def stacked_people(rows, w=640, h_row=22):
    """Por persona: barra apilada por producto (commits 30 días), etiqueta directa del total."""
    left = 150
    plot = w - left - 60
    mx = max((sum(r["by"].values()) for r in rows), default=1) or 1
    H = h_row * len(rows) + 6
    out = [f'<svg viewBox="0 0 {w} {H}" width="100%" xmlns="http://www.w3.org/2000/svg">', hatch_defs()]
    for i, r in enumerate(rows):
        y = h_row * i + 4
        out.append(f'<text x="0" y="{y+12:.1f}" font-size="10.5" fill="{INK}" font-weight="500">{esc(r["who"])}</text>')
        x = left
        tot = sum(r["by"].values())
        for p in PRODUCTS:
            v = r["by"].get(p["key"], 0)
            if not v:
                continue
            L = plot * v / mx
            out.append(f'<rect x="{x:.1f}" y="{y+4}" width="{max(L-2,1):.1f}" height="10" rx="3" fill="{fill_for(p)}"/>')
            x += L
        out.append(f'<text x="{x+6:.1f}" y="{y+12.5:.1f}" font-size="9.5" fill="{INK2}">{tot}</text>')
    out.append("</svg>")
    return "".join(out)


def week_bars(vals, color, hatch=False, w=150, h=46):
    """5 barras (L..V) con etiqueta directa."""
    mx = max(vals) or 1
    gap, bw = 6, (w - 6 * 4) / 5
    out = [f'<svg viewBox="0 0 {w} {h}" width="{w}" height="{h}" xmlns="http://www.w3.org/2000/svg">']
    if hatch:
        out.append(hatch_defs())
    for i, v in enumerate(vals):
        x = i * (bw + gap)
        bh = 0 if v == 0 else max(3, (h - 22) * v / mx)
        out.append(f'<rect x="{x:.1f}" y="{h-12-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="3" fill="{"url(#hatch)" if hatch else color}"/>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{h-14-bh:.1f}" font-size="8.5" fill="{INK}" text-anchor="middle" font-weight="600">{v if v else ""}</text>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{h-2}" font-size="8" fill="{INK3}" text-anchor="middle">{DIAS_C[i]}</text>')
    out.append("</svg>")
    return "".join(out)


def hours_bars(rows, w=640, h_row=34):
    """Horas semana por persona: barra neutra + número grande; debajo, 5 puntos de presencia L..V."""
    left = 150
    plot = w - left - 70
    mx = max((r["hours"] for r in rows), default=1) or 1
    H = h_row * len(rows) + 4
    out = [f'<svg viewBox="0 0 {w} {H}" width="100%" xmlns="http://www.w3.org/2000/svg">']
    for i, r in enumerate(rows):
        y = h_row * i + 2
        out.append(f'<text x="0" y="{y+14:.1f}" font-size="10.5" fill="{INK}" font-weight="500">{esc(r["who"])}</text>')
        L = plot * r["hours"] / mx
        out.append(f'<rect x="{left}" y="{y+5}" width="{max(L,2):.1f}" height="12" rx="4" fill="{INK}" opacity="0.85"/>')
        out.append(f'<text x="{left+max(L,2)+8:.1f}" y="{y+15:.1f}" font-size="13" fill="{INK}" font-weight="600">{r["hours"]:g} h</text>')
        # presencia por día
        for j, hrs in enumerate(r["days"]):
            cx = left + 8 + j * 16
            if hrs > 0:
                out.append(f'<circle cx="{cx}" cy="{y+25}" r="3.2" fill="{INK2}"/>')
            else:
                out.append(f'<circle cx="{cx}" cy="{y+25}" r="3.2" fill="none" stroke="{LINE}" stroke-width="1.2"/>')
        out.append(f'<text x="{left+8+5*16+2}" y="{y+28}" font-size="7.5" fill="{INK3}">L M X J V · media {r["avg"]:g} h/día activo</text>')
    out.append("</svg>")
    return "".join(out)


def presence_grid(rows, days, w=680, row_h=22):
    """Persona × día laborable: círculo cuyo tamaño y tono crecen con las horas estimadas (0 = vacío)."""
    left, right = 130, 60
    colw = (w - left - right) / len(days)
    H = 22 + row_h * len(rows) + 4
    out = [f'<svg viewBox="0 0 {w} {H}" width="100%" xmlns="http://www.w3.org/2000/svg">']
    for j, d in enumerate(days):
        x = left + colw * (j + .5)
        out.append(f'<text x="{x:.1f}" y="9" font-size="8" fill="{INK3}" text-anchor="middle">{DIAS_C[d.weekday()]} {d.day}</text>')
    for i, r in enumerate(rows):
        y = 22 + row_h * i + row_h / 2
        out.append(f'<text x="0" y="{y+3.5:.1f}" font-size="10.5" fill="{INK}" font-weight="500">{esc(r["who"])}</text>')
        for j, hrs in enumerate(r["hours"]):
            x = left + colw * (j + .5)
            if hrs <= 0:
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="2.2" fill="none" stroke="{LINE}" stroke-width="1"/>')
            else:
                rad = 3.5 + 6.5 * min(hrs, 9) / 9
                op = 0.25 + 0.75 * min(hrs, 9) / 9
                out.append(f'<circle cx="{x:.1f}" cy="{y:.1f}" r="{rad:.1f}" fill="{INK}" opacity="{op:.2f}"/>')
        tot = sum(r["hours"])
        out.append(f'<text x="{w-2}" y="{y+4:.1f}" font-size="11" fill="{INK}" font-weight="500" text-anchor="end">{tot:g} h</text>')
    out.append("</svg>")
    return "".join(out)


def team_day_bars(days, hours, people, w=680, h=96):
    """Horas estimadas del equipo por día de la semana, con nº de personas activas bajo cada barra."""
    n = len(days)
    gap = 18
    bw = (w - gap * (n - 1)) / n
    mx = max(hours) or 1
    out = [f'<svg viewBox="0 0 {w} {h}" width="100%" xmlns="http://www.w3.org/2000/svg">']
    for i, (d, v, ppl) in enumerate(zip(days, hours, people)):
        x = i * (bw + gap)
        bh = 0 if v == 0 else max(3, (h - 40) * v / mx)
        out.append(f'<rect x="{x:.1f}" y="{h-26-bh:.1f}" width="{bw:.1f}" height="{bh:.1f}" rx="4" fill="{INK}" opacity="0.85"/>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{h-30-bh:.1f}" font-size="12" fill="{INK}" text-anchor="middle" font-weight="600">{v:g} h</text>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{h-13}" font-size="9" fill="{INK2}" text-anchor="middle">{DIAS[d.weekday()].capitalize()} {d.day}</text>')
        out.append(f'<text x="{x+bw/2:.1f}" y="{h-2}" font-size="8" fill="{INK3}" text-anchor="middle">{ppl} persona{"s" if ppl!=1 else ""}</text>')
    out.append("</svg>")
    return "".join(out)


# ------------------------------------------------------------------ HTML
def b64(path, mime):
    return f"data:{mime};base64," + base64.b64encode(Path(path).read_bytes()).decode()


def css():
    fp = SC / "fonts/InterTight.ttf"
    face = f"@font-face{{font-family:'Inter Tight';src:url({b64(fp, 'font/ttf')}) format('truetype');font-weight:100 900;}}" if fp.exists() else ""
    return f"""
{face}
@page{{size:A4;margin:0}}
*{{box-sizing:border-box}}
html,body{{margin:0;padding:0;background:{SURF};color:{INK};font-family:'Inter Tight',-apple-system,'Helvetica Neue',Arial,sans-serif;-webkit-font-smoothing:antialiased}}
.page{{width:210mm;height:297mm;padding:16mm 16mm 7mm;page-break-after:always;position:relative;overflow:hidden;background:{SURF};display:flex;flex-direction:column}}
.page:last-child{{page-break-after:auto}}
.hdr{{display:flex;justify-content:space-between;align-items:flex-start;margin-bottom:9mm}}
.hdr img{{height:11mm}}
.eyebrow{{font-size:9.5pt;letter-spacing:.14em;text-transform:uppercase;color:{INK2};font-weight:600}}
h1{{font-size:26pt;font-weight:600;letter-spacing:-.02em;margin:1.5mm 0 0;line-height:1.05}}
h1 small{{display:block;font-size:12pt;font-weight:400;color:{INK2};letter-spacing:0;margin-top:1.5mm}}
h2{{font-size:13.5pt;font-weight:600;letter-spacing:-.01em;margin:0 0 3mm}}
h2 span{{color:{INK2};font-weight:400;font-size:10pt;margin-left:2mm}}
.tiles{{display:grid;grid-template-columns:repeat(4,1fr);gap:4mm;margin-bottom:8mm}}
.tile{{background:{CARD};border-radius:5mm;padding:5mm 5mm 4.5mm}}
.tile .k{{font-size:9pt;color:{INK2};font-weight:500}}
.tile .v{{font-size:30pt;font-weight:300;letter-spacing:-.03em;line-height:1;margin:2mm 0 1.5mm}}
.tile .v small{{font-size:13pt;color:{INK2};font-weight:400;margin-left:1mm}}
.tile .d{{font-size:8.5pt;color:{INK2}}}
.tile .d b{{font-weight:600}}
.up{{color:{GOOD}}}.down{{color:{BAD}}}
.sem{{display:grid;grid-template-columns:repeat(6,minmax(0,1fr));gap:2.5mm;margin-bottom:7mm}}
.sem .p{{background:{CARD};border-radius:4mm;padding:3mm 3mm;display:flex;gap:2mm;align-items:center;min-width:0}}
.sem .p>div{{min-width:0}}
.dot{{width:4.5mm;height:4.5mm;border-radius:50%;flex:none}}
.dot.h{{background:repeating-linear-gradient(45deg,#D9DBE0 0 2px,{INK3} 2px 3px)}}
.sem .n{{font-size:8pt;font-weight:600;line-height:1.15}}
.sem .s{{font-size:7.5pt;color:{INK2};margin-top:.5mm}}
.pill{{display:inline-block;font-size:7.5pt;font-weight:600;padding:.8mm 2.2mm;border-radius:2mm;letter-spacing:.02em;text-transform:uppercase}}
.rel{{margin-bottom:6mm}}
.rel li{{font-size:10pt;line-height:1.38;margin:0 0 1.8mm;padding-left:5mm;position:relative}}
.rel li::before{{content:'';position:absolute;left:0;top:.42em;width:2.2mm;height:2.2mm;border-radius:50%;background:var(--c,{INK})}}
.rel li b{{font-weight:600}}
.alerts{{border-radius:4mm;padding:4mm 5mm;margin-top:auto}}
.alerts .t{{font-size:9pt;font-weight:600;margin-bottom:1.5mm;letter-spacing:.04em;text-transform:uppercase}}
.alerts li{{font-size:8.5pt;line-height:1.35;margin:0 0 1mm;list-style:none}}
.alerts ul{{margin:0;padding:0}}
.ab{{color:{BAD}}}.aw{{color:{WARN}}}.ai{{color:{INK2}}}
.rows .r{{display:grid;grid-template-columns:44mm minmax(0,1fr) 14mm;gap:3mm;align-items:center;padding:.6mm 0;border-bottom:1px solid {LINE}}}
.rows .r:last-child{{border-bottom:0}}
.rows .n{{font-size:9.5pt;font-weight:600;display:flex;align-items:center;gap:2mm}}
.rows .n i{{width:2.6mm;height:2.6mm;border-radius:50%;display:inline-block}}
.rows .n i.h{{background:repeating-linear-gradient(45deg,#D9DBE0 0 1px,{INK3} 1px 2px)}}
.rows .v{{font-size:13pt;font-weight:300;text-align:right;letter-spacing:-.02em;line-height:1}}
.rows .v small{{font-size:7.5pt;color:{INK3};display:block;font-weight:400;letter-spacing:0}}
.cards{{display:grid;grid-template-columns:minmax(0,1fr) minmax(0,1fr);gap:4mm}}
.card{{background:{CARD};border-radius:5mm;padding:4mm 5mm 3.5mm;border-top:1.2mm solid var(--c);min-width:0}}
.card .m>*{{min-width:0;flex:1}}
.card .h{{display:flex;justify-content:space-between;align-items:center;margin-bottom:2.5mm}}
.card .h b{{font-size:11pt;font-weight:600}}
.card p{{font-size:8.3pt;line-height:1.36;color:{INK};margin:1.8mm 0}}
.card .who{{display:flex;gap:1.5mm;flex-wrap:wrap;margin-top:2mm}}
.chip{{font-size:7.5pt;font-weight:600;background:#fff;border:1px solid {LINE};border-radius:2mm;padding:.7mm 2mm;color:{INK2}}}
.card .m{{display:flex;gap:4mm;align-items:flex-start;margin-top:1mm}}
.card .kv{{font-size:8pt;color:{INK2};margin-top:2.5mm;display:flex;gap:4mm}}
.card .kv b{{color:{INK};font-weight:600}}
.note{{margin-top:auto;flex:none;width:100%;font-size:7.5pt;color:{INK2};line-height:1.4;border-top:1px solid {LINE};padding-top:2.5mm;white-space:normal}}
.note:empty{{border:0;padding:0}}
.foot{{flex:none;width:100%;font-size:7pt;color:{INK3};display:flex;justify-content:space-between;margin-top:2.5mm}}
.alerts+.foot{{margin-top:3mm}}
.legend{{display:flex;gap:4mm;flex-wrap:wrap;font-size:8pt;color:{INK2};margin:1mm 0 3mm}}
.legend i{{width:2.6mm;height:2.6mm;border-radius:50%;display:inline-block;margin-right:1.2mm;vertical-align:-.3mm}}
.legend i.h{{background:repeating-linear-gradient(45deg,#D9DBE0 0 1px,{INK3} 1px 2px)}}
.sec{{margin-bottom:5mm}}
.small{{font-size:8.5pt;color:{INK2}}}
.numline{{display:flex;align-items:baseline;gap:2mm}}
.numline b{{font-size:15pt;font-weight:300;letter-spacing:-.02em}}
"""


def header(logo, eyebrow, title, sub, right):
    return f"""<div class="hdr"><div><div class="eyebrow">{esc(eyebrow)}</div><h1>{esc(title)}<small>{esc(sub)}</small></h1></div>
<div style="text-align:right"><img src="{logo}" alt="Global Eye Analytics"><div class="small" style="margin-top:1.5mm">{esc(right)}</div></div></div>"""


def footer(page, total, txt):
    return f'<div class="foot"><span>Global Eye Analytics · Quantum · {esc(txt)}</span><span>{page} / {total}</span></div>'


def legend():
    items = "".join(f'<span><i class="{"h" if p.get("hatch") else ""}" style="background:{"" if p.get("hatch") else p["color"]}"></i>{esc(p["name"])}</span>' for p in PRODUCTS)
    return f'<div class="legend">{items}</div>'


def delta(v, avg, unit=""):
    if avg == 0 and v == 0:
        return f'<span class="d">sin referencia</span>'
    if avg == 0:
        return f'<span class="d">media 30 d: <b>0{unit}</b></span>'
    pct = (v - avg) / avg * 100
    cls = "up" if pct >= 0 else "down"
    arrow = "▲" if pct >= 0 else "▼"
    return f'<span class="d"><b class="{cls}">{arrow} {abs(pct):.0f} %</b> vs media 30 d ({avg:g}{unit})</span>'


def alerts_block(items):
    if not items:
        return ""
    worst = "bad" if any(k == "bad" for k, _ in items) else ("warn" if any(k == "warn" for k, _ in items) else "info")
    bg = {"bad": "#FBEDEB", "warn": "#FBF3E3", "info": CARD}[worst]
    col = {"bad": BAD, "warn": WARN, "info": INK2}[worst]
    lis = "".join(f'<li class="{ {"bad":"ab","warn":"aw","info":"ai"}[k] }">{esc(t)}</li>' for k, t in items[:6])
    if len(items) > 6:
        lis += f'<li class="ai">… y {len(items)-6} avisos más.</li>'
    return f'<div class="alerts" style="background:{bg}"><div class="t" style="color:{col}">Atención</div><ul>{lis}</ul></div>'


METHOD = ("Método. Las horas estiman, por persona y día, la franja entre su primer y último registro de trabajo (+1 h de arranque; mínimo 2 h, máximo 9 h). "
          "Miden actividad registrada en el código, no jornada ni rendimiento: no incluyen diseño, reuniones, revisión de otros ni pruebas manuales. "
          "Entregas = integraciones a la rama principal. Funcionalidades = incidencias cerradas en GitHub. Se cuentan todas las ramas de trabajo. "
          "Los fines de semana y festivos no se consideran inactividad. Fuente: GitHub, organización Global-Eye.")


# ------------------------------------------------------------------ informe diario
def daily(D, data, nar):
    logo = b64(SC / "logo.png", "image/png")
    d30 = D - dt.timedelta(29)
    bdays30 = [d30 + dt.timedelta(i) for i in range(30) if is_business(d30 + dt.timedelta(i))]
    nb = len(bdays30) or 1
    people_today = data.people_in(D, D)
    merges_today = data.merges_in(D, D)
    closed_today = data.closed_in(D, D)
    hours_today = sum(data.hours(w, D) for w in people_today)
    avg_people = sum(len(data.people_in(x, x)) for x in bdays30) / nb
    avg_merges = len(data.merges_in(d30, D)) / nb
    avg_hours = sum(data.hours(w, x) for x in bdays30 for w in data.people_in(x, x)) / nb
    active_prods = [p for p in PRODUCTS if data.work_in(d30, D, p["key"])]
    quiet_prods = [p for p in PRODUCTS if not data.work_in(d30, D, p["key"])]
    N = 3
    pages = []

    # ---- página 1
    tiles = f"""<div class="tiles">
<div class="tile"><div class="k">Personas activas</div><div class="v">{len(people_today)}</div>{delta(len(people_today), round(avg_people,1))}</div>
<div class="tile"><div class="k">Entregas</div><div class="v">{len(merges_today)}</div>{delta(len(merges_today), round(avg_merges,1))}</div>
<div class="tile"><div class="k">Funcionalidades cerradas</div><div class="v">{len(closed_today)}</div><span class="d">incidencias cerradas en GitHub</span></div>
<div class="tile"><div class="k">Actividad estimada</div><div class="v">{hours_today:g}<small>h</small></div>{delta(hours_today, round(avg_hours,1), " h")}</div>
</div>"""
    sem = '<div class="sem">' + "".join(
        (lambda st: f'<div class="p"><div class="dot {"h" if p.get("hatch") else ""}" style="background:{"" if p.get("hatch") else p["color"]}"></div><div><div class="n">{esc(p["name"])}</div><div class="s" style="color:{st[1]};font-weight:600">{st[0].capitalize()}</div></div></div>')(data.status(p["key"], D))
        for p in active_prods) + "</div>"
    rel = "".join(f'<li style="--c:{PROD[k]["color"] if k in PROD else INK}"><b>{esc(PROD[k]["name"] if k in PROD else k)}.</b> {esc(t)}</li>' for k, t in nar.get("relevante", []))
    p1 = f"""<div class="page">{header(logo, "Avance diario · Quantum", fecha_larga(D).capitalize(), "Actividad de desarrollo en todos los repositorios de Global Eye", "Elaborado a las 19:00")}
{tiles}
<h2>Estado por producto <span>hoy</span></h2>{sem}
<h2>Lo más relevante</h2><ul class="rel" style="padding:0;margin:0;list-style:none">{rel}</ul>
<div style="flex:1"></div>
{alerts_block(data.alerts(D, D))}
{footer(1, N, "Informe diario")}</div>"""
    pages.append(p1)

    # ---- página 2: productos
    wk_mask = [not is_business(d30 + dt.timedelta(i)) for i in range(30)]
    rows = "".join(
        f'<div class="r"><div class="n"><i class="{"h" if p.get("hatch") else ""}" style="background:{"" if p.get("hatch") else p["color"]}"></i>{esc(p["name"])}</div>'
        f'<div>{sparkline(data.trend(p["key"], D), p["color"], hatch=p.get("hatch"), weekend_mask=wk_mask)}</div>'
        f'<div class="v">{len(data.work_in(D, D, p["key"]))}<small>hoy</small></div></div>'
        for p in active_prods)
    cards = []
    today_prods = [p for p in active_prods if data.work_in(D, D, p["key"])]
    rest_prods = [p for p in active_prods if p not in today_prods]
    for p in today_prods[:4]:
        k = p["key"]
        st = data.status(k, D)
        who = sorted({c["who"] for c in data.work_in(D, D, k)})
        m_today = len(data.merges_in(D, D, k)); m_avg = len(data.merges_in(d30, D, k)) / nb
        h_today = sum(data.hours(w, D) for w in who)
        h_avg = sum(data.hours(w, x) for x in bdays30 for w in {c["who"] for c in data.work_in(x, x, k)}) / nb
        prs = data.prs_open_at(p["repos"], D)
        oldest = max((age for _, age in prs), default=0)
        txt = nar.get("productos", {}).get(k, "Sin entregas relevantes hoy." if not who else "Trabajo en curso.")
        cards.append(f"""<div class="card" style="--c:{p["color"]}"><div class="h"><b>{esc(p["name"])}</b><span class="pill" style="background:{st[1]}22;color:{st[1]}">{esc(st[0])}</span></div>
<div class="m">{bar_pair(m_today, round(m_avg,1), p["color"], "Entregas", hatch=p.get("hatch"))}{bar_pair(h_today, round(h_avg,1), p["color"], "Horas estimadas", fmt=lambda x: f"{x:g} h", hatch=p.get("hatch"))}</div>
<p>{esc(txt)}</p>
<div class="who">{"".join(f'<span class="chip">{esc(w)}</span>' for w in who) or '<span class="chip" style="color:'+INK3+'">nadie hoy</span>'}</div>
<div class="kv"><span>PRs abiertos <b>{len(prs)}</b></span><span>El más antiguo <b>{oldest} d</b></span><span>Cerradas hoy <b>{len(data.closed_in(D, D, k))}</b></span></div></div>""")
    quiet = (("Sin actividad hoy: " + ", ".join(p["name"] for p in rest_prods) + ". ") if rest_prods else "") + \
            (("Sin actividad en 30 días: " + ", ".join(p["name"] for p in quiet_prods) + ".") if quiet_prods else "")
    p2 = f"""<div class="page">{header(logo, "Avance diario · Quantum", "Los productos", "Ritmo de los últimos 30 días y detalle de hoy", fecha_larga(D))}
<h2>Treinta días de actividad <span>una barra por día · gris = fin de semana o festivo</span></h2>
<div class="rows sec">{rows}</div>
<h2>Detalle de hoy</h2>
<div class="cards">{"".join(cards)}</div>
<div class="note">{esc(quiet)}</div>
{footer(2, N, "Informe diario")}</div>"""
    pages.append(p2)

    # ---- página 3: personas
    people30 = data.people_in(d30, D)
    people14 = data.people_in(D - dt.timedelta(13), D)
    tl_rows = []
    for w in sorted(people14, key=lambda w: (-data.hours(w, D), w)):
        pts = [(c["t"].hour + c["t"].minute / 60, c["prod"]) for c in data.work_in(D, D, who=w)]
        act = [data.hours(w, x) for x in bdays30 if data.hours(w, x) > 0]
        tl_rows.append(dict(who=w, points=pts, hours=data.hours(w, D), avg=round(sum(act) / len(act), 1) if act else 0))
    bdays10 = business_days_back(D, 10)
    absent14 = sorted(set(people30) - set(people14))
    absent_txt = ("Activos en el último mes pero sin registros en las dos últimas semanas: " + ", ".join(absent14) + ".") if absent14 else ""
    st_rows = []
    for w in people30:
        by = defaultdict(int)
        for c in data.work_in(d30, D, who=w):
            by[c["prod"]] += 1
        st_rows.append(dict(who=w, by=dict(by)))
    st_rows.sort(key=lambda r: -sum(r["by"].values()))
    p3 = f"""<div class="page">{header(logo, "Avance diario · Quantum", "Las personas", "Cuándo y en qué ha trabajado cada persona", fecha_larga(D))}
<h2>El día, hora a hora <span>cada punto es un registro de trabajo · color = producto</span></h2>
{legend()}
<div class="sec">{timeline(tl_rows)}</div>
<h2>Las dos últimas semanas <span>horas estimadas por persona y día laborable · más grande y oscuro = más horas</span></h2>
<div class="sec">{presence_grid([dict(who=r["who"], hours=[data.hours(r["who"], x) for x in bdays10]) for r in tl_rows], bdays10)}</div>
<h2>En qué anda cada uno <span>últimos 30 días · registros de trabajo por producto</span></h2>
<div class="sec">{stacked_people(st_rows)}</div>
<div class="small">{esc(absent_txt)}</div>
<div class="note">{METHOD}</div>
{footer(3, N, "Informe diario")}</div>"""
    pages.append(p3)
    return f"<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Avance diario Quantum {D}</title><style>{css()}</style></head><body>{''.join(pages)}</body></html>"


# ------------------------------------------------------------------ informe semanal
def weekly(F, data, nar):
    logo = b64(SC / "logo.png", "image/png")
    M = F - dt.timedelta(F.weekday())
    days = [M + dt.timedelta(i) for i in range(5)]
    pM, pF = M - dt.timedelta(7), F - dt.timedelta(7)
    d30 = F - dt.timedelta(29)
    N = 3
    people = data.people_in(M, F); people_prev = data.people_in(pM, pF)
    merges = data.merges_in(M, F); merges_prev = data.merges_in(pM, pF)
    closed = data.closed_in(M, F)
    hours = sum(data.hours_range(w, M, F) for w in people); hours_prev = sum(data.hours_range(w, pM, pF) for w in people_prev)
    active_prods = [p for p in PRODUCTS if data.work_in(d30, F, p["key"])]
    quiet_prods = [p for p in PRODUCTS if not data.work_in(d30, F, p["key"])]

    def dl(v, prev, unit=""):
        if prev == 0:
            return f'<span class="d">semana anterior: <b>{prev:g}{unit}</b></span>'
        pct = (v - prev) / prev * 100
        return f'<span class="d"><b class="{"up" if pct>=0 else "down"}">{"▲" if pct>=0 else "▼"} {abs(pct):.0f} %</b> vs semana anterior ({prev:g}{unit})</span>'

    rango = f"{M.day} – {F.day} de {MESES[F.month-1]} de {F.year}" if M.month == F.month else f"{M.day} de {MESES[M.month-1]} – {F.day} de {MESES[F.month-1]} de {F.year}"
    tiles = f"""<div class="tiles">
<div class="tile"><div class="k">Personas activas</div><div class="v">{len(people)}</div>{dl(len(people), len(people_prev))}</div>
<div class="tile"><div class="k">Entregas</div><div class="v">{len(merges)}</div>{dl(len(merges), len(merges_prev))}</div>
<div class="tile"><div class="k">Funcionalidades cerradas</div><div class="v">{len(closed)}</div><span class="d">incidencias cerradas en GitHub</span></div>
<div class="tile"><div class="k">Actividad estimada</div><div class="v">{hours:g}<small>h</small></div>{dl(hours, hours_prev, " h")}</div>
</div>"""
    sem = '<div class="sem">' + "".join(
        (lambda st: f'<div class="p"><div class="dot {"h" if p.get("hatch") else ""}" style="background:{"" if p.get("hatch") else p["color"]}"></div><div><div class="n">{esc(p["name"])}</div><div class="s" style="color:{st[1]};font-weight:600">{st[0].capitalize()}</div></div></div>')(data.status_week(p["key"], M, F))
        for p in active_prods) + "</div>"
    rel = "".join(f'<li style="--c:{PROD[k]["color"] if k in PROD else INK}"><b>{esc(PROD[k]["name"] if k in PROD else k)}.</b> {esc(t)}</li>' for k, t in nar.get("relevante", []))
    p1 = f"""<div class="page">{header(logo, "Resumen semanal · Quantum", f"Semana {F.isocalendar()[1]}", rango, "Elaborado el viernes a las 19:00")}
{tiles}
<h2>Estado por producto <span>esta semana</span></h2>{sem}
<h2>Lo más relevante de la semana</h2><ul class="rel" style="padding:0;margin:0;list-style:none">{rel}</ul>
<div style="flex:1"></div>
{alerts_block(data.alerts(M, F))}
{footer(1, N, "Resumen semanal")}</div>"""

    # ---- página 2
    cards = []
    main_prods = [p for p in active_prods if data.status_week(p["key"], M, F)[0] != "esporádico"]
    spor_prods = [p for p in active_prods if p not in main_prods]
    for p in main_prods[:4]:
        k = p["key"]
        st = data.status_week(k, M, F)
        per_day = [len(data.work_in(d, d, k)) for d in days]
        who = defaultdict(int)
        for c in data.work_in(M, F, k):
            who[c["who"]] += 1
        prs = data.prs_open_at(p["repos"], F)
        oldest = max((age for _, age in prs), default=0)
        txt = nar.get("productos", {}).get(k, "Sin actividad esta semana." if not who else "Trabajo en curso.")
        chips = "".join(f'<span class="chip">{esc(w)} · {n}</span>' for w, n in sorted(who.items(), key=lambda kv: -kv[1]))
        cards.append(f"""<div class="card" style="--c:{p["color"]}"><div class="h"><b>{esc(p["name"])}</b><span class="pill" style="background:{st[1]}22;color:{st[1]}">{esc(st[0])}</span></div>
<div style="display:flex;gap:5mm;align-items:flex-end"><div>{week_bars(per_day, p["color"], hatch=p.get("hatch"))}<div class="small" style="margin-top:-1mm">registros de trabajo por día</div></div>
<div style="flex:1"><div class="numline"><b>{len(data.merges_in(M, F, k))}</b><span class="small">entregas</span></div><div class="numline"><b>{len(data.closed_in(M, F, k))}</b><span class="small">funcionalidades cerradas</span></div><div class="numline"><b>{sum(per_day)}</b><span class="small">registros de trabajo</span></div></div></div>
<p>{esc(txt)}</p>
<div class="who">{chips or '<span class="chip" style="color:'+INK3+'">nadie</span>'}</div>
<div class="kv"><span>PRs abiertos <b>{len(prs)}</b></span><span>El más antiguo <b>{oldest} d</b></span></div></div>""")
    spor = "".join(
        f'<div class="r"><div class="n"><i class="{"h" if p.get("hatch") else ""}" style="background:{"" if p.get("hatch") else p["color"]}"></i>{esc(p["name"])}</div>'
        f'<div class="small">{esc(nar.get("productos", {}).get(p["key"], "Sin desarrollo activo."))}</div>'
        f'<div class="v">{len(data.work_in(M, F, p["key"]))}<small>semana</small></div></div>'
        for p in spor_prods)
    quiet = ("Sin actividad en 30 días: " + ", ".join(p["name"] for p in quiet_prods) + ".") if quiet_prods else ""
    p2 = f"""<div class="page">{header(logo, "Resumen semanal · Quantum", "Los productos", "Qué ha avanzado cada desarrollo esta semana", rango)}
<div class="cards sec">{"".join(cards)}</div>
{('<h2>Actividad esporádica <span>productos sin desarrollo activo este mes</span></h2><div class="rows">' + spor + '</div>') if spor_prods else ''}
<div class="note">{esc(quiet)}</div>
{footer(2, N, "Resumen semanal")}</div>"""

    # ---- página 3
    hrows = []
    for w in people:
        dh = [data.hours(w, d) for d in days]
        act = [x for x in dh if x > 0]
        hrows.append(dict(who=w, hours=sum(dh), days=dh, avg=round(sum(act) / len(act), 1) if act else 0))
    hrows.sort(key=lambda r: -r["hours"])
    st_rows = []
    for w in people:
        by = defaultdict(int)
        for c in data.work_in(M, F, who=w):
            by[c["prod"]] += 1
        st_rows.append(dict(who=w, by=dict(by)))
    st_rows.sort(key=lambda r: -sum(r["by"].values()))
    # ausentes: activos en los 30 días previos pero no esta semana
    prev_people = set(data.people_in(F - dt.timedelta(35), M - dt.timedelta(1))) - set(people)
    aus = ", ".join(sorted(prev_people)) if prev_people else "nadie"
    p3 = f"""<div class="page">{header(logo, "Resumen semanal · Quantum", "Las personas", "Dedicación estimada y reparto por producto", rango)}
<h2>Horas estimadas esta semana <span>puntos = días con actividad (L a V)</span></h2>
<div class="sec">{hours_bars(hrows)}</div>
<h2>El equipo, día a día <span>horas estimadas sumadas y personas activas</span></h2>
<div class="sec">{team_day_bars(days, [sum(data.hours(w, d) for w in data.people_in(d, d)) for d in days], [len(data.people_in(d, d)) for d in days])}</div>
<h2>Reparto por producto <span>registros de trabajo de la semana</span></h2>
{legend()}
<div class="sec">{stacked_people(st_rows)}</div>
<div class="small" style="margin-top:2mm">Activos en el último mes pero sin actividad esta semana: <b>{esc(aus)}</b>.</div>
<div class="note">{METHOD}</div>
{footer(3, N, "Resumen semanal")}</div>"""
    return f"<!doctype html><html lang='es'><head><meta charset='utf-8'><title>Resumen semanal Quantum {F}</title><style>{css()}</style></head><body>{p1}{p2}{p3}</body></html>"


# ------------------------------------------------------------------ main
def dump(data, d0, d1):
    for p in PRODUCTS:
        w = data.work_in(d0, d1, p["key"])
        m = data.merges_in(d0, d1, p["key"])
        if not w and not m:
            continue
        print(f"\n===== {p['name']}  work={len(w)} merges={len(m)}")
        byday = defaultdict(list)
        for c in sorted(w, key=lambda c: c["t"]):
            byday[c["d"]].append(c)
        for d in sorted(byday):
            print(f"--- {d} ({DIAS[d.weekday()]})")
            for c in byday[d]:
                print(f"  {c['t'].strftime('%H:%M')} {c['who']:<22} {REPO_LABEL[c['repo']][:14]:<14} {c['subj'][:110]}")
        print("  PRs merged:", "; ".join(f"#{x['pr']} {x['title'][20:90]}" for x in sorted(m, key=lambda c: c["t"])))
        cl = data.closed_in(d0, d1, p["key"])
        if cl:
            print("  Issues closed:", "; ".join(f"#{x['n']} {x['title'][:60]}" for x in cl))
    print("\n===== horas por persona/día")
    for d in [d0 + dt.timedelta(i) for i in range((d1 - d0).days + 1)]:
        ps = data.people_in(d, d)
        if ps:
            print(d, DIAS[d.weekday()], {w: data.hours(w, d) for w in ps})


if __name__ == "__main__":
    mode = sys.argv[1]
    data = Data()
    if mode == "dump":
        dump(data, dt.date.fromisoformat(sys.argv[2]), dt.date.fromisoformat(sys.argv[3]))
    else:
        D = dt.date.fromisoformat(sys.argv[2])
        nar_all = json.loads((SC / "narratives.json").read_text(encoding="utf-8")) if (SC / "narratives.json").exists() else {}
        nar = nar_all.get(f"{mode}-{D}", {})
        html = daily(D, data, nar) if mode == "daily" else weekly(D, data, nar)
        _n = iter(range(1, 20))
        html = re.sub(r'<div class="page">', lambda m: f'<div class="page" id="p{next(_n)}">', html)
        out = SC / f"out/{mode}-{D}.html"
        out.parent.mkdir(exist_ok=True)
        out.write_text(html, encoding="utf-8")
        print(out)
