# Identity Manager v2 - Visión General

## 📋 Descripción

Identity Manager v2 es un sistema completo de gestión de identidades, permisos y control de acceso para AWS Bedrock. Proporciona autenticación JWT, control de cuotas, tracking de uso y gestión granular de permisos para aplicaciones de IA.

## 🎯 Características Principales

### Gestión de Identidades
- Integración con AWS Cognito
- Gestión de usuarios y grupos
- Atributos personalizados (person, team)

### Sistema de Tokens JWT
- Generación y validación de tokens
- Perfiles de inferencia personalizados
- Regeneración automática de tokens expirados
- Control de límites por usuario (máx. 2 tokens activos)

### Control de Permisos
- Permisos a nivel de aplicación
- Permisos a nivel de módulo
- Tipos: Read-only, Write, Admin
- Herencia jerárquica de permisos

### Control de Cuotas
- Límites diarios de tokens por usuario/equipo
- Reset automático diario
- Tracking en tiempo real
- Alertas de límites

### Proxy Bedrock
- Proxy HTTP para AWS Bedrock
- Autenticación JWT integrada
- Rate limiting configurable
- Métricas de costo y uso
- Soporte streaming

### Dashboard Web
- Gestión de usuarios y tokens
- Visualización de permisos
- Dashboard de uso del proxy
- Estadísticas en tiempo real

## 🏗️ Arquitectura

```
┌─────────────────────────────────────────────────────────────┐
│                    Frontend Dashboard                        │
│                  (HTML/CSS/JavaScript)                       │
└────────────────────────┬────────────────────────────────────┘
                         │ HTTPS/REST
                         ↓
┌─────────────────────────────────────────────────────────────┐
│              API Gateway + Lambda (Python)                   │
│           identity-mgmt-dev-api-lmbd                        │
└────────────────────────┬────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  PostgreSQL RDS                              │
│              identity_manager_dev_rds                        │
└─────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                  Proxy Bedrock (Go)                          │
│              bedrock-proxy-dev-service                       │
└─────────────────────────────────────────────────────────────┘
                         │
                         ↓
┌─────────────────────────────────────────────────────────────┐
│                    AWS Bedrock                               │
│              (Claude Models)                                 │
└─────────────────────────────────────────────────────────────┘
```

## 📦 Componentes

### Backend (Python)
- **Lambda Function**: API REST para gestión
- **Servicios**: Cognito, Database, JWT, Email, Permissions, Proxy Usage
- **Base de Datos**: PostgreSQL con esquema UUID

### Proxy (Go)
- **Servidor HTTP**: Proxy para AWS Bedrock
- **Autenticación**: Validación JWT
- **Métricas**: Tracking de uso y costos
- **Scheduler**: Reset automático de cuotas

### Frontend (Web)
- **Dashboard**: Interfaz de administración
- **Gestión**: Usuarios, tokens, permisos
- **Visualización**: Gráficas y estadísticas

### Infraestructura (Terraform)
- **RDS**: PostgreSQL 15+
- **Lambda**: Python 3.12
- **VPC**: Networking y seguridad
- **Secrets Manager**: Credenciales

## 🔑 Conceptos Clave

### Aplicaciones
Sistemas que consumen servicios de IA (ej: cline, kb-agent, bedrock-proxy)

### Módulos
Funcionalidades específicas dentro de aplicaciones (ej: chat, document-management)

### Perfiles de Inferencia
Combinación de grupo Cognito + aplicación + modelo LLM

### Tokens JWT
Credenciales de acceso con permisos y perfil de inferencia embebidos

### Cuotas
Límites de uso (tokens) por usuario/equipo con reset diario

## 📊 Flujo de Trabajo Típico

1. **Administrador** crea usuario en Cognito
2. **Usuario** recibe credenciales y es asignado a un grupo
3. **Administrador** asigna permisos de aplicación/módulo
4. **Administrador** genera token JWT con perfil de inferencia
5. **Usuario** usa token para acceder al proxy Bedrock
6. **Proxy** valida token, verifica permisos y cuotas
7. **Sistema** registra uso y actualiza métricas
8. **Dashboard** muestra estadísticas y uso

## 🚀 Estado Actual

### Implementado ✅
- Sistema completo de autenticación y autorización
- Gestión de usuarios y tokens
- Control de permisos granular
- Proxy Bedrock funcional
- Dashboard básico
- Tracking de uso
- Regeneración automática de tokens
- Control de cuotas

### En Desarrollo 🔄
- Dashboard de uso del proxy (integración con BD)
- Optimizaciones de rendimiento
- Tests de integración

## 📚 Documentación Relacionada

- [Arquitectura del Sistema](./02-ARCHITECTURE.md)
- [Guía de Instalación](./03-INSTALLATION.md)
- [API Reference](./04-API-REFERENCE.md)
- [Sistema de Permisos](./05-PERMISSIONS.md)
- [Proxy Bedrock](./06-PROXY-BEDROCK.md)
- [Base de Datos](./07-DATABASE.md)
- [Deployment](./08-DEPLOYMENT.md)

## 🔗 Enlaces Útiles

- **Repositorio**: https://github.com/carlossarrion-wq/identity-manager-v2
- **AWS Bedrock**: https://aws.amazon.com/bedrock/
- **AWS Cognito**: https://aws.amazon.com/cognito/