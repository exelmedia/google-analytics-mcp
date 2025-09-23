#!/usr/bin/env python3
"""
Full MCP Google Analytics API
Complete implementation of all MCP tools as HTTP endpoints
"""

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel
import uvicorn
import os
from typing import Optional, List
import json
import base64
from dotenv import load_dotenv

# Try to load from .env file (created during build if secrets exist)
load_dotenv()

# DEBUG: Print all environment variables at startup
print("=== DEBUG: Environment Variables ===")
print(f"GOOGLE_PROJECT_ID: {os.environ.get('GOOGLE_PROJECT_ID', 'NOT_SET')}")
print(f"GOOGLE_CREDENTIALS_BASE64 length: {len(os.environ.get('GOOGLE_CREDENTIALS_BASE64', ''))}")
print(f"GOOGLE_APPLICATION_CREDENTIALS: {os.environ.get('GOOGLE_APPLICATION_CREDENTIALS', 'NOT_SET')}")
print(f"PORT: {os.environ.get('PORT', 'NOT_SET')}")
print("======================================")

# Function to setup credentials from Base64
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
            json.load(f)  # This will raise exception if invalid JSON
        
        print("SUCCESS: Credentials file created and validated")
        return True, "Credentials successfully set up"
    except Exception as e:
        print(f"ERROR in setup_credentials: {str(e)}")
        return False, f"Error setting up credentials: {str(e)}"

# Setup credentials at startup
print("=== DEBUG: Calling setup_credentials ===")
CREDS_SUCCESS, CREDS_MESSAGE = setup_credentials()
print(f"=== DEBUG: setup_credentials result: {CREDS_SUCCESS}, {CREDS_MESSAGE} ===")

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
    from google.analytics.admin_v1beta.types import (
        GetPropertyRequest,
        ListGoogleAdsLinksRequest,
        ListCustomDimensionsRequest,
        ListCustomMetricsRequest
    )
    GA_AVAILABLE = True
except ImportError as e:
    print(f"Import error: {e}")
    GA_AVAILABLE = False

app = FastAPI(
    title="Google Analytics Full MCP API",
    description="Complete HTTP API for all Google Analytics MCP tools",
    version="2.0.0"
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
        "message": "Google Analytics Full MCP API",
        "version": "2.0.0",
        "status": "running",
        "ga_available": GA_AVAILABLE,
        "credentials_set": CREDS_SUCCESS,
        "credentials_message": CREDS_MESSAGE,
        "mcp_tools": [
            "get_account_summaries",
            "get_property_details", 
            "list_google_ads_links",
            "run_report",
            "run_realtime_report",
            "get_custom_dimensions_and_metrics"
        ]
    }

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "service": "ga-full-mcp-api",
        "google_analytics": GA_AVAILABLE
    }

