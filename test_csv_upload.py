#!/usr/bin/env python3
"""
Test script to verify the enhanced CSV upload endpoint.
"""

import requests
import json
import base64
import time
import io

def test_csv_upload_methods():
    """Test different CSV upload methods."""
    
    base_url = "http://localhost:5000"
    
    # Sample CSV data
    sample_csv = """Company Name,Ship To Name,Ship To Address,BOL#,Delivery Date,Pallet Count,Cube
Test Company,Test Location,123 Test St,BOL123,2024-01-15,5,100.5
Another Company,Another Location,456 Main St,BOL456,2024-01-16,3,75.2"""
    
    print("🧪 Testing Enhanced CSV Upload Endpoint")
    print("=" * 60)
    
    # Test 1: File upload (multipart/form-data)
    print("\n1. Testing file upload (multipart/form-data)...")
    try:
        # Create a timestamp for unique session
        timestamp = int(time.time() * 1000)
        session_id = f"test_session_{timestamp}_file"
        
        files = {
            'file': ('test_data.csv', sample_csv, 'text/csv')
        }
        
        params = {
            '_sid': session_id,
            '_action': 'new_session'
        }
        
        response = requests.post(f"{base_url}/upload-csv", files=files, params=params)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data}")
            print("   ✅ File upload successful")
        else:
            print(f"   ❌ File upload failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    # Test 2: JSON with csv_data
    print("\n2. Testing JSON with csv_data...")
    try:
        timestamp = int(time.time() * 1000)
        session_id = f"test_session_{timestamp}_json"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            'csv_data': sample_csv,
            'filename': 'test_data.csv'
        }
        
        params = {
            '_sid': session_id,
            '_action': 'new_session'
        }
        
        response = requests.post(f"{base_url}/upload-csv", 
                               json=data, 
                               headers=headers, 
                               params=params)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data}")
            print("   ✅ JSON csv_data upload successful")
        else:
            print(f"   ❌ JSON csv_data upload failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    # Test 3: JSON with base64 file_data
    print("\n3. Testing JSON with base64 file_data...")
    try:
        timestamp = int(time.time() * 1000)
        session_id = f"test_session_{timestamp}_base64"
        
        # Encode CSV as base64
        csv_base64 = base64.b64encode(sample_csv.encode('utf-8')).decode('utf-8')
        data_url = f"data:text/csv;base64,{csv_base64}"
        
        headers = {
            'Content-Type': 'application/json'
        }
        
        data = {
            'file_data': data_url,
            'filename': 'test_data.csv'
        }
        
        params = {
            '_sid': session_id,
            '_action': 'new_session'
        }
        
        response = requests.post(f"{base_url}/upload-csv", 
                               json=data, 
                               headers=headers, 
                               params=params)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data}")
            print("   ✅ JSON base64 upload successful")
        else:
            print(f"   ❌ JSON base64 upload failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    # Test 4: Form data with csv_data
    print("\n4. Testing form data with csv_data...")
    try:
        timestamp = int(time.time() * 1000)
        session_id = f"test_session_{timestamp}_form"
        
        data = {
            'csv_data': sample_csv,
            'filename': 'test_data.csv'
        }
        
        params = {
            '_sid': session_id,
            '_action': 'new_session'
        }
        
        response = requests.post(f"{base_url}/upload-csv", 
                               data=data, 
                               params=params)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data}")
            print("   ✅ Form data upload successful")
        else:
            print(f"   ❌ Form data upload failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    # Test 5: Raw CSV data with text/csv content-type
    print("\n5. Testing raw CSV data with text/csv content-type...")
    try:
        timestamp = int(time.time() * 1000)
        session_id = f"test_session_{timestamp}_raw"
        
        headers = {
            'Content-Type': 'text/csv'
        }
        
        params = {
            '_sid': session_id,
            '_action': 'new_session'
        }
        
        response = requests.post(f"{base_url}/upload-csv", 
                               data=sample_csv, 
                               headers=headers, 
                               params=params)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Response: {data}")
            print("   ✅ Raw CSV upload successful")
        else:
            print(f"   ❌ Raw CSV upload failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    # Test 6: Debug request to see what external app is sending
    print("\n6. Testing debug request endpoint...")
    try:
        # Simulate what the external app might be sending
        headers = {
            'Content-Type': 'application/json',
            'Origin': 'http://localhost:8080'
        }
        
        data = {
            'csv_data': sample_csv,
            'filename': 'external_app_data.csv',
            'source': 'external_app'
        }
        
        params = {
            '_t': int(time.time() * 1000),
            '_sid': 'external_session_debug',
            '_action': 'new_session'
        }
        
        response = requests.post(f"{base_url}/debug-request", 
                               json=data, 
                               headers=headers, 
                               params=params)
        print(f"   Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            print(f"   Debug info captured:")
            print(f"     Method: {data['request_info']['method']}")
            print(f"     Content-Type: {data['request_info']['content_type']}")
            print(f"     Has JSON: {data['request_info']['is_json']}")
            print(f"     Query params: {data['request_info']['query_params']}")
            print("   ✅ Debug endpoint working")
        else:
            print(f"   ❌ Debug endpoint failed: {response.text}")
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    print("\n" + "=" * 60)
    print("🏁 CSV Upload Testing Complete!")
    
    print("\n📋 Supported CSV Upload Methods:")
    print("1. File upload (multipart/form-data)")
    print("2. JSON with csv_data field")
    print("3. JSON with base64 file_data field")
    print("4. Form data with csv_data field")
    print("5. Raw CSV with text/csv content-type")
    
    print("\n💡 For External Apps:")
    print("- Use JSON format with 'csv_data' field for simplest integration")
    print("- Include session parameters: _sid, _action=new_session")
    print("- Use /debug-request endpoint to troubleshoot data format issues")

if __name__ == "__main__":
    test_csv_upload_methods() 