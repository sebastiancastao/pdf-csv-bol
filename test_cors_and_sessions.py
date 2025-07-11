#!/usr/bin/env python3
"""
Test script to verify CORS headers and session management fixes.
"""

import requests
import json
import time

def test_cors_and_sessions():
    """Test CORS headers and session management functionality."""
    
    base_url = "http://localhost:5000"
    
    print("🧪 Testing CORS Headers and Session Management")
    print("=" * 60)
    
    # Test 1: CORS preflight with cache-control header
    print("\n1. Testing CORS preflight with cache-control header...")
    try:
        headers = {
            'Access-Control-Request-Method': 'GET',
            'Access-Control-Request-Headers': 'Content-Type,Cache-Control,Pragma',
            'Origin': 'http://localhost:8080'
        }
        response = requests.options(f"{base_url}/", headers=headers)
        print(f"   Status: {response.status_code}")
        
        cors_headers = {
            'Access-Control-Allow-Origin': response.headers.get('Access-Control-Allow-Origin'),
            'Access-Control-Allow-Headers': response.headers.get('Access-Control-Allow-Headers'),
            'Access-Control-Allow-Methods': response.headers.get('Access-Control-Allow-Methods')
        }
        
        print(f"   CORS Headers:")
        for header, value in cors_headers.items():
            print(f"     {header}: {value}")
            
        # Check if cache-control is allowed
        allowed_headers = response.headers.get('Access-Control-Allow-Headers', '')
        if 'cache-control' in allowed_headers.lower():
            print("   ✅ Cache-Control header is allowed")
        else:
            print("   ❌ Cache-Control header is NOT allowed")
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    # Test 2: Create new session explicitly
    print("\n2. Testing new session creation...")
    try:
        response = requests.post(f"{base_url}/new-session")
        print(f"   Status: {response.status_code}")
        data = response.json()
        print(f"   New session ID: {data.get('session_id')}")
        
        if data.get('status') == 'success':
            print("   ✅ New session created successfully")
            new_session_id = data.get('session_id')
        else:
            print("   ❌ Failed to create new session")
            new_session_id = None
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")
        new_session_id = None

    # Test 3: Base URL with _action=new_session parameter
    print("\n3. Testing base URL with _action=new_session...")
    try:
        timestamp = int(time.time() * 1000)
        session_id = f"session_{timestamp}_test123"
        
        params = {
            '_t': timestamp,
            '_sid': session_id,
            '_action': 'new_session',
            'format': 'json'  # Request JSON response
        }
        
        response = requests.get(f"{base_url}/", params=params)
        print(f"   Status: {response.status_code}")
        
        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            print(f"   Response session ID: {data.get('session_id')}")
            print(f"   Status: {data.get('status')}")
            
            if data.get('session_id') != session_id:
                print("   ✅ New session created (different from requested ID)")
            else:
                print("   ⚠️  Session ID matches requested (might be reusing)")
        else:
            print("   ⚠️  HTML response received instead of JSON")
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    # Test 4: Check status with session parameters
    print("\n4. Testing status endpoint with session parameters...")
    try:
        if new_session_id:
            response = requests.get(f"{base_url}/status?_sid={new_session_id}")
            print(f"   Status: {response.status_code}")
            data = response.json()
            
            print(f"   Session ID: {data.get('session_id')}")
            print(f"   Session exists: {data.get('session_exists')}")
            print(f"   Query params: {data.get('query_params')}")
            
            if data.get('session_id') == new_session_id:
                print("   ✅ Session ID correctly retrieved from parameters")
            else:
                print("   ❌ Session ID mismatch")
        else:
            print("   ⚠️  Skipping (no session ID from previous test)")
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    # Test 5: Debug sessions endpoint
    print("\n5. Testing debug sessions endpoint...")
    try:
        response = requests.get(f"{base_url}/debug-sessions")
        print(f"   Status: {response.status_code}")
        data = response.json()
        
        print(f"   Current session: {data.get('current_session_id')}")
        print(f"   Total sessions: {data.get('total_sessions')}")
        
        sessions = data.get('sessions', [])
        for session in sessions[:3]:  # Show first 3 sessions
            print(f"     - {session.get('session_id')}: {len(session.get('files', []))} files")
            
        print("   ✅ Debug endpoint working")
        
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    # Test 6: External app simulation
    print("\n6. Simulating external app request with cache-control...")
    try:
        headers = {
            'Cache-Control': 'no-cache',
            'Pragma': 'no-cache',
            'Accept': 'application/json',
            'Origin': 'http://localhost:8080'
        }
        
        timestamp = int(time.time() * 1000)
        session_id = f"session_{timestamp}_external"
        
        params = {
            '_t': timestamp,
            '_sid': session_id,
            '_action': 'new_session'
        }
        
        response = requests.get(f"{base_url}/", params=params, headers=headers)
        print(f"   Status: {response.status_code}")
        
        # Check CORS headers in response
        cors_origin = response.headers.get('Access-Control-Allow-Origin')
        if cors_origin == '*':
            print("   ✅ CORS Origin header correctly set")
        else:
            print(f"   ❌ CORS Origin header: {cors_origin}")
            
        if response.headers.get('content-type', '').startswith('application/json'):
            data = response.json()
            print(f"   ✅ JSON response received")
            print(f"   Session ID: {data.get('session_id')}")
        else:
            print("   ⚠️  Non-JSON response received")
            
    except Exception as e:
        print(f"   ❌ FAIL: {e}")

    print("\n" + "=" * 60)
    print("🏁 CORS and Session Management Testing Complete!")
    
    print("\n📋 Quick Test Summary:")
    print("- Test CORS preflight with cache-control")
    print("- Test new session creation endpoint")
    print("- Test base URL with _action=new_session")
    print("- Test status endpoint with session params")
    print("- Test debug sessions endpoint")
    print("- Test external app simulation")
    
    print("\n💡 Next Steps:")
    print("- If tests pass, your external app should work")
    print("- Use /new-session endpoint for explicit session creation")
    print("- Use _action=new_session parameter to force new sessions")
    print("- Check /debug-sessions for session troubleshooting")

if __name__ == "__main__":
    test_cors_and_sessions() 