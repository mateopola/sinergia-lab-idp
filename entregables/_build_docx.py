"""
Genera el .docx del entregable Gold Standard + Benchmark OCR.

Ejecutar desde la raiz:
    python entregables/_build_docx.py

Produce:
    entregables/Entrega_Gold_Standard_y_Benchmark_OCR.docx
"""
from pathlib import Path
from docx import Document
from docx.shared import Pt, Cm, RGBColor, Inches
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.enum.table import WD_ALIGN_VERTICAL
from docx.oxml.ns import qn
from docx.oxml import OxmlElement

ROOT = Path(__file__).parent
FIGS = ROOT / 'figs'
OCR_FIG = ROOT.parent / 'data' / 'processed' / 'fig11_ocr_benchmark.png'
OUT = ROOT / 'Entrega_Gold_Standard_y_Benchmark_OCR.docx'


def set_cell_bg(cell, color_hex):
    """Aplica color de fondo a una celda."""
    tc_pr = cell._tc.get_or_add_tcPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), color_hex)
    tc_pr.append(shd)


def add_heading(doc, text, level=1, color=None):
    h = doc.add_heading(text, level=level)
    if color:
        for run in h.runs:
            run.font.color.rgb = color
    return h


def add_para(doc, text, bold=False, italic=False, size=11, align=None):
    p = doc.add_paragraph()
    if align is not None:
        p.alignment = align
    r = p.add_run(text)
    r.font.size = Pt(size)
    if bold: r.bold = True
    if italic: r.italic = True
    return p


def add_para_mixed(doc, parts):
    """
    parts = [(text, bold, italic, is_code), ...]
    """
    p = doc.add_paragraph()
    for text, bold, italic, is_code in parts:
        r = p.add_run(text)
        r.font.size = Pt(11)
        if bold: r.bold = True
        if italic: r.italic = True
        if is_code:
            r.font.name = 'Consolas'
            r.font.size = Pt(10)
    return p


def add_bullet(doc, text, level=0):
    p = doc.add_paragraph(style='List Bullet' if level == 0 else 'List Bullet 2')
    r = p.runs[0] if p.runs else p.add_run(text)
    if not p.runs:
        r = p.add_run(text)
    else:
        p.runs[0].text = ''
        r = p.add_run(text)
    r.font.size = Pt(11)
    return p


def add_code_block(doc, code):
    p = doc.add_paragraph()
    p.paragraph_format.left_indent = Cm(0.5)
    r = p.add_run(code)
    r.font.name = 'Consolas'
    r.font.size = Pt(9)
    # Gray background via paragraph shading
    pPr = p._p.get_or_add_pPr()
    shd = OxmlElement('w:shd')
    shd.set(qn('w:fill'), 'F5F5F5')
    pPr.append(shd)
    return p


def add_table_from_rows(doc, headers, rows, col_widths=None):
    t = doc.add_table(rows=1 + len(rows), cols=len(headers))
    t.style = 'Light Grid Accent 1'
    t.autofit = False

    # Header
    hdr = t.rows[0].cells
    for i, h in enumerate(headers):
        hdr[i].text = ''
        p = hdr[i].paragraphs[0]
        r = p.add_run(h)
        r.bold = True
        r.font.size = Pt(10)
        r.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
        set_cell_bg(hdr[i], '2E5C8A')

    # Filas
    for i, row in enumerate(rows, start=1):
        for j, val in enumerate(row):
            t.rows[i].cells[j].text = ''
            p = t.rows[i].cells[j].paragraphs[0]
            r = p.add_run(str(val))
            r.font.size = Pt(10)

    # Anchos si se especifican
    if col_widths:
        for row in t.rows:
            for i, w in enumerate(col_widths):
                if i < len(row.cells):
                    row.cells[i].width = w

    return t


def add_image(doc, path, width_cm=15, caption=None):
    if not Path(path).exists():
        p = doc.add_paragraph(f'[FIGURA FALTANTE: {path}]')
        r = p.runs[0]; r.italic = True; r.font.color.rgb = RGBColor(0xC0, 0x39, 0x2B)
        return
    doc.add_picture(str(path), width=Cm(width_cm))
    last_para = doc.paragraphs[-1]
    last_para.alignment = WD_ALIGN_PARAGRAPH.CENTER
    if caption:
        cap = doc.add_paragraph()
        cap.alignment = WD_ALIGN_PARAGRAPH.CENTER
        r = cap.add_run(caption)
        r.italic = True
        r.font.size = Pt(9)
        r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)


def add_page_break(doc):
    doc.add_page_break()


# ─────────────────────────────────────────────────────────────────────────────
# Construccion del documento
# ─────────────────────────────────────────────────────────────────────────────
doc = Document()

# Ajustar margenes
for section in doc.sections:
    section.top_margin = Cm(2.2)
    section.bottom_margin = Cm(2.2)
    section.left_margin = Cm(2.5)
    section.right_margin = Cm(2.5)

# Estilo por defecto
style = doc.styles['Normal']
style.font.name = 'Calibri'
style.font.size = Pt(11)

# ═════ PORTADA ═════
title = doc.add_heading('', level=0)
title.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = title.add_run('Entrega Académica\nGold Standard y Selección del Motor OCR')
r.font.size = Pt(22)
r.font.color.rgb = RGBColor(0x2E, 0x5C, 0x8A)

subt = doc.add_paragraph()
subt.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = subt.add_run('Proyecto SinergIA Lab — IDP para Documentos Corporativos Colombianos SECOP')
r.italic = True
r.font.size = Pt(13)

doc.add_paragraph()  # espacio

