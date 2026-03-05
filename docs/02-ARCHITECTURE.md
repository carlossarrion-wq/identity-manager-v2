# Arquitectura del Sistema

## 🏗️ Visión General

Identity Manager v2 sigue una arquitectura de microservicios con separación clara de responsabilidades:

- **Frontend**: SPA (Single Page Application) en JavaScript vanilla
- **Backend**: AWS Lambda con Python 3.12
- **Proxy**: Servidor Go para AWS Bedrock
- **Base de Datos**: PostgreSQL en RDS
- **Infraestructura**: Terraform para IaC

## 📐 Diagrama de Componentes

```
┌──────────────────────────────────────────────────────────────┐
│                         FRONTEND                              │
│  ┌────────────┐  ┌────────────┐  ┌────────────┐            │
│  │  Users     │  │  Tokens    │  │ Permissions│            │
│  │  Manager   │  │  Manager   │  │  Manager   │            │
│  └────────────┘  └────────────┘  └────────────┘            │
│  ┌────────────┐  ┌────────────┐                             │
│  │ Proxy Usage│  │  Dashboard │                             │
│  │  Viewer    │  │  Stats     │                             │
│  └────────────┘  └────────────┘                             │
└────────────────────────┬─────────────────────────────────────┘
                         │ HTTPS/REST
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                      API GATEWAY                              │
└────────────────────────┬─────────────────────────────────────┘
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                   LAMBDA FUNCTION                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │              lambda_function.py                        │  │
│  │  - Request routing                                     │  │
│  │  - Input validation                                    │  │
│  │  - Error handling                                      │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │   Cognito    │  │   Database   │  │     JWT      │      │
│  │   Service    │  │   Service    │  │   Service    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │    Email     │  │ Permissions  │  │ Proxy Usage  │      │
│  │   Service    │  │   Service    │  │   Service    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐                                            │
│  │    Token     │                                            │
│  │ Regeneration │                                            │
│  └──────────────┘                                            │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                    POSTGRESQL RDS                             │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  Tables:                                               │  │
│  │  - identity-manager-models-tbl                        │  │
│  │  - identity-manager-applications-tbl                  │  │
│  │  - identity-manager-modules-tbl                       │  │
│  │  - identity-manager-profiles-tbl                      │  │
│  │  - identity-manager-tokens-tbl                        │  │
│  │  - identity-manager-permission-types-tbl              │  │
│  │  - identity-manager-app-permissions-tbl               │  │
│  │  - identity-manager-module-permissions-tbl            │  │
│  │  - identity-manager-config-tbl                        │  │
│  │  - identity-manager-audit-tbl                         │  │
│  │  - bedrock-proxy-usage-tracking-tbl                   │  │
│  └────────────────────────────────────────────────────────┘  │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                    PROXY BEDROCK (Go)                         │
│  ┌────────────────────────────────────────────────────────┐  │
│  │  HTTP Server                                           │  │
│  │  - Request handling                                    │  │
│  │  - Streaming support                                   │  │
│  └────────────────────────────────────────────────────────┘  │
│                                                               │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────────┐      │
│  │     Auth     │  │    Quota     │  │   Metrics    │      │
│  │  Middleware  │  │  Middleware  │  │    Worker    │      │
│  └──────────────┘  └──────────────┘  └──────────────┘      │
│  ┌──────────────┐  ┌──────────────┐                         │
│  │   Database   │  │  Scheduler   │                         │
│  │   Client     │  │  (Cron)      │                         │
│  └──────────────┘  └──────────────┘                         │
└────────────────────────┬─────────────────────────────────────┘
                         │
                         ↓
┌──────────────────────────────────────────────────────────────┐
│                      AWS BEDROCK                              │
│  - Claude 3.5 Sonnet                                         │
│  - Claude 3 Opus                                             │
│  - Claude 3 Haiku                                            │
│  - Inference Profiles                                        │
└──────────────────────────────────────────────────────────────┘
```

## 🔄 Flujos de Datos

### 1. Creación de Usuario

```
Admin → Frontend → API Gateway → Lambda
                                   ↓
                            Cognito Service
                                   ↓
                            AWS Cognito (create user)
                                   ↓
                            Database Service
                                   ↓
                            PostgreSQL (audit log)
                                   ↓
                            Email Service (optional)
                                   ↓
                            AWS SES (send welcome email)
```

