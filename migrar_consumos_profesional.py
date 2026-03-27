import argparse
import csv
import shutil
import sqlite3
from collections import defaultdict
from datetime import datetime
from pathlib import Path

EXCEL_EPOCH = datetime(1899, 12, 30)


def date_to_excel(date_iso: str) -> int:
    dt = datetime.strptime(date_iso, "%Y-%m-%d")
    return (dt - EXCEL_EPOCH).days


def parse_fecha_ddmmyyyy(raw: str):
    value = (raw or "").strip()
    if not value:
        return None
    try:
        return datetime.strptime(value, "%d-%m-%Y").strftime("%Y-%m-%d")
    except ValueError:
        return None


def parse_num(raw: str):
    value = (raw or "").strip()
    if not value:
        return None

    value = value.replace("$", "").replace(" ", "").replace("\xa0", "")
    if "," in value and "." in value:
        value = value.replace(".", "").replace(",", ".")
    elif "," in value:
        value = value.replace(",", ".")
    elif value.count(".") > 1:
        value = value.replace(".", "")

    try:
        return float(value)
    except ValueError:
        return None


def clean_text(value):
    return (value or "").strip()


def ensure_schema(cur: sqlite3.Cursor, dry_run: bool):
    cols = {r[1] for r in cur.execute("PRAGMA table_info(movimientos_consumo)").fetchall()}
    if "documento_ref" not in cols:
        if dry_run:
            print("[DRY] faltaría agregar columna documento_ref en movimientos_consumo")
        else:
            cur.execute("ALTER TABLE movimientos_consumo ADD COLUMN documento_ref TEXT")


def load_items(cur: sqlite3.Cursor):
    result = {}
    rows = cur.execute(
        "SELECT sku, nombre, COALESCE(stock_actual,0), COALESCE(precio_unitario_promedio,0) FROM items"
    ).fetchall()
    for row in rows:
        sku = clean_text(row[0])
        result[sku] = {
            "nombre": clean_text(row[1]),
            "stock": float(row[2] or 0),
            "precio": float(row[3] or 0),
        }
    return result


def load_csv_rows(csv_path: Path, items: dict):
    parsed = []
    errors = []
    unknown_skus = defaultdict(int)

    last_error = None
    for encoding in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            with csv_path.open("r", encoding=encoding, newline="") as fh:
                reader = csv.DictReader(fh, delimiter=";")
                for idx, row in enumerate(reader, start=2):
                    sku = clean_text(row.get("SKU"))
                    fecha_iso = parse_fecha_ddmmyyyy(row.get("Fecha"))
                    solicitante = clean_text(row.get("Solicitado"))
                    cantidad = parse_num(row.get("Consumo"))
                    precio_csv = parse_num(row.get("$ UN"))
                    ot = clean_text(row.get("OT"))
                    obs = clean_text(row.get("OBS"))

                    if not sku:
                        errors.append(f"L{idx}: SKU vacío")
                        continue
                    if sku not in items:
                        unknown_skus[sku] += 1
                        continue
                    if not fecha_iso:
                        errors.append(f"L{idx}: fecha inválida ({row.get('Fecha')})")
                        continue
                    if cantidad is None or cantidad <= 0:
                        errors.append(f"L{idx}: cantidad inválida ({row.get('Consumo')})")
                        continue

                    fecha_excel = date_to_excel(fecha_iso)
                    precio = precio_csv if (precio_csv is not None and precio_csv >= 0) else items[sku]["precio"]
                    total = round(cantidad * precio, 2)

                    parsed.append(
                        {
                            "sku": sku,
                            "descripcion": items[sku]["nombre"],
                            "fecha_excel": fecha_excel,
                            "solicitante": solicitante,
                            "cantidad": cantidad,
                            "precio": precio,
                            "total": total,
                            "ot": ot,
                            "obs": obs,
                        }
                    )
            break
        except UnicodeDecodeError as exc:
            last_error = exc
            parsed.clear()
            errors.clear()
            unknown_skus.clear()
    else:
        raise last_error

    return parsed, errors, unknown_skus