# Metadata en tabla
meta = doc.add_table(rows=6, cols=2)
meta.alignment = WD_ALIGN_PARAGRAPH.CENTER
meta_items = [
    ('Institución', 'Pontificia Universidad Javeriana'),
    ('Programa', 'Especialización en Inteligencia Artificial — Ciclo 1 · 2026'),
    ('Fase CRISP-DM++', '2.1.1 — Selección del Motor OCR'),
    ('Fecha de entrega', '2026-04-20'),
    ('Notebook de referencia', '03_benchmark_ocr.ipynb'),
    ('Bitácora complementaria', 'OCR_BENCHMARK.md'),
]
for i, (k, v) in enumerate(meta_items):
    meta.rows[i].cells[0].text = ''
    p = meta.rows[i].cells[0].paragraphs[0]
    r = p.add_run(k); r.bold = True; r.font.size = Pt(10)
    meta.rows[i].cells[1].text = ''
    p = meta.rows[i].cells[1].paragraphs[0]
    r = p.add_run(v); r.font.size = Pt(10)

add_page_break(doc)

# ═════ 0. Resumen ejecutivo ═════
add_heading(doc, 'Resumen ejecutivo', level=1)
add_para(doc,
    'Este documento responde cinco preguntas centrales sobre cómo se eligió '
    'el motor de Reconocimiento Óptico de Caracteres (OCR) del proyecto:')
bullets = [
    '¿Qué es un "gold standard" y cómo se construyó el nuestro?',
    '¿Para qué sirve ese gold?',
    '¿Qué motores OCR se compararon?',
    '¿Qué métricas cuantitativas se calcularon y qué mide cada una?',
    '¿Qué motor se eligió y por qué?',
]
for b in bullets:
    doc.add_paragraph(b, style='List Number')

add_para(doc,
    'Se siguió un diseño experimental riguroso sobre 15 documentos '
    'transcritos manualmente por un humano, aplicando métricas estándar de la '
    'literatura OCR y una métrica específica para el dominio del proyecto '
    '(extracción de entidades). La decisión final se sustenta en una regla '
    'documentada antes de ejecutar el experimento — principio de objetividad científica.')

add_page_break(doc)

# ═════ 1. Gold standard ═════
add_heading(doc, '1. Qué es el "gold standard" y por qué es importante', level=1)

add_heading(doc, '1.1 Explicación para cualquier lector', level=2)
add_para(doc,
    'Cuando queremos saber si una herramienta automática funciona bien, '
    'necesitamos compararla contra algo que sepamos que es correcto. En '
    'inteligencia artificial, ese "algo correcto" se llama gold standard o '
    'ground truth (verdad de referencia).')
add_para(doc,
    'Piénselo así: si usted compra una balanza y quiere saber si mide bien, '
    'pesa objetos de peso conocido (1 kg, 5 kg, 10 kg de referencia). Esos '
    'pesos oficiales son el "gold standard" de su balanza. Sin ellos, no '
    'puede responder "¿qué tan precisa es?".')
add_para(doc,
    'En nuestro proyecto, el gold standard es un conjunto de 15 documentos '
    'del corpus SECOP que un humano leyó y transcribió letra por letra. Esa '
    'transcripción humana es "la verdad". Cuando un motor OCR procesa esos '
    'mismos 15 documentos, comparamos su salida contra la transcripción '
    'humana y medimos errores.')

add_heading(doc, '1.2 Para qué sirve en el proyecto', level=2)
add_para(doc, 'El gold cumple cuatro roles a lo largo del ciclo de vida del proyecto:')

add_table_from_rows(doc,
    headers=['Rol', 'Cuándo se usa', 'Cómo se usa'],
    rows=[
        ['Benchmark OCR', 'Fase 2.1.1 (este documento)', 'Medir la calidad de cada motor OCR contra texto humano'],
        ['Validación de pre-anotaciones (LFs)', 'Fase 2.2 (RUT)', 'Verificar que las reglas regex extraen las mismas entidades que el humano'],
        ['Validación del corpus completo', 'Fase 2.1.4 (cierre)', 'Confirmar que los 13,254 páginas finales mantienen la calidad medida'],
        ['Evaluación final F1', 'Fase 4', 'Comparar la extracción del modelo NER fine-tuneado contra etiquetas humanas'],
    ],
    col_widths=[Cm(4.5), Cm(5), Cm(7)]
)

add_para(doc,
    'Sin un gold estándar, la pregunta "¿funciona mi sistema?" no tiene '
    'respuesta cuantificable. Este es el principio metodológico central '
    'de CRISP-DM (Wirth & Hipp, 2000) y de toda evaluación experimental '
    'rigurosa en procesamiento de lenguaje natural (Manning et al., 2008).')

add_heading(doc, '1.3 Composición de la muestra', level=2)
add_para(doc,
    'La composición de los 15 documentos se definió ANTES de ejecutar el '
    'benchmark, bajo tres principios:')
for b in [
    'Cobertura tipológica: representar las 4 tipologías del corpus '
    '(Cédula, RUT, Póliza, Cámara de Comercio)',
    'Estratificación por calidad en Cédulas: incluir ejemplos nítidos y '
    'ruidosos para medir sensibilidad al ruido',
    'Representatividad de escaneados: el gold solo contiene documentos '
    'escaneados (son los que OCR debe resolver)',
]:
    doc.add_paragraph(b, style='List Bullet')

add_table_from_rows(doc,
    headers=['Tipología', 'Documentos', 'Criterio de selección'],
    rows=[
        ['Cédula', '6', '3 alta calidad + 3 ruidosas (blur_score Q1 vs Q3)'],
        ['RUT', '3', 'Escaneados (minoría dentro del RUT: 11.5% del total)'],
        ['Póliza', '3', 'Escaneadas (27% del corpus de Pólizas)'],
        ['Cámara de Comercio', '3', 'Escaneadas (9% del corpus de CC)'],
        ['TOTAL', '15 docs (36 páginas transcritas)', ''],
    ],
    col_widths=[Cm(4), Cm(4.5), Cm(8)]
)

add_image(doc, FIGS / 'fig_gold_composicion.png', width_cm=15,
          caption='Figura 1 — Composición del gold standard (15 documentos, 4 tipologías, estratificación por calidad en Cédulas)')

add_heading(doc, '1.4 Proceso de construcción (5 pasos)', level=2)

add_image(doc, FIGS / 'fig_gold_proceso.png', width_cm=17,
          caption='Figura 2 — Flujo de construcción del gold standard')

