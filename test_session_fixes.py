#!/usr/bin/env python3
"""
Test script to verify session management fixes for the BOL processing system.
This script tests the session isolation, external session handling, and workflow integrity.
"""

import requests
import json
import time
import threading
from concurrent.futures import ThreadPoolExecutor, as_completed

# Test configuration
BASE_URL = "http://localhost:8080"  # Updated port
SESSION_TEST_ID_1 = "test_session_001"
SESSION_TEST_ID_2 = "test_session_002"

def test_session_isolation():
    """Test that different sessions are properly isolated."""
    print("🧪 Testing session isolation...")
    
    try:
        # Create two different sessions
        session1_resp = requests.post(f"{BASE_URL}/new-session", params={"_sid": SESSION_TEST_ID_1})
        session2_resp = requests.post(f"{BASE_URL}/new-session", params={"_sid": SESSION_TEST_ID_2})
        
        if session1_resp.status_code == 200 and session2_resp.status_code == 200:
            session1_data = session1_resp.json()
            session2_data = session2_resp.json()
            
            print(f"✅ Session 1 created: {session1_data['session_id']}")
            print(f"✅ Session 2 created: {session2_data['session_id']}")
            
            # Verify they are different
            if session1_data['session_id'] != session2_data['session_id']:
                print("✅ Sessions are properly isolated")
                return True
            else:
                print("❌ Sessions are not isolated")
                return False
        else:
            print(f"❌ Failed to create sessions: {session1_resp.status_code}, {session2_resp.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Session isolation test error: {str(e)}")
        return False

def test_external_session_handling():
    """Test external session ID handling."""
    print("🧪 Testing external session handling...")
    
    try:
        # Test session creation with specific ID
        test_session_id = "external_test_123"
        response = requests.post(f"{BASE_URL}/new-session", params={"_sid": test_session_id})
        
        if response.status_code == 200:
            data = response.json()
            if data['session_id'] == test_session_id:
                print(f"✅ External session created with correct ID: {test_session_id}")
                
                # Test session status
                status_resp = requests.get(f"{BASE_URL}/status", params={"_sid": test_session_id})
                if status_resp.status_code == 200:
                    status_data = status_resp.json()
                    if status_data['session_id'] == test_session_id:
                        print("✅ External session status correctly reported")
                        
                        # Test session cleanup
                        clear_resp = requests.post(f"{BASE_URL}/clear-session", params={"_sid": test_session_id})
                        if clear_resp.status_code == 200:
                            print("✅ External session cleared successfully")
                            return True
                        else:
                            print(f"❌ Failed to clear external session: {clear_resp.status_code}")
                            return False
                    else:
                        print("❌ External session status mismatch")
                        return False
                else:
                    print(f"❌ Failed to get external session status: {status_resp.status_code}")
                    return False
            else:
                print(f"❌ External session ID mismatch: expected {test_session_id}, got {data['session_id']}")
                return False
        else:
            print(f"❌ Failed to create external session: {response.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ External session test error: {str(e)}")
        return False

def test_session_workflow_integrity():
    """Test complete workflow integrity with session management."""
    print("🧪 Testing workflow integrity...")
    
    try:
        workflow_session_id = "workflow_test_456"
        
        # Step 1: Clear any existing session
        requests.post(f"{BASE_URL}/clear-session", params={"_sid": workflow_session_id})
        
        # Step 2: Create new session
        new_session_resp = requests.post(f"{BASE_URL}/new-session", params={"_sid": workflow_session_id})
        if new_session_resp.status_code != 200:
            print(f"❌ Failed to create workflow session: {new_session_resp.status_code}")
            return False
        
        print(f"✅ Workflow session created: {workflow_session_id}")
        
        # Step 3: Check session status
        status_resp = requests.get(f"{BASE_URL}/status", params={"_sid": workflow_session_id})
        if status_resp.status_code == 200:
            status_data = status_resp.json()
            print(f"✅ Session status: {status_data['status']}")
        else:
            print(f"❌ Failed to get session status: {status_resp.status_code}")
            return False
        
        # Step 4: Check debug info
        debug_resp = requests.get(f"{BASE_URL}/debug-sessions", params={"_sid": workflow_session_id})
        if debug_resp.status_code == 200:
            debug_data = debug_resp.json()
            print(f"✅ Debug info retrieved - Current session: {debug_data['current_session']}")
            print(f"✅ Workflow status: {debug_data['workflow_status']}")
        else:
            print(f"❌ Failed to get debug info: {debug_resp.status_code}")
            return False
        
        # Step 5: Clean up
        clear_resp = requests.post(f"{BASE_URL}/clear-session", params={"_sid": workflow_session_id})
        if clear_resp.status_code == 200:
            print("✅ Workflow session cleaned up")
            return True
        else:
            print(f"❌ Failed to clean up workflow session: {clear_resp.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Workflow integrity test error: {str(e)}")
        return False

