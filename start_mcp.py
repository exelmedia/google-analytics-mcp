#!/usr/bin/env python3
"""
Start script for Google Analytics MCP Server with working credentials setup
"""
import os
import json
import base64
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# DEBUG: Print all environment variables at startup
print("=== DEBUG: MCP Server Environment Variables ===")
print(f"GOOGLE_PROJECT_ID: {os.environ.get('GOOGLE_PROJECT_ID', 'NOT_SET')}")
print(f"GOOGLE_CREDENTIALS_BASE64 length: {len(os.environ.get('GOOGLE_CREDENTIALS_BASE64', ''))}")
print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'NOT_SET')}")
print("===============================================")

def setup_credentials():
    """Setup Google credentials from Base64 environment variable"""
    print("=== DEBUG: setup_credentials() called ===")
    try:
        credentials_base64 = os.environ.get('GOOGLE_CREDENTIALS_BASE64')
        print(f"credentials_base64 length: {len(credentials_base64) if credentials_base64 else 0}")
        if not credentials_base64:
            print("ERROR: GOOGLE_CREDENTIALS_BASE64 not found in environment")
            return False, "GOOGLE_CREDENTIALS_BASE64 not set"
        
        # Create /app directory if it doesn't exist
        os.makedirs('/app', exist_ok=True)
        
        # Decode Base64 and write to file
        credentials_data = base64.b64decode(credentials_base64)
        credentials_path = '/app/credentials.json'
        
        with open(credentials_path, 'wb') as f:
            f.write(credentials_data)
        
        # Set environment variable for Google client libraries
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = credentials_path
        
        # Verify the JSON is valid
        with open(credentials_path, 'r') as f:
            creds_data = json.load(f)
            print(f"SUCCESS: Credentials loaded for {creds_data.get('client_email', 'unknown')}")
        
        print("SUCCESS: Credentials file created and validated")
        return True, "Credentials successfully set up"
    except Exception as e:
        print(f"ERROR in setup_credentials: {str(e)}")
        return False, f"Error setting up credentials: {str(e)}"

# Setup credentials at startup
print("=== DEBUG: Calling setup_credentials ===")
CREDS_SUCCESS, CREDS_MESSAGE = setup_credentials()
print(f"=== DEBUG: setup_credentials result: {CREDS_SUCCESS}, {CREDS_MESSAGE} ===")

if not CREDS_SUCCESS:
    print("ERROR: Cannot start MCP server without valid credentials")
    exit(1)

# Now start the original Google Analytics MCP Server
print("=== Starting Original Google Analytics MCP Server ===")
try:
    print("Starting MCP server...")
    from analytics_mcp.server import run_server
    run_server()
except ImportError as e:
    print(f"IMPORT ERROR: {e}")
    print("Available files:")
    print(os.listdir('.'))
    
    # Try alternative - run via command
    print("Trying to run via command...")
    import subprocess
    import sys
    subprocess.run([sys.executable, "-c", "from analytics_mcp.server import run_server; run_server()"])
except Exception as e:
    print(f"ERROR: MCP Server crashed: {e}")
    import traceback
    traceback.print_exc()
    exit(1)
