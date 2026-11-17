# Informe de actividad Quantum

Genera cada tarde (19:00 hora peninsular) un PDF de tres páginas con la actividad de desarrollo de todos los repositorios activos de Global-Eye, y los viernes un resumen semanal. Pensado para lectores no técnicos que necesitan comparar el nivel de actividad entre productos y entre personas, con la marca de Global Eye y los colores oficiales de cada aplicación Quantum.

## Archivos

| Archivo | Para qué |
|---|---|
| `ROUTINE_PROMPT.md` | Instrucciones completas que ejecuta la sesión programada (Routine) cada tarde. |
| `config.json` | Destinatarios, asuntos, zona horaria. |
| `extract.sh` | Vuelca los commits de todas las ramas de los repos clonados a `data/commits.tsv`. |
| `build.py` | Calcula métricas y genera el HTML A4 (`daily` / `weekly` / `dump`). |
| `render.sh` | HTML → PDF con Chromium; descarga la tipografía Inter Tight si falta; opcionalmente capturas por página. |
| `logo.png` | Logo Global Eye (el mismo que usan las apps). |
| `narratives.example.json` | Ejemplo del texto de negocio que redacta Claude cada día. |

## Qué mide y cómo

- **Registros de trabajo**: commits que no son merges, por fecha de autor, en todas las ramas (una funcionalidad en curso cuenta aunque no esté integrada).
- **Entregas**: integraciones de PR en la rama principal.
- **Funcionalidades cerradas**: incidencias cerradas en GitHub.
- **Horas estimadas**: por persona y día, franja entre el primer y el último registro + 1 h de arranque, mínimo 2 h, máximo 9 h. **Mide actividad registrada, no jornada ni rendimiento**: no incluye diseño, reuniones, revisión de PRs ni pruebas manuales. Esta nota aparece en el pie de cada informe y no debe quitarse.
- **Estado por producto**: *avanzando* (funcionalidad nueva entregada), *mantenimiento* (solo correcciones), *en curso* (trabajo sin entregas), *sin actividad hoy*, *parado* (5 días laborables sin actividad en un producto que estaba activo), *esporádico* (menos de 10 registros en 30 días).
- **Fines de semana y festivos nacionales** no cuentan como inactividad.
- **Alertas**: persona activa que lleva 2 semanas sin registros; producto con más del 90 % del trabajo mensual de una sola persona; PRs con más de 7 días sin integrar.

## Colores

Resi `#006BBC` · CRM `#EF7D00` · Infraestructuras `#0B8F7A` · Identity `#6B4E9B` · Team `#B23A48` · Plataforma común (ERP, Layout Lib, Auth Lib) gris rayado. La paleta de cinco tonos pasa la validación de daltonismo; el naranja de CRM siempre lleva etiqueta de texto porque no alcanza 3:1 sobre el fondo.

## Ejecución manual

```bash
bash extract.sh data quantum.resi.back quantum.resi.front quantum.infraestructuras.backend ...
# escribir data/github.json y narratives.json (ver ROUTINE_PROMPT.md)
bash render.sh daily 2026-09-03 png     # png = capturas por página para revisar
bash render.sh weekly 2026-09-04
```

Requisitos: Python 3.11+, Chromium (Playwright lo deja en `/opt/pw-browsers`), acceso a fonts.googleapis.com para la tipografía (si no, cae a la sans del sistema).
