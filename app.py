from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
import sqlite3, hashlib, os
from datetime import datetime

app = Flask(__name__, template_folder='templates')
CORS(app)
DB = os.path.join(os.path.dirname(__file__), 'ecopulso.db')

def get_db():
    db = getattr(g, '_db', None)
    if db is None:
        db = g._db = sqlite3.connect(DB)
        db.row_factory = sqlite3.Row
    return db

@app.teardown_appcontext
def close_db(e):
    db = getattr(g, '_db', None)
    if db: db.close()

def h(pw): return hashlib.sha256(pw.encode()).hexdigest()

def init_db():
    with app.app_context():
        db = sqlite3.connect(DB)
        db.executescript("""
        CREATE TABLE IF NOT EXISTS usuarios (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nombre TEXT NOT NULL,
            correo TEXT UNIQUE NOT NULL,
            contrasena TEXT NOT NULL,
            rol TEXT DEFAULT 'gestor',
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS consumos (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER REFERENCES usuarios(id),
            area TEXT NOT NULL,
            kwh REAL NOT NULL CHECK(kwh>=0),
            fecha TEXT NOT NULL,
            medidor TEXT,
            co2_kg REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS simulaciones (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            usuario_id INTEGER,
            descripcion TEXT,
            kwh_actual REAL,
            porcentaje_ahorro REAL,
            kwh_proyectado REAL,
            ahorro_cop REAL,
            co2_evitado REAL,
            created_at TEXT DEFAULT (datetime('now'))
        );
        CREATE TABLE IF NOT EXISTS parametros (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            clave TEXT UNIQUE NOT NULL,
            valor TEXT NOT NULL
        );
        INSERT OR IGNORE INTO parametros(clave,valor) VALUES
            ('tarifa_kwh_cop','750'),('factor_co2','0.4'),('meta_mensual_kwh','5000');
        INSERT OR IGNORE INTO usuarios(nombre,correo,contrasena,rol) VALUES
            ('Admin EcoPulso','admin@ecopulso.co',
             '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9','admin');
        """)
        # Seed consumos
        count = db.execute("SELECT COUNT(*) FROM consumos").fetchone()[0]
        if count == 0:
            areas = ['Aulas','Laboratorios','Administrativo','Otros']
            data = [
                ('2025-08',[2100,1200,900,400]),('2025-09',[1900,1100,850,350]),
                ('2025-10',[2200,1300,950,450]),('2025-11',[1800,1050,820,330]),
                ('2025-12',[2400,1500,1100,500]),('2026-01',[1700,1000,800,300]),
                ('2026-02',[2000,1200,900,400]),('2026-03',[1950,1150,870,380]),
                ('2026-04',[1950,1200,870,380]),
            ]
            for mes, vals in data:
                for i, area in enumerate(areas):
                    co2 = round(vals[i]*0.4/1000,4)
                    db.execute("INSERT INTO consumos(usuario_id,area,kwh,fecha,medidor,co2_kg) VALUES(?,?,?,?,?,?)",
                               (1,area,vals[i],mes+'-15','MED-0'+str(i+1),co2))
        db.commit(); db.close()

# ── AUTH
@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    u = get_db().execute("SELECT * FROM usuarios WHERE correo=? AND contrasena=?",
                         (d['correo'], h(d['contrasena']))).fetchone()
    if not u: return jsonify({'ok':False,'msg':'Credenciales incorrectas'}),401
    return jsonify({'ok':True,'usuario':{'id':u['id'],'nombre':u['nombre'],'correo':u['correo'],'rol':u['rol']}})

@app.route('/api/registro', methods=['POST'])
def registro():
    d = request.json
    try:
        get_db().execute("INSERT INTO usuarios(nombre,correo,contrasena) VALUES(?,?,?)",
                         (d['nombre'],d['correo'],h(d['contrasena'])))
        get_db().commit()
        u = get_db().execute("SELECT * FROM usuarios WHERE correo=?", (d['correo'],)).fetchone()
        return jsonify({'ok':True,'usuario':{'id':u['id'],'nombre':u['nombre'],'correo':u['correo'],'rol':u['rol']}})
    except: return jsonify({'ok':False,'msg':'Correo ya registrado'}),400