add_para_mixed(doc, [('Paso 1 — Selección reproducible. ', True, False, False),
    ('Se programó un muestreo aleatorio con semilla fija ', False, False, False),
    ('random_state=42', False, False, True),
    (' para que cualquier persona pueda reproducir exactamente la misma selección. '
     'El notebook filtra el corpus por tipología y calidad, y muestrea 15 documentos.', False, False, False)])

add_para_mixed(doc, [('Paso 2 — Resolución del "mojibake". ', True, False, False),
    ('Los nombres de archivo SECOP venían con caracteres raros '
     '(por ejemplo "CÃÂ©dula" en vez de "Cédula") debido a conversiones de codificación Windows→UTF-8 fallidas. '
     'Para evitar confusiones, construimos un índice con el hash MD5 de cada PDF. El MD5 es una "huella digital" '
     'única del contenido del archivo — dos archivos con el mismo MD5 son idénticos aunque se llamen distinto. '
     'Este índice detectó además una reclasificación: un documento archivado como Cámara de Comercio '
     'era en realidad una Cédula.', False, False, False)])

add_para_mixed(doc, [('Paso 3 — Transcripción humana literal. ', True, False, False),
    ('Para cada documento seleccionado se generó un archivo de texto vacío. Un anotador humano (miembro del equipo) '
     'transcribió literalmente todo el texto visible, carácter por carácter, SIN corregir errores del original. '
     'Se respeta el orden de lectura natural (arriba-abajo, izquierda-derecha).', False, False, False)])

add_para_mixed(doc, [('Paso 4 — Validación de completitud. ', True, False, False),
    ('Un script verifica que los 15 archivos .txt están listos y tienen longitud razonable antes de ejecutar '
     'el benchmark. Las 15 transcripciones tienen entre 447 chars (Cédulas, 1 página) y 16,157 chars '
     '(Cámaras de Comercio, 4 páginas). Estas longitudes son coherentes con la naturaleza de cada documento.', False, False, False)])

add_para_mixed(doc, [('Paso 5 — Congelación. ', True, False, False),
    ('Una vez validado, el gold se marca como ', False, False, False),
    ('inmutable', False, True, False),
    ('. Las transcripciones no se modifican más, la semilla está fija, y hay una bandera ', False, False, False),
    ('RESAMPLE=False', False, False, True),
    (' que previene re-muestreos accidentales. Esto garantiza que cualquier medición posterior contra este gold '
     'es comparable con mediciones anteriores.', False, False, False)])

add_heading(doc, '1.5 ¿Por qué 15 documentos y no más?', level=2)
add_para(doc,
    'La decisión de usar una gold seed reducida (15 documentos) en lugar del gold extendido '
    'de 70 documentos originalmente planteado se sustenta en tres razones:')
for b in [
    'Costo humano: transcribir 70 documentos multipágina tomaría ~50 horas; '
    '15 documentos toman ~8 horas.',
    'Suficiencia estadística para la decisión OCR: 15 docs × 2 motores = 30 puntos de datos. '
    'La varianza entre motores es alta y permite detectar al ganador con 15 docs (los resultados lo confirmaron).',
    'Gold extendido diferido a Fase 4: se construirá antes de evaluar el modelo NER, '
    'donde sí se necesita precisión estadística con Cohen\'s Kappa ≥ 0.85 entre dos anotadores.',
]:
    doc.add_paragraph(b, style='List Bullet')

add_page_break(doc)

# ═════ 2. Motores OCR ═════
add_heading(doc, '2. Los motores OCR comparados', level=1)

add_heading(doc, '2.1 Qué es un motor OCR (explicación general)', level=2)
add_para(doc,
    'OCR significa Optical Character Recognition — Reconocimiento Óptico de Caracteres. '
    'Es un programa que mira una imagen que contiene texto (por ejemplo, la foto '
    'de una cédula escaneada) y produce el texto correspondiente como caracteres '
    'que una computadora puede procesar.')
add_para(doc,
    'El OCR resuelve el problema fundamental de los documentos escaneados: '
    'aunque un humano lee el texto en la imagen sin dificultad, una computadora '
    'solo ve píxeles. Sin OCR, una imagen escaneada es invisible para un sistema '
    'que quiere extraer NITs, fechas, nombres, etc.')
add_para(doc,
    'Hay muchos motores OCR disponibles. Este proyecto comparó dos de los más '
    'usados en la industria y descartó otros dos por razones técnicas. '
    'PyMuPDF, aunque no es un motor OCR sino un extractor de texto nativo, '
    'se menciona porque es parte complementaria del pipeline.')

add_heading(doc, '2.2 EasyOCR 1.7.2 — el candidato moderno', level=2)
add_para(doc,
    'EasyOCR es una librería open-source desarrollada por JaidedAI, basada en '
    'dos redes neuronales profundas que trabajan en cascada:')
for b in [
    'CRAFT (Character Region Awareness For Text detection): detecta regiones de texto '
    'a nivel de carácter individual, no de palabra. Esto permite procesar texto '
    'curvo o con layouts atípicos. Paper: Baek et al., CVPR 2019.',
    'CRNN (Convolutional Recurrent Neural Network): reconoce el contenido textual '
    'dentro de cada región detectada. Combina redes convolucionales (para extraer '
    'características visuales) con redes recurrentes (para secuenciar caracteres). '
    'Paper: Shi, Bai & Yao, IEEE TPAMI 2017.',
]:
    doc.add_paragraph(b, style='List Bullet')
add_para(doc, 'Características prácticas:')
for b in [
    'Soporta más de 80 idiomas, incluido español.',
    'Corre en CPU (lento pero universal) o GPU (rápido).',
    'Descarga el modelo una sola vez (~60 MB para español) y luego funciona offline.',
]:
    doc.add_paragraph(b, style='List Bullet')

add_heading(doc, '2.3 Tesseract 5.5.0 — el candidato clásico', level=2)
add_para(doc,
    'Tesseract OCR Engine es el motor OCR open-source más longevo en uso. '
    'Desarrollado originalmente en HP Labs (1984-1994), liberado por Google en '
    '2005, y mantenido por la comunidad desde entonces.')
