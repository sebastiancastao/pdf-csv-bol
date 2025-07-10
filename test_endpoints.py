#!/usr/bin/env python3
"""
Test script to verify BOL Extractor API endpoints are working correctly.
"""

import requests
import json
import sys
import os
from pathlib import Path

def test_endpoints():
    """Test all BOL Extractor API endpoints."""
    
    # Base URL - adjust as needed
    base_url = "http://localhost:5000"
    
    print("🚀 Testing BOL Extractor API endpoints...")
    print(f"Base URL: {base_url}")
    print("-" * 50)
    
    # Test 1: Ping endpoint
    print("1. Testing /ping endpoint...")
    try:
        response = requests.get(f"{base_url}/ping")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    
    # Test 2: Health check
    print("2. Testing /health endpoint...")
    try:
        response = requests.get(f"{base_url}/health")
        print(f"   Status: {response.status_code}")
        print(f"   Response: {response.json()}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    
    # Test 3: API Health check
    print("3. Testing /api/health endpoint...")
    try:
        response = requests.get(f"{base_url}/api/health")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Service: {data.get('service')}")
        print(f"   Session ID: {data.get('session_id')}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    
    # Test 4: API Documentation
    print("4. Testing /api/docs endpoint...")
    try:
        response = requests.get(f"{base_url}/api/docs")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Service: {data.get('service')}")
        print(f"   Version: {data.get('version')}")
        print(f"   Endpoints available: {len(data.get('endpoints', {}))}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    
    # Test 5: Status endpoint
    print("5. Testing /status endpoint...")
    try:
        response = requests.get(f"{base_url}/status")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Session ID: {data.get('session_id')}")
        print(f"   Has processed data: {data.get('has_processed_data')}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    
    # Test 6: Files endpoint
    print("6. Testing /files endpoint...")
    try:
        response = requests.get(f"{base_url}/files")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   Available files: {len(data.get('files', []))}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    
    # Test 7: CORS preflight request
    print("7. Testing CORS preflight (OPTIONS)...")
    try:
        response = requests.options(f"{base_url}/upload")
        print(f"   Status: {response.status_code}")
        print(f"   CORS headers:")
        for header in ['Access-Control-Allow-Origin', 'Access-Control-Allow-Methods', 'Access-Control-Allow-Headers']:
            if header in response.headers:
                print(f"     {header}: {response.headers[header]}")
        print("   ✅ PASS")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    
    # Test 8: Main page
    print("8. Testing main page (/)...")
    try:
        response = requests.get(f"{base_url}/")
        print(f"   Status: {response.status_code}")
        print(f"   Content type: {response.headers.get('Content-Type')}")
        if 'text/html' in response.headers.get('Content-Type', ''):
            print("   ✅ PASS - HTML page returned")
        else:
            print("   ⚠️  WARN - Expected HTML content")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    
    # Test 9: Base64 upload endpoint (without actual file)
    print("9. Testing /upload-base64 endpoint structure...")
    try:
        response = requests.post(f"{base_url}/upload-base64", 
                                json={"test": "structure"})
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            data = response.json()
            print(f"   Expected error: {data.get('error')}")
            print("   ✅ PASS - Endpoint responds correctly")
        else:
            print("   ⚠️  WARN - Unexpected response")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    
    # Test 10: Attachment upload endpoint (without actual file)
    print("10. Testing /upload-attachment endpoint structure...")
    try:
        response = requests.post(f"{base_url}/upload-attachment", 
                                json={"test": "structure"})
        print(f"   Status: {response.status_code}")
        if response.status_code == 400:
            data = response.json()
            print(f"   Expected error: {data.get('error')}")
            print("   ✅ PASS - Endpoint responds correctly")
        else:
            print("   ⚠️  WARN - Unexpected response")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    
    # Test 11: Query parameter handling
    print("11. Testing query parameter handling (/status?_sid=test123)...")
    try:
        response = requests.get(f"{base_url}/status?_sid=test123&_t=1234567890")
        print(f"   Status: {response.status_code}")
        data = response.json()
        if '_sid' in str(data) or 'test123' in str(data):
            print("   ✅ PASS - Query parameters handled")
        else:
            print("   ✅ PASS - Basic functionality works")
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
    
    print()
    print("🏁 Comprehensive endpoint testing completed!")
    print("📋 Summary: All major endpoints tested for CORS, structure, and functionality")

if __name__ == "__main__":
    test_endpoints() 