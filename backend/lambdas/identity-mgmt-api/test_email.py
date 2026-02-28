#!/usr/bin/env python3
"""
Script de prueba para el servicio de email
"""

import os
import sys

# Configurar variables de entorno necesarias
os.environ['AWS_REGION'] = 'eu-west-1'
os.environ['EMAIL_SMTP_SECRET_NAME'] = 'identity-mgmt-dev-email-smtp'

# Añadir el directorio actual al path
sys.path.insert(0, os.path.dirname(__file__))

from services.email_service import EmailService

def test_email_service():
    """Probar el servicio de email"""
    
    print("=" * 60)
    print("PRUEBA DEL SERVICIO DE EMAIL")
    print("=" * 60)
    
    try:
        # Inicializar servicio
        print("\n1. Inicializando servicio de email...")
        email_service = EmailService()
        print(f"   ✓ Servicio inicializado")
        print(f"   - SMTP Server: {email_service.smtp_server}")
        print(f"   - SMTP Port: {email_service.smtp_port}")
        print(f"   - Gmail User: {email_service.gmail_user}")
        print(f"   - Timezone: {email_service.timezone}")
        
        # Preparar datos de prueba
        print("\n2. Preparando datos de prueba...")
        recipient_email = "csarrion@babel.es"
        recipient_name = "Carlos Sarrión"
        token = "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJzdWIiOiIxMjM0NTY3ODkwIiwibmFtZSI6IkpvaG4gRG9lIiwiaWF0IjoxNTE2MjM5MDIyfQ.SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
        token_info = {
            'profile': {
                'profile_name': 'Test Profile',
                'model': 'anthropic.claude-3-5-sonnet-20241022-v2:0',
                'application': 'Test Application'
            },
            'expires_at': '2026-05-30 21:30:00',
            'validity_days': 90
        }
        print(f"   ✓ Datos preparados")
        print(f"   - Destinatario: {recipient_email}")
        print(f"   - Nombre: {recipient_name}")
        
        # Enviar email
        print("\n3. Enviando email de prueba...")
        result = email_service.send_token_email(
            recipient_email=recipient_email,
            recipient_name=recipient_name,
            token=token,
            token_info=token_info
        )
        
        if result:
            print(f"   ✓ Email enviado exitosamente!")
            print(f"\n{'=' * 60}")
            print("PRUEBA COMPLETADA CON ÉXITO")
            print("=" * 60)
            return True
        else:
            print(f"   ✗ Error al enviar email")
            print(f"\n{'=' * 60}")
            print("PRUEBA FALLIDA")
            print("=" * 60)
            return False
            
    except Exception as e:
        print(f"\n   ✗ Error: {e}")
        print(f"\n{'=' * 60}")
        print("PRUEBA FALLIDA CON EXCEPCIÓN")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_email_service()
    sys.exit(0 if success else 1)