def get_rows_to_delete(cur: sqlite3.Cursor, keep_year: int, keep_month: int):
    start = datetime(keep_year, keep_month, 1)
    if keep_month == 12:
        end = datetime(keep_year + 1, 1, 1)
    else:
        end = datetime(keep_year, keep_month + 1, 1)

    d_ini = date_to_excel(start.strftime("%Y-%m-%d"))
    d_fin = date_to_excel(end.strftime("%Y-%m-%d"))

    rows = cur.execute(
        """
        SELECT rowid, item_sku, COALESCE(cantidad_consumida,0) AS cant
        FROM movimientos_consumo
        WHERE COALESCE(fecha_consumo,0) < ? OR COALESCE(fecha_consumo,0) >= ?
        """,
        (d_ini, d_fin),
    ).fetchall()
    return rows, d_ini, d_fin


def dry_audit(cur: sqlite3.Cursor, parsed_rows: list, rows_to_delete: list, items: dict):
    restore_by_sku = defaultdict(float)
    for row in rows_to_delete:
        sku = clean_text(row[1])
        restore_by_sku[sku] += float(row[2] or 0)

    simulated_stock = {sku: data["stock"] for sku, data in items.items()}
    for sku, qty in restore_by_sku.items():
        if sku in simulated_stock:
            simulated_stock[sku] += qty

    insert_ok = 0
    insert_skip_stock = 0
    for rec in parsed_rows:
        sku = rec["sku"]
        qty = rec["cantidad"]
        if simulated_stock[sku] - qty < 0:
            insert_skip_stock += 1
            continue
        simulated_stock[sku] -= qty
        insert_ok += 1

    return restore_by_sku, insert_ok, insert_skip_stock


def apply_migration(
    con: sqlite3.Connection,
    cur: sqlite3.Cursor,
    db_path: Path,
    backup_dir: Path,
    parsed_rows: list,
    rows_to_delete: list,
    restore_by_sku: dict,
):
    backup_dir.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_file = backup_dir / f"system_pre_migracion_consumos_{ts}.db"
    shutil.copy2(db_path, backup_file)

    cur.execute("BEGIN IMMEDIATE")
    documento_ref = f"MIG-CONSUMOS-{datetime.now().strftime('%Y%m%d%H%M%S')}"

    for sku, qty in restore_by_sku.items():
        cur.execute("UPDATE items SET stock_actual = COALESCE(stock_actual,0) + ? WHERE sku = ?", (qty, sku))

    rowids = [row[0] for row in rows_to_delete]
    if rowids:
        marks = ",".join(["?"] * len(rowids))
        cur.execute(f"DELETE FROM movimientos_consumo WHERE rowid IN ({marks})", rowids)

    current_stock = {}
    rows = cur.execute("SELECT sku, COALESCE(stock_actual,0) FROM items").fetchall()
    for row in rows:
        current_stock[clean_text(row[0])] = float(row[1] or 0)

    ins_ok = 0
    ins_skip = 0
    for rec in parsed_rows:
        sku = rec["sku"]
        qty = rec["cantidad"]
        if current_stock[sku] - qty < 0:
            ins_skip += 1
            continue

        new_stock = current_stock[sku] - qty
        cur.execute(
            """
            INSERT INTO movimientos_consumo
            (item_sku, descripcion_item, fecha_consumo, solicitante_nombre,
             cantidad_consumida, precio_unitario, total_consumo, orden_trabajo_id,
             observaciones, stock_actual_en_consumo, documento_ref)
            VALUES (?,?,?,?,?,?,?,?,?,?,?)
            """,
            (
                sku,
                rec["descripcion"],
                rec["fecha_excel"],
                rec["solicitante"],
                qty,
                rec["precio"],
                rec["total"],
                rec["ot"],
                rec["obs"],
                new_stock,
                documento_ref,
            ),
        )
        cur.execute("UPDATE items SET stock_actual = ? WHERE sku = ?", (new_stock, sku))
        current_stock[sku] = new_stock
        ins_ok += 1

    con.commit()
    return backup_file, documento_ref, ins_ok, ins_skip