### 2. Generación de Token JWT

```
Admin → Frontend → API Gateway → Lambda
                                   ↓
                            Cognito Service (get user info)
                                   ↓
                            Database Service (get profile, check limits)
                                   ↓
                            JWT Service (generate token)
                                   ↓
                            Database Service (save token)
                                   ↓
                            Email Service (optional)
```

### 3. Request al Proxy Bedrock

```
Client → Proxy Bedrock
           ↓
    Auth Middleware (validate JWT)
           ↓
    Database (get user info)
           ↓
    Quota Middleware (check limits)
           ↓
    Database (check quota)
           ↓
    Bedrock Client (translate format)
           ↓
    AWS Bedrock (process request)
           ↓
    Stream Processor (parse response)
           ↓
    Metrics Worker (async)
           ↓
    Database (save metrics)
```

### 4. Regeneración Automática de Token

```
Proxy → Detect expired token
         ↓
    Lambda (regenerate_token endpoint)
         ↓
    Token Regeneration Service
         ↓
    Check auto_regenerate_tokens flag
         ↓
    Check active tokens limit
         ↓
    Get expired token info
         ↓
    JWT Service (generate new token)
         ↓
    Database Service (save new token, mark old as regenerated)
         ↓
    Email Service (send new token)
```

## 🔐 Seguridad

### Autenticación
- **Frontend**: Sesión con AWS Cognito
- **API**: Validación de sesión Cognito
- **Proxy**: Validación JWT con firma HMAC-SHA256

### Autorización
- **Permisos**: Verificación en base de datos
- **Cuotas**: Validación de límites diarios
- **Tokens**: Hash almacenado, no el token completo

### Datos Sensibles
- **Secrets Manager**: Credenciales de BD y JWT secret
- **Encriptación**: RDS con encriptación en reposo
- **Logs**: Sanitización de datos sensibles

## 📊 Escalabilidad

### Lambda
- **Concurrencia**: Auto-scaling según demanda
- **Timeout**: 5 minutos
- **Memory**: 512 MB (configurable)

### RDS
- **Connection Pool**: Min 5, Max 25 conexiones
- **Read Replicas**: Posible para lectura
- **Multi-AZ**: Recomendado para producción

### Proxy
- **Horizontal Scaling**: ECS con múltiples tasks
- **Load Balancer**: ALB para distribución
- **Worker Pool**: Procesamiento asíncrono de métricas

## 🔍 Monitoreo

### CloudWatch
- **Lambda**: Logs, métricas, errores
- **RDS**: CPU, memoria, conexiones
- **Proxy**: Logs estructurados JSON

### Métricas Clave
- Requests por minuto
- Latencia promedio
- Tasa de errores
- Uso de cuotas
- Costos de Bedrock

## 🎯 Patrones de Diseño

### Backend
- **Service Layer**: Separación de lógica de negocio
- **Repository Pattern**: Acceso a datos
- **Factory Pattern**: Creación de servicios

### Proxy
- **Middleware Chain**: Procesamiento secuencial
- **Worker Pattern**: Procesamiento asíncrono
- **Observer Pattern**: Métricas y eventos

### Frontend
- **Module Pattern**: Organización de código
- **Observer Pattern**: Actualización de UI
- **Singleton**: Configuración global

## 📝 Convenciones

### Nomenclatura
- **Tablas**: `identity-manager-<función>-tbl`
- **Lambda**: `<app>-<env>-<función>-lmbd`
- **Secrets**: `<app>-<env>-<tipo>-<detalle>`
- **Base de Datos**: `<app>_<env>_rds`

### Código
- **Python**: PEP 8
- **Go**: gofmt
- **JavaScript**: ESLint
- **SQL**: Lowercase con guiones

## 🔄 Ciclo de Vida

### Desarrollo
1. Código en feature branch
2. Tests locales
3. Pull request
4. Code review
5. Merge a develop

### Deployment
1. Build de artefactos
2. Deploy a dev
3. Tests de integración
4. Deploy a pre
5. Tests de aceptación
6. Deploy a pro

## 📚 Referencias

- [AWS Lambda Best Practices](https://docs.aws.amazon.com/lambda/latest/dg/best-practices.html)
- [PostgreSQL Performance](https://www.postgresql.org/docs/current/performance-tips.html)
- [Go Concurrency Patterns](https://go.dev/blog/pipelines)