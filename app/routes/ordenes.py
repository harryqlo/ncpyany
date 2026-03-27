
from flask import Blueprint, jsonify, request
from app.db import get_db, date_to_excel, excel_to_date
from app.search_utils import contains_terms_where
from datetime import datetime

bp = Blueprint('ordenes', __name__, url_prefix='/api/ordenes')

@bp.route('', strict_slashes=False)
def api_ot():
    """
    Obtiene listado de órdenes de trabajo
    """
    c=get_db()
    try:
        pg=int(request.args.get('page',1)); pp2=int(request.args.get('per_page',50)); se=request.args.get('search','').strip()
        w,p=[],[]
        if se:
            search_where, search_params = contains_terms_where(se, ['CAST(id AS TEXT)', 'descripcion_componente', 'cliente_nombre'])
            if search_where:
                w.append(search_where)
                p += search_params
        ws=(' WHERE '+' AND '.join(w)) if w else ''
        t=c.execute(f'SELECT COUNT(*) FROM ordenes_trabajo{ws}',p).fetchone()[0]; o=(pg-1)*pp2
        rows=c.execute(f'SELECT id,estado_ingreso,registro_referencia,descripcion_componente,cliente_nombre,fecha_ot,codigo_referencia,listado_materiales FROM ordenes_trabajo{ws} ORDER BY id DESC LIMIT ? OFFSET ?',p+[pp2,o]).fetchall()
        items=[{'id':r[0],'estado':r[1],'referencia':r[2],'descripcion':r[3],'cliente':r[4],'fecha':excel_to_date(r[5]) if r[5] else None,'codigo':r[6],'materiales':r[7]} for r in rows]
        return jsonify({'items':items,'total':t,'page':pg,'per_page':pp2,'total_pages':max(1,-(-t//pp2))})
    finally: c.close()

@bp.route('', methods=['POST'], strict_slashes=False)
def api_cot():
    """
    Crea una nueva orden de trabajo
    """
    c=get_db()
    try:
        d=request.json; fs=date_to_excel(d.get('fecha',datetime.now().strftime('%Y-%m-%d')))
        c.execute('INSERT INTO ordenes_trabajo (estado_ingreso,registro_referencia,descripcion_componente,cliente_nombre,fecha_ot,codigo_referencia,listado_materiales) VALUES (?,?,?,?,?,?,?)',[d.get('estado',''),d.get('referencia',''),d.get('descripcion',''),d.get('cliente',''),fs,d.get('codigo',''),d.get('materiales','')]); 
        c.commit()
        # Obtener el ID de la OT recién creada
        new_id = c.execute('SELECT last_insert_rowid()').fetchone()[0]
        return jsonify({'ok':True,'msg':'OT creada','id':new_id})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/<int:ot_id>', methods=['PUT'])
def api_eot(ot_id):
    """
    Edita una orden de trabajo existente
    """
    c=get_db()
    try:
        # Verificar que existe
        exists = c.execute('SELECT id FROM ordenes_trabajo WHERE id=?',[ot_id]).fetchone()
        if not exists: return jsonify({'ok':False,'msg':'OT no encontrada'}),404
        
        d=request.json; fs=date_to_excel(d.get('fecha',datetime.now().strftime('%Y-%m-%d')))
        c.execute('UPDATE ordenes_trabajo SET estado_ingreso=?,registro_referencia=?,descripcion_componente=?,cliente_nombre=?,fecha_ot=?,codigo_referencia=?,listado_materiales=? WHERE id=?',[d.get('estado',''),d.get('referencia',''),d.get('descripcion',''),d.get('cliente',''),fs,d.get('codigo',''),d.get('materiales',''),ot_id])
        c.commit()
        return jsonify({'ok':True,'msg':'OT actualizada'})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/<int:ot_id>', methods=['DELETE'])
def api_dot(ot_id):
    """
    Elimina una orden de trabajo
    """
    c=get_db()
    try:
        # Verificar que existe
        exists = c.execute('SELECT id FROM ordenes_trabajo WHERE id=?',[ot_id]).fetchone()
        if not exists: return jsonify({'ok':False,'msg':'OT no encontrada'}),404
        
        c.execute('DELETE FROM ordenes_trabajo WHERE id=?',[ot_id])
        c.commit()
        return jsonify({'ok':True,'msg':'OT eliminada'})
    except Exception as e: return jsonify({'ok':False,'msg':str(e)}),400
    finally: c.close()

@bp.route('/siguiente')
def api_sot():
    """
    Obtiene el siguiente número de OT disponible
    """
    c=get_db()
    try:
        last = c.execute('SELECT MAX(id) FROM ordenes_trabajo').fetchone()[0]
        siguiente = (last or 0) + 1
        return jsonify({'siguiente':siguiente})
    finally: c.close()
