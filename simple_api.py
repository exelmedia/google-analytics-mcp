#!/usr/bin/env python3
"""
Simple HTTP API for Google Analytics
Direct integration without MCP subprocess
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from typing import Optional, List
import json
import base64

# Function to setup credentials from Base64
def setup_credentials():
    """Setup Google credentials from Base64 environment variable"""
    try:
        credentials_base64 = os.environ.get('GOOGLE_CREDENTIALS_BASE64')
        if not credentials_base64:
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
            json.load(f)  # This will raise exception if invalid JSON
        
        return True, "Credentials successfully set up"
    except Exception as e:
        return False, f"Error setting up credentials: {str(e)}"

# Setup credentials at startup
CREDS_SUCCESS, CREDS_MESSAGE = setup_credentials()

# Import Google Analytics libraries
try:
    from google.analytics.admin_v1beta import AnalyticsAdminServiceClient
    from google.analytics.data_v1beta import BetaAnalyticsDataClient
    from google.analytics.data_v1beta.types import (
        RunReportRequest,
        RunRealtimeReportRequest,
        Dimension,
        Metric,
        DateRange
    )
    GA_AVAILABLE = True
except ImportError:
    GA_AVAILABLE = False

app = FastAPI(
    title="Google Analytics Simple API",
    description="Simple HTTP API for Google Analytics data",
    version="1.0.0"
)

# Enable CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ReportRequest(BaseModel):
    property_id: str
    start_date: str = "7daysAgo"
    end_date: str = "today"
    metrics: List[str] = ["sessions", "users"]
    dimensions: List[str] = ["country"]

@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "message": "Google Analytics Simple API",
        "version": "1.0.0",
        "status": "running",
        "ga_available": GA_AVAILABLE,
        "credentials_set": CREDS_SUCCESS,
        "credentials_message": CREDS_MESSAGE
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ga-simple-api",
        "google_analytics": GA_AVAILABLE
    }

@app.get("/test")
async def test_endpoint():
    """Test endpoint for debugging"""
    return {
        "message": "Test endpoint working!",
        "environment": {
            "GOOGLE_APPLICATION_CREDENTIALS": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")),
            "GOOGLE_PROJECT_ID": os.environ.get("GOOGLE_PROJECT_ID", "not_set"),
            "GOOGLE_CREDENTIALS_BASE64": bool(os.environ.get("GOOGLE_CREDENTIALS_BASE64")),
            "PORT": os.environ.get("PORT", "9000")
        }
    }

@app.get("/debug")
async def debug_endpoint():
    """Debug endpoint for credentials"""
    try:
        creds_path = '/app/credentials.json'
        file_exists = os.path.exists(creds_path)
        file_size = os.path.getsize(creds_path) if file_exists else 0
        
        # Try to read first few characters
        first_chars = ""
        if file_exists:
            try:
                with open(creds_path, 'r') as f:
                    first_chars = f.read(50)
            except:
                first_chars = "(read error)"
        
        return {
            "credentials_setup": {
                "success": CREDS_SUCCESS,
                "message": CREDS_MESSAGE
            },
            "file_status": {
                "exists": file_exists,
                "size": file_size,
                "first_chars": first_chars
            },
            "environment": {
                "GOOGLE_APPLICATION_CREDENTIALS": os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"),
                "GOOGLE_CREDENTIALS_BASE64_LENGTH": len(os.environ.get("GOOGLE_CREDENTIALS_BASE64", ""))
            }
        }
    except Exception as e:
        return {"error": str(e)}

@app.get("/accounts")
async def get_accounts():
    """Get account summaries"""
    if not GA_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google Analytics libraries not available")
    
    try:
        client = AnalyticsAdminServiceClient()
        accounts = list(client.list_accounts())
        
        result = []
        for account in accounts:
            result.append({
                "name": account.name,
                "display_name": account.display_name,
                "create_time": str(account.create_time),
                "update_time": str(account.update_time)
            })
        
        return {"accounts": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching accounts: {str(e)}")

@app.post("/report")
async def run_report(report: ReportRequest):
    """Run Google Analytics report"""
    if not GA_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google Analytics libraries not available")
    
    try:
        client = BetaAnalyticsDataClient()
        
        # Build request
        request = RunReportRequest(
            property=f"properties/{report.property_id}",
            dimensions=[Dimension(name=dim) for dim in report.dimensions],
            metrics=[Metric(name=metric) for metric in report.metrics],
            date_ranges=[DateRange(start_date=report.start_date, end_date=report.end_date)]
        )
        
        # Run report
        response = client.run_report(request=request)
        
        # Format response
        result = {
            "dimension_headers": [header.name for header in response.dimension_headers],
            "metric_headers": [header.name for header in response.metric_headers],
            "rows": []
        }
        
        for row in response.rows:
            formatted_row = {
                "dimensions": [value.value for value in row.dimension_values],
                "metrics": [value.value for value in row.metric_values]
            }
            result["rows"].append(formatted_row)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running report: {str(e)}")

@app.post("/realtime-report/{property_id}")
async def run_realtime_report(property_id: str):
    """Run real-time report"""
    if not GA_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google Analytics libraries not available")
    
    try:
        client = BetaAnalyticsDataClient()
        
        request = RunRealtimeReportRequest(
            property=f"properties/{property_id}",
            dimensions=[Dimension(name="country")],
            metrics=[Metric(name="activeUsers")]
        )
        
        response = client.run_realtime_report(request=request)
        
        result = {
            "dimension_headers": [header.name for header in response.dimension_headers],
            "metric_headers": [header.name for header in response.metric_headers],
            "rows": []
        }
        
        for row in response.rows:
            formatted_row = {
                "dimensions": [value.value for value in row.dimension_values],
                "metrics": [value.value for value in row.metric_values]
            }
            result["rows"].append(formatted_row)
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error running realtime report: {str(e)}")

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )