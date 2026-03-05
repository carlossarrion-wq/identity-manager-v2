# Identity Manager v2 - Documento de Diseño

## 📋 Propósito

Este documento describe el diseño de alto nivel de Identity Manager v2. Para documentación detallada, consulta el directorio `docs/`.

## 🎯 Objetivos del Sistema

1. **Gestión Centralizada**: Administrar identidades, permisos y tokens desde un único punto
2. **Seguridad**: Autenticación robusta con JWT y control de acceso granular
3. **Escalabilidad**: Arquitectura serverless que escala automáticamente
4. **Auditoría**: Registro completo de todas las operaciones
5. **Control de Costos**: Cuotas y límites para controlar uso de AWS Bedrock

## 🏗️ Arquitectura de Alto Nivel

### Componentes Principales

```
┌─────────────────────────────────────────────────────────────┐
│                    FRONTEND (Dashboard)                      │
│  - Gestión de usuarios                                       │
│  - Gestión de tokens                                         │
│  - Gestión de permisos                                       │
│  - Visualización de uso                                      │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/REST
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              BACKEND (Lambda + Python)                       │
│  - API REST única con routing interno                        │
│  - Servicios: Cognito, Database, JWT, Email, Permissions    │
│  - Validación y autorización                                 │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              BASE DE DATOS (PostgreSQL RDS)                  │
│  - Esquema con UUIDs                                         │
│  - 10+ tablas principales                                    │
│  - Vistas y triggers                                         │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              PROXY BEDROCK (Go + ECS)                        │
│  - Autenticación JWT                                         │
│  - Control de cuotas                                         │
│  - Métricas y tracking                                       │
│  - Traducción de formatos                                    │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    AWS BEDROCK                               │
│  - Modelos Claude                                            │
│  - Inference Profiles                                        │
└─────────────────────────────────────────────────────────────┘
```

## 🔑 Conceptos Clave

### Aplicaciones
Sistemas que consumen servicios de IA (ej: cline, kb-agent, bedrock-proxy)

### Módulos
Funcionalidades específicas dentro de aplicaciones (ej: chat, document-management)

### Perfiles de Inferencia
Combinación de:
- Grupo de Cognito
- Aplicación
- Modelo LLM
- ARN del modelo

### Tokens JWT
Credenciales de acceso que incluyen:
- User ID y email
- Team (grupo de Cognito)
- Person (nombre completo)
- Perfil de inferencia por defecto
- Fecha de expiración
- JTI único

### Permisos
Control de acceso en dos niveles:
- **Aplicación**: Acceso a toda la aplicación
- **Módulo**: Acceso a módulos específicos

Tipos: Read-only (10), Write (50), Admin (100)

### Cuotas
Límites de uso:
- Diarios por usuario/equipo
- Basados en tokens consumidos
- Reset automático a las 00:00 UTC
- Bloqueo automático al exceder límite

## 🔄 Flujos Principales

### 1. Creación de Usuario
```
Admin → Frontend → Lambda → Cognito (create user)
                          → Database (audit log)
                          → Email (welcome)
```

### 2. Generación de Token
```
Admin → Frontend → Lambda → Cognito (get user info)
                          → Database (check limits, get profile)
                          → JWT Service (generate token)
                          → Database (save token hash)
                          → Email (send token - optional)
```

### 3. Request al Proxy
```
Client → Proxy → Auth Middleware (validate JWT)
              → Database (verify token, get user info)
              → Quota Middleware (check limits)
              → Database (check quota)
              → Bedrock Client (translate & send)
              → AWS Bedrock (process)
              → Stream Processor (parse response)
              → Metrics Worker (async save)
              → Database (save metrics)
```

### 4. Regeneración Automática
```
Proxy → Detect expired token
     → Lambda (regenerate_token endpoint)
     → Token Regeneration Service
     → Check auto_regenerate_tokens flag
     → Check active tokens limit
     → Generate new token
     → Database (save new, mark old as regenerated)
     → Email (send new token)
```

## 🔐 Seguridad

### Autenticación
- **Frontend**: AWS Cognito session
- **API**: Cognito session validation
- **Proxy**: JWT validation (HMAC-SHA256)

### Autorización
- Verificación de permisos en base de datos
- Validación de cuotas antes de cada request
- Auditoría de todas las operaciones

### Datos Sensibles
- Tokens: Solo hash almacenado (SHA-256)
- Credenciales: AWS Secrets Manager
- Base de Datos: Encriptación en reposo
- Logs: Sanitización automática

## 📊 Modelo de Datos

### Tablas Principales
1. **models**: Catálogo de modelos LLM
2. **applications**: Aplicaciones del sistema
3. **modules**: Módulos de aplicaciones
4. **profiles**: Perfiles de inferencia
5. **tokens**: Tokens JWT emitidos
6. **permission-types**: Tipos de permisos
7. **app-permissions**: Permisos de aplicación
8. **module-permissions**: Permisos de módulo
9. **config**: Configuración del sistema
10. **audit**: Registro de auditoría

### Tablas del Proxy
1. **user-quotas**: Cuotas de usuarios
2. **usage-tracking**: Tracking de uso

## 🎨 Decisiones de Diseño

### UUIDs como Primary Keys
- Mejor seguridad (no secuenciales)
- Facilita distribución y replicación
- Compatible con sistemas externos

### Nomenclatura con Guiones
- Estándar corporativo
- Formato: `identity-manager-<función>-tbl`
- Consistencia en todo el sistema

### Arquitectura Serverless
- Lambda para backend (auto-scaling)
- RDS para persistencia
- ECS para proxy (horizontal scaling)

### Single API Endpoint
- POST único con routing interno
- Simplifica API Gateway
- Facilita versionado

### Regeneración Automática de Tokens
- Mejora experiencia de usuario
- Configurable por usuario
- Límite de tokens activos (5)
- Email automático con nuevo token

## 📈 Escalabilidad

### Lambda
- Auto-scaling según demanda
- Timeout: 5 minutos
- Memory: 512 MB - 1024 MB

### RDS
- Connection pooling (5-25 conexiones)
- Read replicas para lectura
- Multi-AZ para alta disponibilidad

### Proxy
- ECS con múltiples tasks
- ALB para distribución
- Worker asíncrono para métricas

## 🔍 Monitoreo

### Métricas Clave
- Requests por minuto
- Latencia promedio
- Tasa de errores
- Uso de cuotas
- Costos de Bedrock

### Logs
- CloudWatch Logs
- Formato JSON estructurado
- Sanitización automática
- Retención configurable

## 📚 Referencias

Para información detallada, consulta:

- **[Arquitectura Completa](docs/02-ARCHITECTURE.md)**: Diagramas y flujos detallados
- **[API Reference](docs/04-API-REFERENCE.md)**: Todas las operaciones disponibles
- **[Sistema de Permisos](docs/05-PERMISSIONS.md)**: Lógica de permisos
- **[Proxy Bedrock](docs/06-PROXY-BEDROCK.md)**: Implementación del proxy
- **[Base de Datos](docs/07-DATABASE.md)**: Esquema completo
- **[Deployment](docs/08-DEPLOYMENT.md)**: Guía de despliegue

---

**Versión**: 2.0  
**Última actualización**: 2026-03-05  
**Estado**: Producción