# GitHub Templates - Referencia Rápida

## 📌 Estructura de titulos en Issues

```
APP | Módulo | Sección | Funcionalidad
```

**Ejemplos:**
- `Application 1 | Actividades | Calendario | Seguimiento mensual`
- `[BUG] Aplication 2 | Fichas | Validación email - No rechaza caracteres especiales`
- `TASK | Aplication 1 | Clientes | Crear endpoints de filtrado`

---

## 🎯 Tipos de Issues

### 1️⃣ Feature - Nueva Funcionalidad
Usa cuando añadas una nueva funcionalidad, módulo o sección.

**Campos principales:**
- **Objetivo**: Qué se quiere lograr
- **Historia de Usuario**: Contexto del usuario
- **Criterios de Aceptación**: Condiciones que deben cumplirse
- **DoD**: Tareas técnicas necesarias
- **Estimación**: Puntos de complejidad (1, 2, 3, 5, 8, 13)

---

### 🐛 Bug - Error a Corregir
Usa cuando reportes un comportamiento inesperado o error.

**Campos principales:**
- **Descripción del Error**: Qué está mal
- **Cómo Reproducir**: Pasos exactos para reproducirlo
- **Comportamiento Esperado**: Qué debería pasar
- **Comportamiento Actual**: Qué sucede ahora
- **Logs/Capturas**: Evidencia del problema (opcional pero ayuda)

---

### ✔️ Task - Tarea Concreta
Usa para tareas específicas que completan una Feature o Bug.

**Campos principales:**
- **Descripción**: Qué hay que hacer
- **Detalles/Requisitos**: Info técnica
- **Issue Padre**: A qué Feature/Bug pertenece (#XXX)

---

## 📤 Pull Request Template

Toda PR debe:
1. **Relacionarse con una issue**: `Cierra: #123`
2. **Describir brevemente** los cambios
3. **Completar el checklist** antes de pedir review
4. **Referenciar screenshots** si hay cambios visuales
5. **Indicar breaking changes** si los hay

**Rama naming:**
- Feature: `feature/{issue-number}` o `feature/{description}`
- Bug fix: `fix/{issue-number}` o `fix/{description}`

---

## 🔄 Flujo de Trabajo

```
1. Crear Issue (Feature/Bug/Task)
2. ↓
3. Crear Branch desde main
4. ↓
5. Desarrollar y hacer commits pequeños
6. ↓
7. Abrir Pull Request
8. ↓
9. Review (mínimo 1 reviewer)
10. ↓
11. Merge Commit
12. ↓
13. Eliminar branch
14. ↓
15. Marcar Issue como Done
```

---

## ⚡ Tips de Agilidad

✅ **Hazlo simple:**
- No hagas PRs enormes, divídelas en partes
- Issues pequeñas = más fáciles de trackear
- Commits cortos facilitan el review

✅ **Comunica bien:**
- Estructura clara en titles = búsqueda fácil
- Criterios de aceptación = menos preguntas
- DoD = menos vueltas de review

✅ **Automatiza:**
- Usa templates = menos tiempo escribiendo
- Labels = better filtering en el board
- Links en PRs = autoclose de issues

---