# ===== MCP TOOL 1: get_account_summaries =====
@app.get("/accounts")
async def get_account_summaries():
    """Get account summaries - MCP Tool: get_account_summaries"""
    if not GA_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google Analytics libraries not available")
    
    try:
        client = AnalyticsAdminServiceClient()
        accounts = list(client.list_accounts())
        
        result = []
        for account in accounts:
            # Also get properties for each account
            properties = []
            try:
                props = list(client.list_properties(parent=account.name))
                for prop in props:
                    properties.append({
                        "name": prop.name,
                        "display_name": prop.display_name,
                        "property_id": prop.name.split('/')[-1],
                        "create_time": str(prop.create_time) if prop.create_time else None,
                        "website_url": getattr(prop, 'website_url', ''),
                        "time_zone": getattr(prop, 'time_zone', ''),
                        "currency_code": getattr(prop, 'currency_code', '')
                    })
            except Exception as e:
                print(f"Error fetching properties for account {account.name}: {e}")
                
            result.append({
                "name": account.name,
                "display_name": account.display_name,
                "create_time": str(account.create_time) if account.create_time else None,
                "update_time": str(account.update_time) if account.update_time else None,
                "account_type": getattr(account, 'account_type', 'STANDARD'),
                "properties": properties
            })
        
        return {"accounts": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching accounts: {str(e)}")

# ===== MCP TOOL 2: get_property_details =====
@app.get("/property/{property_id}")
async def get_property_details(property_id: str):
    """Get property details - MCP Tool: get_property_details"""
    if not GA_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google Analytics libraries not available")
    
    try:
        client = AnalyticsAdminServiceClient()
        
        # Property name format: properties/{property_id}
        property_name = f"properties/{property_id}"
        
        request = GetPropertyRequest(name=property_name)
        property_details = client.get_property(request=request)
        
        result = {
            "name": property_details.name,
            "display_name": property_details.display_name,
            "property_id": property_id,
            "create_time": str(property_details.create_time) if property_details.create_time else None,
            "update_time": str(property_details.update_time) if property_details.update_time else None,
            "website_url": getattr(property_details, 'website_url', ''),
            "time_zone": getattr(property_details, 'time_zone', ''),
            "currency_code": getattr(property_details, 'currency_code', ''),
            "industry_category": getattr(property_details, 'industry_category', None),
            "service_level": getattr(property_details, 'service_level', None),
            "property_type": getattr(property_details, 'property_type', None)
        }
        
        return result
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching property details: {str(e)}")

# ===== MCP TOOL 3: list_google_ads_links =====
@app.get("/ads-links/{property_id}")
async def list_google_ads_links(property_id: str):
    """List Google Ads links - MCP Tool: list_google_ads_links"""
    if not GA_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google Analytics libraries not available")
    
    try:
        client = AnalyticsAdminServiceClient()
        
        # Property name format: properties/{property_id}
        property_name = f"properties/{property_id}"
        
        request = ListGoogleAdsLinksRequest(parent=property_name)
        ads_links = list(client.list_google_ads_links(request=request))
        
        result = []
        for link in ads_links:
            result.append({
                "name": link.name,
                "display_name": getattr(link, 'display_name', ''),
                "customer_id": getattr(link, 'customer_id', ''),
                "ads_personalization_enabled": getattr(link, 'ads_personalization_enabled', False),
                "create_time": str(link.create_time) if hasattr(link, 'create_time') and link.create_time else None,
                "update_time": str(link.update_time) if hasattr(link, 'update_time') and link.update_time else None,
                "link_id": link.name.split('/')[-1] if link.name else None
            })
        
        return {"links": result}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching Google Ads links: {str(e)}")

# ===== MCP TOOL 4: run_report =====
@app.post("/report")
async def run_report(report: ReportRequest):
    """Run Google Analytics report - MCP Tool: run_report"""
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

# ===== MCP TOOL 5: run_realtime_report =====
@app.post("/realtime-report/{property_id}")
async def run_realtime_report(property_id: str):
    """Run real-time report - MCP Tool: run_realtime_report"""
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

# ===== MCP TOOL 6: get_custom_dimensions_and_metrics =====
@app.get("/custom-dimensions-metrics/{property_id}")
async def get_custom_dimensions_and_metrics(property_id: str):
    """Get custom dimensions and metrics - MCP Tool: get_custom_dimensions_and_metrics"""
    if not GA_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google Analytics libraries not available")
    
    try:
        client = AnalyticsAdminServiceClient()
        
        # Property name format: properties/{property_id}
        property_name = f"properties/{property_id}"
        
        # Get custom dimensions
        custom_dimensions = []
        try:
            dims_request = ListCustomDimensionsRequest(parent=property_name)
            dimensions = list(client.list_custom_dimensions(request=dims_request))
            
            for dimension in dimensions:
                custom_dimensions.append({
                    "name": dimension.name,
                    "display_name": dimension.display_name,
                    "parameter_name": dimension.parameter_name,
                    "dimension_id": dimension.name.split('/')[-1] if dimension.name else None,
                    "scope": getattr(dimension, 'scope', None),
                    "description": getattr(dimension, 'description', ''),
                    "disallow_ads_personalization": getattr(dimension, 'disallow_ads_personalization', False)
                })
        except Exception as e:
            print(f"Error fetching custom dimensions: {e}")
        
        # Get custom metrics
        custom_metrics = []
        try:
            metrics_request = ListCustomMetricsRequest(parent=property_name)
            metrics = list(client.list_custom_metrics(request=metrics_request))
            
            for metric in metrics:
                custom_metrics.append({
                    "name": metric.name,
                    "display_name": metric.display_name,
                    "parameter_name": metric.parameter_name,
                    "metric_id": metric.name.split('/')[-1] if metric.name else None,
                    "measurement_unit": getattr(metric, 'measurement_unit', None),
                    "scope": getattr(metric, 'scope', None),
                    "description": getattr(metric, 'description', ''),
                    "restricted_metric_type": getattr(metric, 'restricted_metric_type', None)
                })
        except Exception as e:
            print(f"Error fetching custom metrics: {e}")
        
        return {
            "property_id": property_id,
            "custom_dimensions": custom_dimensions,
            "custom_metrics": custom_metrics
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching custom dimensions and metrics: {str(e)}")

# ===== ADDITIONAL ENDPOINTS =====
@app.get("/properties")
async def list_all_properties():
    """List all available properties across all accounts - MCP Tool: list_properties"""
    if not GA_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google Analytics libraries not available")
    
    try:
        client = AnalyticsAdminServiceClient()
        
        # Get all accounts first
        accounts = list(client.list_accounts())
        
        all_properties = []
        for account in accounts:
            try:
                # List properties for each account
                properties = list(client.list_properties(parent=account.name))
                
                for prop in properties:
                    property_id = prop.name.split('/')[-1] if prop.name else 'unknown'
                    
                    all_properties.append({
                        "property_id": property_id,
                        "name": prop.name,
                        "display_name": prop.display_name,
                        "account_name": account.display_name,
                        "account_id": account.name,
                        "website_url": getattr(prop, 'website_url', ''),
                        "time_zone": getattr(prop, 'time_zone', ''),
                        "currency_code": getattr(prop, 'currency_code', ''),
                        "create_time": str(prop.create_time) if hasattr(prop, 'create_time') and prop.create_time else None,
                        "property_type": str(getattr(prop, 'property_type', 'STANDARD'))
                    })
                    
            except Exception as e:
                print(f"Error fetching properties for account {account.name}: {e}")
                continue
        
        return {
            "properties": all_properties,
            "total_count": len(all_properties)
        }
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error fetching properties: {str(e)}")

@app.get("/properties/summary")
async def get_properties_summary():
    """Quick summary of available properties with just ID and name"""
    if not GA_AVAILABLE:
        raise HTTPException(status_code=500, detail="Google Analytics libraries not available")
    
    try:
        client = AnalyticsAdminServiceClient()
        accounts = list(client.list_accounts())
        
        summary = []
        for account in accounts:
            try:
                properties = list(client.list_properties(parent=account.name))
                for prop in properties:
                    property_id = prop.name.split('/')[-1] if prop.name else 'unknown'
                    summary.append({
                        "property_id": property_id,
                        "display_name": prop.display_name,
                        "account": account.display_name
                    })
            except Exception as e:
                continue
                
        return {"properties": summary}
        
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error: {str(e)}")

# ===== DEBUG ENDPOINTS =====
@app.get("/test")
async def test_endpoint():
    """Test endpoint for debugging"""
    return {
        "message": "Full MCP API Test endpoint working!",
        "environment": {
            "GOOGLE_APPLICATION_CREDENTIALS": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")),
            "GOOGLE_PROJECT_ID": os.environ.get("GOOGLE_PROJECT_ID", "not_set"),
            "GOOGLE_CREDENTIALS_BASE64": bool(os.environ.get("GOOGLE_CREDENTIALS_BASE64")),
            "PORT": os.environ.get("PORT", "9000")
        },
        "available_endpoints": [
            "GET /accounts - get_account_summaries",
            "GET /property/{property_id} - get_property_details", 
            "GET /ads-links/{property_id} - list_google_ads_links",
            "POST /report - run_report",
            "POST /realtime-report/{property_id} - run_realtime_report",
            "GET /custom-dimensions-metrics/{property_id} - get_custom_dimensions_and_metrics",
            "GET /properties - list_all_properties",
            "GET /properties/summary - get_properties_summary"
        ]
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
            },
            "mcp_tools_status": {
                "ga_libraries_available": GA_AVAILABLE,
                "credentials_configured": CREDS_SUCCESS,
                "all_tools_ready": GA_AVAILABLE and CREDS_SUCCESS
            }
        }
    except Exception as e:
        return {"error": str(e)}

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    uvicorn.run(
        app, 
        host="0.0.0.0", 
        port=port,
        log_level="info"
    )