def main():
    parser = argparse.ArgumentParser(description="Migración profesional de consumos desde CSV")
    parser.add_argument("--db", default=r"c:\Users\bodega.NORTHCHROME\Downloads\north_chrome2\north_chrome\system\system.db")
    parser.add_argument("--csv", default=r"C:\Users\bodega.NORTHCHROME\Desktop\CONSUMOS.csv")
    parser.add_argument("--keep-year", type=int, default=2026)
    parser.add_argument("--keep-month", type=int, default=3)
    parser.add_argument("--apply", action="store_true", help="Aplica cambios reales (sin este flag es dry-run)")
    args = parser.parse_args()

    db_path = Path(args.db)
    csv_path = Path(args.csv)
    dry_run = not args.apply

    if not db_path.exists():
        raise FileNotFoundError(f"No existe DB: {db_path}")
    if not csv_path.exists():
        raise FileNotFoundError(f"No existe CSV: {csv_path}")

    con = sqlite3.connect(str(db_path))
    con.row_factory = sqlite3.Row
    cur = con.cursor()

    try:
        ensure_schema(cur, dry_run=dry_run)
        items = load_items(cur)
        parsed_rows, errors, unknown_skus = load_csv_rows(csv_path, items)
        rows_to_delete, d_ini, d_fin = get_rows_to_delete(cur, args.keep_year, args.keep_month)
        restore_by_sku, insert_ok, insert_skip_stock = dry_audit(cur, parsed_rows, rows_to_delete, items)

        print("=== PRE-AUDITORÍA ===")
        print(f"Rango preservado (serial Excel): [{d_ini}, {d_fin})")
        print(f"CSV filas válidas parseadas: {len(parsed_rows)}")
        print(f"CSV errores formato: {len(errors)}")
        print(f"SKUs desconocidos: {sum(unknown_skus.values())} ({len(unknown_skus)} sku únicos)")
        print(f"Filas DB a eliminar (fuera del mes preservado): {len(rows_to_delete)}")
        print(f"Filas que podrían insertarse por stock: {insert_ok}")
        print(f"Filas omitidas por stock insuficiente: {insert_skip_stock}")

        if errors[:10]:
            print("\nPrimeros errores CSV:")
            for e in errors[:10]:
                print(" -", e)

        if unknown_skus:
            print("\nTop SKUs desconocidos:")
            for sku, cnt in sorted(unknown_skus.items(), key=lambda x: x[1], reverse=True)[:15]:
                print(f" - {sku}: {cnt}")

        if dry_run:
            print("\n[DRY RUN] No se hicieron cambios.")
            return

        backup_dir = db_path.parent / "backups"
        backup_file, documento_ref, ins_ok, ins_skip = apply_migration(
            con=con,
            cur=cur,
            db_path=db_path,
            backup_dir=backup_dir,
            parsed_rows=parsed_rows,
            rows_to_delete=rows_to_delete,
            restore_by_sku=restore_by_sku,
        )

        print("\n=== EJECUCIÓN OK ===")
        print(f"Backup creado: {backup_file}")
        print(f"Eliminadas (fuera del mes preservado): {len(rows_to_delete)}")
        print(f"Insertadas desde CSV: {ins_ok}")
        print(f"Omitidas por stock: {ins_skip}")
        print(f"documento_ref migración: {documento_ref}")

    except Exception as e:
        con.rollback()
        print("\n[ERROR] rollback ejecutado:", str(e))
        raise
    finally:
        con.close()


if __name__ == "__main__":
    main()