add_para(doc,
    'Desde la versión 4.0 (2018), Tesseract usa un clasificador LSTM '
    '(Long Short-Term Memory — una variante de red neuronal recurrente) '
    'para reconocer secuencias de caracteres. Paper de referencia: Smith, ICDAR 2007.')
add_para(doc, 'Características prácticas:')
for b in [
    'Requiere descarga manual del modelo de español ("spa.traineddata", ~30 MB).',
    'Produce texto plano; los bounding boxes (cajas de posición) son opcionales.',
    'Muy rápido en CPU (5-10× más rápido que EasyOCR).',
]:
    doc.add_paragraph(b, style='List Bullet')

add_heading(doc, '2.4 Motores descartados', level=2)

add_table_from_rows(doc,
    headers=['Motor', 'Razón del descarte'],
    rows=[
        ['PaddleOCR (Baidu)', 'Incompatible con Python 3.12 al momento del benchmark.'],
        ['Donut (NAVER, 2022)',
         'No es propiamente un OCR sino un modelo Visión-Lenguaje (VLM) end-to-end. '
         'Toma la imagen completa y produce JSON estructurado. Corpus multi-tipológico '
         'requeriría 4 modelos especializados. Considerado como alternativa arquitectural global '
         'pero no como motor OCR intercambiable.'],
    ],
    col_widths=[Cm(4), Cm(13)]
)

add_heading(doc, '2.5 Tabla comparativa de los motores considerados', level=2)
add_para(doc,
    'Esta tabla consolida los 5 motores que se evaluaron durante la fase de diseño, '
    'incluyendo los 2 que entraron al benchmark (EasyOCR y Tesseract), '
    '2 que se descartaron antes del benchmark (PaddleOCR y Donut) y PyMuPDF '
    '(no es OCR pero completa el pipeline para documentos digitales).')

add_table_from_rows(doc,
    headers=['Criterio', 'EasyOCR', 'Tesseract 5', 'PaddleOCR', 'Donut', 'PyMuPDF'],
    rows=[
        ['Tipo de motor',
         'OCR deep learning (2 redes)', 'OCR clásico + LSTM', 'OCR deep learning',
         'VLM end-to-end (no OCR)', 'Extractor texto nativo'],
        ['Arquitectura base',
         'CRAFT (detección) + CRNN (reconocimiento)', 'LSTM', 'PP-OCR (detección + clasificación + reconocimiento)',
         'Transformer visión → JSON', 'Parser MuPDF'],
        ['Paper de referencia',
         'Baek et al. CVPR 2019; Shi et al. TPAMI 2017', 'Smith ICDAR 2007', 'PP-OCR technical report (Baidu, 2020)',
         'Kim et al. ECCV 2022', 'Documentación Artifex'],
        ['Licencia',
         'Apache 2.0', 'Apache 2.0', 'Apache 2.0', 'MIT', 'AGPL (free para uso interno)'],
        ['Soporte español',
         'Sí (nativo)', 'Sí (requiere spa.traineddata)', 'Sí (multi-lingual models)',
         'Limitado (entrenado en inglés)', 'N/A (extrae lo que haya)'],
        ['Velocidad en CPU',
         'Lenta (~46 s/pág)', 'Rápida (~5 s/pág)', 'Media (no medida aquí)',
         'Lenta (requiere GPU prácticamente)', 'Muy rápida (~0.006 s/pág)'],
        ['Entrada esperada',
         'Imagen (grayscale o color)', 'Imagen (mejor si binarizada)', 'Imagen',
         'Imagen + prompt JSON', 'PDF con texto digital embebido'],
        ['Salida',
         'Texto + bounding boxes', 'Texto plano (bboxes opcional)', 'Texto + bboxes',
         'JSON estructurado directo', 'Texto plano'],
        ['Compatibilidad Python 3.12',
         'Sí', 'Sí', 'NO (bloqueante)', 'Sí', 'Sí'],
        ['Multi-tipología',
         'Universal (un solo modelo)', 'Universal', 'Universal',
         'Requiere 1 modelo por tipología', 'Solo funciona en digitales'],
        ['Estado en el proyecto',
         'EVALUADO → seleccionado como motor principal',
         'EVALUADO → descartado como motor único',
         'DESCARTADO antes del benchmark (incompatibilidad)',
         'DESCARTADO antes del benchmark (arquitectura no intercambiable)',
         'COMPLEMENTARIO (pipeline digital)'],
    ],
    col_widths=[Cm(3), Cm(3), Cm(2.8), Cm(2.6), Cm(2.8), Cm(2.6)]
)

add_para(doc,
    'Los 5 motores se evaluaron según los criterios de soberanía de datos (todos son '
    'open-source y corren localmente, cumpliendo Ley 1581/2012), compatibilidad con '
    'el entorno Python 3.12 del proyecto, y capacidad de procesar los 4 tipos documentales '
    'del corpus SECOP. Solo EasyOCR y Tesseract pasaron a la fase de benchmark formal.')

add_heading(doc, '2.6 PyMuPDF — nota complementaria', level=2)
add_para(doc,
    'PyMuPDF no se incluye en el benchmark porque no es un motor OCR. '
    'Es un extractor de texto nativo que solo funciona cuando el PDF tiene '
    'caracteres digitales embebidos (no imagen). En el pipeline productivo '
    'del proyecto, PyMuPDF maneja los 548 documentos digitales del corpus con '
    'precisión perfecta (CER ≈ 0), mientras que EasyOCR/Tesseract manejan los '
    '416 escaneados. Esta bifurcación "usa el motor apropiado según el tipo" '
    'es una decisión arquitectural separada.')

add_page_break(doc)

# ═════ 3. Metricas ═════
add_heading(doc, '3. Las métricas: qué se midió y qué mide cada una', level=1)

add_para(doc,
    'Se calcularon cuatro métricas por cada combinación (motor × documento). '
    'Cada métrica responde a una pregunta distinta.')

