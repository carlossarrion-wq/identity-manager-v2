# 📘 GUÍA DE IMPLEMENTACIÓN: AMS Logging Policy en Identity Manager

**Proyecto:** Sistema de Login con Herramientas (Identity Manager)  
**Librería:** ams-logging-policy v1.0.0  
**Fecha de inicio:** 4 de Marzo de 2026  
**Responsable:** Carlos Sarrión López  
**Estado:** 🚧 En Progreso

---

## 📋 ÍNDICE

1. [Resumen Ejecutivo](#resumen-ejecutivo)
2. [Objetivos](#objetivos)
3. [Prerrequisitos](#prerrequisitos)
4. [Fase 1: Preparación e Instalación](#fase-1-preparación-e-instalación)
5. [Fase 2: Integración Básica en Lambda](#fase-2-integración-básica-en-lambda)
6. [Fase 3: Integración con Auditoría](#fase-3-integración-con-auditoría)
7. [Fase 4: Testing y Validación](#fase-4-testing-y-validación)
8. [Fase 5: Despliegue](#fase-5-despliegue-opcional)
9. [Troubleshooting](#troubleshooting)
10. [Checklist Final](#checklist-final)

---

## 📊 RESUMEN EJECUTIVO

Esta guía documenta la implementación de la librería `ams-logging-policy` en el proyecto Identity Manager. La librería proporciona logging estructurado en JSON siguiendo los estándares corporativos de AMS Naturgy.

**Beneficios esperados:**
- ✅ Logs estructurados en JSON para mejor análisis
- ✅ Trazabilidad completa con trace_id y request_id
- ✅ Sanitización automática de datos sensibles
- ✅ Integración con sistema de auditoría existente
- ✅ Cumplimiento con Política de Logs v1.0

---

## 🎯 OBJETIVOS

### Objetivos Principales
1. ✅ Integrar librería ams-logging-policy en el backend
2. ✅ Reemplazar logging actual con logs estructurados
3. ✅ Conectar logs con tabla de auditoría
4. ✅ Implementar trazabilidad extremo a extremo

### Objetivos Secundarios
1. ✅ Mejorar observabilidad del sistema
2. ✅ Facilitar debugging y análisis de logs
3. ✅ Preparar infraestructura para dashboards

---

## ✅ PRERREQUISITOS

Antes de comenzar, verificar:

- [x] Python 3.8+ instalado
- [x] Acceso a la carpeta `ams-logging-policy-python`
- [x] Proyecto Identity Manager funcionando localmente
- [x] Permisos de escritura en el proyecto
- [x] Git configurado (para commits)

---

## 🔧 FASE 1: PREPARACIÓN E INSTALACIÓN

**Duración estimada:** 15-20 minutos  
**Estado:** ✅ COMPLETADA

### ✅ Paso 1.1: Copiar la librería al proyecto

**Objetivo:** Copiar el código fuente de `ams_logging` a `backend/shared/`

**⚠️ IMPORTANTE:** Usar `;` en lugar de `&&` en todos los comandos

**Comandos (Windows CMD):**
```cmd
REM Desde la raíz del proyecto SistemaLoginHerramientas

REM Crear directorio si no existe
mkdir backend\shared\ams_logging

REM Copiar todos los archivos de la librería
xcopy /E /I /Y ams-logging-policy-python\src\ams_logging backend\shared\ams_logging
```

**Verificación:**
```cmd
dir backend\shared\ams_logging
```

**Archivos esperados:**
- ✅ `__init__.py`
- ✅ `logger.py`
- ✅ `config.py`
- ✅ `constants.py`
- ✅ `sanitizer.py`
- ✅ `async_logger.py`
- ✅ `context.py`
- ✅ `decorators.py`
- ✅ `middleware.py`

**Estado:** ⬜ No iniciado

---

### ✅ Paso 1.2: Actualizar requirements-local.txt

**Objetivo:** Añadir dependencia necesaria para desarrollo local

**Acción:**
Abrir `requirements-local.txt` y añadir al final:

```txt
# AMS Logging Policy
python-json-logger>=2.0.0
```

**Comando para instalar:**
```cmd
pip install -r requirements-local.txt
```

**Estado:** ⬜ No iniciado

---

### ✅ Paso 1.3: Actualizar requirements.txt de Lambda

**Objetivo:** Añadir dependencia para el deployment de Lambda

**Acción:**
Abrir `backend/auth-lambda/requirements.txt` y añadir al final:

```txt
# AMS Logging Policy
python-json-logger>=2.0.0
```

**Estado:** ⬜ No iniciado

---

### ✅ Paso 1.4: Crear script de prueba inicial

**Objetivo:** Verificar que la librería funciona correctamente

**Acción:**
Crear archivo `test_ams_logging.py` en la raíz del proyecto

**Comando para ejecutar:**
```cmd
python test_ams_logging.py
```

**Resultado esperado:**
- ✅ Todos los tests pasan
- ✅ Se ven logs en formato JSON en la consola
- ✅ Los campos sensibles están sanitizados

**Estado:** ⬜ No iniciado

---

### ✅ Paso 1.5: Verificar instalación completa

**Checklist de verificación:**

- [ ] Carpeta `backend/shared/ams_logging` existe
- [ ] Todos los archivos .py están presentes
- [ ] `requirements-local.txt` actualizado
- [ ] `backend/auth-lambda/requirements.txt` actualizado
- [ ] Dependencias instaladas
- [ ] Script `test_ams_logging.py` creado
- [ ] Script de prueba ejecutado exitosamente
- [ ] Logs en formato JSON visibles en consola

**Estado:** ⬜ No iniciado

---

## 🚀 FASE 2: INTEGRACIÓN BÁSICA EN LAMBDA

**Duración estimada:** 30-40 minutos  
**Estado:** ⏳ Pendiente

### ✅ Paso 2.1: Crear módulo de logging centralizado

**Objetivo:** Crear un wrapper que configure el logger para Identity Manager

**Acción 1:** Crear carpeta `backend/shared/logging/`

```cmd
mkdir backend\shared\logging
```

**Acción 2:** Crear archivo `backend/shared/logging/__init__.py`

**Acción 3:** Crear archivo `backend/shared/logging/ams_logger_wrapper.py`

**Estado:** ⬜ No iniciado

---

### ✅ Paso 2.2: Integrar en lambda_function.py

**Objetivo:** Añadir logging estructurado al handler principal de Lambda

**Cambios a realizar:**

1. Importar el logger
2. Configurar logger en `initialize_services()`
3. Añadir trazabilidad (trace_id, request_id)
4. Añadir logs en el routing

**⚠️ IMPORTANTE:** Usar `;` en lugar de `&&`

**Estado:** ⬜ No iniciado

---

### ✅ Paso 2.3: Integrar en auth_service.py

**Objetivo:** Añadir logs estructurados en las operaciones de autenticación

**Logs a añadir:**
- ✅ AUTH_LOGIN_ATTEMPT
- ✅ AUTH_COGNITO_SUCCESS
- ✅ AUTH_PERMISSIONS_LOADED
- ✅ AUTH_LOGIN_SUCCESS
- ✅ AUTH_LOGIN_FAILED

**Estado:** ⬜ No iniciado

---

### ✅ Paso 2.4: Probar integración localmente

**Objetivo:** Verificar que los logs estructurados funcionan

**Comandos:**
```cmd
REM Iniciar servidor local
python local_server.py
```

**En otra terminal:**
```cmd
REM Test 1: Login exitoso
curl -X POST http://localhost:5000/auth/login -H "Content-Type: application/json" -d "{\"email\":\"test@example.com\",\"password\":\"password123\"}"
```

**Verificar:**
- [ ] Logs aparecen en formato JSON
- [ ] Cada log tiene `trace.id` y `request.id`
- [ ] Los eventos tienen nombres consistentes
- [ ] Los datos sensibles están sanitizados
- [ ] Los logs de error incluyen `error.type` y `error.message`

**Estado:** ⬜ No iniciado

---

## 📊 FASE 3: INTEGRACIÓN CON AUDITORÍA

**Duración estimada:** 45-60 minutos  
**Estado:** ⏳ Pendiente

### ✅ Paso 3.1: Crear servicio de auditoría mejorado

**Objetivo:** Crear servicio que convierta logs estructurados a registros de auditoría

**Acción:** Crear archivo `backend/shared/services/audit_service.py`

**Funcionalidades:**
- ✅ Registrar operaciones en tabla de auditoría
- ✅ Integrar con AMS Logger
- ✅ Añadir trazabilidad (trace_id, request_id)
- ✅ Mapear eventos a operaciones

**Estado:** ⬜ No iniciado

---

### ✅ Paso 3.2: Integrar audit_service en auth_service

**Objetivo:** Registrar automáticamente operaciones críticas

**Operaciones a registrar:**
- ✅ LOGIN (exitoso/fallido)
- ✅ LOGOUT
- ✅ TOKEN_VERIFY
- ✅ PASSWORD_CHANGE
- ✅ PERMISSION_CHECK

**Estado:** ⬜ No iniciado

---

### ✅ Paso 3.3: Actualizar tabla de auditoría (opcional)

**Objetivo:** Añadir campos de trazabilidad si no existen

**Campos a verificar/añadir:**
- `trace_id` VARCHAR(50)
- `request_id` VARCHAR(100)

**SQL (si es necesario):**
```sql
ALTER TABLE "identity-manager-audit-tbl" 
ADD COLUMN IF NOT EXISTS trace_id VARCHAR(50),
ADD COLUMN IF NOT EXISTS request_id VARCHAR(100);

CREATE INDEX IF NOT EXISTS idx_audit_trace_id 
ON "identity-manager-audit-tbl"(trace_id);
```

**Estado:** ⬜ No iniciado

---

## 🧪 FASE 4: TESTING Y VALIDACIÓN

**Duración estimada:** 30-40 minutos  
**Estado:** ⏳ Pendiente

### ✅ Paso 4.1: Pruebas funcionales

**Escenarios a probar:**

1. **Login exitoso**
   - [ ] Log estructurado generado
   - [ ] Registro en tabla de auditoría
   - [ ] trace_id y request_id presentes

2. **Login fallido**
   - [ ] Log de error con detalles
   - [ ] Registro en auditoría
   - [ ] error.type y error.message presentes

3. **Verificación de token**
   - [ ] Log de verificación
   - [ ] Trazabilidad mantenida

4. **Cambio de contraseña**
   - [ ] Log de operación
   - [ ] Datos sensibles sanitizados

**Estado:** ⬜ No iniciado

---

### ✅ Paso 4.2: Verificar sanitización

**Pruebas:**
- [ ] Contraseñas redactadas (`***REDACTED***`)
- [ ] Tokens redactados
- [ ] Emails enmascarados (`j***@example.com`)
- [ ] Otros datos sensibles protegidos

**Estado:** ⬜ No iniciado

---

### ✅ Paso 4.3: Verificar trazabilidad

**Pruebas:**
- [ ] trace_id se propaga entre servicios
- [ ] request_id único por petición
- [ ] Logs correlacionables por trace_id
- [ ] Auditoría incluye trazabilidad

**Estado:** ⬜ No iniciado

---

### ✅ Paso 4.4: Verificar formato JSON

**Verificar campos obligatorios:**
- [ ] `@timestamp`
- [ ] `log.level`
- [ ] `service.name` = "identity-mgmt"
- [ ] `service.version`
- [ ] `labels.environment`
- [ ] `event.name`
- [ ] `event.outcome`
- [ ] `message`
- [ ] `trace.id`
- [ ] `request.id`

**Estado:** ⬜ No iniciado

---

## 🚀 FASE 5: DESPLIEGUE (OPCIONAL)

**Duración estimada:** 1-2 horas  
**Estado:** ⏳ Pendiente

### ✅ Paso 5.1: Actualizar script de deployment

**Objetivo:** Incluir librería ams_logging en el paquete Lambda

**Acción:** Modificar `deploy_lambda_windows.py`

**Verificar que se incluya:**
- [ ] Carpeta `backend/shared/ams_logging`
- [ ] Carpeta `backend/shared/logging`
- [ ] Dependencia `python-json-logger`

**Estado:** ⬜ No iniciado

---

### ✅ Paso 5.2: Desplegar a Lambda

**Comandos:**
```cmd
python deploy_lambda_windows.py
```

**Verificar:**
- [ ] Deployment exitoso
- [ ] Lambda actualizada
- [ ] Logs estructurados en CloudWatch

**Estado:** ⬜ No iniciado

---

### ✅ Paso 5.3: Configurar CloudWatch Insights (opcional)

**Objetivo:** Crear queries para análisis de logs

**Queries de ejemplo:**

```
# Buscar por trace_id
fields @timestamp, event.name, message
| filter trace.id = "abc123"
| sort @timestamp desc

# Errores de autenticación
fields @timestamp, event.name, error.message, user_email
| filter event.name = "AUTH_LOGIN_FAILED"
| sort @timestamp desc

# Operaciones por usuario
fields @timestamp, event.name, message
| filter cognito_email = "user@example.com"
| sort @timestamp desc
```

**Estado:** ⬜ No iniciado

---

## 🔧 TROUBLESHOOTING

### Problema: Módulo ams_logging no encontrado

**Solución:**
```cmd
REM Verificar que la carpeta existe
dir backend\shared\ams_logging

REM Verificar que __init__.py existe
type backend\shared\ams_logging\__init__.py
```

---

### Problema: Logs no aparecen en formato JSON

**Solución:**
- Verificar que el logger está configurado correctamente
- Verificar que no hay otros loggers interfiriendo
- Verificar que stdout no está siendo redirigido

---

### Problema: Datos sensibles no se sanitizan

**Solución:**
- Verificar que `enable_sanitization=True` en LogConfig
- Verificar que los campos tienen nombres reconocibles (password, token, etc.)
- Revisar `constants.py` para ver campos sensibles

---

### Problema: trace_id no se propaga

**Solución:**
- Verificar que se llama a `logger.set_trace_id()` al inicio
- Verificar que se usa el mismo logger en todos los servicios
- Verificar que LogContext está funcionando

---

## ✅ CHECKLIST FINAL

### Fase 1: Preparación
- [ ] Librería copiada a `backend/shared/ams_logging`
- [ ] Requirements actualizados
- [ ] Dependencias instaladas
- [ ] Script de prueba ejecutado exitosamente

### Fase 2: Integración Lambda
- [ ] Módulo de logging creado
- [ ] lambda_function.py modificado
- [ ] auth_service.py modificado
- [ ] Pruebas locales exitosas

### Fase 3: Auditoría
- [ ] audit_service.py creado
- [ ] Integración con auth_service
- [ ] Tabla de auditoría actualizada (si necesario)

### Fase 4: Testing
- [ ] Pruebas funcionales completadas
- [ ] Sanitización verificada
- [ ] Trazabilidad verificada
- [ ] Formato JSON verificado

### Fase 5: Despliegue (Opcional)
- [ ] Script de deployment actualizado
- [ ] Desplegado a Lambda
- [ ] CloudWatch Insights configurado

---

## 📝 NOTAS IMPORTANTES

### ⚠️ Recordatorios
1. **SIEMPRE usar `;` en lugar de `&&` en comandos**
2. Hacer commit después de cada fase completada
3. Probar localmente antes de desplegar
4. Verificar sanitización de datos sensibles
5. Documentar cualquier problema encontrado

### 📊 Métricas de Éxito
- ✅ 100% de logs en formato JSON
- ✅ 100% de operaciones críticas registradas en auditoría
- ✅ 0 datos sensibles expuestos en logs
- ✅ Trazabilidad completa en todas las operaciones

---

## 📞 SOPORTE

Para dudas o problemas:
- Revisar documentación en `ams-logging-policy-python/README.md`
- Consultar ejemplos en `ams-logging-policy-python/examples/`
- Contactar con el equipo de Delivery AMS

---

**Última actualización:** 4 de Marzo de 2026, 17:26  
**Versión del documento:** 1.0  
**Estado general:** 🚧 En Progreso (0% completado)