def test_concurrent_sessions():
    """Test concurrent session handling to check for race conditions."""
    print("🧪 Testing concurrent session handling...")
    
    def create_session_worker(session_id):
        """Worker function to create a session."""
        try:
            response = requests.post(f"{BASE_URL}/new-session", params={"_sid": session_id}, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return {'success': True, 'session_id': data['session_id'], 'actual_id': session_id}
            else:
                return {'success': False, 'error': f'Status {response.status_code}', 'session_id': session_id}
        except Exception as e:
            return {'success': False, 'error': str(e), 'session_id': session_id}
    
    try:
        # Create multiple sessions concurrently
        session_ids = [f"concurrent_test_{i}" for i in range(5)]
        
        with ThreadPoolExecutor(max_workers=5) as executor:
            # Submit all session creation tasks
            futures = [executor.submit(create_session_worker, session_id) for session_id in session_ids]
            
            # Collect results
            results = []
            for future in as_completed(futures):
                result = future.result()
                results.append(result)
        
        # Analyze results
        successful_sessions = [r for r in results if r['success']]
        failed_sessions = [r for r in results if not r['success']]
        
        print(f"✅ Successful concurrent sessions: {len(successful_sessions)}")
        if failed_sessions:
            print(f"❌ Failed concurrent sessions: {len(failed_sessions)}")
            for failed in failed_sessions:
                print(f"   - {failed['session_id']}: {failed['error']}")
        
        # Check for duplicates
        session_ids_created = [r['session_id'] for r in successful_sessions]
        unique_sessions = set(session_ids_created)
        
        if len(session_ids_created) == len(unique_sessions):
            print("✅ All concurrent sessions have unique IDs")
            
            # Clean up concurrent sessions
            for session_id in session_ids:
                requests.post(f"{BASE_URL}/clear-session", params={"_sid": session_id})
            print("✅ Concurrent sessions cleaned up")
            
            return len(failed_sessions) == 0
        else:
            print("❌ Duplicate session IDs found in concurrent creation")
            return False
            
    except Exception as e:
        print(f"❌ Concurrent session test error: {str(e)}")
        return False

def test_session_persistence():
    """Test that sessions persist correctly across requests."""
    print("🧪 Testing session persistence...")
    
    try:
        persistence_session_id = "persistence_test_789"
        
        # Create session
        create_resp = requests.post(f"{BASE_URL}/new-session", params={"_sid": persistence_session_id})
        if create_resp.status_code != 200:
            print(f"❌ Failed to create persistence test session: {create_resp.status_code}")
            return False
        
        # Make multiple requests with same session ID
        for i in range(3):
            status_resp = requests.get(f"{BASE_URL}/status", params={"_sid": persistence_session_id})
            if status_resp.status_code == 200:
                status_data = status_resp.json()
                if status_data['session_id'] != persistence_session_id:
                    print(f"❌ Session ID changed on request {i+1}: {status_data['session_id']}")
                    return False
            else:
                print(f"❌ Failed status request {i+1}: {status_resp.status_code}")
                return False
            
            time.sleep(0.5)  # Small delay between requests
        
        print("✅ Session persisted correctly across multiple requests")
        
        # Clean up
        requests.post(f"{BASE_URL}/clear-session", params={"_sid": persistence_session_id})
        return True
        
    except Exception as e:
        print(f"❌ Session persistence test error: {str(e)}")
        return False

def test_debug_endpoint():
    """Test the debug endpoint functionality."""
    print("🧪 Testing debug endpoint...")
    
    try:
        # Create a test session for debugging
        debug_session_id = "debug_test_999"
        requests.post(f"{BASE_URL}/new-session", params={"_sid": debug_session_id})
        
        # Get debug info
        debug_resp = requests.get(f"{BASE_URL}/debug-sessions", params={"_sid": debug_session_id})
        
        if debug_resp.status_code == 200:
            debug_data = debug_resp.json()
            
            # Check required fields
            required_fields = ['current_session', 'workflow_status', 'all_sessions', 'total_sessions']
            missing_fields = [field for field in required_fields if field not in debug_data]
            
            if missing_fields:
                print(f"❌ Debug endpoint missing fields: {missing_fields}")
                return False
            
            print(f"✅ Debug endpoint returned complete data")
            print(f"   - Current session: {debug_data['current_session']}")
            print(f"   - Total sessions: {debug_data['total_sessions']}")
            print(f"   - Workflow status: {debug_data['workflow_status']}")
            
            # Clean up
            requests.post(f"{BASE_URL}/clear-session", params={"_sid": debug_session_id})
            return True
        else:
            print(f"❌ Debug endpoint failed: {debug_resp.status_code}")
            return False
            
    except Exception as e:
        print(f"❌ Debug endpoint test error: {str(e)}")
        return False

def cleanup_test_sessions():
    """Clean up any test sessions that might be left over."""
    test_session_patterns = [
        "test_session_", "external_test_", "workflow_test_", 
        "concurrent_test_", "persistence_test_", "debug_test_"
    ]
    
    try:
        # Get all sessions
        debug_resp = requests.get(f"{BASE_URL}/debug-sessions")
        if debug_resp.status_code == 200:
            debug_data = debug_resp.json()
            all_sessions = debug_data.get('all_sessions', [])
            
            for session_info in all_sessions:
                session_id = session_info.get('session_id', '')
                if any(pattern in session_id for pattern in test_session_patterns):
                    requests.post(f"{BASE_URL}/clear-session", params={"_sid": session_id})
                    print(f"🗑️ Cleaned up test session: {session_id}")
    except:
        pass  # Ignore cleanup errors

def main():
    """Run all session management tests."""
    print("=" * 70)
    print("🧪 SESSION MANAGEMENT FIXES TEST SUITE")
    print("=" * 70)
    print("Testing the fixes for session conflicts and race conditions...")
    print(f"Target URL: {BASE_URL}")
    print()
    
    # Clean up any existing test sessions first
    cleanup_test_sessions()
    
    # Test results
    results = []
    
    # Run tests
    tests = [
        ("Session Isolation", test_session_isolation),
        ("External Session Handling", test_external_session_handling),
        ("Workflow Integrity", test_session_workflow_integrity),
        ("Concurrent Sessions", test_concurrent_sessions),
        ("Session Persistence", test_session_persistence),
        ("Debug Endpoint", test_debug_endpoint),
    ]
    
    for test_name, test_func in tests:
        print(f"🧪 Running: {test_name}")
        try:
            result = test_func()
            results.append((test_name, result))
            print(f"Result: {'✅ PASSED' if result else '❌ FAILED'}")
        except Exception as e:
            print(f"❌ TEST ERROR: {str(e)}")
            results.append((test_name, False))
        print("-" * 50)
        time.sleep(1)  # Small delay between tests
    
    # Final cleanup
    cleanup_test_sessions()
    
    # Summary
    print("\n" + "=" * 70)
    print("📊 SESSION TESTS SUMMARY")
    print("=" * 70)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
    
    print("-" * 70)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL SESSION TESTS PASSED! Session management fixes are working correctly.")
        print("\n💡 Session Management is now:")
        print("✅ Properly isolated between different workflows")
        print("✅ Handling external session IDs correctly") 
        print("✅ Preventing session reuse conflicts")
        print("✅ Safe for concurrent access")
        print("✅ Providing proper debugging information")
    else:
        print("⚠️ Some session tests failed. Please check the session management implementation.")
    
    print("\n📋 Session Management Workflow:")
    print("1. Frontend calls /clear-session to ensure clean state")
    print("2. Frontend calls /new-session to create isolated session")
    print("3. All subsequent requests use ?_sid={session_id} parameter")
    print("4. Backend uses exact session ID provided (no reuse logic)")
    print("5. Sessions are properly isolated and cleaned up when done")

if __name__ == "__main__":
    main() 