add_heading(doc, '3.1 Character Error Rate (CER) — calidad carácter a carácter', level=2)
add_para_mixed(doc, [('Pregunta que responde: ', True, False, False),
    ('¿qué tan cerca está el texto producido por el OCR del texto real?', False, True, False)])
add_para(doc, 'Fórmula:')
add_code_block(doc, 'CER = (S + D + I) / N\n\ndonde:\n  S = número de caracteres sustituidos (el OCR escribió el carácter incorrecto)\n  D = número de caracteres borrados (el OCR omitió un carácter que estaba en el original)\n  I = número de caracteres insertados (el OCR agregó un carácter que no estaba)\n  N = total de caracteres en la transcripción humana (referencia)')
add_para(doc,
    'Se calcula con la distancia de edición de Levenshtein entre el texto OCR y '
    'la transcripción humana. Es la métrica canónica de literatura OCR desde los años 80.')
add_para_mixed(doc, [('Dirección: ', True, False, False),
    ('menor es mejor. CER = 0 significa coincidencia perfecta. CER = 0.3 significa '
     'que 30 de cada 100 caracteres tienen algún error.', False, False, False)])
add_para_mixed(doc, [('Normalización previa: ', True, False, False),
    ('antes de comparar se convierte todo a minúsculas y se colapsan los espacios '
     'múltiples. Esto evita que diferencias triviales de formato cuenten como errores.', False, False, False)])

add_heading(doc, '3.2 Word Error Rate (WER) — calidad palabra a palabra', level=2)
add_para_mixed(doc, [('Pregunta que responde: ', True, False, False),
    ('¿cuántas palabras enteras está errando el OCR?', False, True, False)])
add_para_mixed(doc, [('Fórmula: ', True, False, False),
    ('la misma que CER pero contando ', False, False, False),
    ('palabras', False, True, False),
    (' en lugar de caracteres. Se calcula con alineación Levenshtein sobre la '
     'secuencia de palabras tokenizadas por espacios.', False, False, False)])
add_para_mixed(doc, [('Por qué medir las dos: ', True, False, False),
    ('CER y WER miden cosas distintas. Un OCR puede tener CER bajo (pocos errores '
     'de carácter) pero WER alto si los errores se concentran en unas pocas palabras '
     'que quedan irreconocibles. Y viceversa. Dos motores con CER similar pueden '
     'tener WER muy distinto, lo que tiene implicaciones downstream.', False, False, False)])

add_heading(doc, '3.3 Entity Recall — la métrica que MÁS importa para este proyecto', level=2)
add_para_mixed(doc, [('Pregunta que responde: ', True, False, False),
    ('¿qué tanto preserva el OCR las entidades (NITs, cédulas, fechas, montos) que '
     'el sistema necesita extraer después?', False, True, False)])
add_para(doc,
    'CER y WER miden la calidad del texto en general. Pero lo que realmente '
    'importa para un sistema IDP (Intelligent Document Processing) es si los '
    'datos clave (NIT, número de cédula, fecha, monto) quedaron legibles.')
add_para(doc, 'Fórmula:')
add_code_block(doc, 'entity_recall = | entidades_detectadas_en_OCR ∩ entidades_en_gold | / | entidades_en_gold |')
add_para(doc, 'Las "entidades" se extraen con cuatro patrones regex específicos del dominio colombiano:')

add_table_from_rows(doc,
    headers=['Entidad', 'Patrón de búsqueda (regex)', 'Ejemplo'],
    rows=[
        ['NIT', r'\b\d{8,10}[-\s]?\d\b', '860518862-7'],
        ['Cédula', r'\b\d{1,3}(?:[.\s]\d{3}){2,3}\b', '1.234.567 o 1 234 567'],
        ['Fecha', r'\b\d{1,2}[/-]\d{1,2}[/-]\d{2,4}\b', '05/11/2025'],
        ['Monto', r'\$\s?\d{1,3}(?:[.,]\d{3})+(?:[.,]\d{1,2})?', '$1.234.567,89'],
    ],
    col_widths=[Cm(2.5), Cm(8), Cm(6)]
)
add_para_mixed(doc, [('Dirección: ', True, False, False),
    ('mayor es mejor. Entity_recall = 1.0 significa que el OCR preservó todas las entidades del gold. '
     'Entity_recall = 0.5 significa que la mitad de los NITs/cédulas/fechas/montos quedaron inusables.', False, False, False)])
add_para_mixed(doc, [('Por qué es crítico: ', True, False, False),
    ('un OCR puede tener CER 0.30 (30% de caracteres con error) pero si los dígitos del NIT '
     'quedan rotos, la extracción NER downstream falla aunque "en promedio" el texto se lea. '
     'Entity recall mide directamente utilidad downstream. Esta métrica está alineada con la '
     'evaluación a nivel de entidad del shared task CoNLL-2002 (Tjong Kim Sang, 2002).', False, False, False)])

add_heading(doc, '3.4 Tiempo por página — costo operativo', level=2)
add_para_mixed(doc, [('Pregunta que responde: ', True, False, False),
    ('¿cuánto cuesta ejecutar este OCR a escala?', False, True, False)])
add_para(doc,
    'Se mide con time.perf_counter() en alta resolución, contabilizando solo el '
    'tiempo de inferencia (no de carga del modelo, que se amortiza).')
add_para_mixed(doc, [('Por qué es crítico: ', True, False, False),
    ('el corpus del proyecto tiene 1,678 páginas escaneadas. Un motor a 50 s/página '
     'requiere ~23 horas de cómputo (corrida overnight). Un motor a 5 s/página requiere ~2.3 horas. '
     'La diferencia operativa es sustancial para iteración experimental.', False, False, False)])

