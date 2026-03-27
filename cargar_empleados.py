"""Carga empleados reales reemplazando datos demo."""
import sqlite3, shutil
from datetime import date

src = 'system/system.db'
bak = f'system/system_backup_{date.today().isoformat()}.db'
shutil.copy2(src, bak)
print(f'Backup: {bak}')

conn = sqlite3.connect(src)
c = conn.cursor()

c.execute('DELETE FROM herramientas_movimientos')
print(f'Movimientos demo eliminados: {c.rowcount}')
c.execute('DELETE FROM empleados')
print(f'Empleados demo eliminados: {c.rowcount}')

empleados = [
    ('2001', 'EDUARDO MORENO', 'inactivo'),
    ('2002', 'ALEJANDRO OSORIO', 'activo'),
    ('2003', 'JHON ECHEVERRIA', 'activo'),
    ('2004', 'CARLOS ALFARO', 'inactivo'),
    ('2008', 'ALEXANDER LOPEZ', 'activo'),
    ('2009', 'CRISTOPHER PEREZ', 'inactivo'),
    ('2011', 'EDWIN BARRIOS', 'activo'),
    ('2012', 'ANDRES CASTILLO', 'activo'),
    ('2013', 'AXEL ZULETA', 'inactivo'),
    ('2014', 'JUAN SANCHOS', 'activo'),
    ('2016', 'JOSE VERDEJO', 'activo'),
    ('2020', 'MIGUEL CRUZ V.', 'activo'),
    ('2021', 'NICOLAS CARVALLO', 'inactivo'),
    ('2026', 'WALTER MUÑOZ', 'activo'),
    ('2027', 'RENE SANCHEZ', 'activo'),
    ('2030', 'AYMER ORTEGA', 'activo'),
    ('2031', 'JEAN CASTRO', 'activo'),
    ('2032', 'JASSON MORENO', 'inactivo'),
    ('2034', 'LIMBERTH FLORES', 'inactivo'),
    ('2038', 'MATIAS BARNETT', 'inactivo'),
    ('2041', 'JAVIERA ROJAS', 'inactivo'),
    ('2042', 'RUBEN GONZALEZ', 'inactivo'),
    ('2043', 'WALDO GONZALEZ', 'inactivo'),
    ('2044', 'SEBASTIAN MANCILLA', 'inactivo'),
    ('2046', 'DANIEL VIERA', 'activo'),
    ('2047', 'NORTH CHROME', 'activo'),
    ('2050', 'MAURICIO VERDEJO', 'activo'),
    ('2053', 'JOHAN LONDOÑO', 'inactivo'),
    ('2054', 'JAVIER BARRERA', 'activo'),
    ('2060', 'LUIS FAUNDES', 'inactivo'),
    ('2061', 'GABRIEL MIRANDA', 'activo'),
    ('2065', 'GONZALO AREYUNA', 'activo'),
    ('2066', 'DAVID STEVEN SOLIS', 'inactivo'),
]

c.executemany(
    "INSERT INTO empleados (numero_identificacion, nombre, estado, fecha_creacion) VALUES (?, ?, ?, date('now'))",
    empleados
)

conn.commit()

c.execute('SELECT COUNT(*) FROM empleados')
total = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM empleados WHERE estado='activo'")
activos = c.fetchone()[0]
c.execute("SELECT COUNT(*) FROM empleados WHERE estado='inactivo'")
inactivos = c.fetchone()[0]

print(f'\nEmpleados cargados: {total}')
print(f'  Activos: {activos}')
print(f'  Inactivos (finiquitados): {inactivos}')

print('\n--- Lista completa ---')
c.execute('SELECT numero_identificacion, nombre, estado FROM empleados ORDER BY numero_identificacion')
for r in c.fetchall():
    print(f'  {r[0]}  {r[1]:<25} {r[2]}')

conn.close()
print('\nOK')
