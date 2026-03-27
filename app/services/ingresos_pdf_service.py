import re
from datetime import datetime
from io import BytesIO

try:
    from pypdf import PdfReader
except Exception:  # pragma: no cover - fallback cuando dependencia no está instalada
    PdfReader = None

try:
    import pdfplumber
except Exception:  # pragma: no cover - fallback cuando dependencia no está instalada
    pdfplumber = None


_DATE_PATTERNS = [
    re.compile(r'\b(\d{4})[-/.](\d{1,2})[-/.](\d{1,2})\b'),
    re.compile(r'\b(\d{1,2})[-/.](\d{1,2})[-/.](\d{4})\b'),
]


def _normalize_spaces(text):
    return re.sub(r'\s+', ' ', (text or '')).strip()


def _parse_number(raw):
    value = (raw or '').strip()
    if not value:
        return None
    value = re.sub(r'[^0-9,.-]', '', value)
    if not value:
        return None

    if ',' in value and '.' in value:
        if value.rfind(',') > value.rfind('.'):
            value = value.replace('.', '').replace(',', '.')
        else:
            value = value.replace(',', '')
    elif ',' in value:
        value = value.replace('.', '').replace(',', '.')

    try:
        return float(value)
    except (ValueError, TypeError):
        return None


def _extract_date(lines):
    for line in lines:
        normalized = _normalize_spaces(line)
        if not normalized:
            continue
        for pattern in _DATE_PATTERNS:
            match = pattern.search(normalized)
            if not match:
                continue
            groups = match.groups()
            try:
                if len(groups[0]) == 4:
                    dt = datetime(int(groups[0]), int(groups[1]), int(groups[2]))
                else:
                    dt = datetime(int(groups[2]), int(groups[1]), int(groups[0]))
                return dt.strftime('%Y-%m-%d')
            except ValueError:
                continue
    return ''


def _extract_doc_field(lines, labels):
    for line in lines:
        normalized = _normalize_spaces(line)
        low = normalized.lower()
        for label in labels:
            short_label = len(label.replace(' ', '')) <= 3
            if short_label:
                if not re.search(rf'\b{re.escape(label)}\b', low):
                    continue
            elif label not in low:
                continue
            if ':' in normalized:
                right = normalized.split(':', 1)[1].strip()
                if right:
                    return right[:80]
            parts = normalized.split()
            if parts:
                return parts[-1][:80]
    return ''


def _extract_supplier(lines):
    supplier = _extract_doc_field(lines, ['proveedor', 'razon social'])
    if supplier:
        return supplier

    company_markers = ('spa', 'ltda', 's.a', 's.a.', 'eirl')
    for line in lines[:12]:
        normalized = _normalize_spaces(line)
        if len(normalized) < 4:
            continue
        low = normalized.lower()
        if any(marker in low for marker in company_markers):
            return normalized[:120]
    return ''


def _extract_lines_from_pdf(file_stream):
    raw_bytes = file_stream.read()
    if not raw_bytes:
        return []

    lines = []

    if PdfReader is not None:
        try:
            reader = PdfReader(BytesIO(raw_bytes))
            for page in reader.pages:
                text = page.extract_text() or ''
                if not text:
                    try:
                        text = page.extract_text(extraction_mode='layout') or ''
                    except TypeError:
                        text = ''
                for raw_line in text.splitlines():
                    clean = _normalize_spaces(raw_line)
                    if clean:
                        lines.append(clean)
        except Exception:
            lines = []

    if lines:
        return lines

    if pdfplumber is not None:
        try:
            with pdfplumber.open(BytesIO(raw_bytes)) as pdf:
                for page in pdf.pages:
                    text = page.extract_text() or ''
                    for raw_line in text.splitlines():
                        clean = _normalize_spaces(raw_line)
                        if clean:
                            lines.append(clean)
        except Exception:
            lines = []

    return lines


def _find_numeric_tokens(tokens):
    numeric = []
    for index, token in enumerate(tokens):
        value = _parse_number(token)
        if value is None:
            continue
        numeric.append((index, value, token))
    return numeric


