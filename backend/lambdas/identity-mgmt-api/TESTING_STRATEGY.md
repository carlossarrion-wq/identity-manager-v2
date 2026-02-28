# Estrategia de Testing - Identity Manager API Lambda

## 📋 Índice

1. [Visión General](#visión-general)
2. [Niveles de Testing](#niveles-de-testing)
3. [Testing de Servicios](#testing-de-servicios)
4. [Estrategias de Acceso a RDS](#estrategias-de-acceso-a-rds)
5. [Mocking y Fixtures](#mocking-y-fixtures)
6. [Testing en Diferentes Entornos](#testing-en-diferentes-entornos)
7. [CI/CD Integration](#cicd-integration)

---

## 🎯 Visión General

La Lambda está compuesta por 3 servicios principales que requieren diferentes estrategias de testing:

1. **CognitoService**: Interactúa con AWS Cognito (servicio externo)
2. **DatabaseService**: Interactúa con PostgreSQL RDS (requiere conectividad)
3. **JWTService**: Lógica interna de generación/validación JWT

### Desafíos de Testing

- ✅ **JWTService**: Fácil de testear (lógica pura)
- ⚠️ **CognitoService**: Requiere credenciales AWS y User Pool
- ❌ **DatabaseService**: Requiere acceso a RDS (VPC privada)

---

## 🏗️ Niveles de Testing

### 1. Unit Tests (Local)
- **Objetivo**: Testear lógica de negocio aislada
- **Herramientas**: pytest, unittest.mock
- **Cobertura**: 80%+

### 2. Integration Tests (Local con Mocks)
- **Objetivo**: Testear interacción entre componentes
- **Herramientas**: pytest, moto (AWS mocking)
- **Cobertura**: Flujos principales

### 3. Integration Tests (EC2 Bridge)
- **Objetivo**: Testear con servicios reales
- **Herramientas**: pytest + SSH tunnel
- **Cobertura**: Casos críticos

### 4. End-to-End Tests (AWS)
- **Objetivo**: Testear Lambda desplegada
- **Herramientas**: AWS Lambda invoke
- **Cobertura**: Smoke tests

---

## 🧪 Testing de Servicios

### 1. JWTService Testing

#### ✅ Estrategia: Unit Tests Puros (Local)

**Ventajas:**
- No requiere servicios externos
- Rápido y determinista
- Fácil de ejecutar en CI/CD

**Archivo**: `tests/unit/test_jwt_service.py`

```python
import pytest
import jwt
from datetime import datetime, timedelta
from services.jwt_service import JWTService

class TestJWTService:
    
    @pytest.fixture
    def jwt_service(self, monkeypatch):
        """Fixture con secret key mockeada"""
        monkeypatch.setenv('JWT_SECRET_KEY', 'test-secret-key-12345')
        service = JWTService()
        service.secret_key = 'test-secret-key-12345'
        return service
    
    @pytest.fixture
    def user_info(self):
        return {
            'user_id': 'test-user-123',
            'email': 'test@example.com',
            'person': 'Test User',
            'groups': ['developers-group']
        }
    
    @pytest.fixture
    def profile_info(self):
        return {
            'profile_id': 'profile-uuid-123',
            'profile_name': 'Test Profile',
            'model_id': 'claude-3-5-sonnet'
        }
    
    def test_generate_token_success(self, jwt_service, user_info, profile_info):
        """Test: Generar token JWT correctamente"""
        result = jwt_service.generate_token(
            user_info=user_info,
            profile_info=profile_info,
            validity_period='90_days'
        )
        
        assert 'jwt' in result
        assert 'jti' in result
        assert 'token_hash' in result
        assert result['validity_days'] == 90
        
        # Verificar estructura del token
        decoded = jwt.decode(
            result['jwt'],
            'test-secret-key-12345',
            algorithms=['HS256'],
            options={"verify_signature": True}
        )
        
        assert decoded['user_id'] == 'test-user-123'
        assert decoded['email'] == 'test@example.com'
        assert decoded['team'] == 'developers-group'
        assert decoded['iss'] == 'identity-manager'
        assert 'bedrock-proxy' in decoded['aud']
    
    def test_generate_token_invalid_period(self, jwt_service, user_info, profile_info):
        """Test: Período de validez inválido"""
        with pytest.raises(ValueError, match='Período de validez inválido'):
            jwt_service.generate_token(
                user_info=user_info,
                profile_info=profile_info,
                validity_period='invalid_period'
            )
    
    def test_validate_token_success(self, jwt_service, user_info, profile_info):
        """Test: Validar token válido"""
        token_data = jwt_service.generate_token(
            user_info=user_info,
            profile_info=profile_info,
            validity_period='1_day'
        )
        
        payload = jwt_service.validate_token(token_data['jwt'])
        
        assert payload['user_id'] == 'test-user-123'
        assert payload['email'] == 'test@example.com'
    
    def test_validate_token_expired(self, jwt_service):
        """Test: Token expirado"""
        # Crear token expirado
        expired_payload = {
            'user_id': 'test-user',
            'exp': int((datetime.utcnow() - timedelta(hours=1)).timestamp()),
            'iat': int((datetime.utcnow() - timedelta(hours=2)).timestamp()),
            'iss': 'identity-manager',
            'aud': ['bedrock-proxy']
        }
        
        expired_token = jwt.encode(
            expired_payload,
            'test-secret-key-12345',
            algorithm='HS256'
        )
        
        with pytest.raises(jwt.ExpiredSignatureError):
            jwt_service.validate_token(expired_token)
    
    def test_calculate_hash(self, jwt_service):
        """Test: Calcular hash de token"""
        token = "test.jwt.token"
        hash1 = jwt_service._calculate_hash(token)
        hash2 = jwt_service._calculate_hash(token)
        
        assert hash1 == hash2  # Determinista
        assert len(hash1) == 64  # SHA-256
    
    def test_verify_token_hash(self, jwt_service):
        """Test: Verificar hash de token"""
        token = "test.jwt.token"
        stored_hash = jwt_service._calculate_hash(token)
        
        assert jwt_service.verify_token_hash(token, stored_hash) is True
        assert jwt_service.verify_token_hash(token, "wrong-hash") is False
```

**Ejecutar tests:**
```bash
cd backend/lambdas/identity-mgmt-api
pytest tests/unit/test_jwt_service.py -v --cov=services.jwt_service
```

---

### 2. CognitoService Testing

#### ✅ Estrategia: Mocking con `moto` (Local)

**Ventajas:**
- No requiere User Pool real
- Rápido y reproducible
- No consume recursos AWS

**Archivo**: `tests/unit/test_cognito_service.py`

```python
import pytest
import boto3
from moto import mock_cognitoidp
from services.cognito_service import CognitoService

@mock_cognitoidp
class TestCognitoService:
    
    @pytest.fixture
    def cognito_setup(self, monkeypatch):
        """Setup de Cognito mockeado"""
        # Crear User Pool mock
        client = boto3.client('cognito-idp', region_name='eu-west-1')
        
        user_pool = client.create_user_pool(
            PoolName='test-pool',
            Policies={
                'PasswordPolicy': {
                    'MinimumLength': 8,
                    'RequireUppercase': True,
                    'RequireLowercase': True,
                    'RequireNumbers': True,
                    'RequireSymbols': True
                }
            }
        )
        
        pool_id = user_pool['UserPool']['Id']
        
        # Crear grupo
        client.create_group(
            GroupName='developers-group',
            UserPoolId=pool_id,
            Description='Test group'
        )
        
        # Configurar variables de entorno
        monkeypatch.setenv('COGNITO_USER_POOL_ID', pool_id)
        monkeypatch.setenv('AWS_REGION', 'eu-west-1')
        
        return {
            'pool_id': pool_id,
            'client': client
        }
    
    def test_create_user_success(self, cognito_setup):
        """Test: Crear usuario correctamente"""
        service = CognitoService()
        
        result = service.create_user(
            email='test@example.com',
            person='Test User',
            group='developers-group',
            send_email=False
        )
        
        assert result['success'] is True
        assert result['user']['email'] == 'test@example.com'
        assert result['user']['person'] == 'Test User'
        assert 'developers-group' in result['user']['groups']
    
    def test_create_user_duplicate(self, cognito_setup):
        """Test: Usuario duplicado"""
        service = CognitoService()
        
        # Crear primer usuario
        service.create_user(
            email='test@example.com',
            person='Test User',
            group='developers-group',
            send_email=False
        )
        
        # Intentar crear duplicado
        with pytest.raises(ValueError, match='ya existe'):
            service.create_user(
                email='test@example.com',
                person='Test User 2',
                group='developers-group',
                send_email=False
            )
    
    def test_get_user_success(self, cognito_setup):
        """Test: Obtener usuario existente"""
        service = CognitoService()
        
        # Crear usuario
        service.create_user(
            email='test@example.com',
            person='Test User',
            group='developers-group',
            send_email=False
        )
        
        # Obtener usuario
        user = service.get_user('test@example.com')
        
        assert user['email'] == 'test@example.com'
        assert user['person'] == 'Test User'
        assert 'developers-group' in user['groups']
    
    def test_get_user_not_found(self, cognito_setup):
        """Test: Usuario no encontrado"""
        service = CognitoService()
        
        with pytest.raises(ValueError, match='Usuario no encontrado'):
            service.get_user('nonexistent@example.com')
    
    def test_delete_user_success(self, cognito_setup):
        """Test: Eliminar usuario"""
        service = CognitoService()
        
        # Crear usuario
        service.create_user(
            email='test@example.com',
            person='Test User',
            group='developers-group',
            send_email=False
        )
        
        # Eliminar usuario
        result = service.delete_user('test@example.com')
        
        assert result is True
        
        # Verificar que no existe
        with pytest.raises(ValueError):
            service.get_user('test@example.com')
    
    def test_list_users(self, cognito_setup):
        """Test: Listar usuarios"""
        service = CognitoService()
        
        # Crear varios usuarios
        for i in range(3):
            service.create_user(
                email=f'user{i}@example.com',
                person=f'User {i}',
                group='developers-group',
                send_email=False
            )
        
        # Listar usuarios
        result = service.list_users(limit=10)
        
        assert len(result['users']) == 3
        assert result['total_count'] == 3
    
    def test_list_groups(self, cognito_setup):
        """Test: Listar grupos"""
        service = CognitoService()
        
        result = service.list_groups()
        
        assert len(result['groups']) >= 1
        assert any(g['group_name'] == 'developers-group' for g in result['groups'])
```

**Ejecutar tests:**
```bash
pip install moto[cognitoidp]
pytest tests/unit/test_cognito_service.py -v
```

---

### 3. DatabaseService Testing

#### ❌ Problema: RDS en VPC Privada

**Opciones de Acceso:**

##### Opción 1: ❌ Abrir RDS a Internet (NO RECOMENDADO)
```
❌ Riesgos de seguridad
❌ Viola mejores prácticas
❌ No aceptable para producción
```

##### Opción 2: ✅ SSH Tunnel vía EC2 (RECOMENDADO)
```
✅ Seguro
✅ No modifica configuración de RDS
✅ Auditable
```

##### Opción 3: ✅ PostgreSQL Local con Docker (DESARROLLO)
```
✅ Rápido para desarrollo
✅ No requiere AWS
✅ Reproducible
```

##### Opción 4: ✅ Mocking Completo (UNIT TESTS)
```
✅ Muy rápido
✅ No requiere BD
✅ Ideal para CI/CD
```

---

## 🔐 Estrategias de Acceso a RDS

### Estrategia A: SSH Tunnel vía EC2 (Integration Tests)

#### Setup del Tunnel

**Script**: `tests/integration/setup_db_tunnel.sh`

```bash
#!/bin/bash
# Crear SSH tunnel a RDS vía EC2

EC2_HOST="ec2-user@18.202.140.248"
EC2_KEY="~/.ssh/ec2_new_key"
RDS_HOST="identity-manager-dev-rds.czuimyk2qu10.eu-west-1.rds.amazonaws.com"
RDS_PORT="5432"
LOCAL_PORT="15432"

echo "Creando SSH tunnel a RDS..."
echo "Local: localhost:$LOCAL_PORT -> RDS: $RDS_HOST:$RDS_PORT"

ssh -i $EC2_KEY \
    -N \
    -L $LOCAL_PORT:$RDS_HOST:$RDS_PORT \
    $EC2_HOST \
    -o ServerAliveInterval=60 \
    -o ServerAliveCountMax=3

# Mantener tunnel abierto
# Ctrl+C para cerrar
```

#### Tests con Tunnel

**Archivo**: `tests/integration/test_database_service.py`

```python
import pytest
import psycopg2
import os
from services.database_service import DatabaseService

# Marcar tests que requieren BD real
pytestmark = pytest.mark.integration

@pytest.fixture(scope="module")
def db_connection_params():
    """Parámetros de conexión vía SSH tunnel"""
    return {
        'host': 'localhost',
        'port': 15432,  # Puerto del tunnel
        'database': 'identity_manager_dev_rds',
        'user': 'dbadmin',
        'password': os.environ.get('DB_PASSWORD')
    }

@pytest.fixture(scope="module")
def verify_tunnel(db_connection_params):
    """Verificar que el tunnel SSH está activo"""
    try:
        conn = psycopg2.connect(**db_connection_params, connect_timeout=5)
        conn.close()
        return True
    except Exception as e:
        pytest.skip(f"SSH tunnel no disponible: {e}")

class TestDatabaseServiceIntegration:
    
    def test_connection(self, verify_tunnel, monkeypatch):
        """Test: Conexión a BD"""
        # Mock de Secrets Manager para usar tunnel
        def mock_get_credentials(self):
            return {
                'host': 'localhost',
                'port': '15432',
                'dbname': 'identity_manager_dev_rds',
                'username': 'dbadmin',
                'password': os.environ.get('DB_PASSWORD')
            }
        
        monkeypatch.setattr(
            DatabaseService,
            '_get_db_credentials',
            mock_get_credentials
        )
        
        service = DatabaseService()
        
        with service.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute('SELECT 1')
            result = cursor.fetchone()
            assert result[0] == 1
    
    def test_list_profiles(self, verify_tunnel, monkeypatch):
        """Test: Listar perfiles de inferencia"""
        def mock_get_credentials(self):
            return {
                'host': 'localhost',
                'port': '15432',
                'dbname': 'identity_manager_dev_rds',
                'username': 'dbadmin',
                'password': os.environ.get('DB_PASSWORD')
            }
        
        monkeypatch.setattr(
            DatabaseService,
            '_get_db_credentials',
            mock_get_credentials
        )
        
        service = DatabaseService()
        result = service.list_profiles()
        
        assert 'profiles' in result
        assert isinstance(result['profiles'], list)
    
    def test_get_config(self, verify_tunnel, monkeypatch):
        """Test: Obtener configuración"""
        def mock_get_credentials(self):
            return {
                'host': 'localhost',
                'port': '15432',
                'dbname': 'identity_manager_dev_rds',
                'username': 'dbadmin',
                'password': os.environ.get('DB_PASSWORD')
            }
        
        monkeypatch.setattr(
            DatabaseService,
            '_get_db_credentials',
            mock_get_credentials
        )
        
        service = DatabaseService()
        result = service.get_config()
        
        assert 'config' in result
        assert 'cognito_user_pool_id' in result['config']
```

**Ejecutar tests con tunnel:**
```bash
# Terminal 1: Iniciar tunnel
./tests/integration/setup_db_tunnel.sh

# Terminal 2: Ejecutar tests
export DB_PASSWORD='your-password'
pytest tests/integration/test_database_service.py -v -m integration
```

---

### Estrategia B: PostgreSQL Local con Docker (Desarrollo)

#### Docker Compose Setup

**Archivo**: `tests/docker-compose.test.yml`

```yaml
version: '3.8'

services:
  postgres-test:
    image: postgres:15
    environment:
      POSTGRES_DB: identity_manager_test
      POSTGRES_USER: testuser
      POSTGRES_PASSWORD: testpass
    ports:
      - "15433:5432"
    volumes:
      - ../../database/schema/identity_manager_schema_v3_uuid.sql:/docker-entrypoint-initdb.d/01-schema.sql
      - ../../database/seeds/insert_data_v3_uuid.sql:/docker-entrypoint-initdb.d/02-seeds.sql
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U testuser"]
      interval: 5s
      timeout: 5s
      retries: 5
```

#### Tests con Docker

**Archivo**: `tests/integration/test_database_service_docker.py`

```python
import pytest
import time
import subprocess
from services.database_service import DatabaseService

@pytest.fixture(scope="module")
def docker_postgres():
    """Iniciar PostgreSQL en Docker"""
    # Iniciar contenedor
    subprocess.run([
        'docker-compose',
        '-f', 'tests/docker-compose.test.yml',
        'up', '-d'
    ], check=True)
    
    # Esperar a que esté listo
    time.sleep(10)
    
    yield
    
    # Limpiar
    subprocess.run([
        'docker-compose',
        '-f', 'tests/docker-compose.test.yml',
        'down', '-v'
    ])

class TestDatabaseServiceDocker:
    
    def test_save_and_get_token(self, docker_postgres, monkeypatch):
        """Test: Guardar y obtener token"""
        def mock_get_credentials(self):
            return {
                'host': 'localhost',
                'port': '15433',
                'dbname': 'identity_manager_test',
                'username': 'testuser',
                'password': 'testpass'
            }
        
        monkeypatch.setattr(
            DatabaseService,
            '_get_db_credentials',
            mock_get_credentials
        )
        
        service = DatabaseService()
        
        # Guardar token
        from datetime import datetime, timedelta
        token_record = service.save_token(
            user_id='test-user',
            email='test@example.com',
            jti='test-jti-123',
            token_hash='test-hash',
            profile_id='some-uuid',
            expires_at=datetime.utcnow() + timedelta(days=90)
        )
        
        assert 'token_id' in token_record
        
        # Obtener token
        token = service.get_token(token_record['token_id'])
        assert token['jti'] == 'test-jti-123'
```

**Ejecutar tests con Docker:**
```bash
docker-compose -f tests/docker-compose.test.yml up -d
pytest tests/integration/test_database_service_docker.py -v
docker-compose -f tests/docker-compose.test.yml down -v
```

---

### Estrategia C: Mocking Completo (Unit Tests)

**Archivo**: `tests/unit/test_database_service_mock.py`

```python
import pytest
from unittest.mock import Mock, MagicMock, patch
from services.database_service import DatabaseService

class TestDatabaseServiceMocked:
    
    @pytest.fixture
    def mock_connection(self):
        """Mock de conexión a BD"""
        conn = MagicMock()
        cursor = MagicMock()
        conn.cursor.return_value = cursor
        return conn, cursor
    
    def test_list_tokens_mocked(self, mock_connection, monkeypatch):
        """Test: Listar tokens con mock"""
        conn, cursor = mock_connection
        
        # Mock de datos
        cursor.fetchall.return_value = [
            {
                'token_id': 'uuid-1',
                'jti': 'jti-1',
                'user_email': 'user1@example.com',
                'status': 'active'
            },
            {
                'token_id': 'uuid-2',
                'jti': 'jti-2',
                'user_email': 'user2@example.com',
                'status': 'active'
            }
        ]
        
        cursor.fetchone.return_value = {'total': 2}
        
        # Mock de get_connection
        service = DatabaseService()
        
        with patch.object(service, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = conn
            
            result = service.list_tokens()
            
            assert len(result['tokens']) == 2
            assert result['total_count'] == 2
            assert result['tokens'][0]['jti'] == 'jti-1'
    
    def test_save_token_mocked(self, mock_connection, monkeypatch):
        """Test: Guardar token con mock"""
        conn, cursor = mock_connection
        
        # Mock de resultado
        from datetime import datetime
        cursor.fetchone.return_value = {
            'id': 'new-uuid',
            'issued_at': datetime.utcnow()
        }
        
        service = DatabaseService()
        
        with patch.object(service, 'get_connection') as mock_get_conn:
            mock_get_conn.return_value.__enter__.return_value = conn
            
            from datetime import timedelta
            result = service.save_token(
                user_id='test-user',
                email='test@example.com',
                jti='test-jti',
                token_hash='hash',
                profile_id='profile-uuid',
                expires_at=datetime.utcnow() + timedelta(days=90)
            )
            
            assert 'token_id' in result
            assert result['token_id'] == 'new-uuid'
```

---

## 🎭 Mocking y Fixtures

### Fixtures Compartidos

**Archivo**: `tests/conftest.py`

```python
import pytest
import os
from unittest.mock import Mock

@pytest.fixture
def mock_aws_credentials(monkeypatch):
    """Mock de credenciales AWS"""
    monkeypatch.setenv('AWS_ACCESS_KEY_ID', 'testing')
    monkeypatch.setenv('AWS_SECRET_ACCESS_KEY', 'testing')
    monkeypatch.setenv('AWS_SECURITY_TOKEN', 'testing')
    monkeypatch.setenv('AWS_SESSION_TOKEN', 'testing')
    monkeypatch.setenv('AWS_REGION', 'eu-west-1')

@pytest.fixture
def mock_secrets_manager():
    """Mock de Secrets Manager"""
    with patch('boto3.client') as mock_client:
        mock_sm = Mock()
        mock_sm.get_secret_value.return_value = {
            'SecretString': json.dumps({
                'host': 'localhost',
                'port': '5432',
                'dbname': 'test_db',
                'username': 'testuser',
                'password': 'testpass',
                'jwt_secret_key': 'test-jwt-secret'
            })
        }
        mock_client.return_value = mock_sm
        yield mock_sm

@pytest.fixture
def sample_user_info():
    """Usuario de ejemplo"""
    return {
        'user_id': 'test-user-123',
        'email': 'test@example.com',
        'person': 'Test User',
        'groups': ['developers-group'],
        'status': 'CONFIRMED',
        'enabled': True
    }

@pytest.fixture
def sample_profile_info():
    """Perfil de ejemplo"""
    return {
        'profile_id': 'profile-uuid-123',
        'profile_name': 'Test Profile',
        'model_id': 'claude-3-5-sonnet',
        'model_arn': 'arn:aws:bedrock:...',
        'is_active': True
    }
```

---

## 🌍 Testing en Diferentes Entornos

### Matriz de Testing

| Entorno | JWT Service | Cognito Service | Database Service |
|---------|-------------|-----------------|------------------|
| **Local (Unit)** | ✅ Tests puros | ✅ Moto mocks | ✅ Mocks completos |
| **Local (Docker)** | ✅ Tests puros | ✅ Moto mocks | ✅ PostgreSQL local |
| **Local (SSH Tunnel)** | ✅ Tests puros | ⚠️ Cognito real | ✅ RDS vía tunnel |
| **EC2** | ✅ Tests puros | ✅ Cognito real | ✅ RDS directo |
| **Lambda (AWS)** | ✅ E2E tests | ✅ E2E tests | ✅ E2E tests |

### Configuración por Entorno

**Archivo**: `pytest.ini`

```ini
[pytest]
markers =
    unit: Unit tests (no external dependencies)
    integration: Integration tests (requires external services)
    docker: Tests that require Docker
    tunnel: Tests that require SSH tunnel
    e2e: End-to-end tests in AWS
    slow: Slow running tests

testpaths = tests
python_files = test_*.py
python_classes = Test*
python_functions = test_*

# Opciones por defecto
addopts = 
    -v
    --strict-markers
    --tb=short
    --cov=services
    --cov=utils
    --cov-report=html
    --cov-report=term-missing
```

### Comandos de Testing

```bash
# Unit tests (rápidos, sin dependencias)
pytest -m unit

# Integration tests con Docker
pytest -m "integration and docker"

# Integration tests con SSH tunnel
pytest -m "integration and tunnel"

# Todos los tests excepto E2E
pytest -m "not e2e"

# Solo tests rápidos
pytest -m "not slow"

# Con cobertura
pytest --cov=services --cov-report=html

# Verbose con output
pytest -v -s
```

---

## 🚀 CI/CD Integration

### GitHub Actions Workflow

**Archivo**: `.github/workflows/test-lambda.yml`

```yaml
name: Test Lambda Function

on:
  push:
    branches: [main, develop]
    paths:
      - 'backend/lambdas/identity-mgmt-api/**'
  pull_request:
    branches: [main, develop]

jobs:
  unit-tests:
    runs-on: ubuntu-latest
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          cd backend/lambdas/identity-mgmt-api
          pip install -r requirements.txt
          pip install pytest pytest-cov moto[cognitoidp]
      
      - name: Run unit tests
        run: |
          cd backend/lambdas/identity-mgmt-api
          pytest tests/unit -v --cov=services --cov=utils
      
      - name: Upload coverage
        uses: codecov/codecov-action@v3
  
  integration-tests-docker:
    runs-on: ubuntu-latest
    
    services:
      postgres:
        image: postgres:15
        env:
          POSTGRES_DB: identity_manager_test
          POSTGRES_USER: testuser
          POSTGRES_PASSWORD: testpass
        ports:
          - 5432:5432
        options: >-
          --health-cmd pg_isready
          --health-interval 10s
          --health-timeout 5s
          --health-retries 5
    
    steps:
      - uses: actions/checkout@v3
      
      - name: Set up Python
        uses: actions/setup-python@v4
        with:
          python-version: '3.12'
      
      - name: Install dependencies
        run: |
          cd backend/lambdas/identity-mgmt-api
          pip install -r requirements.txt
          pip install pytest pytest-cov
      
      - name: Initialize database
        run: |
          PGPASSWORD=testpass psql -h localhost -U testuser -d identity_manager_test -f database/schema/identity_manager_schema_v3_uuid.sql
          PGPASSWORD=testpass psql -h localhost -U testuser -d identity_manager_test -f database/seeds/insert_data_v3_uuid.sql
      
      - name: Run integration tests
        env:
          DB_PASSWORD: testpass
        run: |
          cd backend/lambdas/identity-mgmt-api
          pytest tests/integration -v -m docker
```

---

## 📊 Resumen de Estrategias

### Recomendación por Caso de Uso

#### Desarrollo Local Diario
```bash
# Opción 1: Solo unit tests (más rápido)
pytest -m unit

# Opción 2: Con PostgreSQL Docker
docker-compose -f tests/docker-compose.test.yml up -d
pytest -m "unit or docker"
```

#### Testing Completo Pre-Commit
```bash
# Con SSH tunnel a RDS
./tests/integration/setup_db_tunnel.sh &
export DB_PASSWORD='your-password'
pytest -m "unit or integration"
```

#### CI/CD Pipeline
```bash
# Unit tests + Docker integration
pytest -m "unit or docker" --cov=services --cov=utils
```

#### Testing en AWS (Post-Deploy)
```bash
# E2E tests con Lambda desplegada
pytest -m e2e
```

---

## 🎯 Objetivos de Cobertura

- **Unit Tests**: 80%+ de cobertura
- **Integration Tests**: Flujos críticos (crear token, gestionar usuarios)
- **E2E Tests**: Smoke tests (verificar que Lambda responde)

---

## 📝 Checklist de Testing

- [ ] Unit tests para JWTService (100% cobertura)
- [ ] Unit tests para CognitoService con moto
- [ ] Unit tests para DatabaseService con mocks
- [ ] Integration tests con PostgreSQL Docker
- [ ] Integration tests con SSH tunnel (opcional)
- [ ] E2E tests en AWS Lambda
- [ ] CI/CD pipeline configurado
- [ ] Documentación de testing actualizada

---

## 👥 Contacto

**Proyecto**: Identity Manager v5.0
**Equipo**: TCS Team
**Última actualización**: 2026-02-28
