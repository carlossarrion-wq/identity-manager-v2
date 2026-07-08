"""
Local Development Server for Identity Manager API
Wraps the Lambda function for local development
"""
import json
import os
import sys
from pathlib import Path

# Add the Lambda directory to Python path
lambda_dir = Path(__file__).parent / "lambdas" / "identity-mgmt-api"
sys.path.insert(0, str(lambda_dir))

from fastapi import FastAPI, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
import uvicorn

# Import the Lambda handler
from lambda_function import lambda_handler

app = FastAPI(title="Identity Manager API - Local Development")

# Enable CORS for frontend
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class MockLambdaContext:
    """Mock Lambda context for local development"""
    def __init__(self):
        self.aws_request_id = "local-dev-request"
        self.function_name = "identity-mgmt-dev-api-lmbd"
        self.memory_limit_in_mb = "512"
        self.invoked_function_arn = "arn:aws:lambda:local:000000000000:function:local-dev"

@app.post("/{path:path}")
@app.get("/{path:path}")
@app.put("/{path:path}")
@app.delete("/{path:path}")
async def proxy_to_lambda(request: Request, path: str):
    """Proxy all requests to the Lambda handler"""
    
    # Build the Lambda event from FastAPI request
    body = None
    if request.method in ["POST", "PUT", "PATCH"]:
        try:
            body = await request.json()
        except:
            body = {}
    
    event = {
        "httpMethod": request.method,
        "path": f"/{path}",
        "pathParameters": {"proxy": path},
        "queryStringParameters": dict(request.query_params) if request.query_params else None,
        "headers": dict(request.headers),
        "body": json.dumps(body) if body else None,
        "requestContext": {
            "requestId": "local-dev-request",
            "authorizer": {
                "claims": {
                    "sub": "local-dev-user",
                    "email": "admin@test.com",
                    "cognito:groups": ["admin"],
                    "cognito:username": "admin"
                }
            }
        }
    }
    
    # Call the Lambda handler
    context = MockLambdaContext()
    try:
        response = lambda_handler(event, context)
        
        # Extract status code and body
        status_code = response.get("statusCode", 200)
        body = response.get("body", "{}")
        headers = response.get("headers", {})
        
        # Parse body if it's a string
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except:
                pass
        
        return JSONResponse(content=body, status_code=status_code, headers=headers)
    except Exception as e:
        return JSONResponse(
            content={"error": str(e), "message": "Internal server error"},
            status_code=500
        )

@app.get("/")
async def root():
    """Health check endpoint"""
    return {
        "service": "Identity Manager API",
        "status": "running",
        "environment": "local-development"
    }

@app.get("/health")
async def health():
    """Health check endpoint"""
    return {"status": "healthy"}

@app.post("/api/login")
async def login(request: Request):
    """Mock login endpoint for local development"""
    try:
        body = await request.json()
        email = body.get("email")
        
        # In local mode, accept any login with admin@test.com
        if email == "admin@test.com":
            # Return mock user data with token
            return JSONResponse(content={
                "success": True,
                "user": {
                    "id": "test-cognito-admin",
                    "email": "admin@test.com",
                    "username": "admin",
                    "groups": ["admin-group"]
                },
                "message": "Login successful (local development mode)"
            })
        else:
            return JSONResponse(
                content={"success": False, "message": "Invalid credentials"},
                status_code=401
            )
    except Exception as e:
        return JSONResponse(
            content={"success": False, "message": str(e)},
            status_code=500
        )

if __name__ == "__main__":
    port = int(os.getenv("PORT", "8000"))
    print(f"\n{'='*60}")
    print(f"🚀 Identity Manager API - Local Development Server")
    print(f"{'='*60}")
    print(f"Server running on: http://localhost:{port}")
    print(f"Health check: http://localhost:{port}/health")
    print(f"{'='*60}\n")
    
    uvicorn.run(app, host="0.0.0.0", port=port, log_level="info")
