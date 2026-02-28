# Identity Manager Dashboard

Dashboard web para gestionar usuarios, tokens JWT y perfiles de inferencia del Identity Manager.

## 🎨 Características

- **Gestión de Usuarios**: Crear, listar y eliminar usuarios de Cognito
- **Gestión de Tokens**: Crear, visualizar y revocar tokens JWT
- **Perfiles de Inferencia**: Ver perfiles disponibles y sus configuraciones
- **Grupos de Cognito**: Visualizar grupos y sus miembros
- **Interfaz Moderna**: Diseño responsive con Amazon Ember font
- **Tiempo Real**: Conexión directa con la API Lambda

## 📁 Estructura

```
dashboard/
├── index.html          # Página principal del dashboard
├── css/
│   └── dashboard.css   # Estilos del dashboard
├── js/
│   ├── config.js       # Configuración de la API
│   ├── api.js          # Cliente API para Lambda
│   └── dashboard.js    # Lógica principal del dashboard
└── README.md           # Este archivo
```

## 🚀 Cómo Usar

### Opción 1: Servidor Python Simple

```bash
cd /Users/csarrion/Cline/identity-manager-v2/frontend/dashboard
python3 -m http.server 8080
```

Luego abre: http://localhost:8080

### Opción 2: Servidor Node.js

```bash
cd /Users/csarrion/Cline/identity-manager-v2/frontend/dashboard
npx http-server -p 8080
```

Luego abre: http://localhost:8080

### Opción 3: Live Server (VS Code)

1. Instala la extensión "Live Server" en VS Code
2. Click derecho en `index.html`
3. Selecciona "Open with Live Server"

## ⚙️ Configuración

### Endpoint de la API

El endpoint de la Lambda está configurado en `js/config.js`:

```javascript
const API_CONFIG = {
    endpoint: 'https://vgrajswesgyujgxpw5g65tw5py0kihum.lambda-url.eu-west-1.on.aws/',
    timeout: 30000
};
```

Si necesitas cambiar el endpoint, edita este archivo.

## 📋 Funcionalidades por Pestaña

### 1. Users (Usuarios)

**Estadísticas:**
- Total de usuarios en Cognito
- Tokens activos
- Perfiles activos
- Total de grupos

**Acciones:**
- ✅ Crear nuevo usuario
- 📋 Listar todos los usuarios
- 🗑️ Eliminar usuario

**Crear Usuario:**
1. Click en "Create User"
2. Completa el formulario:
   - Email (requerido)
   - Nombre de la persona (requerido)
   - Grupo de Cognito (requerido)
   - Contraseña temporal (opcional)
   - Enviar email de bienvenida (checkbox)
3. Click en "Create User"

### 2. Tokens

**Acciones:**
- ✅ Crear nuevo token JWT
- 📋 Listar todos los tokens
- 👁️ Ver detalles del token
- 🚫 Revocar token

**Crear Token:**
1. Click en "Create Token"
2. Selecciona:
   - Usuario (de la lista de usuarios)
   - Perfil de inferencia (de la lista de perfiles)
   - Período de validez (1, 7, 30, 60 o 90 días)
3. Click en "Create Token"
4. Copia el token JWT generado

**Ver Token:**
- Click en el icono 👁️ para ver detalles completos
- Información mostrada:
  - Token ID
  - JTI (JWT ID)
  - User ID
  - Email
  - Perfil asociado
  - Fecha de creación
  - Fecha de expiración
  - Estado (Active/Revoked)

**Revocar Token:**
- Click en el icono 🚫 para revocar un token activo
- Confirma la acción
- El token quedará marcado como revocado

### 3. Profiles (Perfiles de Inferencia)

**Información mostrada:**
- Profile ID
- Nombre del perfil
- Aplicación asociada
- Modelo de IA (Model ID)
- Grupo de Cognito
- Estado (Active/Inactive)
- Fecha de creación

### 4. Groups (Grupos de Cognito)

**Información mostrada:**
- Nombre del grupo
- Descripción
- Precedencia
- Número de usuarios

## 🎯 Operaciones de la API

El dashboard se comunica con la Lambda usando las siguientes operaciones:

### Usuarios
- `list_users` - Listar usuarios
- `create_user` - Crear usuario
- `delete_user` - Eliminar usuario

### Tokens
- `list_tokens` - Listar tokens
- `create_token` - Crear token
- `validate_token` - Validar token
- `revoke_token` - Revocar token
- `delete_token` - Eliminar token

### Perfiles
- `list_profiles` - Listar perfiles

### Grupos
- `list_groups` - Listar grupos

### Configuración
- `get_config` - Obtener configuración

## 🔧 Desarrollo

### Estructura del Código

**config.js:**
- Configuración del endpoint de la API
- Configuración del dashboard (paginación, formato de fechas, etc.)

**api.js:**
- Clase `IdentityManagerAPI` con métodos para cada operación
- Manejo de errores y timeouts
- Logging de requests/responses

**dashboard.js:**
- Inicialización del dashboard
- Gestión de estado global
- Funciones para cada pestaña
- Renderizado de tablas
- Manejo de modales
- Utilidades (formateo de fechas, alertas, etc.)

### Añadir Nueva Funcionalidad

1. **Añadir método en api.js:**
```javascript
async nuevaOperacion(parametros) {
    return await this.request('nueva_operacion', { parametros });
}
```

2. **Añadir función en dashboard.js:**
```javascript
async function ejecutarNuevaOperacion() {
    try {
        const result = await api.nuevaOperacion(params);
        // Procesar resultado
    } catch (error) {
        showAlert('error', error.message);
    }
}
```

3. **Añadir UI en index.html:**
```html
<button onclick="ejecutarNuevaOperacion()">Nueva Acción</button>
```

## 🎨 Personalización de Estilos

Los colores principales están definidos en `config.js`:

```javascript
colors: {
    primary: '#319795',    // Teal
    secondary: '#2c7a7b',  // Dark Teal
    success: '#38b2ac',    // Green
    warning: '#ed8936',    // Orange
    error: '#e53e3e',      // Red
    info: '#4299e1'        // Blue
}
```

Para cambiar el tema, edita estos valores y los gradientes en `dashboard.css`.

## 🐛 Debugging

### Ver Logs en Consola

Abre las DevTools del navegador (F12) y ve a la pestaña Console para ver:
- Requests a la API
- Responses de la API
- Errores
- Estado de conexión

### Problemas Comunes

**Error: "Disconnected from API"**
- Verifica que el endpoint en `config.js` sea correcto
- Verifica que la Lambda esté desplegada y funcionando
- Verifica la conectividad de red

**Error: "Failed to fetch"**
- Problema de CORS en la Lambda
- Verifica que la Lambda tenga configurado CORS correctamente

**Tokens no se muestran**
- Verifica que la operación `list_tokens` esté implementada en la Lambda
- Revisa los logs de la consola para ver el error específico

## 📝 Notas

- El dashboard requiere que la Lambda esté desplegada y accesible
- No requiere autenticación (considera añadirla en producción)
- Los datos se cargan en tiempo real desde la API
- No hay caché local, cada acción consulta la API

## 🔐 Seguridad

**⚠️ IMPORTANTE:** Este dashboard no tiene autenticación implementada. Para producción:

1. Añade autenticación con AWS Cognito
2. Implementa autorización basada en roles
3. Usa HTTPS siempre
4. Añade rate limiting
5. Valida todas las entradas del usuario
6. Implementa logging de auditoría

## 📚 Recursos

- [AWS Lambda Function URLs](https://docs.aws.amazon.com/lambda/latest/dg/lambda-urls.html)
- [Amazon Ember Font](https://developer.amazon.com/en-US/alexa/branding/echo-guidelines/identity-guidelines/typography)
- [Chart.js Documentation](https://www.chartjs.org/docs/latest/)
- [Moment.js Documentation](https://momentjs.com/docs/)

## 🤝 Contribuir

Para añadir nuevas funcionalidades:

1. Añade la operación en la Lambda
2. Añade el método en `api.js`
3. Añade la función en `dashboard.js`
4. Añade la UI en `index.html`
5. Añade estilos en `dashboard.css` si es necesario
6. Actualiza este README

## 📄 Licencia

Este proyecto es parte del Identity Manager v2.
