# Ritual de actualización post-ejecución

Este documento codifica el **flujo de trabajo obligatorio** cada vez que se ejecuta (o re-ejecuta) un notebook del proyecto. El objetivo es mantener la narrativa del proyecto viva y respaldada por **prints reales verificables**, no por números aspiracionales.

## Por qué existe este documento

Los reportes en `reports/` son **insumos del informe final**. Si los números ahí no coinciden con los outputs reales del notebook, el informe pierde credibilidad académica. Este ritual garantiza la consistencia.

---

## El ritual — 5 pasos obligatorios tras Run All

### Paso 1: Analizar los prints reales

Abrir el notebook ejecutado y revisar **cada celda con output**. Buscar:

- Números clave (cobertura, CER, errores, tiempos)
- Mensajes inesperados (warnings, errors benignos)
- Distribuciones que difieran de las esperadas
- Ejemplos mostrados (primeras N filas) — buscar casos atípicos

Extraer los outputs textuales a un archivo `_nb_outputs/nbXX.txt` con:

```bash
python -c "
import json, os
nb = json.loads(open('notebooks/nbXX.ipynb', encoding='utf-8').read())
with open('_nb_outputs/nbXX.txt', 'w', encoding='utf-8') as fo:
    for i, c in enumerate(nb['cells']):
        if c['cell_type'] != 'code' or not c.get('outputs'): continue
        text = ''.join(
            ''.join(o.get('text', ''))
            for o in c['outputs']
            if 'text' in o
        )
        if text.strip():
            fo.write(f'### Cell {i} ###\n{text}\n\n')
"
```

### Paso 2: Actualizar el reporte correspondiente

En `reports/nbXX_resultados.md`:

1. **Sección 4 (Los resultados):** reemplazar números esperados con números reales. Embeber los prints exactos en bloques ````` ```.

2. **Sección 5 (Lectura crítica):** interpretar los números. Cada número debe tener su "so what":
   - ¿Se confirmó la hipótesis?
   - ¿Hay sorpresa? → documentar en anomalías
   - ¿Cambia la estrategia para el siguiente notebook?

3. **Sección 6 (Anomalías):** documentar cualquier warning, error benigno, o comportamiento inesperado.

4. **Sección 7 (Qué sigue):** actualizar si el resultado cambia el plan del siguiente notebook.

### Paso 3: Actualizar el plan maestro

En `PLAN_MODELADO_CRISPDM.md`, marcar tasks con `[x]` y añadir datos reales:

```markdown
- [x] **Task ejecutada** — Output: `data/.../archivo.csv`. Cobertura medida: X%. Ver [reports/nbXX_resultados.md](reports/nbXX_resultados.md).
```

### Paso 4: Actualizar README.md

Si el notebook cambió el estado de una fase:

| Fase | Estado anterior | Estado nuevo |
|---|---|---|
| Fase 2 §2.2 | 🟡 En curso | 🟢 Pipeline completo |

### Paso 5: Commit + push

Mensaje de commit con formato:

```
feat(fase X.Y): nbXX ejecutado — [resumen 1 línea]

- Cobertura medida: X% (predicho: Y%)
- Hallazgos: [1-2 puntos clave]
- Próximo paso: [nb siguiente]

Ver reports/nbXX_resultados.md para análisis completo.

Co-Authored-By: Claude Opus 4.7 (1M context) <noreply@anthropic.com>
```

Push a `main`.

---

## Ejemplo aplicado — nb06 (RUT LFs)

Tras ejecutar `06_preanotaciones_rut.ipynb`:

### Paso 1 — prints extraídos

```
Pre-anotaciones generadas: 216 docs
Cobertura nit: 0.981 / razon_social: 0.819 / regimen: 0.986
              direccion: 0.931 / municipio: 0.995 / representante_legal: 0.653
Tareas Label Studio generadas: 216
```

### Paso 2 — reporte actualizado

Números reales embebidos en `reports/nb06_resultados.md` §4. Hipótesis confirmada (cobertura >90% para entidades regulatorias, <70% para variabilidad estructural). Hallazgo nuevo documentado: `representante_legal` es el cuello de botella.

### Paso 3 — plan actualizado

En `PLAN_MODELADO_CRISPDM.md §2.2`:

```markdown
- [x] Generar pre-anotaciones automáticas sobre los 216 RUT — Notebook 06 ejecutado.
  Cobertura:
  | Entidad | Cobertura |
  | nit | 98.1% |
  | razon_social | 81.9% |
  ...
```

### Paso 4 — README actualizado

```markdown
| Fase 2 §2.2 | 🟡 En curso | RUT (nb06) ✅ cobertura 65-99%. Cédulas (nb07) ✅... |
```

### Paso 5 — commit

```
feat(fase2.2): nb06 ejecutado — RUT pre-anotaciones via Snorkel

- 216 docs procesados, cobertura 65-99% por entidad
- Hipótesis Snorkel confirmada (entidades regulatorias >90%)
- Cuello de botella: representante_legal a 65% (variabilidad estructural)
- Próximo: nb07 Cédulas

Ver reports/nb06_resultados.md para análisis completo.
```

---

## Reglas estrictas

### DO

- ✅ Ejecutar el notebook completo (Run All) antes de documentar
- ✅ Citar números **exactos** del output, no redondeos aproximados
- ✅ Embeber bloques de print reales en el reporte (con ```` ``` ````)
- ✅ Documentar sorpresas y falsos positivos
- ✅ Marcar implicaciones explícitas para el siguiente notebook
- ✅ Usar fuentes verificables (arXiv, DOI, normatividad oficial)

### DON'T

- ❌ Documentar sobre valores de smoke test (pueden diferir de la corrida completa)
- ❌ Usar aproximaciones ("~80%") cuando el valor real está disponible ("80.8%")
- ❌ Citar blogs sin paper asociado
- ❌ Saltarse el paso 2 aunque los números no hayan cambiado — puede haber warnings nuevos
- ❌ Commitear JSONs con PII (rut_preanotaciones_labelstudio.json, corpus_ocr.csv, etc.). Siempre verificar `.gitignore`

---

## Qué hacer si re-ejecutas un notebook

Si un notebook se re-ejecuta (por fix de código, cambio de datos, etc.):

1. Los outputs antiguos del .ipynb se sobrescriben automáticamente
2. **El reporte .md NO se actualiza automáticamente** — hay que aplicar el ritual otra vez
3. Si los números cambiaron, documentar el **delta** en la sección 6 (Anomalías):

```markdown
### Hallazgo 7 — Cambio vs ejecución anterior (2026-04-20)
Tras re-ejecución el 2026-04-25 con fix XXX:
- Cobertura `nit`: 98.1% → 99.5% (+1.4 puntos)
- Causa: [explicar]
```

---

## Artefactos del ritual

Tras cada ejecución, el repo debe quedar con:

- Notebook .ipynb con outputs (no borrar outputs antes de commit — son evidencia)
- `_nb_outputs/nbXX.txt` con prints extraídos (local, no commiteado)
- Reporte `reports/nbXX_resultados.md` actualizado
- Plan y README actualizados si aplica
- Commit con mensaje descriptivo

---

## Referencias

- [PLAN_MODELADO_CRISPDM.md](PLAN_MODELADO_CRISPDM.md) — fuente de verdad del plan
- [PROPUESTA_MODELOS.md](PROPUESTA_MODELOS.md) — candidatos de modelado con citas científicas
- [OCR_BENCHMARK.md](OCR_BENCHMARK.md) — bitácora OCR
- [reports/README.md](reports/README.md) — índice de reportes narrativos