def _detect_sku(tokens):
    for index, token in enumerate(tokens[:6]):
        token_clean = re.sub(r'[^A-Za-z0-9_-]', '', token)
        if len(token_clean) < 3:
            continue
        has_letter = re.search(r'[A-Za-z]', token_clean) is not None
        has_digit = re.search(r'\d', token_clean) is not None
        if has_letter and has_digit:
            return index, token_clean.upper()
    return None, ''


def _best_item_match(catalog, description):
    if not catalog:
        return None

    desc = _normalize_spaces(description).lower()
    if len(desc) < 4:
        return None

    tokens = [t for t in re.findall(r'[a-z0-9]+', desc) if len(t) >= 3]
    if not tokens:
        return None

    best = None
    for item in catalog['items']:
        name = item['nombre_norm']
        score = sum(1 for token in tokens if token in name)
        if score <= 0:
            continue
        ratio = score / max(1, len(tokens))
        if ratio < 0.5:
            continue
        if not best or ratio > best['ratio']:
            best = {
                'ratio': ratio,
                'sku': item['sku'],
                'nombre': item['nombre'],
                'unidad': item['unidad'],
            }

    if not best:
        return None

    return {
        'sku': best['sku'],
        'nombre': best['nombre'],
        'unidad': best['unidad'],
        'method': 'descripcion',
        'confidence': round(0.55 + min(0.35, best['ratio'] * 0.4), 2),
    }


def _build_catalog(conn):
    rows = conn.execute('SELECT sku, nombre, unidad_medida_nombre FROM items').fetchall()
    items = []
    by_sku = {}

    for row in rows:
        sku = (row['sku'] or '').strip().upper()
        nombre = (row['nombre'] or '').strip()
        unidad = (row['unidad_medida_nombre'] or '').strip()
        if not sku:
            continue
        entry = {
            'sku': sku,
            'nombre': nombre,
            'unidad': unidad,
            'nombre_norm': _normalize_spaces(nombre).lower(),
        }
        items.append(entry)
        by_sku[sku] = entry

    return {'items': items, 'by_sku': by_sku}


def _is_likely_item_line(line):
    low = line.lower()
    banned_markers = (
        'subtotal', 'total neto', 'iva', 'exento', 'descuento', 'fecha', 'factura',
        'guia', 'guía', 'orden de compra', 'rut', 'telefono', 'dirección', 'direccion'
    )
    if any(marker in low for marker in banned_markers):
        return False

    number_count = len(re.findall(r'\d+[\d.,]*', line))
    if number_count < 2:
        return False

    has_letters = re.search(r'[A-Za-zÁÉÍÓÚáéíóúÑñ]', line) is not None
    return has_letters


