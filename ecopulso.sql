-- ============================================================
--  EcoPulso — Base de Datos Completa (SQL)
--  Sistema de Gestión Energética · ODS 7 (Meta 7.3)
--  Universidad Cooperativa de Colombia · Campus Montería
--  Ingeniería de Sistemas · Febrero 2026
--  Equipo: Juan Negrette, Cinthya Cogollo, Yulissa Garces
--  Docente: Mauricio Ricardo Padilla
-- ============================================================

DROP TABLE IF EXISTS simulaciones;
DROP TABLE IF EXISTS consumos;
DROP TABLE IF EXISTS parametros;
DROP TABLE IF EXISTS usuarios;

-- ─── TABLA: usuarios
CREATE TABLE usuarios (
    id          INTEGER  PRIMARY KEY AUTOINCREMENT,
    nombre      TEXT     NOT NULL,
    correo      TEXT     NOT NULL UNIQUE,
    contrasena  TEXT     NOT NULL,
    rol         TEXT     NOT NULL DEFAULT 'gestor' CHECK(rol IN ('admin','gestor')),
    created_at  TEXT     NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_usuarios_correo ON usuarios(correo);

-- ─── TABLA: consumos
CREATE TABLE consumos (
    id          INTEGER  PRIMARY KEY AUTOINCREMENT,
    usuario_id  INTEGER  NOT NULL REFERENCES usuarios(id) ON DELETE CASCADE,
    area        TEXT     NOT NULL,
    kwh         REAL     NOT NULL CHECK(kwh >= 0),
    fecha       TEXT     NOT NULL,
    medidor     TEXT,
    co2_kg      REAL,
    created_at  TEXT     NOT NULL DEFAULT (datetime('now'))
);
CREATE INDEX IF NOT EXISTS idx_consumos_fecha   ON consumos(fecha);
CREATE INDEX IF NOT EXISTS idx_consumos_area    ON consumos(area);
CREATE INDEX IF NOT EXISTS idx_consumos_usuario ON consumos(usuario_id);

-- ─── TABLA: simulaciones
CREATE TABLE simulaciones (
    id                INTEGER  PRIMARY KEY AUTOINCREMENT,
    usuario_id        INTEGER  REFERENCES usuarios(id) ON DELETE SET NULL,
    descripcion       TEXT,
    kwh_actual        REAL     NOT NULL,
    porcentaje_ahorro REAL     NOT NULL CHECK(porcentaje_ahorro BETWEEN 0.1 AND 99.9),
    kwh_proyectado    REAL     NOT NULL,
    ahorro_cop        REAL     NOT NULL,
    co2_evitado       REAL     NOT NULL,
    created_at        TEXT     NOT NULL DEFAULT (datetime('now'))
);

-- ─── TABLA: parametros
CREATE TABLE parametros (
    id      INTEGER  PRIMARY KEY AUTOINCREMENT,
    clave   TEXT     NOT NULL UNIQUE,
    valor   TEXT     NOT NULL
);

-- ─── VISTAS
CREATE VIEW IF NOT EXISTS v_consumo_mensual AS
SELECT substr(fecha,1,7) AS mes, SUM(kwh) AS total_kwh,
       SUM(co2_kg) AS total_co2_kg, COUNT(*) AS registros,
       ROUND(SUM(kwh)*750,0) AS costo_cop
FROM consumos GROUP BY substr(fecha,1,7) ORDER BY mes;

CREATE VIEW IF NOT EXISTS v_consumo_por_area AS
SELECT area, COUNT(*) AS registros, ROUND(SUM(kwh),2) AS total_kwh,
       ROUND(SUM(kwh)*100.0/(SELECT SUM(kwh) FROM consumos),1) AS pct_total,
       ROUND(SUM(co2_kg),4) AS total_co2_kg, ROUND(SUM(kwh)*750,0) AS costo_cop
FROM consumos GROUP BY area ORDER BY total_kwh DESC;

-- ────────────────────────────────────────────────
--  DATOS
-- ────────────────────────────────────────────────

INSERT INTO parametros(clave,valor) VALUES
    ('tarifa_kwh_cop','750'),
    ('factor_co2','0.4'),
    ('meta_mensual_kwh','5000');

-- Contraseña: admin123 → SHA-256
INSERT INTO usuarios(id,nombre,correo,contrasena,rol,created_at) VALUES
    (1,'Admin EcoPulso','admin@ecopulso.co',
     '240be518fabd2724ddb6f04eeb1da5967448d7e831c08c8fa822809f74c720a9',
     'admin','2026-02-01 08:00:00');

-- Consumos: Agosto 2025 → Abril 2026 (36 registros)
-- factor CO2: 0.4 kg / kWh → co2_kg = kwh * 0.4 / 1000
INSERT INTO consumos(usuario_id,area,kwh,fecha,medidor,co2_kg) VALUES
(1,'Aulas',2100,'2025-08-15','MED-01',0.84),
(1,'Laboratorios',1200,'2025-08-15','MED-02',0.48),
(1,'Administrativo',900,'2025-08-15','MED-03',0.36),
(1,'Otros',400,'2025-08-15','MED-04',0.16),
(1,'Aulas',1900,'2025-09-15','MED-01',0.76),
(1,'Laboratorios',1100,'2025-09-15','MED-02',0.44),
(1,'Administrativo',850,'2025-09-15','MED-03',0.34),
(1,'Otros',350,'2025-09-15','MED-04',0.14),
(1,'Aulas',2200,'2025-10-15','MED-01',0.88),
(1,'Laboratorios',1300,'2025-10-15','MED-02',0.52),
(1,'Administrativo',950,'2025-10-15','MED-03',0.38),
(1,'Otros',450,'2025-10-15','MED-04',0.18),
(1,'Aulas',1800,'2025-11-15','MED-01',0.72),
(1,'Laboratorios',1050,'2025-11-15','MED-02',0.42),
(1,'Administrativo',820,'2025-11-15','MED-03',0.328),
(1,'Otros',330,'2025-11-15','MED-04',0.132),
(1,'Aulas',2400,'2025-12-15','MED-01',0.96),
(1,'Laboratorios',1500,'2025-12-15','MED-02',0.60),
(1,'Administrativo',1100,'2025-12-15','MED-03',0.44),
(1,'Otros',500,'2025-12-15','MED-04',0.20),
(1,'Aulas',1700,'2026-01-15','MED-01',0.68),
(1,'Laboratorios',1000,'2026-01-15','MED-02',0.40),
(1,'Administrativo',800,'2026-01-15','MED-03',0.32),
(1,'Otros',300,'2026-01-15','MED-04',0.12),
(1,'Aulas',2000,'2026-02-15','MED-01',0.80),
(1,'Laboratorios',1200,'2026-02-15','MED-02',0.48),
(1,'Administrativo',900,'2026-02-15','MED-03',0.36),
(1,'Otros',400,'2026-02-15','MED-04',0.16),
(1,'Aulas',1950,'2026-03-15','MED-01',0.78),
(1,'Laboratorios',1150,'2026-03-15','MED-02',0.46),
(1,'Administrativo',870,'2026-03-15','MED-03',0.348),
(1,'Otros',380,'2026-03-15','MED-04',0.152),
(1,'Aulas',1950,'2026-04-15','MED-01',0.78),
(1,'Laboratorios',1200,'2026-04-15','MED-02',0.48),
(1,'Administrativo',870,'2026-04-15','MED-03',0.348),
(1,'Otros',380,'2026-04-15','MED-04',0.152);

-- ============================================================
--  CONSULTAS DE REFERENCIA
-- ============================================================
/*
SELECT * FROM v_consumo_mensual;
SELECT * FROM v_consumo_por_area;
SELECT SUM(kwh) FROM consumos WHERE fecha LIKE strftime('%Y-%m','now') || '%';
*/