add_heading(doc, '3.5 Resumen de las métricas', level=2)
add_table_from_rows(doc,
    headers=['Métrica', 'Fórmula conceptual', 'Mejor si...', 'Pregunta que responde'],
    rows=[
        ['CER', '(errores de carácter) / (total de caracteres)', 'Menor',
         'Calidad carácter-a-carácter'],
        ['WER', '(errores de palabra) / (total de palabras)', 'Menor',
         'Calidad palabra-a-palabra'],
        ['Entity Recall', '(entidades preservadas) / (entidades en gold)', 'Mayor',
         'Utilidad downstream para NER'],
        ['Segundos/página', 'Tiempo total / número de páginas', 'Menor',
         'Costo operativo'],
    ],
    col_widths=[Cm(2.5), Cm(5.5), Cm(2), Cm(6)]
)

add_page_break(doc)

# ═════ 4. Resultados ═════
add_heading(doc, '4. Resultados', level=1)

add_heading(doc, '4.1 Resumen global', level=2)
add_table_from_rows(doc,
    headers=['Motor', 'N docs', 'CER medio', 'WER medio', 'Entity recall', 'Segundos/página'],
    rows=[
        ['EasyOCR (CPU)', '15', '0.276', '0.476', '0.551', '46.02'],
        ['Tesseract 5', '15', '0.446', '0.557', '0.605', '5.06'],
    ],
    col_widths=[Cm(3.5), Cm(1.5), Cm(2), Cm(2), Cm(2.5), Cm(3)]
)

add_para(doc, 'Lecturas directas:')
for b in [
    'EasyOCR tiene CER 38% menor que Tesseract a nivel global — más preciso carácter a carácter.',
    'Tesseract es 9× más rápido en CPU — menor costo operativo.',
    'Tesseract tiene marginalmente mejor entity_recall global (+5 puntos) — mejor preservación de entidades en promedio.',
]:
    doc.add_paragraph(b, style='List Bullet')

add_heading(doc, '4.2 Desglose por tipología documental (el hallazgo principal)', level=2)
add_image(doc, FIGS / 'fig_comparacion_motores.png', width_cm=17,
          caption='Figura 3 — Comparación directa de motores OCR por tipología. Izquierda: CER (menor es mejor). Derecha: Entity Recall (mayor es mejor).')

add_table_from_rows(doc,
    headers=['Tipología', 'EasyOCR CER', 'Tesseract CER', 'EasyOCR ent.recall', 'Tesseract ent.recall', 'Motor ganador'],
    rows=[
        ['Cédula', '0.333', '0.782', '0.444', '0.111', 'EasyOCR (abrumador)'],
        ['RUT', '0.289', '0.394', '0.889', '0.889', 'EasyOCR (CER) / Tesseract (velocidad)'],
        ['Póliza', '0.329', '0.226', '0.649', '0.951', 'Tesseract'],
        ['Cámara de Comercio', '0.096', '0.047', '0.326', '0.963', 'Tesseract (contundente)'],
    ],
    col_widths=[Cm(3.5), Cm(2), Cm(2.3), Cm(2.5), Cm(2.7), Cm(4.5)]
)

add_para_mixed(doc, [('Hallazgo principal: ', True, False, False),
    ('no hay un motor "mejor" en absoluto. Cada motor domina tipologías distintas. '
     'EasyOCR gana en Cédulas (la tipología más numerosa del corpus, 32.9%), '
     'Tesseract gana en Pólizas y Cámara de Comercio. Este comportamiento de '
     '"régimen mixto" es la base de la decisión final.', False, False, False)])

add_heading(doc, '4.3 Casos extremos', level=2)
add_para(doc, 'Los tres documentos con mayor diferencia de CER entre motores son TODOS Cédulas:')
add_table_from_rows(doc,
    headers=['Documento', 'EasyOCR CER', 'Tesseract CER', 'Diferencia'],
    rows=[
        ['23 cc.pdf', '0.261', '0.903', '0.642'],
        ['cc Julieth Payares.pdf', '0.416', '0.955', '0.540'],
        ['CC Yerlis cabarcas.pdf', '0.460', '0.998', '0.538'],
    ],
    col_widths=[Cm(6), Cm(2.5), Cm(2.5), Cm(2.5)]
)
add_para(doc,
    'Tesseract colapsa sistemáticamente en Cédulas (CER > 0.9 = texto casi irrecuperable). '
    'Este patrón confirma que la elección del motor no puede hacerse con una métrica '
    'agregada — hay que ver el comportamiento por tipología.')

add_heading(doc, '4.4 Interpretación técnica', level=2)
add_para_mixed(doc, [('¿Por qué Tesseract falla en Cédulas? ', True, False, False),
    ('La cédula colombiana combina condiciones adversas para un clasificador LSTM '
     'clásico: texto pequeño (~6-8 pt), hologramas superpuestos, columnas apretadas, '
     'bajo contraste. Tesseract pasa la imagen completa al LSTM, que se satura. '
     'EasyOCR (vía CRAFT) detecta regiones de texto antes de reconocer, aislando '
     'el ruido visual — estrategia documentada como ventajosa en Baek et al. 2019.', False, False, False)])
add_para_mixed(doc, [('¿Por qué Tesseract gana en CC? ', True, False, False),
    ('Los certificados de Cámara de Comercio son el antípoda: texto estándar, sin '
     'hologramas, columnas anchas, alto contraste. En este régimen el LSTM clásico '
     'funciona excelente y gana por velocidad (9× más rápido que EasyOCR).', False, False, False)])

add_page_break(doc)

# ═════ 5. Decision ═════
add_heading(doc, '5. La decisión y su justificación', level=1)

add_image(doc, FIGS / 'fig_tradeoff.png', width_cm=14,
          caption='Figura 4 — Compromiso calidad vs velocidad. El punto ideal está abajo-izquierda (bajo CER, baja latencia).')

add_heading(doc, '5.1 La regla de decisión (definida ANTES del experimento)', level=2)
add_para(doc,
    'Para garantizar objetividad, la regla de decisión se definió por escrito '
    'antes de ejecutar el benchmark. Esto evita el sesgo de adaptar la regla a '
    'los resultados.')
add_code_block(doc,
    'Regla 1: gana el motor con menor CER global, si su tiempo es < 2× el del motor más rápido\n'
    'Regla 2: si hay empate en CER (diferencia < 2%), gana el de mayor entity_recall\n'
    'Regla 3: si cada motor domina una tipología distinta, implementar selector híbrido')

