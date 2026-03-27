from flask import Blueprint, jsonify, request
from app.db import get_db
from app.search_utils import contains_terms_where

bp = Blueprint('componentes', __name__, url_prefix='/api/componentes')

@bp.route('', strict_slashes=False)
def api_comp():
    """
    Obtiene listado de componentes con filtros y paginación
    """
    c=get_db()
    try:
        pg=int(request.args.get('page',1)); pp2=int(request.args.get('per_page',50)); se=request.args.get('search','').strip()
        w,p=[],[]
        if se:
            search_where, search_params = contains_terms_where(se, ['nombre', 'codigo', 'descripcion'])
            if search_where:
                w.append(search_where)
                p += search_params
        ws=(' WHERE '+' AND '.join(w)) if w else ''
        t=c.execute(f'SELECT COUNT(*) FROM componentes{ws}',p).fetchone()[0]; o=(pg-1)*pp2
        rows=c.execute(f'SELECT id,nombre,codigo,descripcion FROM componentes{ws} ORDER BY id DESC LIMIT ? OFFSET ?',p+[pp2,o]).fetchall()
        items=[{'id':r[0],'nombre':r[1],'codigo':r[2],'descripcion':r[3]} for r in rows]
        return jsonify({'items':items,'total':t,'page':pg,'per_page':pp2,'total_pages':max(1,-(-t//pp2))})
    finally: c.close()

@bp.route('', methods=['POST'], strict_slashes=False)
def api_ccomp():
    """
    Crea un nuevo componente
    """
    c=get_db()
    try:
        d=request.json
        if not d.get('nombre'): return jsonify({'ok':False,'msg':'Nombre obligatorio'}),400
        c.execute('INSERT INTO componentes (nombre,codigo,descripcion) VALUES (?,?,?)',[d['nombre'],d.get('codigo',''),d.get('descripcion','')])
        c.commit()
        new_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]
        return jsonify({'ok':True,'msg':'Componente creado','id':new_id})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/<int:comp_id>', methods=['PUT'])
def api_ecomp(comp_id):
    """
    Edita un componente existente
    """
    c=get_db()
    try:
        exists = c.execute('SELECT id FROM componentes WHERE id=?',[comp_id]).fetchone()
        if not exists: return jsonify({'ok':False,'msg':'Componente no encontrado'}),404
        
        d=request.json
        if not d.get('nombre'): return jsonify({'ok':False,'msg':'Nombre obligatorio'}),400
        c.execute('UPDATE componentes SET nombre=?,codigo=?,descripcion=? WHERE id=?',[d['nombre'],d.get('codigo',''),d.get('descripcion',''),comp_id])
        c.commit()
        return jsonify({'ok':True,'msg':'Componente actualizado'})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/<int:comp_id>', methods=['DELETE'])
def api_dcomp(comp_id):
    """
    Elimina un componente y sus materiales asociados
    """
    c=get_db()
    try:
        exists = c.execute('SELECT id FROM componentes WHERE id=?',[comp_id]).fetchone()
        if not exists: return jsonify({'ok':False,'msg':'Componente no encontrado'}),404
        
        # Eliminar materiales asociados
        c.execute('DELETE FROM componentes_materiales WHERE componente_id=?',[comp_id])
        # Eliminar componente
        c.execute('DELETE FROM componentes WHERE id=?',[comp_id])
        c.commit()
        return jsonify({'ok':True,'msg':'Componente eliminado'})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/<int:comp_id>/materiales')
def api_comp_mat(comp_id):
    """
    Obtiene los materiales de un componente específico
    """
    c=get_db()
    try:
        rows=c.execute('SELECT cm.item_sku,cm.cantidad_necesaria,i.nombre,i.unidad_medida,i.stock_actual FROM componentes_materiales cm LEFT JOIN items i ON cm.item_sku=i.sku WHERE cm.componente_id=? ORDER BY cm.item_sku',[comp_id]).fetchall()
        items=[{'sku':r[0],'cantidad':r[1],'nombre':r[2] or '','unidad':r[3] or '','stock':r[4] or 0} for r in rows]
        return jsonify({'materiales':items})
    finally: c.close()

@bp.route('/<int:comp_id>/materiales', methods=['POST'])
def api_add_mat(comp_id):
    """
    Agrega un material a un componente
    """
    c=get_db()
    try:
        d=request.json
        if not d.get('sku'): return jsonify({'ok':False,'msg':'SKU obligatorio'}),400
        cantidad = float(d.get('cantidad',0))
        if cantidad <= 0: return jsonify({'ok':False,'msg':'Cantidad debe ser > 0'}),400
        
        # Verificar que el item existe
        item = c.execute('SELECT sku FROM items WHERE sku=?',[d['sku']]).fetchone()
        if not item: return jsonify({'ok':False,'msg':'Item no encontrado'}),404
        
        # Verificar si ya existe
        exists = c.execute('SELECT componente_id FROM componentes_materiales WHERE componente_id=? AND item_sku=?',[comp_id,d['sku']]).fetchone()
        if exists:
            # Actualizar cantidad
            c.execute('UPDATE componentes_materiales SET cantidad_necesaria=? WHERE componente_id=? AND item_sku=?',[cantidad,comp_id,d['sku']])
        else:
            # Insertar nuevo
            c.execute('INSERT INTO componentes_materiales (componente_id,item_sku,cantidad_necesaria) VALUES (?,?,?)',[comp_id,d['sku'],cantidad])
        
        c.commit()
        return jsonify({'ok':True,'msg':'Material agregado'})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/<int:comp_id>/materiales/<sku>', methods=['DELETE'])
def api_rm_mat(comp_id, sku):
    """
    Elimina un material de un componente
    """
    c=get_db()
    try:
        c.execute('DELETE FROM componentes_materiales WHERE componente_id=? AND item_sku=?',[comp_id,sku])
        c.commit()
        return jsonify({'ok':True,'msg':'Material eliminado'})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/<int:comp_id>/stock-necesario')
def api_stock_nec(comp_id):
    """
    Calcula el stock necesario vs disponible para producir un componente
    """
    c=get_db()
    try:
        rows=c.execute('SELECT cm.item_sku,cm.cantidad_necesaria,i.nombre,i.stock_actual,i.unidad_medida FROM componentes_materiales cm LEFT JOIN items i ON cm.item_sku=i.sku WHERE cm.componente_id=?',[comp_id]).fetchall()
        
        materiales = []
        puede_producir = True
        for r in rows:
            sku, necesario, nombre, stock, unidad = r
            stock = stock or 0
            suficiente = stock >= necesario
            if not suficiente: puede_producir = False
            materiales.append({
                'sku': sku,
                'nombre': nombre or '',
                'necesario': necesario,
                'disponible': stock,
                'unidad': unidad or '',
                'suficiente': suficiente,
                'faltante': max(0, necesario - stock)
            })
        
        return jsonify({'materiales': materiales, 'puede_producir': puede_producir})
    finally: c.close()
