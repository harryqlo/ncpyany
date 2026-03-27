"""
Calcula y actualiza la clasificación ABC del inventario según valor de consumo.

Lógica:
  - Clase A: 80% superior del valor acumulado → conteo cada 14 días
  - Clase B: siguiente 15%                    → conteo cada 30 días
  - Clase C: 5% restante                      → conteo cada 90 días

Uso:
  python calcular_abc.py
  python calcular_abc.py --umbral-a 75 --umbral-b 92
"""
import argparse
import sqlite3
import os
import sys
from datetime import date, timedelta

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, BASE_DIR)

try:
    from config import DB_PATH
except ImportError:
    DB_PATH = os.path.join(BASE_DIR, 'system', 'system.db')

# Frecuencias de conteo por clase (días)
FRECUENCIA_DIAS = {'A': 14, 'B': 30, 'C': 90}


def _asignar_clase(pct_acumulado, umbral_a, umbral_b):
    if pct_acumulado <= umbral_a:
        return 'A'
    if pct_acumulado <= umbral_b:
        return 'B'
    return 'C'


def calcular(umbral_a: float = 80.0, umbral_b: float = 95.0, verbose: bool = True):
    """
    Recalcula la clasificación ABC y la almacena en items_clasificacion_abc.
    Preserva `ultimo_conteo` si el ítem ya existía; recalcula `proximo_conteo`.

    Returns:
        dict con resumen {'A': int, 'B': int, 'C': int, 'total': int}
    """
    conn = sqlite3.connect(str(DB_PATH))
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    c = conn.cursor()

    try:
        # Verificar que la tabla existe
        existe = c.execute(
            "SELECT name FROM sqlite_master WHERE type='table' AND name='items_clasificacion_abc'"
        ).fetchone()
        if not existe:
            print("✗ Tabla items_clasificacion_abc no existe. Ejecuta primero crear_tablas_auditorias.py")
            return {}

        # Obtener ítems con valor de consumo estimado
        rows = c.execute("""
            SELECT
                i.sku,
                i.nombre,
                COALESCE(i.consumos_totales_historicos, 0)          AS consumo,
                COALESCE(i.precio_unitario_promedio, 0)             AS precio,
                COALESCE(i.consumos_totales_historicos, 0) *
                    COALESCE(i.precio_unitario_promedio, 0)         AS valor_anual
            FROM items i
            WHERE i.sku IS NOT NULL AND i.sku <> ''
            ORDER BY valor_anual DESC
        """).fetchall()

        if not rows:
            if verbose:
                print("  Sin ítems para clasificar.")
            return {}

        total_valor = sum(r['valor_anual'] for r in rows)
        hoy = date.today()
        acumulado = 0.0
        conteos = {'A': 0, 'B': 0, 'C': 0}

        for r in rows:
            acumulado += r['valor_anual']
            pct = (acumulado / total_valor * 100) if total_valor > 0 else 100.0
            clase = _asignar_clase(pct, umbral_a, umbral_b)
            freq = FRECUENCIA_DIAS[clase]

            # Preservar último conteo si existe
            existente = c.execute(
                "SELECT ultimo_conteo FROM items_clasificacion_abc WHERE item_sku=?",
                [r['sku']]
            ).fetchone()

            if existente and existente['ultimo_conteo']:
                try:
                    ultimo = date.fromisoformat(existente['ultimo_conteo'])
                    proximo = (ultimo + timedelta(days=freq)).isoformat()
                except ValueError:
                    proximo = (hoy + timedelta(days=freq)).isoformat()
            else:
                proximo = (hoy + timedelta(days=freq)).isoformat()

            c.execute("""
                INSERT INTO items_clasificacion_abc
                    (item_sku, clase, valor_anual, pct_acumulado,
                     frecuencia_conteo_dias, proximo_conteo, updated_at)
                VALUES (?,?,?,?,?,?,date('now'))
                ON CONFLICT(item_sku) DO UPDATE SET
                    clase                 = excluded.clase,
                    valor_anual           = excluded.valor_anual,
                    pct_acumulado         = excluded.pct_acumulado,
                    frecuencia_conteo_dias= excluded.frecuencia_conteo_dias,
                    proximo_conteo        = excluded.proximo_conteo,
                    updated_at            = date('now')
            """, [r['sku'], clase, r['valor_anual'], pct, freq, proximo])

            conteos[clase] += 1

        conn.commit()

        if verbose:
            total = sum(conteos.values())
            print(f"✓ Clasificación ABC actualizada ({total} ítems)")
            print(f"  Clase A (≤{umbral_a}% valor): {conteos['A']} ítems — conteo cada 14 días")
            print(f"  Clase B (≤{umbral_b}% valor): {conteos['B']} ítems — conteo cada 30 días")
            print(f"  Clase C (resto):               {conteos['C']} ítems — conteo cada 90 días")

        conteos['total'] = sum(conteos.values())
        return conteos

    except Exception as e:
        conn.rollback()
        print(f"✗ Error: {e}")
        raise
    finally:
        conn.close()


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description="Calcula clasificación ABC del inventario North Chrome"
    )
    parser.add_argument('--umbral-a', type=float, default=80.0,
                        help="Porcentaje acumulado límite para clase A (default: 80)")
    parser.add_argument('--umbral-b', type=float, default=95.0,
                        help="Porcentaje acumulado límite para clase B (default: 95)")
    args = parser.parse_args()

    print(f"Base de datos: {DB_PATH}")
    calcular(umbral_a=args.umbral_a, umbral_b=args.umbral_b)