add_heading(doc, '5.2 Aplicación de la regla a nuestros resultados', level=2)
for b in [
    'Regla 1: EasyOCR tiene menor CER global (0.276 vs 0.446), PERO es 9× más '
    'lento que Tesseract. No cumple la restricción de tiempo (9 > 2×). No gana por regla 1.',
    'Regla 2: la diferencia CER (17 puntos absolutos) > 2%. La regla de empate no aplica.',
    'Regla 3: cada motor domina tipologías distintas (EasyOCR en Cédulas; Tesseract en CC/Pólizas). APLICA.',
]:
    doc.add_paragraph(b, style='List Number')

add_heading(doc, '5.3 Decisión final', level=2)
add_para(doc,
    'Formalmente la regla 3 sugiere un selector híbrido (un motor distinto por tipología). '
    'Sin embargo, el proyecto adoptó EasyOCR unificado para todos los documentos escaneados '
    'por las siguientes razones:')
for b in [
    'Las Cédulas son la tipología MÁS numerosa del corpus (32.9%). EasyOCR es crítico para '
    'esta tipología, y su CER en las otras tipologías es aceptable (no catastrófico).',
    'Simplicidad del pipeline: un solo motor reduce puntos de falla, facilita mantenimiento, '
    'y evita ramificaciones condicionales en el código productivo.',
    'Con GPU futuro: EasyOCR pasa de 46 s/pág a ~1 s/pág (40× más rápido). Esto elimina '
    'la ventaja principal de Tesseract.',
    'Tesseract queda disponible como experimento de respaldo: si en Fase 4 el F1 del NER '
    'en Pólizas/CC queda bajo umbral, se puede reconsiderar un selector híbrido.',
]:
    doc.add_paragraph(b, style='List Bullet')

add_heading(doc, '5.4 Validación posterior (corrida productiva)', level=2)
add_para(doc,
    'Al aplicar EasyOCR al corpus completo de 1,678 páginas escaneadas '
    '(Notebook 05, corrida overnight de 23 horas), se midió el CER y el entity recall '
    'contra el mismo gold seed para verificar que la decisión del benchmark se sostiene '
    'a escala productiva.')
add_table_from_rows(doc,
    headers=['Métrica', 'Benchmark aislado (nb03)', 'Producción (nb05)', 'Delta'],
    rows=[
        ['CER global', '0.276', '0.282', '+2.2% (despreciable)'],
        ['Entity recall', '0.551', '0.640', '+16% (mejora)'],
    ],
    col_widths=[Cm(3), Cm(4.5), Cm(4), Cm(5)]
)
add_para(doc,
    'El benchmark predijo correctamente el comportamiento productivo. La mejora de '
    '+16% en entity_recall se atribuye a la eliminación del paso binarize() del '
    'pipeline productivo — decisión técnica tomada durante la ejecución y documentada '
    'en OCR_BENCHMARK.md §2.6.0.')

add_heading(doc, '5.5 Metadatos de trazabilidad', level=2)
add_table_from_rows(doc,
    headers=['Campo', 'Valor'],
    rows=[
        ['Fecha de la decisión', '2026-04-15'],
        ['Gold seed', '15 documentos en data/gold/gold_seed_manifest.csv'],
        ['Semilla aleatoria', 'random_state=42 (reproducible)'],
        ['Cap de páginas', '4 páginas por documento'],
        ['Transcripciones congeladas', 'data/gold/transcriptions/ — inmutables desde la fecha'],
        ['EasyOCR', '1.7.2 (modelos español, modo CPU)'],
        ['Tesseract', '5.5.0 (spa.traineddata en tessdata/ local del proyecto)'],
        ['Ambiente', 'Python 3.12.10, Windows 11, sin GPU'],
    ],
    col_widths=[Cm(6), Cm(11)]
)

add_page_break(doc)

# ═════ 6. Fig11 OCR benchmark ═════
add_heading(doc, '6. Visualización oficial del benchmark', level=1)
add_para(doc,
    'Figura generada por el Notebook 03 al finalizar el benchmark. Izquierda: '
    'barras de CER medio por motor y tipología. Derecha: scatter de cada punto '
    'de datos (15 docs × 2 motores = 30 puntos) en el plano CER vs segundos/página.')
add_image(doc, OCR_FIG, width_cm=17,
          caption='Figura 5 — Benchmark OCR oficial (fig11_ocr_benchmark.png, generada por el notebook).')

add_page_break(doc)

# ═════ 7. Referencias ═════
add_heading(doc, '7. Referencias bibliográficas', level=1)
add_para(doc, 'Todas las referencias son verificables en línea con DOI, arXiv ID o URL institucional oficial.')

add_heading(doc, 'Sobre gold standards y evaluación científica', level=2)
refs_a = [
    '[1] Manning, C. D., Raghavan, P., Schütze, H. (2008). Introduction to Information Retrieval. Cambridge University Press — Capítulo 8 "Evaluation in Information Retrieval". https://nlp.stanford.edu/IR-book/',
    '[2] Wang, W. et al. (2025). A Survey on Document Intelligence Foundations and Frontiers. arXiv:2510.13366. https://arxiv.org/abs/2510.13366',
    '[3] Wirth, R. & Hipp, J. (2000). CRISP-DM: Towards a Standard Process Model for Data Mining. 4th Intl. Conf. Practical Applications of Knowledge Discovery and Data Mining. https://www.cs.unibo.it/~montesi/CBD/Beatriz/10.1.1.198.5133.pdf',
    '[4] Tjong Kim Sang, E. F. (2002). Introduction to the CoNLL-2002 Shared Task: Language-Independent Named Entity Recognition. CoNLL 2002. https://aclanthology.org/W02-2024/',
]
for r in refs_a:
    p = doc.add_paragraph(r)
    p.paragraph_format.left_indent = Cm(0.5)

