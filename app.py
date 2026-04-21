from flask import Flask, request, jsonify, send_from_directory, g
from flask_cors import CORS
import sqlite3, hashlib, os
from datetime import datetime

# 🔥 Statsig
from statsig import statsig
statsig.initialize(os.getenv("STATSIG_SERVER_KEY"))

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
        db.commit(); db.close()

# ── AUTH
@app.route('/api/login', methods=['POST'])
def login():
    d = request.json
    u = get_db().execute("SELECT * FROM usuarios WHERE correo=? AND contrasena=?",
                         (d['correo'], h(d['contrasena']))).fetchone()

    if not u:
        statsig.log_event(
            user={"userID": d['correo']},
            event_name="login_fallido"
        )
        return jsonify({'ok':False,'msg':'Credenciales incorrectas'}),401

    statsig.log_event(
        user={"userID": u['id']},
        event_name="login_exitoso"
    )

    return jsonify({'ok':True,'usuario':{'id':u['id'],'nombre':u['nombre'],'correo':u['correo'],'rol':u['rol']}})

@app.route('/api/registro', methods=['POST'])
def registro():
    d = request.json
    try:
        get_db().execute("INSERT INTO usuarios(nombre,correo,contrasena) VALUES(?,?,?)",
                         (d['nombre'],d['correo'],h(d['contrasena'])))
        get_db().commit()

        statsig.log_event(
            user={"userID": d['correo']},
            event_name="registro_usuario"
        )

        u = get_db().execute("SELECT * FROM usuarios WHERE correo=?", (d['correo'],)).fetchone()
        return jsonify({'ok':True,'usuario':{'id':u['id'],'nombre':u['nombre'],'correo':u['correo'],'rol':u['rol']}})
    except:
        return jsonify({'ok':False,'msg':'Correo ya registrado'}),400

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

    statsig.log_event(
        user={"userID": "sistema"},
        event_name="consulta_stats"
    )

    return jsonify({'kwh_actual':ka,'kwh_anterior':kp,'delta':delta})

# ── CONSUMOS
@app.route('/api/consumos', methods=['POST'])
def add_consumo():
    d = request.json
    p = {r['clave']:float(r['valor']) for r in get_db().execute("SELECT * FROM parametros")}
    co2 = round(d['kwh']*p['factor_co2']/1000,4)

    get_db().execute("INSERT INTO consumos(usuario_id,area,kwh,fecha,medidor,co2_kg) VALUES(?,?,?,?,?,?)",
                     (d['usuario_id'],d['area'],d['kwh'],d['fecha'],d.get('medidor',''),co2))
    get_db().commit()

    statsig.log_event(
        user={"userID": d['usuario_id']},
        event_name="nuevo_consumo",
        value=d['kwh']
    )

    return jsonify({'ok':True,'co2_kg':co2})

# ── VISITA
@app.route('/')
def index():
    statsig.log_event(
        user={"userID": "anonimo"},
        event_name="visita_app"
    )
    return send_from_directory('templates','index.html')

if __name__ == '__main__':
    init_db()
    app.run(debug=True, port=5050)