# ── STATS
@app.route('/api/stats')
def stats():
    db = get_db()
    p = {r['clave']:float(r['valor']) for r in db.execute("SELECT * FROM parametros")}
    tarifa, factor, meta = p['tarifa_kwh_cop'], p['factor_co2'], p['meta_mensual_kwh']
    now = datetime.now()
    mes = now.strftime('%Y-%m')
    mes_ant = f"{now.year}-{now.month-1:02d}" if now.month>1 else f"{now.year-1}-12"
    def kwh(m): return db.execute("SELECT COALESCE(SUM(kwh),0) FROM consumos WHERE fecha LIKE ?", (m+'%',)).fetchone()[0]
    ka, kp = kwh(mes), kwh(mes_ant)
    delta = round(((ka-kp)/kp*100) if kp else 0, 1)
    por_mes = [dict(r) for r in db.execute(
        "SELECT substr(fecha,1,7) mes, SUM(kwh) total, SUM(co2_kg) co2 FROM consumos GROUP BY mes ORDER BY mes DESC LIMIT 9")]
    por_area = [dict(r) for r in db.execute(
        "SELECT area, SUM(kwh) total FROM consumos GROUP BY area ORDER BY total DESC")]
    total_all = sum(a['total'] for a in por_area) or 1
    for a in por_area: a['pct'] = round(a['total']/total_all*100,1)
    return jsonify({'kwh_actual':ka,'kwh_anterior':kp,'delta':delta,
                    'costo':round(ka*tarifa),'co2':round(ka*factor/1000,3),
                    'eficiencia':round(max(0,min(100,(1-ka/meta)*100+50)),1) if meta else 0,
                    'meta':meta,'tarifa':tarifa,
                    'por_mes':list(reversed(por_mes)),'por_area':por_area})

# ── CONSUMOS
@app.route('/api/consumos', methods=['GET'])
def get_consumos():
    rows = get_db().execute("SELECT c.*,u.nombre usuario FROM consumos c JOIN usuarios u ON c.usuario_id=u.id ORDER BY c.fecha DESC LIMIT 200").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/consumos', methods=['POST'])
def add_consumo():
    d = request.json
    p = {r['clave']:float(r['valor']) for r in get_db().execute("SELECT * FROM parametros")}
    co2 = round(d['kwh']*p['factor_co2']/1000,4)
    get_db().execute("INSERT INTO consumos(usuario_id,area,kwh,fecha,medidor,co2_kg) VALUES(?,?,?,?,?,?)",
                     (d['usuario_id'],d['area'],d['kwh'],d['fecha'],d.get('medidor',''),co2))
    get_db().commit()
    return jsonify({'ok':True,'co2_kg':co2})

@app.route('/api/consumos/<int:cid>', methods=['DELETE'])
def del_consumo(cid):
    get_db().execute("DELETE FROM consumos WHERE id=?", (cid,))
    get_db().commit()
    return jsonify({'ok':True})

# ── SIMULACIONES
@app.route('/api/simulaciones', methods=['GET'])
def get_sims():
    rows = get_db().execute("SELECT * FROM simulaciones ORDER BY created_at DESC LIMIT 50").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/api/simulaciones', methods=['POST'])
def add_sim():
    d = request.json
    p = {r['clave']:float(r['valor']) for r in get_db().execute("SELECT * FROM parametros")}
    pct = d['porcentaje_ahorro']/100
    proy = round(d['kwh_actual']*(1-pct),2)
    ahorro = round((d['kwh_actual']-proy)*p['tarifa_kwh_cop'])
    co2ev = round((d['kwh_actual']-proy)*p['factor_co2']/1000*1000,2)
    get_db().execute("INSERT INTO simulaciones(usuario_id,descripcion,kwh_actual,porcentaje_ahorro,kwh_proyectado,ahorro_cop,co2_evitado) VALUES(?,?,?,?,?,?,?)",
                     (d.get('usuario_id',1),d.get('descripcion',''),d['kwh_actual'],d['porcentaje_ahorro'],proy,ahorro,co2ev))
    get_db().commit()
    return jsonify({'ok':True,'kwh_proyectado':proy,'ahorro_cop':ahorro,'co2_evitado':co2ev})

# ── USUARIOS
@app.route('/api/usuarios')
def get_usuarios():
    rows = get_db().execute("SELECT id,nombre,correo,rol,created_at FROM usuarios").fetchall()
    return jsonify([dict(r) for r in rows])

@app.route('/')
def index(): return send_from_directory('templates','index.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5050)