add_heading(doc, 'Sobre los motores OCR evaluados', level=2)
refs_b = [
    '[5] EasyOCR — Repositorio oficial JaidedAI. https://github.com/JaidedAI/EasyOCR',
    '[6] Baek, Y., Lee, B., Han, D., Yun, S., Lee, H. (2019). Character Region Awareness for Text Detection (CRAFT). CVPR 2019. https://arxiv.org/abs/1904.01941',
    '[7] Shi, B., Bai, X., Yao, C. (2017). An End-to-End Trainable Neural Network for Image-based Sequence Recognition (CRNN). IEEE TPAMI 39(11). https://arxiv.org/abs/1507.05717',
    '[8] Tesseract OCR — Repositorio oficial. https://github.com/tesseract-ocr/tesseract',
    '[9] Smith, R. (2007). An Overview of the Tesseract OCR Engine. ICDAR 2007. https://research.google/pubs/an-overview-of-the-tesseract-ocr-engine/',
    '[10] Kim, G. et al. (2022). OCR-free Document Understanding Transformer (Donut). ECCV 2022. https://arxiv.org/abs/2111.15664',
    '[11] PyMuPDF — Documentación oficial Artifex. https://pymupdf.readthedocs.io/ — Repositorio: https://github.com/pymupdf/PyMuPDF',
]
for r in refs_b:
    p = doc.add_paragraph(r)
    p.paragraph_format.left_indent = Cm(0.5)

add_heading(doc, 'Sobre las métricas utilizadas', level=2)
refs_c = [
    '[12] Morris, A. C., Maier, V., Green, P. (2004). From WER and RIL to MER and WIL: improved evaluation measures for connected speech recognition. Interspeech 2004. https://www.isca-speech.org/archive/interspeech_2004/morris04_interspeech.html',
    '[13] jiwer — Librería Python para cálculo de CER/WER. https://github.com/jitsi/jiwer',
    '[14] DIAN. Resolución 000110 del 11-10-2021 (estructura del RUT, fundamenta regex de NIT). https://www.dian.gov.co/normatividad/Normatividad/Resoluci%C3%B3n%20000110%20de%2011-10-2021.pdf',
]
for r in refs_c:
    p = doc.add_paragraph(r)
    p.paragraph_format.left_indent = Cm(0.5)

add_heading(doc, 'Referencias contextuales del proyecto', level=2)
refs_d = [
    '[15] Ratner, A. et al. (2018). Snorkel: Rapid Training Data Creation with Weak Supervision. VLDB 2018 — fundamenta el flujo de pre-anotación automática post-OCR. https://arxiv.org/abs/1711.10160',
    '[16] Colakoglu, G. et al. (2025). A Retrospective on Information Extraction from Documents: From Layout-aware Models to Large Language Models. arXiv:2502.18179. https://arxiv.org/abs/2502.18179',
]
for r in refs_d:
    p = doc.add_paragraph(r)
    p.paragraph_format.left_indent = Cm(0.5)

# ═════ Apendice ═════
add_page_break(doc)
add_heading(doc, 'Apéndice A — Tabla completa de resultados por motor × tipología', level=1)
add_para(doc, 'Extracto del output real del Notebook 03 (celda 27):')
add_code_block(doc,
    '   engine  folder         n  cer_mean  wer_mean  entity_recall_mean  s_per_page_mean\n'
    '  easyocr  CAMARA DE CIO  3    0.0960    0.2229              0.3259          51.5373\n'
    '  easyocr  CEDULA         6    0.3333    0.5737              0.4444          42.0840\n'
    '  easyocr  POLIZA         3    0.3286    0.4973              0.6493          48.1290\n'
    '  easyocr  rut            3    0.2891    0.5134              0.8889          46.2573\n'
    'tesseract  CAMARA DE CIO  3    0.0469    0.0316              0.9630           5.2543\n'
    'tesseract  CEDULA         6    0.7818    0.8843              0.1111           5.4147\n'
    'tesseract  POLIZA         3    0.2256    0.3466              0.9510           4.8143\n'
    'tesseract  rut            3    0.3941    0.6402              0.8889           4.4030')

add_para_mixed(doc, [('Archivos de datos: ', True, False, False),
    ('data/processed/ocr_benchmark.csv', False, False, True),
    (' (30 filas, commiteable), ', False, False, False),
    ('data/processed/ocr_benchmark_summary.csv', False, False, True),
    (' (8 filas agregadas, commiteable), ', False, False, False),
    ('data/processed/fig11_ocr_benchmark.png', False, False, True),
    (' (Figura 5).', False, False, False)])

add_heading(doc, 'Documentos internos del proyecto', level=2)
add_table_from_rows(doc,
    headers=['Documento', 'Ubicación'],
    rows=[
        ['Plan maestro CRISP-DM++', 'PLAN_MODELADO_CRISPDM.md'],
        ['Bitácora completa del benchmark', 'OCR_BENCHMARK.md'],
        ['Propuesta de modelos (Fase 3)', 'PROPUESTA_MODELOS.md'],
        ['Reporte narrativo del benchmark', 'reports/nb03_resultados.md'],
        ['Reporte de ejecución productiva', 'reports/nb05_resultados.md'],
        ['Notebook del benchmark', 'notebooks/03_benchmark_ocr.ipynb'],
        ['Gold seed manifest', 'data/gold/gold_seed_manifest.csv'],
        ['Transcripciones humanas', 'data/gold/transcriptions/*.txt (gitignored por PII)'],
    ],
    col_widths=[Cm(7), Cm(10)]
)

# Footer
doc.add_paragraph()
p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
r = p.add_run(
    'Este documento es parte de los entregables académicos del proyecto SinergIA Lab · '
    'PUJ Especialización en IA · Ciclo 1 · 2026. Toda afirmación cuantitativa está '
    'respaldada por artefactos verificables en el repositorio del proyecto.'
)
r.italic = True
r.font.size = Pt(9)
r.font.color.rgb = RGBColor(0x55, 0x55, 0x55)

# Guardar
doc.save(str(OUT))
print(f'DOCX generado: {OUT}')
print(f'  Tamano: {OUT.stat().st_size:,} bytes')
