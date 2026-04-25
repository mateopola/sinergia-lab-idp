# Criterios de anotación — Fase 2.2

Guía de referencia rápida para revisar las 516 pre-anotaciones en Label Studio. Para cada entidad se especifica **qué marcar**, **qué NO marcar**, y **casos borde** frecuentes. Usar junto con [LABEL_STUDIO_SETUP.md](LABEL_STUDIO_SETUP.md).

**Regla de oro:** marcar **solo el valor**, no el label. Ejemplo:
- ✅ Marcar: `901772377-1`
- ❌ No marcar: `NIT: 901772377-1`

---

## RUT (DIAN) — 6 entidades

### `nit`
- **Qué:** número de identificación tributaria del contribuyente.
- **Formato típico:** 9-10 dígitos + DV (ej: `901772377-1` o `901 772 377 1`).
- **Dónde:** casilla 5 ("Número de Identificación Tributaria") + casilla 6 (DV).
- **NO marcar:** NITs de terceros (contadores, representantes, notarías) que aparecen en el documento. Solo el del contribuyente principal.

### `razon_social`
- **Qué:** nombre jurídico completo de la persona jurídica, tal como aparece en casilla 35.
- **Formato:** MAYÚSCULAS + forma jurídica al final (SAS, LTDA, S.A., E.U., EIRL).
- **Ejemplo:** `ORTIZ CARRASCAL INGENIERIA SAS`
- **NO marcar:** si el RUT es de persona natural (vacío), no marcar.

### `regimen`
- **Qué:** régimen tributario del contribuyente.
- **Valores canónicos:** `ordinario`, `simple`, `simplificado`, `gran_contribuyente`, `especial`.
- **Dónde:** sección Responsabilidades (códigos 05/06/07/48/...).
- **Nota:** `simple` (RST, Ley 2155/2021) ≠ `simplificado` (antiguo IVA simplificado). No confundir.

### `direccion`
- **Qué:** dirección principal (casilla 41).
- **Ejemplo:** `CL 3 B # 45 - 68`.
- **NO marcar:** email, teléfono ni departamento/ciudad (tienen sus propias casillas).

### `municipio`
- **Qué:** ciudad o municipio de la dirección principal (casilla 40).
- **Ejemplo:** `Ocaña`, `Bogota D.C.`, `Medellín`.
- **Normalización:** las variantes `Bogota D.C`, `BOGOTA D.C.`, `Bogota DC` se unificaron a `Bogota D.C.` en pre-procesamiento.

### `representante_legal`
- **Qué:** nombre completo del representante legal de la persona jurídica.
- **Dónde:** al final del documento, firma del solicitante.
- **Ejemplo:** `ORTIZ CARRASCAL DIEGO FERNANDO`.
- **Cuello de botella detectado en nb06** (cobertura 65%): a menudo está en "Firma del solicitante" sin keyword; hay que leer el contexto.

---

## Cédulas — 9 entidades (bimodal)

Puedes referirte a la **imagen** si el OCR tiene errores — pero las marcas van sobre el **texto**.

### `numero`
- **Qué:** número de cédula.
- **Formato:** 8-10 dígitos, puede tener puntos (`1.012.345.678`) o espacios.
- **Cuello de botella (nb07):** cédulas nítidas tienen cobertura 47% vs ruidosas 80% — revisar con cuidado las nítidas.

### `nombre_completo`
- **Qué:** nombres de pila (sin apellidos).
- **Dónde:** debajo del label "NOMBRES" en la cédula.
- **Ejemplo:** `DIEGO FERNANDO`.

### `apellidos`
- **Qué:** primer y segundo apellido.
- **Dónde:** debajo de "APELLIDOS".
- **Ejemplo:** `ORTIZ CARRASCAL`.

### `fecha_nacimiento`
- **Qué:** fecha de nacimiento en cualquier formato (`DD-MM-YYYY`, `DD/MMM/YYYY`, etc.).
- **NO marcar:** `fecha_expedicion` (es otra entidad).

### `lugar_nacimiento`
- **Qué:** ciudad + departamento de nacimiento.
- **Ejemplo:** `BOGOTA D.C.`, `MEDELLIN / ANTIOQUIA`.

### `fecha_expedicion`
- **Qué:** fecha de expedición de la cédula.
- **Dónde:** en el reverso, sección "EXPEDICION".

### `lugar_expedicion`
- **Qué:** ciudad donde fue expedida la cédula.

### `sexo`
- **Qué:** `M` o `F`.
- **NO marcar:** la palabra "SEXO" (solo el valor).

### `rh`
- **Qué:** tipo sanguíneo + factor RH (ej: `O+`, `A-`, `AB+`).

---

## Pólizas — 9 entidades

**Contexto (nb08):** solo `numero_poliza` y `aseguradora` vienen pre-anotados. Las 7 restantes hay que marcarlas **a mano**.

### `numero_poliza`
- **Qué:** número único de la póliza.
- **Formato:** alfanumérico variable, típicamente 6-15 caracteres.
- **Dónde:** carátula de la póliza, suele aparecer tras "Póliza No." / "Número de Póliza".

### `aseguradora`
- **Qué:** compañía emisora de la póliza.
- **Valores frecuentes en el corpus (nb08):** `Mundial de Seguros` (62%), `SURA / Suramericana`, `La Equidad`, `Allianz`, `Mapfre`, `AXA`, `Bolívar`, `Colpatria`.
- **NO marcar:** el broker/intermediario (si aparece).

### `tomador`
- **Qué:** persona o empresa que contrata la póliza (paga la prima).
- **Dónde:** "TOMADOR:" en la carátula.
- **Puede ser:** persona natural (con cédula) o jurídica (con NIT).

