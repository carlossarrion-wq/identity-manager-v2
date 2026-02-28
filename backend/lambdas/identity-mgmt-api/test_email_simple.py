#!/usr/bin/env python3
"""
Script de prueba simple para el servicio de email (sin dependencias de BD)
"""

import os
import sys
import json

# Configurar variables de entorno necesarias
os.environ['AWS_REGION'] = 'eu-west-1'
os.environ['EMAIL_SMTP_SECRET_NAME'] = 'identity-mgmt-dev-email-smtp'

def test_email_direct():
    """Probar el envío de email directamente"""
    
    print("=" * 60)
    print("PRUEBA DIRECTA DEL SERVICIO DE EMAIL")
    print("=" * 60)
    
    try:
        import boto3
        import smtplib
        import ssl
        from email.mime.text import MIMEText
        from email.mime.multipart import MIMEMultipart
        from datetime import datetime
        
        # 1. Obtener credenciales de Secrets Manager
        print("\n1. Obteniendo credenciales de Secrets Manager...")
        secrets_client = boto3.client('secretsmanager', region_name='eu-west-1')
        secret_name = 'identity-mgmt-dev-email-smtp'
        
        response = secrets_client.get_secret_value(SecretId=secret_name)
        credentials = json.loads(response['SecretString'])
        
        smtp_config = credentials.get('gmail_smtp', {})
        email_settings = credentials.get('email_settings', {})
        
        smtp_server = smtp_config.get('server', 'smtp.gmail.com')
        smtp_port = smtp_config.get('port', 587)
        gmail_user = smtp_config.get('user', '')
        gmail_password = smtp_config.get('password', '')
        use_tls = smtp_config.get('use_tls', True)
        
        print(f"   ✓ Credenciales obtenidas")
        print(f"   - SMTP Server: {smtp_server}")
        print(f"   - SMTP Port: {smtp_port}")
        print(f"   - Gmail User: {gmail_user}")
        print(f"   - Use TLS: {use_tls}")
        
        # 2. Preparar email
        print("\n2. Preparando email de prueba...")
        recipient_email = "carlos.sarrion@es.ibm.com"
        recipient_name = "Carlos Sarrión"
        
        message = MIMEMultipart('alternative')
        message['Subject'] = "🔑 TEST - Nuevo Token JWT Creado - Identity Manager"
        message['From'] = f"Identity Manager <{gmail_user}>"
        message['To'] = recipient_email
        message['Reply-To'] = gmail_user
        
        # Texto plano
        text_body = f"""
NUEVO TOKEN JWT CREADO (TEST)
==============================

Hola {recipient_name},

Este es un email de prueba del servicio de envío de tokens JWT.

Perfil: Test Profile
Modelo: anthropic.claude-3-5-sonnet-20241022-v2:0
Aplicación: Test Application
Validez: 90 días
Expira: 2026-05-30 21:30:00

TOKEN JWT (EJEMPLO):
--------------------
eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token

---
Email de prueba enviado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}
© 2026 Identity Manager
"""
        
        # HTML
        html_body = f"""
<!DOCTYPE html>
<html>
<head>
    <meta charset="UTF-8">
    <style>
        body {{ font-family: Arial, sans-serif; line-height: 1.6; color: #333; max-width: 600px; margin: 0 auto; padding: 20px; }}
        .header {{ background-color: #4CAF50; color: white; padding: 20px; text-align: center; border-radius: 5px 5px 0 0; }}
        .content {{ background-color: #f9f9f9; padding: 20px; border: 1px solid #ddd; border-radius: 0 0 5px 5px; }}
        .token-box {{ background-color: #fff; border: 2px solid #4CAF50; border-radius: 5px; padding: 15px; margin: 20px 0; word-wrap: break-word; font-family: monospace; font-size: 12px; }}
        .footer {{ text-align: center; color: #666; font-size: 12px; margin-top: 20px; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>🔑 TEST - Nuevo Token JWT Creado</h1>
    </div>
    <div class="content">
        <p>Hola <strong>{recipient_name}</strong>,</p>
        <p>Este es un email de prueba del servicio de envío de tokens JWT.</p>
        <p><strong>Detalles del Token:</strong></p>
        <ul>
            <li>Perfil: Test Profile</li>
            <li>Modelo: anthropic.claude-3-5-sonnet-20241022-v2:0</li>
            <li>Aplicación: Test Application</li>
            <li>Validez: 90 días</li>
            <li>Expira: 2026-05-30 21:30:00</li>
        </ul>
        <p><strong>Token JWT (Ejemplo):</strong></p>
        <div class="token-box">
            eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.test.token
        </div>
    </div>
    <div class="footer">
        <p>Email de prueba enviado el: {datetime.now().strftime('%d/%m/%Y %H:%M:%S')}</p>
        <p>&copy; 2026 Identity Manager</p>
    </div>
</body>
</html>
"""
        
        part1 = MIMEText(text_body, 'plain', 'utf-8')
        part2 = MIMEText(html_body, 'html', 'utf-8')
        
        message.attach(part1)
        message.attach(part2)
        
        print(f"   ✓ Email preparado")
        print(f"   - Destinatario: {recipient_email}")
        print(f"   - Asunto: {message['Subject']}")
        
        # 3. Enviar email
        print("\n3. Enviando email via SMTP...")
        context = ssl.create_default_context()
        
        with smtplib.SMTP(smtp_server, smtp_port) as server:
            print(f"   - Conectando a {smtp_server}:{smtp_port}...")
            
            if use_tls:
                print(f"   - Iniciando TLS...")
                server.starttls(context=context)
            
            print(f"   - Autenticando como {gmail_user}...")
            server.login(gmail_user, gmail_password)
            
            print(f"   - Enviando mensaje...")
            server.send_message(message)
        
        print(f"   ✓ Email enviado exitosamente!")
        print(f"\n{'=' * 60}")
        print("✅ PRUEBA COMPLETADA CON ÉXITO")
        print("=" * 60)
        print(f"\nRevisa tu bandeja de entrada: {recipient_email}")
        return True
        
    except Exception as e:
        print(f"\n   ✗ Error: {e}")
        print(f"\n{'=' * 60}")
        print("❌ PRUEBA FALLIDA CON EXCEPCIÓN")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    success = test_email_direct()
    sys.exit(0 if success else 1)