def _extract_item_candidate(line, catalog):
    if not _is_likely_item_line(line):
        return None

    tokens = line.split(' ')
    if len(tokens) < 3:
        return None

    numeric = _find_numeric_tokens(tokens)
    if len(numeric) < 2:
        return None

    sku_index, sku = _detect_sku(tokens)
    reversed_numbers = list(reversed(numeric))
    total = reversed_numbers[0][1]
    price = reversed_numbers[1][1] if len(reversed_numbers) > 1 else None
    quantity = reversed_numbers[2][1] if len(reversed_numbers) > 2 else None

    if quantity is None:
        qty_idx = reversed_numbers[1][0] - 1 if len(reversed_numbers) > 1 else reversed_numbers[0][0] - 1
        if 0 <= qty_idx < len(tokens):
            quantity = _parse_number(tokens[qty_idx])

    if quantity is None and price:
        quantity = round(total / price, 2) if price > 0 else None

    if not quantity or quantity <= 0:
        return None

    if price is None:
        price = round(total / quantity, 2) if quantity > 0 else 0

    desc_start = 0
    if sku_index is not None:
        desc_start = sku_index + 1
    while desc_start < len(tokens):
        probe = tokens[desc_start]
        only_num_or_symbol = re.sub(r'[0-9\W_]+', '', probe) == ''
        if not only_num_or_symbol:
            break
        desc_start += 1
    desc_end = numeric[0][0] if numeric else len(tokens)
    description = _normalize_spaces(' '.join(tokens[desc_start:desc_end]))
    if len(description) < 3:
        return None

    match = _best_item_match(catalog, description)
    use_sku = ''
    if match:
        use_sku = match['sku']

    confidence = 0.4
    if description:
        confidence += 0.1
    if price and quantity:
        confidence += 0.15
    if match:
        confidence += min(0.15, match['confidence'] - 0.5)
    confidence = round(min(0.99, max(0.05, confidence)), 2)

    warnings = []
    if not match:
        warnings.append('No se pudo vincular automáticamente por descripción')
    if not description:
        warnings.append('Descripción no detectada con claridad')

    return {
        'raw': line,
        'sku': use_sku,
        'sku_detectado': sku,
        'descripcion': description,
        'cantidad': round(quantity, 3),
        'precio': round(price or 0, 2),
        'total': round((price or 0) * quantity, 2),
        'descuento_pct': 0,
        'confidence': confidence,
        'matched': bool(match),
        'match_method': (match or {}).get('method', ''),
        'item_nombre': (match or {}).get('nombre', description),
        'item_unidad': (match or {}).get('unidad', ''),
        'warnings': warnings,
    }


def parse_ingreso_pdf(file_stream, db_conn):
    lines = _extract_lines_from_pdf(file_stream)
    if not lines:
        return {
            'documento': {
                'fecha': '',
                'proveedor': '',
                'factura': '',
                'guia': '',
                'oc': '',
                'transportista': '',
                'observaciones': '',
                'confidence': 0,
                'warnings': ['No se pudo extraer texto del PDF (puede ser escaneado o protegido)'],
            },
            'items': [],
            'stats': {'lineas': 0, 'items_detectados': 0, 'items_match_catalogo': 0, 'warnings': 1},
        }

    catalog = _build_catalog(db_conn)
    doc_fecha = _extract_date(lines)
    doc_proveedor = _extract_supplier(lines)
    doc_factura = _extract_doc_field(lines, ['factura', 'folio'])
    doc_guia = _extract_doc_field(lines, ['guia', 'guía'])
    doc_oc = _extract_doc_field(lines, ['orden compra', 'o/c', 'oc'])

    items = []
    for line in lines:
        candidate = _extract_item_candidate(line, catalog)
        if candidate:
            items.append(candidate)

    dedup = {}
    for item in items:
        key = f"{item['sku'] or item['descripcion']}|{item['cantidad']}|{item['precio']}"
        if key in dedup:
            if item['confidence'] > dedup[key]['confidence']:
                dedup[key] = item
        else:
            dedup[key] = item
    items = list(dedup.values())

    doc_confidence = 0.25
    if doc_fecha:
        doc_confidence += 0.2
    if doc_proveedor:
        doc_confidence += 0.2
    if doc_factura or doc_guia or doc_oc:
        doc_confidence += 0.2
    if items:
        doc_confidence += 0.15
    doc_confidence = round(min(0.95, doc_confidence), 2)

    warnings = []
    if not doc_proveedor:
        warnings.append('Proveedor no detectado automáticamente')
    if not items:
        warnings.append('No se detectaron líneas de productos con suficiente certeza')

    matched_count = sum(1 for item in items if item.get('matched'))

    return {
        'documento': {
            'fecha': doc_fecha,
            'proveedor': doc_proveedor,
            'factura': doc_factura,
            'guia': doc_guia,
            'oc': doc_oc,
            'transportista': '',
            'observaciones': 'Pre-cargado desde PDF. Revisión humana requerida antes de registrar.',
            'confidence': doc_confidence,
            'warnings': warnings,
        },
        'items': items,
        'stats': {
            'lineas': len(lines),
            'items_detectados': len(items),
            'items_match_catalogo': matched_count,
            'warnings': len(warnings) + sum(1 for item in items if item.get('warnings')),
        },
    }