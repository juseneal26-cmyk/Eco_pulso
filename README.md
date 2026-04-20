# EcoPulso 🌊⚡
**Sistema de Gestión Energética · ODS 7 Meta 7.3**
Universidad Cooperativa de Colombia · Campus Montería · 2026

**Equipo:** Juan Negrette · Cinthya Cogollo · Yulissa Garces
**Docente:** Mauricio Ricardo Padilla

---

## Instalación en 3 pasos

```bash
# 1. Instalar dependencias Python
pip install flask flask-cors

# 2. Iniciar el servidor
python app.py

# 3. Abrir en el navegador
http://localhost:5050
```

**Login demo:** `admin@ecopulso.co` / `admin123`

---

## Estructura del proyecto

```
ecopulso/
├── app.py              ← Backend Flask + API REST (8 endpoints)
├── ecopulso.db         ← Base de datos SQLite (auto-generada)
├── ecopulso.sql        ← Script SQL completo (schema + datos)
├── README.md
└── templates/
    └── index.html      ← Frontend completo (SPA)
```

## Base de datos

| Tabla | Descripción |
|-------|-------------|
| `usuarios` | Cuentas con rol admin/gestor, hash SHA-256 |
| `consumos` | 36 registros Ago 2025 → Abr 2026, 4 áreas |
| `simulaciones` | Escenarios de ahorro guardados |
| `parametros` | Tarifa COP, factor CO₂, meta mensual |

## API REST

| Método | Ruta | Descripción |
|--------|------|-------------|
| POST | `/api/login` | Autenticación |
| POST | `/api/registro` | Crear cuenta |
| GET | `/api/stats` | KPIs del dashboard |
| GET/POST | `/api/consumos` | Listar / crear consumo |
| DELETE | `/api/consumos/:id` | Eliminar registro |
| GET/POST | `/api/simulaciones` | Historial / crear simulación |
| GET | `/api/usuarios` | Listar usuarios |
