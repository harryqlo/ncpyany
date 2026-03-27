"""
Jobs operativos para confiabilidad del sistema.

Ejemplos:
  python jobs_operativos.py --mode daily
  python jobs_operativos.py --mode weekly-restore
"""

import argparse
import json
import shutil
import sqlite3
import tempfile
from datetime import datetime
from pathlib import Path

from app.db import get_db
from config import ALERTS, BACKUP_DIR, DB_PATH, SYSTEM_DIR
from logger_config import log_alert, log_immutable_event, logger


REPORTS_DIR = Path(SYSTEM_DIR) / "ops_reports"


def _safe_scalar(cursor, query, params=None):
    row = cursor.execute(query, params or []).fetchone()
    return row[0] if row else 0


def check_prestamos_vencidos():
    dias = int(ALERTS.get("prestamo_vencido_dias", 30))
    c = get_db("paniol")
    try:
        total = _safe_scalar(
            c,
            """
            SELECT COUNT(*)
            FROM herramientas_movimientos
            WHERE fecha_retorno IS NULL
            AND date(fecha_salida) <= date('now', '-' || ? || ' days')
            """,
            [dias],
        )

        if total > 0:
            log_alert(
                "PRESTAMOS_VENCIDOS",
                "HIGH",
                f"total={total} limite_dias={dias}",
            )

        return {
            "check": "prestamos_vencidos",
            "status": "alert" if total > 0 else "ok",
            "total": int(total),
            "limite_dias": dias,
        }
    finally:
        c.close()


def check_stock_critico():
    threshold = int(ALERTS.get("stock_critico", 5))

    c_general = get_db("general")
    c_paniol = get_db("paniol")
    try:
        crit_items = _safe_scalar(
            c_general,
            "SELECT COUNT(*) FROM items WHERE stock_actual <= ?",
            [threshold],
        )
        crit_herr = _safe_scalar(
            c_paniol,
            "SELECT COUNT(*) FROM herramientas WHERE cantidad_disponible <= ?",
            [threshold],
        )

        total = int(crit_items) + int(crit_herr)
        if total > 0:
            log_alert(
                "STOCK_CRITICO",
                "MEDIUM",
                (
                    f"items_bodega={int(crit_items)} "
                    f"herramientas_paniol={int(crit_herr)} umbral={threshold}"
                ),
            )

        return {
            "check": "stock_critico",
            "status": "alert" if total > 0 else "ok",
            "items_bodega": int(crit_items),
            "herramientas_paniol": int(crit_herr),
            "umbral": threshold,
        }
    finally:
        c_general.close()
        c_paniol.close()


def check_inconsistencias_cantidad():
    c = get_db("paniol")
    c_general = get_db("general")
    try:
        negativas = _safe_scalar(
            c,
            "SELECT COUNT(*) FROM herramientas WHERE cantidad_disponible < 0",
        )
        sobre_total = _safe_scalar(
            c,
            "SELECT COUNT(*) FROM herramientas WHERE cantidad_disponible > cantidad_total",
        )
        stock_general_negativo = _safe_scalar(
            c_general,
            "SELECT COUNT(*) FROM items WHERE stock_actual < 0",
        )
        total = int(negativas) + int(sobre_total) + int(stock_general_negativo)

        if total > 0:
            log_alert(
                "INCONSISTENCIA_CANTIDAD",
                "CRITICAL",
                (
                    f"herr_negativas={int(negativas)} "
                    f"herr_sobre_total={int(sobre_total)} "
                    f"items_stock_negativo={int(stock_general_negativo)}"
                ),
            )

        return {
            "check": "inconsistencias_cantidad",
            "status": "alert" if total > 0 else "ok",
            "negativas": int(negativas),
            "sobre_total": int(sobre_total),
            "items_stock_negativo": int(stock_general_negativo),
        }
    finally:
        c.close()
        c_general.close()


def check_db_integrity(db_path):
    conn = sqlite3.connect(str(db_path))
    try:
        result = conn.execute("PRAGMA integrity_check").fetchone()
        value = (result[0] if result else "unknown").lower()
        ok = value == "ok"
        if not ok:
            log_alert("DB_INTEGRITY", "CRITICAL", f"db={db_path} result={value}")
        return {
            "check": f"db_integrity:{Path(db_path).name}",
            "status": "ok" if ok else "alert",
            "result": value,
        }
    finally:
        conn.close()


