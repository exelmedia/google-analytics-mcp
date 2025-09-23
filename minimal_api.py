#!/usr/bin/env python3
"""
Minimal FastAPI server for testing
"""

from fastapi import FastAPI
import uvicorn
import os

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Hello World from FastAPI!", "status": "working"}

@app.get("/health")
def health():
    return {"status": "healthy"}

@app.get("/env")
def env():
    return {
        "PORT": os.environ.get("PORT", "not_set"),
        "PWD": os.environ.get("PWD", "not_set"),
        "GOOGLE_PROJECT_ID": os.environ.get("GOOGLE_PROJECT_ID", "not_set"),
        "GOOGLE_APPLICATION_CREDENTIALS": bool(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"))
    }

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 9000))
    print(f"Starting server on port {port}")
    uvicorn.run(app, host="0.0.0.0", port=port)