### `asegurado`
- **Qué:** persona o bien cubierto por la póliza (puede coincidir con el tomador o no).
- **Dónde:** "ASEGURADO:".

### `vigencia_desde`
- **Qué:** fecha de inicio de la cobertura.
- **Formato:** fecha con o sin hora (`2025-01-01`, `1 de enero de 2025 00:00`).

### `vigencia_hasta`
- **Qué:** fecha de terminación.

### `valor_asegurado`
- **Qué:** monto máximo cubierto (suma asegurada).
- **Formato:** con símbolo monetario y separadores (`$100.000.000`, `COP 50,000,000`).
- **Cobertura baja en corpus (40.2% en pág 1):** a veces está en anexos — si no aparece en las primeras páginas, no forzarlo.

### `prima_neta`
- **Qué:** monto que paga el tomador.
- **NO marcar:** prima total con IVA/tasas — solo la neta si están discriminadas. Si solo hay una, marcarla.

### `amparo_principal`
- **Qué:** tipo de cobertura principal (ramo).
- **Valores frecuentes:** `Cumplimiento Estatal`, `Seriedad de la Oferta`, `RCE`, `Vida Grupo`, `SOAT`, `Vigilancia`.

---

## Cámara de Comercio — 10 entidades

**Contexto (nb09):** documento regulado por Decreto 2150/1995 → estructura uniforme → cobertura alta (96.7% razón social). Es la tipología **más rápida de revisar**.

### `nit`
- **Qué:** NIT de la entidad registrada.
- **Formato:** igual que en RUT.

### `razon_social`
- **Qué:** denominación social completa con forma jurídica.
- **Cobertura:** 96.7% pre-anotado → casi solo confirmar.

### `matricula`
- **Qué:** número de matrícula mercantil asignado por la Cámara.
- **Formato:** 6-10 dígitos, a veces con prefijo de la Cámara.

### `tipo_sociedad`
- **Qué:** forma jurídica específica.
- **Valores:** `SAS`, `LTDA`, `S.A.`, `EIRL`, `E.U.`, `Cooperativa`, `Fundación`, etc.
- **NO marcar:** lo que ya está dentro de `razon_social` — marcar aparte cuando aparece el tipo explícito en una tabla/sección dedicada.

### `fecha_renovacion`
- **Qué:** fecha de la última renovación de la matrícula.
- **Dónde:** sección "Información general" o "Renovación".

### `domicilio`
- **Qué:** dirección comercial registrada.
- **NO marcar:** dirección de notificación si es distinta (a menos que no haya domicilio principal).

### `objeto_social`
- **Qué:** descripción de las actividades de la empresa.
- **Formato:** puede ser muy largo (párrafos enteros).
- **Criterio:** marcar **todo el bloque** hasta el punto final.

### `representante_legal`
- **Qué:** nombre completo del representante legal vigente.
- **Dónde:** sección "Representación Legal" o "Nombramientos".
- **NO marcar:** suplentes ni representantes removidos.

### `activos`
- **Qué:** valor total de activos.
- **Formato:** `$XXX.XXX.XXX` + año.
- **Dónde:** en la sección de estados financieros o cifras reportadas.

### `capital_social`
- **Qué:** capital suscrito/pagado de la sociedad.
- **Formato:** monto en pesos.

---

## Reglas transversales

### Qué hacer con falsos positivos
Eliminar sin reemplazar. Si la regex marcó `5 4` como "código DANE" pensando que era NIT, solo borrar.

### Qué hacer con spans cortados
Ajustar bordes arrastrando. Ejemplo:
- Pre-anotado: `ORTIZ CARRASCAL INGENIERIA SAS\n` (incluye salto de línea)
- Correcto: `ORTIZ CARRASCAL INGENIERIA SAS` (sin el `\n`)

### Qué hacer con entidades repetidas
Si la misma entidad aparece varias veces en el documento (ej: NIT aparece en carátula y en pie de página), marcar **solo la primera ocurrencia**. No duplicar.

### Qué hacer cuando no se encuentra una entidad esperada
No forzar. Mejor una entidad faltante (se penaliza con recall bajo pero es honesto) que una entidad mal etiquetada (envenena el dataset).

### Qué hacer con PII sensible
El corpus tiene PII real. **Nunca compartir screenshots fuera del equipo**. Label Studio guarda todo local — no subir los JSONs exportados a la nube.

---

## Preguntas frecuentes

**¿Qué pasa si un doc está mal OCR'd y no se entiende?**
→ Skip. En Label Studio: botón "Skip" (no "Submit"). Se marcará como pendiente para revisión grupal.

**¿Cuánto me demoro por doc?**
Estimado: CC ~1.5 min/doc (solo confirmar), RUT ~2 min/doc, Pólizas ~3 min/doc (marcar 7 a mano), Cédulas ~3 min/doc (bimodal).

**¿Puedo pausar a la mitad?**
Sí. Label Studio guarda progreso automáticamente por tarea submiteada. Cerrar tab no pierde nada.

**¿Cómo sé que terminé?**
Panel de proyecto → contador "Annotated" debe igualar "Total tasks". Para RUT: 216/216.

---

## Referencias

- [LABEL_STUDIO_SETUP.md](LABEL_STUDIO_SETUP.md) — instalación + configs XML
- [reports/nb06_resultados.md](reports/nb06_resultados.md) — detalle cobertura RUT
- [reports/nb07_resultados.md](reports/nb07_resultados.md) — paradoja Cédulas
- [reports/nb08_resultados.md](reports/nb08_resultados.md) — Pólizas layout variable
- [reports/nb09_resultados.md](reports/nb09_resultados.md) — CC estructura regulada