def run_daily_checks():
    checks = [
        check_prestamos_vencidos(),
        check_stock_critico(),
        check_inconsistencias_cantidad(),
        check_db_integrity(DB_PATH),
    ]

    has_alert = any(item["status"] != "ok" for item in checks)
    payload = {
        "mode": "daily",
        "ts": datetime.utcnow().isoformat(),
        "checks": checks,
        "has_alert": has_alert,
    }

    if has_alert:
        logger.warning("Daily operational checks completed with alerts")
    else:
        logger.info("Daily operational checks completed successfully")

    log_immutable_event("OPERATIONS_DAILY_CHECK", payload, actor="system-job")
    return payload


def _latest_backup_file():
    backup_dir = Path(BACKUP_DIR)
    patterns = ["system_*.db.backup", "system_*.db"]
    files = []
    for pattern in patterns:
        files.extend(backup_dir.glob(pattern))
    if not files:
        return None
    return max(files, key=lambda p: p.stat().st_mtime)


def run_weekly_restore_test():
    source = _latest_backup_file()
    if source is None:
        msg = "No se encontró backup para restore test"
        log_alert("RESTORE_TEST", "CRITICAL", msg)
        payload = {
            "mode": "weekly-restore",
            "ts": datetime.utcnow().isoformat(),
            "status": "alert",
            "message": msg,
        }
        log_immutable_event("OPERATIONS_RESTORE_TEST", payload, actor="system-job")
        return payload

    with tempfile.TemporaryDirectory(prefix="nc_restore_test_") as tmp:
        restore_path = Path(tmp) / "restore_test.db"
        shutil.copy2(source, restore_path)

        integrity = check_db_integrity(restore_path)
        ok = integrity["status"] == "ok"

        payload = {
            "mode": "weekly-restore",
            "ts": datetime.utcnow().isoformat(),
            "status": "ok" if ok else "alert",
            "backup_source": str(source),
            "restore_target": str(restore_path),
            "integrity": integrity,
        }

        if ok:
            logger.info("Weekly restore test completed successfully")
        else:
            log_alert(
                "RESTORE_TEST",
                "CRITICAL",
                f"integrity_check failed source={source}",
            )

        log_immutable_event("OPERATIONS_RESTORE_TEST", payload, actor="system-job")
        return payload


def save_report(payload):
    REPORTS_DIR.mkdir(parents=True, exist_ok=True)
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    mode = payload.get("mode", "job")
    path = REPORTS_DIR / f"{mode}_{ts}.json"
    path.write_text(json.dumps(payload, ensure_ascii=True, indent=2), encoding="utf-8")
    return path


# ─────────────────────────────────────────────────────────────────────────────
# JOBS DE AUDITORÍAS DE INVENTARIO
# ─────────────────────────────────────────────────────────────────────────────

def _crear_sesion_auditoria(tipo: str) -> dict:
    """
    Genera una sesión de auditoría automática para el tipo dado.
    Delega la lógica de selección de ítems al módulo de auditorías.
    """
    c = get_db("general")
    try:
        plan = c.execute(
            "SELECT * FROM auditorias_planes WHERE tipo=? AND activo=1 LIMIT 1",
            [tipo]
        ).fetchone()

        if not plan:
            msg = f"Sin plan activo para tipo='{tipo}'"
            logger.warning(msg)
            return {"status": "skip", "motivo": "sin_plan", "tipo": tipo}

        plan = dict(plan)
        ciclo = plan["ciclo_actual"] if tipo == "rotativo" else None
        total_ciclos = plan["total_ciclos"] if tipo == "rotativo" else None

        # Reutilizar helper del blueprint para consistencia
        from app.routes.auditorias import _seleccionar_items
        items = _seleccionar_items(
            c, tipo,
            ciclo=ciclo,
            total_ciclos=total_ciclos,
            filtro_categoria=plan.get("filtro_categoria"),
            filtro_clase=plan.get("filtro_clase"),
        )

        if not items:
            logger.warning(f"Auditoria {tipo}: sin items para el ciclo {ciclo}")
            return {"status": "skip", "motivo": "sin_items", "tipo": tipo}

        from datetime import datetime as _dt, date as _d, timedelta as _td
        ahora = _dt.now().isoformat(timespec="seconds")
        semana = _d.today().strftime("%G-W%V")
        mes = _d.today().strftime("%Y-%m")

        cur = c.execute("""
            INSERT INTO auditorias_sesiones
                (plan_id,tipo,estado,fecha_inicio,auditado_por,
                 total_items,ciclo_numero,semana_iso,mes_periodo)
            VALUES (?,?,?,?,?,?,?,?,?)
        """, [plan["id"], tipo, "pendiente", ahora, "sistema",
               len(items), ciclo, semana, mes])
        sid = cur.lastrowid

        for it in items:
            c.execute("""
                INSERT OR IGNORE INTO auditorias_detalle
                    (sesion_id,item_sku,item_nombre,categoria,clase_abc,stock_sistema)
                VALUES (?,?,?,?,?,?)
            """, [sid, it["sku"], it["nombre"],
                  it["categoria_nombre"], it["clase_abc"], it["stock_sistema"]])

        # Avanzar rotación del plan
        if tipo == "rotativo" and total_ciclos:
            nuevo_ciclo = (ciclo % total_ciclos) + 1
            prox = (_d.today() + _td(days=7)).isoformat()
            c.execute(
                "UPDATE auditorias_planes SET ciclo_actual=?, fecha_proxima=? WHERE id=?",
                [nuevo_ciclo, prox, plan["id"]]
            )
        elif tipo == "semanal":
            prox = (_d.today() + _td(weeks=1)).isoformat()
            c.execute("UPDATE auditorias_planes SET fecha_proxima=? WHERE id=?",
                      [prox, plan["id"]])
        elif tipo == "mensual":
            hoy = _d.today()
            if hoy.month == 12:
                prox = _d(hoy.year + 1, 1, 1).isoformat()
            else:
                prox = _d(hoy.year, hoy.month + 1, 1).isoformat()
            c.execute("UPDATE auditorias_planes SET fecha_proxima=? WHERE id=?",
                      [prox, plan["id"]])

        c.commit()

        payload = {
            "tipo": tipo,
            "sesion_id": sid,
            "total_items": len(items),
            "ciclo": ciclo,
            "semana": semana,
            "mes": mes,
        }
        log_immutable_event("AUDITORIA_SESION_CREADA", payload, actor="system-job")
        logger.info(f"Auditoria {tipo}: sesion #{sid} creada con {len(items)} items")
        return {"status": "ok", **payload}

    except Exception as e:
        c.rollback()
        logger.error(f"Error creando auditoria {tipo}: {e}")
        return {"status": "error", "tipo": tipo, "msg": str(e)}
    finally:
        c.close()


