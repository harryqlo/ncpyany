import re
content = open('index.html', encoding='utf-8').read()

ids_html = set(re.findall(r'id="(mant-form-[^"]+)"', content))
print("IDs mant-form en HTML:")
for i in sorted(ids_html): print(" ", i)

# IDs que busca el JS
js_ids = [
    'mant-form-herr-nombre','mant-form-id','mant-form-tipo','mant-form-descripcion',
    'mant-form-fecha','mant-form-responsable','mant-form-tecnico','mant-form-taller',
    'mant-form-orden-trabajo','mant-form-presupuesto','mant-form-costo-final',
    'mant-form-tiempo-est','mant-form-tiempo-real','mant-form-proveedor',
    'mant-form-proxima-fecha','mant-form-observaciones','mant-form-nota-interna',
    'mant-galeria-previsualizacion','mant-contador-fotos'
]
print("\nFaltantes en HTML:")
for i in js_ids:
    if i not in ids_html:
        print(f"  FALTA: {i}")
print("OK" if all(i in ids_html for i in js_ids if i != 'mant-form-id') else "")
