# Identity Manager v2

Sistema completo de gestión de identidades, permisos y control de acceso para AWS Bedrock.

## 🎯 Características

- **Gestión de Identidades**: Integración con AWS Cognito
- **Tokens JWT**: Generación, validación y regeneración automática
- **Control de Permisos**: Granular a nivel de aplicación y módulo
- **Control de Cuotas**: Límites diarios con reset automático
- **Proxy Bedrock**: Servidor Go para AWS Bedrock con autenticación
- **Dashboard Web**: Interfaz de administración completa
- **Tracking de Uso**: Métricas detalladas y análisis de costos

## 🚀 Quick Start

```bash
# 1. Clonar repositorio
git clone https://github.com/carlossarrion-wq/identity-manager-v2.git
cd identity-manager-v2

# 2. Desplegar infraestructura
cd deployment/terraform/environments/dev
terraform init
terraform apply

# 3. Desplegar backend
cd backend/lambdas/identity-mgmt-api
pip3 install -r requirements.txt -t .
zip -r lambda.zip .
aws lambda update-function-code --function-name identity-mgmt-dev-api-lmbd --zip-file fileb://lambda.zip

# 4. Desplegar proxy
cd proxy-bedrock
docker build -t bedrock-proxy .
# Ver docs/06-PROXY-BEDROCK.md para deployment completo
```

## 📁 Estructura del Proyecto

```
identity-manager-v2/
├── backend/              # Lambda Python (API)
├── proxy-bedrock/        # Proxy Go para Bedrock
├── frontend/             # Dashboard web
├── database/             # Esquemas y migraciones SQL
├── deployment/           # Terraform IaC
└── docs/                 # Documentación completa
```

## 📚 Documentación

La documentación completa está en el directorio `docs/`:

1. **[Visión General](docs/01-OVERVIEW.md)** - Introducción y características
2. **[Arquitectura](docs/02-ARCHITECTURE.md)** - Diseño del sistema
3. **[Instalación](docs/03-INSTALLATION.md)** - Guía de instalación
4. **[API Reference](docs/04-API-REFERENCE.md)** - Referencia de API
5. **[Permisos](docs/05-PERMISSIONS.md)** - Sistema de permisos
6. **[Proxy Bedrock](docs/06-PROXY-BEDROCK.md)** - Documentación del proxy
7. **[Base de Datos](docs/07-DATABASE.md)** - Esquema y tablas
8. **[Deployment](docs/08-DEPLOYMENT.md)** - Guía de deployment

## 🏗️ Arquitectura

```
Frontend Dashboard → API Gateway → Lambda (Python)
                                      ↓
                                PostgreSQL RDS
                                      ↓
                            Proxy Bedrock (Go)
                                      ↓
                                AWS Bedrock
```

## 🔧 Tecnologías

- **Backend**: Python 3.12, AWS Lambda
- **Proxy**: Go 1.21+
- **Frontend**: JavaScript, HTML5, CSS3
- **Base de Datos**: PostgreSQL 15+ (RDS)
- **Infraestructura**: Terraform, AWS (Lambda, RDS, ECS, Cognito)

## 🔐 Seguridad

- Autenticación JWT con HMAC-SHA256
- Integración con AWS Cognito
- Encriptación en reposo (RDS)
- Secrets Manager para credenciales
- Auditoría completa de operaciones

## 📊 Estado del Proyecto

### Implementado ✅
- Sistema de autenticación y autorización
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

## 🤝 Contribuir

1. Fork el proyecto
2. Crear feature branch (`git checkout -b feature/AmazingFeature`)
3. Commit cambios (`git commit -m 'Add AmazingFeature'`)
4. Push al branch (`git push origin feature/AmazingFeature`)
5. Abrir Pull Request

## 📝 Licencia

Este proyecto es privado y confidencial.

## 👥 Equipo

Desarrollado por el equipo de TCS para gestión de identidades en AWS Bedrock.

## 🔗 Enlaces

- **Repositorio**: https://github.com/carlossarrion-wq/identity-manager-v2
- **AWS Bedrock**: https://aws.amazon.com/bedrock/
- **AWS Cognito**: https://aws.amazon.com/cognito/

---

Para más información, consulta la [documentación completa](docs/01-OVERVIEW.md).