def run_auditoria_rotativa():
    result = _crear_sesion_auditoria("rotativo")
    return {
        "mode": "auditoria-rotativa",
        "ts": datetime.utcnow().isoformat(),
        "has_alert": result["status"] == "error",
        **result,
    }


def run_auditoria_semanal():
    result = _crear_sesion_auditoria("semanal")
    return {
        "mode": "auditoria-semanal",
        "ts": datetime.utcnow().isoformat(),
        "has_alert": result["status"] == "error",
        **result,
    }


def run_auditoria_mensual():
    result = _crear_sesion_auditoria("mensual")
    return {
        "mode": "auditoria-mensual",
        "ts": datetime.utcnow().isoformat(),
        "has_alert": result["status"] == "error",
        **result,
    }


def run_actualizar_abc():
    try:
        from calcular_abc import calcular
        resultado = calcular(verbose=False)
        payload = {
            "mode": "actualizar-abc",
            "ts": datetime.utcnow().isoformat(),
            "has_alert": False,
            "status": "ok",
            "clasificacion": resultado,
        }
        log_immutable_event("ABC_ACTUALIZADO", payload, actor="system-job")
        logger.info(f"ABC actualizado: {resultado}")
        return payload
    except Exception as e:
        logger.error(f"Error actualizando ABC: {e}")
        return {
            "mode": "actualizar-abc",
            "ts": datetime.utcnow().isoformat(),
            "has_alert": True,
            "status": "error",
            "msg": str(e),
        }


# ─────────────────────────────────────────────────────────────────────────────
# ENTRY POINT
# ─────────────────────────────────────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Jobs operativos North Chrome")
    parser.add_argument(
        "--mode",
        choices=[
            "daily",
            "weekly-restore",
            "auditoria-rotativa",
            "auditoria-semanal",
            "auditoria-mensual",
            "actualizar-abc",
        ],
        default="daily",
        help="Tipo de job operativo",
    )
    args = parser.parse_args()

    mode_map = {
        "daily":              run_daily_checks,
        "weekly-restore":     run_weekly_restore_test,
        "auditoria-rotativa": run_auditoria_rotativa,
        "auditoria-semanal":  run_auditoria_semanal,
        "auditoria-mensual":  run_auditoria_mensual,
        "actualizar-abc":     run_actualizar_abc,
    }
    payload = mode_map[args.mode]()

    report_path = save_report(payload)
    print(json.dumps(payload, ensure_ascii=True, indent=2))
    print(f"Report saved: {report_path}")

    has_alert = payload.get("has_alert", False) or payload.get("status") == "alert"
    raise SystemExit(1 if has_alert else 0)


if __name__ == "__main__":
    main()
