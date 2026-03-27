import re


def _term_to_like_pattern(term: str) -> str:
    value = (term or '').strip()
    if not value:
        return ''

    # Permite coincidencias flexibles cuando el usuario escribe separadores
    # distintos a los almacenados en BD: 3/4, 3-4, 3.4, etc.
    chunks = re.findall(r'[\w]+', value, flags=re.UNICODE)
    if not chunks:
        return f'%{value}%'

    return '%' + '%'.join(chunks) + '%'


def contains_terms_where(raw_search, fields):
    terms = [t.strip() for t in (raw_search or '').split() if t and t.strip()]
    if not terms:
        return '', []

    clauses = []
    params = []

    for term in terms:
        like = _term_to_like_pattern(term)
        if not like:
            continue

        term_clause = '(' + ' OR '.join([f'{field} LIKE ? COLLATE NOCASE' for field in fields]) + ')'
        clauses.append(term_clause)
        params.extend([like] * len(fields))

    if not clauses:
        return '', []

    return ' AND '.join(clauses), params
