"""
Local Server for Testing Auth Lambda
=====================================
Servidor Flask para probar la Lambda de autenticación localmente
"""

from flask import Flask, request, jsonify
from flask_cors import CORS
import sys
import os
import logging

# Añadir paths para importar módulos
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(current_dir, 'backend', 'auth-lambda'))
sys.path.insert(0, os.path.join(current_dir, 'backend'))

from lambda_function import lambda_handler

# Configurar logging SOLO para Flask/Werkzeug (no para root logger)
# Esto permite que los logs JSON del AMS Logger pasen sin ser reformateados
flask_logger = logging.getLogger('werkzeug')
flask_logger.setLevel(logging.INFO)

# Handler para Flask con formato tradicional
flask_handler = logging.StreamHandler(sys.stdout)
flask_handler.setFormatter(logging.Formatter(
    '%(asctime)s - %(name)s - %(levelname)s - %(message)s'
))
flask_logger.addHandler(flask_handler)

# Logger para este módulo
logger = logging.getLogger(__name__)
logger.setLevel(logging.INFO)
logger.addHandler(flask_handler)

# NO configurar el root logger con basicConfig para permitir que AMS Logger
# escriba directamente a stdout sin interferencias

# Crear app Flask
app = Flask(__name__)
CORS(app)  # Habilitar CORS para testing desde frontend

# Deshabilitar el logger por defecto de Flask para evitar duplicados
app.logger.disabled = True
log = logging.getLogger('werkzeug')
log.disabled = False


class MockContext:
    """Mock del contexto de Lambda para testing local"""
    aws_request_id = 'local-test-request'


@app.route('/auth/login', methods=['POST'])
def login():
    """Endpoint de login"""
    try:
        # Simular evento de API Gateway
        event = {
            'path': '/auth/login',
            'httpMethod': 'POST',
            'body': request.get_json(),
            'headers': dict(request.headers)  # Convertir a dict para que sea serializable
        }
        
        # Llamar al handler de Lambda
        response = lambda_handler(event, MockContext())
        
        # Extraer body y status code
        status_code = response.get('statusCode', 200)
        body = response.get('body', '{}')
        
        # Si body es string, parsearlo
        if isinstance(body, str):
            import json
            body = json.loads(body)
        
        return jsonify(body), status_code
        
    except Exception as e:
        logger.error(f"Error en login: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': str(e)
        }), 500


@app.route('/auth/verify', methods=['POST'])
def verify():
    """Endpoint de verificación de token"""
    try:
        # Simular evento de API Gateway
        event = {
            'path': '/auth/verify',
            'httpMethod': 'POST',
            'body': request.get_json(),
            'headers': dict(request.headers)  # Convertir a dict para que sea serializable
        }
        
        # Llamar al handler de Lambda
        response = lambda_handler(event, MockContext())
        
        # Extraer body y status code
        status_code = response.get('statusCode', 200)
        body = response.get('body', '{}')
        
        # Si body es string, parsearlo
        if isinstance(body, str):
            import json
            body = json.loads(body)
        
        return jsonify(body), status_code
        
    except Exception as e:
        logger.error(f"Error en verify: {e}", exc_info=True)
        return jsonify({
            'valid': False,
            'error': str(e)
        }), 500


@app.route('/auth/forgot-password', methods=['POST'])
def forgot_password():
    """Endpoint de recuperación de contraseña"""
    try:
        # Simular evento de API Gateway
        event = {
            'path': '/auth/forgot-password',
            'httpMethod': 'POST',
            'body': request.get_json(),
            'headers': dict(request.headers)  # Convertir a dict para que sea serializable
        }
        
        # Llamar al handler de Lambda
        response = lambda_handler(event, MockContext())
        
        # Extraer body y status code
        status_code = response.get('statusCode', 200)
        body = response.get('body', '{}')
        
        # Si body es string, parsearlo
        if isinstance(body, str):
            import json
            body = json.loads(body)
        
        return jsonify(body), status_code
        
    except Exception as e:
        logger.error(f"Error en forgot-password: {e}", exc_info=True)
        return jsonify({
            'success': False,
            'error': 'INTERNAL_ERROR',
            'message': str(e)
        }), 500


@app.route('/health', methods=['GET'])
def health():
    """Health check endpoint"""
    return jsonify({
        'status': 'healthy',
        'service': 'auth-lambda-local',
        'version': '1.0.0'
    })


@app.route('/', methods=['GET'])
def index():
    """Redirigir a la página de login"""
    return app.send_static_file('login.html')


@app.route('/api-info', methods=['GET'])
def api_info():
    """Información de la API"""
    return jsonify({
        'service': 'Auth Lambda - Local Server',
        'version': '1.0.0',
        'endpoints': {
            'POST /auth/login': {
                'description': 'Autenticar usuario con Cognito',
                'body': {
                    'email': 'user@example.com',
                    'password': 'password123'
                },
                'response': {
                    'success': True,
                    'token': 'jwt_token',
                    'user': {},
                    'permissions': [],
                    'expiresAt': 'ISO8601'
                }
            },
            'POST /auth/verify': {
                'description': 'Verificar token JWT',
                'body': {
                    'token': 'jwt_token'
                },
                'response': {
                    'valid': True,
                    'user': {},
                    'permissions': [],
                    'expiresAt': 'ISO8601'
                }
            },
            'GET /health': {
                'description': 'Health check'
            }
        }
    })


if __name__ == '__main__':
    print("=" * 60)
    print("🚀 Auth Lambda - Servidor Local")
    print("=" * 60)
    print("\n📍 Endpoints disponibles:")
    print("   • POST http://localhost:5000/auth/login")
    print("   • POST http://localhost:5000/auth/verify")
    print("   • GET  http://localhost:5000/health")
    print("\n📝 Ejemplo de uso con curl:")
    print('\n   Login:')
    print('   curl -X POST http://localhost:5000/auth/login \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"email":"user@example.com","password":"password123"}\'')
    print('\n   Verify:')
    print('   curl -X POST http://localhost:5000/auth/verify \\')
    print('     -H "Content-Type: application/json" \\')
    print('     -d \'{"token":"your_jwt_token_here"}\'')
    print("\n" + "=" * 60)
    print("⚙️  Iniciando servidor en http://localhost:5000")
    print("   📊 Los logs JSON estructurados aparecerán a continuación")
    print("=" * 60 + "\n")
    
    app.run(host='0.0.0.0', port=5000, debug=True)