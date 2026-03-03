# Propuesta de Diseño: Dashboard de Uso del Proxy Bedrock

## 📋 Resumen Ejecutivo

Diseño de una nueva pantalla integrada en el dashboard actual para consultar y visualizar el uso del proxy Bedrock por parte de los usuarios, con gráficas interactivas y análisis por equipos.

---

## 🎨 Diseño Visual

### Look and Feel
- **Estilo Base**: Mismo diseño que el dashboard actual (AWS Amazon Ember font, colores corporativos)
- **Inspiración**: Página de referencia con esquema de colores teal/verde azulado (#4A9B8E)
- **Diseño**: Más compacto y orientado a métricas visuales
- **Responsive**: Adaptable a diferentes tamaños de pantalla

### Paleta de Colores
```css
--primary-teal: #4A9B8E;
--primary-teal-dark: #3A7B6E;
--primary-teal-light: #6ABBA8;
--accent-orange: #FF9900;
--accent-blue: #0073BB;
--accent-purple: #8B5CF6;
--background-light: #F5F7FA;
--text-primary: #232F3E;
--text-secondary: #687078;
--border-color: #D5DBDB;
--success-green: #16A34A;
--warning-yellow: #F59E0B;
--error-red: #DC2626;
```

---

## 📐 Estructura de la Página

### 1. Navegación Principal
**Ubicación**: Barra de tabs existente
```
[Users] [Tokens] [Profiles] [Groups] [Permissions] [Proxy Bedrock] ← NUEVO
```

**Icono SVG**:
```html
<svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" stroke-width="1.5" stroke="currentColor">
    <path stroke-linecap="round" stroke-linejoin="round" d="M3 13.125C3 12.504 3.504 12 4.125 12h2.25c.621 0 1.125.504 1.125 1.125v6.75C7.5 20.496 6.996 21 6.375 21h-2.25A1.125 1.125 0 013 19.875v-6.75zM9.75 8.625c0-.621.504-1.125 1.125-1.125h2.25c.621 0 1.125.504 1.125 1.125v11.25c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V8.625zM16.5 4.125c0-.621.504-1.125 1.125-1.125h2.25C20.496 3 21 3.504 21 4.125v15.75c0 .621-.504 1.125-1.125 1.125h-2.25a1.125 1.125 0 01-1.125-1.125V4.125z" />
</svg>
```

---

### 2. Sección de Filtros (Header)

```
┌─────────────────────────────────────────────────────────────────┐
│  📊 Proxy Bedrock Usage Analytics                    [Refresh]  │
│                                                                   │
│  📅 Fecha Desde: [2026-03-03 ▼]  Hasta: [2026-03-03 ▼]  [Apply]│
│                                                                   │
│  Quick Filters: [Today] [Last 7 Days] [Last 30 Days] [Custom]  │
└─────────────────────────────────────────────────────────────────┘
```

**Características**:
- Selector de fechas con calendario desplegable (usando HTML5 date input)
- Por defecto: día actual
- Botones de filtro rápido para períodos comunes
- Botón de refresh para actualizar datos

---

### 3. Barra Superior - Métricas Globales (KPIs)

```
┌──────────────────┬──────────────────┬──────────────────┬──────────────────┐
│  Total Requests  │  Total Tokens    │  Total Cost      │  Avg Response    │
│     12,458       │    2.4M          │    $124.50       │     1,234ms      │
│  ↑ 15% vs prev   │  ↑ 12% vs prev   │  ↑ 18% vs prev   │  ↓ 5% vs prev    │
└──────────────────┴──────────────────┴──────────────────┴──────────────────┘
```

**Características**:
- 4 tarjetas de métricas principales
- Indicadores de tendencia (↑↓) comparando con período anterior
- Colores: verde para mejoras, rojo para empeoramientos
- Animación de conteo al cargar

---

### 4. Barra de Gráficas Principales (3 columnas)

```
┌─────────────────────┬─────────────────────┬─────────────────────┐
│  Consumo por Hora   │  Consumo por Equipo │  Consumo por Día    │
│                     │                     │                     │
│  [Histograma]       │  [Histograma]       │  [Histograma]       │
│                     │                     │                     │
│  00h ████           │  Team A ████████    │  Mon ████           │
│  01h ██             │  Team B ██████      │  Tue ██████         │
│  02h █              │  Team C ████        │  Wed ████████       │
│  ...                │  Team D ██          │  ...                │
│                     │                     │                     │
│  Peak: 14:00 (1.2K) │  Top: Team A (45%)  │  Peak: Wed (3.5K)   │
└─────────────────────┴─────────────────────┴─────────────────────┘
```

**Características**:
- **Gráfica 1 - Consumo por Hora**: 
  - Histograma de barras verticales (24 horas)
  - Colores degradados según intensidad
  - Tooltip con detalles al hover
  - Muestra hora pico

- **Gráfica 2 - Consumo por Equipo**:
  - Histograma horizontal de barras
  - Colores diferentes por equipo
  - Porcentaje del total
  - Top 10 equipos

- **Gráfica 3 - Consumo por Día**:
  - Histograma de barras verticales
  - Colores según día de la semana
  - Muestra tendencia
  - Día con mayor actividad

**Tecnología**: Chart.js (ya incluido en el proyecto)

---

### 5. Tabla de Consumo por Usuario

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Consumo por Usuario                                          [Export CSV]  │
├──────────────┬─────────────────┬──────────────┬────────────┬───────────────┤
│ Email        │ Person          │ Team         │ Requests   │ Tokens        │
├──────────────┼─────────────────┼──────────────┼────────────┼───────────────┤
│ john@ex.com  │ John Doe        │ Team Alpha   │ 1,234      │ 245K          │
│ jane@ex.com  │ Jane Smith      │ Team Beta    │ 987        │ 198K          │
│ bob@ex.com   │ Bob Johnson     │ Team Alpha   │ 756        │ 151K          │
│ ...          │ ...             │ ...          │ ...        │ ...           │
├──────────────┴─────────────────┴──────────────┴────────────┴───────────────┤
│  Showing 1-10 of 45 users                          [< 1 2 3 4 5 >]         │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Características**:
- Tabla ordenable por cualquier columna
- Búsqueda/filtro por email, persona o equipo
- Paginación (10, 25, 50, 100 registros por página)
- Botón de exportación a CSV
- Colores alternados en filas para mejor legibilidad
- Indicador visual para usuarios con alto consumo (>80% del promedio)

**Columnas**:
1. **Email**: Email del usuario (cognito_email)
2. **Person**: Nombre de la persona (extraído de Cognito)
3. **Team**: Equipo/Grupo al que pertenece (cognito_group_name)
4. **Total Requests**: Número total de peticiones
5. **Tokens**: Total de tokens (input + output)
6. **Cost**: Costo total en USD (opcional, con toggle)
7. **Avg Response**: Tiempo promedio de respuesta (opcional, con toggle)

---

### 6. Gráfica de Línea - Tendencia por Equipos

```
┌─────────────────────────────────────────────────────────────────────────────┐
│  Tendencia de Consumo por Equipo                                            │
│                                                                              │
│  Requests                                                                    │
│  1500 ┤                                                                      │
│       │                                    ╭─────╮                           │
│  1000 ┤                  ╭────╮          ╱       ╰─╮                        │
│       │        ╭────╮   ╱      ╰────╮  ╱            ╰─╮                     │
│   500 ┤  ╭────╯     ╰──╯            ╰─╯                ╰────╮               │
│       │ ╱                                                     ╰──            │
│     0 ┴──────────────────────────────────────────────────────────────────   │
│       Mon    Tue    Wed    Thu    Fri    Sat    Sun                         │
│                                                                              │
│  Legend: ─── Team Alpha  ─── Team Beta  ─── Team Gamma  ─── Team Delta    │
└─────────────────────────────────────────────────────────────────────────────┘
```

**Características**:
- Gráfica de líneas múltiples (una por equipo)
- Colores distintivos por equipo
- Puntos interactivos con tooltip
- Leyenda con toggle para mostrar/ocultar equipos
- Zoom y pan para períodos largos
- Área sombreada bajo las líneas (opcional)

**Tecnología**: Chart.js con plugin de zoom

---

## 🗄️ Estructura de Datos

### Tabla Principal: `bedrock-proxy-usage-tracking-tbl`

```sql
CREATE TABLE "bedrock-proxy-usage-tracking-tbl" (
    id UUID PRIMARY KEY,
    cognito_user_id VARCHAR(255) NOT NULL,
    cognito_email VARCHAR(255) NOT NULL,
    request_timestamp TIMESTAMP NOT NULL,
    model_id VARCHAR(255) NOT NULL,
    source_ip VARCHAR(45),
    user_agent TEXT,
    aws_region VARCHAR(50),
    tokens_input INTEGER,
    tokens_output INTEGER,
    tokens_cache_read INTEGER DEFAULT 0,
    tokens_cache_creation INTEGER DEFAULT 0,
    cost_usd DECIMAL(10, 6),
    processing_time_ms INTEGER,
    response_status VARCHAR(20) NOT NULL,
    error_message TEXT,
    created_at TIMESTAMP NOT NULL
);
```

### Datos Necesarios Adicionales

Para obtener el **equipo/team** de cada usuario, necesitamos:
1. Consultar Cognito para obtener los grupos del usuario
2. O agregar una columna `team` en la tabla de tracking
3. O crear una tabla de mapeo usuario-equipo

**Recomendación**: Agregar columna `cognito_group_name` a la tabla de tracking:

```sql
ALTER TABLE "bedrock-proxy-usage-tracking-tbl" 
ADD COLUMN cognito_group_name VARCHAR(100);

CREATE INDEX idx_usage_group ON "bedrock-proxy-usage-tracking-tbl"(cognito_group_name);
```

---

## 🔌 APIs Necesarias

### 1. GET `/api/proxy-usage/summary`
**Descripción**: Obtiene métricas globales para el período seleccionado

**Query Parameters**:
- `start_date`: Fecha inicio (YYYY-MM-DD)
- `end_date`: Fecha fin (YYYY-MM-DD)

**Response**:
```json
{
  "period": {
    "start": "2026-03-01",
    "end": "2026-03-03"
  },
  "metrics": {
    "total_requests": 12458,
    "total_tokens_input": 1234567,
    "total_tokens_output": 1234567,
    "total_tokens": 2469134,
    "total_cost_usd": 124.50,
    "avg_processing_time_ms": 1234,
    "success_rate": 98.5
  },
  "comparison": {
    "requests_change_pct": 15.2,
    "tokens_change_pct": 12.3,
    "cost_change_pct": 18.1,
    "processing_time_change_pct": -5.2
  }
}
```

---

### 2. GET `/api/proxy-usage/by-hour`
**Descripción**: Consumo acumulado por horas del día

**Query Parameters**:
- `start_date`: Fecha inicio
- `end_date`: Fecha fin

**Response**:
```json
{
  "data": [
    {"hour": 0, "requests": 45, "tokens": 9000},
    {"hour": 1, "requests": 23, "tokens": 4600},
    ...
    {"hour": 23, "requests": 67, "tokens": 13400}
  ],
  "peak_hour": {
    "hour": 14,
    "requests": 1234,
    "tokens": 246800
  }
}
```

---

### 3. GET `/api/proxy-usage/by-team`
**Descripción**: Consumo por equipo/grupo

**Query Parameters**:
- `start_date`: Fecha inicio
- `end_date`: Fecha fin
- `limit`: Número de equipos (default: 10)

**Response**:
```json
{
  "data": [
    {
      "team": "tcs-bi-dwh-group",
      "requests": 5678,
      "tokens": 1135600,
      "cost_usd": 56.78,
      "percentage": 45.6
    },
    {
      "team": "tcs-analytics-group",
      "requests": 3456,
      "tokens": 691200,
      "cost_usd": 34.56,
      "percentage": 27.7
    }
  ],
  "total_teams": 8
}
```

---

### 4. GET `/api/proxy-usage/by-day`
**Descripción**: Consumo por día

**Query Parameters**:
- `start_date`: Fecha inicio
- `end_date`: Fecha fin

**Response**:
```json
{
  "data": [
    {
      "date": "2026-03-01",
      "day_name": "Monday",
      "requests": 3456,
      "tokens": 691200,
      "cost_usd": 34.56
    },
    {
      "date": "2026-03-02",
      "day_name": "Tuesday",
      "requests": 4567,
      "tokens": 913400,
      "cost_usd": 45.67
    }
  ],
  "peak_day": {
    "date": "2026-03-02",
    "requests": 4567
  }
}
```

---

### 5. GET `/api/proxy-usage/by-user`
**Descripción**: Consumo detallado por usuario

**Query Parameters**:
- `start_date`: Fecha inicio
- `end_date`: Fecha fin
- `page`: Número de página (default: 1)
- `page_size`: Registros por página (default: 10)
- `sort_by`: Campo de ordenación (default: requests)
- `sort_order`: asc/desc (default: desc)
- `search`: Búsqueda por email/nombre

**Response**:
```json
{
  "data": [
    {
      "cognito_user_id": "uuid-123",
      "cognito_email": "john.doe@example.com",
      "person_name": "John Doe",
      "team": "tcs-bi-dwh-group",
      "total_requests": 1234,
      "total_tokens_input": 123400,
      "total_tokens_output": 123400,
      "total_tokens": 246800,
      "total_cost_usd": 12.34,
      "avg_processing_time_ms": 1234,
      "success_rate": 99.2
    }
  ],
  "pagination": {
    "page": 1,
    "page_size": 10,
    "total_records": 45,
    "total_pages": 5
  }
}
```

---

### 6. GET `/api/proxy-usage/trend-by-team`
**Descripción**: Tendencia temporal por equipo

**Query Parameters**:
- `start_date`: Fecha inicio
- `end_date`: Fecha fin
- `granularity`: hour/day/week (default: day)
- `teams`: Lista de equipos (opcional, comma-separated)

**Response**:
```json
{
  "granularity": "day",
  "teams": [
    {
      "team": "tcs-bi-dwh-group",
      "data": [
        {"timestamp": "2026-03-01", "requests": 1234, "tokens": 246800},
        {"timestamp": "2026-03-02", "requests": 1456, "tokens": 291200}
      ]
    },
    {
      "team": "tcs-analytics-group",
      "data": [
        {"timestamp": "2026-03-01", "requests": 987, "tokens": 197400},
        {"timestamp": "2026-03-02", "requests": 1123, "tokens": 224600}
      ]
    }
  ]
}
```

---

### 7. GET `/api/proxy-usage/export`
**Descripción**: Exportar datos a CSV

**Query Parameters**:
- `start_date`: Fecha inicio
- `end_date`: Fecha fin
- `format`: csv/json (default: csv)

**Response**: Archivo CSV descargable

---

## 💻 Implementación Frontend

### Archivos a Crear

```
frontend/dashboard/
├── js/
│   ├── proxy-usage.js          # Lógica principal del dashboard
│   └── proxy-usage-charts.js   # Configuración de gráficas
└── css/
    └── proxy-usage.css          # Estilos específicos
```

### Estructura HTML (Fragmento)

```html
<!-- Proxy Bedrock Tab -->
<div id="proxy-usage-tab" class="tab-content">
    <!-- Header con filtros -->
    <div class="section-header">
        <h2>📊 Proxy Bedrock Usage Analytics</h2>
        <button class="refresh-button" onclick="refreshProxyUsage()">
            <span class="refresh-icon">&#x21bb;</span>
            Refresh
        </button>
    </div>
    
    <!-- Filtros de fecha -->
    <div class="card filters-card">
        <div class="date-filters">
            <div class="form-group">
                <label for="usage-start-date">Desde:</label>
                <input type="date" id="usage-start-date" />
            </div>
            <div class="form-group">
                <label for="usage-end-date">Hasta:</label>
                <input type="date" id="usage-end-date" />
            </div>
            <button class="btn-primary" onclick="applyDateFilter()">Apply</button>
        </div>
        <div class="quick-filters">
            <button onclick="setQuickFilter('today')">Today</button>
            <button onclick="setQuickFilter('7days')">Last 7 Days</button>
            <button onclick="setQuickFilter('30days')">Last 30 Days</button>
        </div>
    </div>
    
    <!-- KPIs -->
    <div class="metrics-grid">
        <div class="metric-card">
            <h3>Total Requests</h3>
            <div class="metric-value" id="total-requests">-</div>
            <div class="metric-trend" id="requests-trend"></div>
        </div>
        <!-- Más KPIs... -->
    </div>
    
    <!-- Gráficas principales -->
    <div class="charts-grid">
        <div class="chart-card">
            <h3>Consumo por Hora</h3>
            <canvas id="chart-by-hour"></canvas>
        </div>
        <div class="chart-card">
            <h3>Consumo por Equipo</h3>
            <canvas id="chart-by-team"></canvas>
        </div>
        <div class="chart-card">
            <h3>Consumo por Día</h3>
            <canvas id="chart-by-day"></canvas>
        </div>
    </div>
    
    <!-- Tabla de usuarios -->
    <div class="card">
        <div class="table-header">
            <h2>Consumo por Usuario</h2>
            <button class="btn-secondary" onclick="exportToCSV()">
                Export CSV
            </button>
        </div>
        <table id="usage-by-user-table">
            <!-- Tabla dinámica -->
        </table>
    </div>
    
    <!-- Gráfica de tendencia -->
    <div class="card">
        <h2>Tendencia de Consumo por Equipo</h2>
        <canvas id="chart-trend-by-team"></canvas>
    </div>
</div>
```

---

## 🎨 Estilos CSS Específicos

```css
/* Proxy Usage Specific Styles */
.filters-card {
    background: var(--background-light);
    padding: 1.5rem;
    border-radius: 8px;
    margin-bottom: 2rem;
}

.date-filters {
    display: flex;
    gap: 1rem;
    align-items: end;
    margin-bottom: 1rem;
}

.quick-filters {
    display: flex;
    gap: 0.5rem;
}

.quick-filters button {
    padding: 0.5rem 1rem;
    border: 1px solid var(--border-color);
    background: white;
    border-radius: 4px;
    cursor: pointer;
    transition: all 0.2s;
}

.quick-filters button:hover {
    background: var(--primary-teal);
    color: white;
    border-color: var(--primary-teal);
}

.metrics-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(250px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.metric-card {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    border-left: 4px solid var(--primary-teal);
}

.metric-value {
    font-size: 2.5rem;
    font-weight: bold;
    color: var(--primary-teal);
    margin: 0.5rem 0;
}

.metric-trend {
    font-size: 0.9rem;
    color: var(--text-secondary);
}

.metric-trend.positive {
    color: var(--success-green);
}

.metric-trend.negative {
    color: var(--error-red);
}

.charts-grid {
    display: grid;
    grid-template-columns: repeat(auto-fit, minmax(300px, 1fr));
    gap: 1.5rem;
    margin-bottom: 2rem;
}

.chart-card {
    background: white;
    padding: 1.5rem;
    border-radius: 8px;
    box-shadow: 0 2px 4px rgba(0,0,0,0.1);
}

.chart-card h3 {
    margin-bottom: 1rem;
    color: var(--text-primary);
    font-size: 1.1rem;
}

.chart-card canvas {
    max-height: 300px;
}

.table-header {
    display: flex;
    justify-content: space-between;
    align-items: center;
    margin-bottom: 1rem;
}
```

---

## 📊 Configuración de Gráficas (Chart.js)

### Ejemplo: Gráfica de Consumo por Hora

```javascript
// proxy-usage-charts.js

function createHourlyChart(data) {
    const ctx = document.getElementById('chart-by-hour').getContext('2d');
    
    return new Chart(ctx, {
        type: 'bar',
        data: {
            labels: data.map(d => `${d.hour}:00`),
            datasets: [{
                label: 'Requests',
                data: data.map(d => d.requests),
                backgroundColor: 'rgba(74, 155, 142, 0.6)',
                borderColor: 'rgba(74, 155, 142, 1)',
                borderWidth: 1
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            plugins: {
                legend: {
                    display: false
                },
                tooltip: {
                    callbacks: {
                        label: function(context) {
                            return `Requests: ${context.parsed.y.toLocaleString()}`;
                        }
                    }
                }
            },
            scales: {
                y: {
                    beginAtZero: true,
                    ticks: {
                        callback: function(value) {
                            return value.toLocaleString();
                        }
                    }
                }
            }
        }
    });
}
```

---

## 🔐 Permisos y Seguridad

### Control de Acceso
- Solo usuarios con permiso `admin` o `analytics` pueden acceder
- Los usuarios normales solo ven sus propios datos
- Los administradores ven datos de todos los usuarios

### Validación
- Validar rangos de fechas (máximo 90 días)
- Sanitizar inputs de búsqueda
- Rate limiting en las APIs

---

## 📱 Responsive Design

### Breakpoints
```css
/* Desktop: > 1200px */
.charts-grid {
    grid-template-columns: repeat(3, 1fr);
}

/* Tablet: 768px - 1200px */
@media (max-width: 1200px) {
    .charts-grid {
        grid-template-columns: repeat(2, 1fr);
    }
}

/* Mobile: < 768px */
@media (max-width: 768px) {
    .charts-grid {
        grid-template-columns: 1fr;
    }
    
    .date-filters {
        flex-direction: column;
    }
    
    .metrics-grid {
        grid-template-columns: 1fr;
    }
}
```

---

## 🚀 Plan de Implementación

### Fase 1: Backend (2-3 días)
1. ✅ Tabla de tracking ya existe
2. Agregar columna `cognito_group_name` a la tabla
3. Crear las 7 APIs necesarias
4. Implementar lógica de agregación y cálculos
5. Testing de APIs

### Fase 2: Frontend (3-4 días)
1. Crear estructura HTML del nuevo tab
2. Implementar filtros de fecha
3. Crear las 3 gráficas principales (Chart.js)
4. Implementar tabla de usuarios con paginación
5. Crear gráfica de tendencia por equipos
6. Implementar exportación a CSV

### Fase 3: Integración (1-2 días)
1. Integrar con el dashboard existente
2. Ajustar estilos para consistencia
3. Testing de integración
4. Optimización de rendimiento

### Fase 4: Testing y Refinamiento (1-2 días)
1. Testing funcional completo
2. Testing de responsive design
3. Optimización de queries
4. Documentación

**Total Estimado**: 7-11 días

---

## 📈 Métricas de Éxito

1. **Rendimiento**: Carga de página < 2 segundos
2. **Usabilidad**: Usuarios pueden encontrar información en < 30 segundos
3. **Precisión**: Datos 100% consistentes con la base de datos
4. **Adopción**: 80% de administradores usan el dashboard semanalmente

---

## 🔄 Futuras Mejoras

### Versión 2.0
- Alertas automáticas por uso excesivo
- Predicción de costos con ML
- Comparación entre períodos
- Drill-down por modelo específico
- Dashboard personalizable (drag & drop widgets)
- Exportación a PDF con gráficas
- Integración con Slack/Teams para notificaciones

### Versión 3.0
- Real-time updates con WebSockets
- Análisis de sentimiento en errores
- Recomendaciones de optimización
- Benchmarking entre equipos
- Gamificación (badges por uso eficiente)

---

## 📝 Notas Técnicas

### Optimizaciones de Base de Datos
```sql
-- Índices adicionales recomendados
CREATE INDEX idx_usage_timestamp_team 
ON "bedrock-proxy-usage-tracking-tbl"(request_timestamp, cognito_group_name);

CREATE INDEX idx_usage_date_range 
ON "bedrock-proxy-usage-tracking-tbl"(request_timestamp) 
WHERE request_timestamp >= CURRENT_DATE - INTERVAL '90 days';

-- Vista materializada para agregaciones frecuentes
CREATE MATERIALIZED VIEW mv_daily_usage_summary AS
SELECT 
    DATE(request_timestamp) as usage_date,
    cognito_group_name,
    COUNT(*) as total_requests,
    SUM(tokens_input + tokens_output) as total_tokens,
    SUM(cost_usd) as total_cost,
    AVG(processing_time_ms) as