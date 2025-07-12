#!/usr/bin/env python3
"""
Test script for stateless processing endpoints.
This demonstrates how to use the new stateless processing without session management.
"""

import requests
import json
import time
from pathlib import Path

# Configuration
API_URL = "http://localhost:8080"  # Change to your actual API URL
TEST_FILES_DIR = Path(__file__).parent / "test_files"

def test_stateless_processing():
    """Test the new stateless processing endpoints."""
    
    print("🧪 Testing Stateless Processing Endpoints")
    print("=" * 50)
    
    # Test 1: Check if API is running
    print("\n1. Testing API connectivity...")
    try:
        response = requests.get(f"{API_URL}/health")
        if response.status_code == 200:
            print("✅ API is running")
            print(f"   Status: {response.json()}")
        else:
            print(f"❌ API health check failed: {response.status_code}")
            return False
    except Exception as e:
        print(f"❌ Cannot connect to API: {e}")
        return False
    
    # Test 2: Get API documentation
    print("\n2. Getting API documentation...")
    try:
        response = requests.get(f"{API_URL}/api/docs")
        if response.status_code == 200:
            docs = response.json()
            print("✅ API documentation retrieved")
            print(f"   Service: {docs.get('service', 'Unknown')}")
            print(f"   Version: {docs.get('version', 'Unknown')}")
            
            # Check if stateless endpoints are available
            endpoints = docs.get('endpoints', {})
            if 'POST /upload-stateless' in endpoints:
                print("✅ Stateless endpoints are available")
            else:
                print("❌ Stateless endpoints not found")
                return False
        else:
            print(f"❌ Failed to get API docs: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting API docs: {e}")
    
    # Test 3: Test stateless example endpoint
    print("\n3. Getting stateless processing examples...")
    try:
        response = requests.get(f"{API_URL}/example-stateless")
        if response.status_code == 200:
            examples = response.json()
            print("✅ Stateless examples retrieved")
            print(f"   Title: {examples.get('title', 'Unknown')}")
            
            # Show migration benefits
            benefits = examples.get('migration_benefits', {})
            if benefits:
                print("   Migration Benefits:")
                for key, value in benefits.items():
                    print(f"     • {key}: {value}")
        else:
            print(f"❌ Failed to get examples: {response.status_code}")
    except Exception as e:
        print(f"❌ Error getting examples: {e}")
    
    # Test 4: Test stateless processing with mock data
    print("\n4. Testing stateless processing with mock data...")
    
    # Create a simple test PDF content (not a real PDF, just for API testing)
    test_pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj\ntrailer<</Size 2/Root 1 0 R>>\nstartxref\n0\n%%EOF\n"
    
    # Create test CSV content
    test_csv_content = """Invoice No.,Style,Cartons,Individual Pieces,Order Date,Ship To Name,Purchase Order No.,Start Date,Cancel Date
G12345,TEST123,1,24,01/01/2025,Test Customer,PO12345,01/05/2025,01/30/2025
G12346,TEST124,2,48,01/01/2025,Test Customer,PO12346,01/05/2025,01/30/2025"""
    
    try:
        # Test single stateless endpoint
        print("   Testing /upload-stateless endpoint...")
        
        files = {
            'file': ('test.pdf', test_pdf_content, 'application/pdf'),
            'csv_file': ('test.csv', test_csv_content, 'text/csv')
        }
        
        response = requests.post(f"{API_URL}/upload-stateless", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Stateless processing completed successfully")
            print(f"   Status: {result.get('status', 'Unknown')}")
            print(f"   Request ID: {result.get('request_id', 'Unknown')}")
            
            # Check if CSV data is returned
            if 'csv_data' in result:
                csv_lines = result['csv_data'].split('\n')
                print(f"   CSV Lines: {len(csv_lines)}")
                print(f"   Row Count: {result.get('row_count', 'Unknown')}")
            else:
                print("   No CSV data returned")
        else:
            print(f"❌ Stateless processing failed: {response.status_code}")
            try:
                error = response.json()
                print(f"   Error: {error.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Error testing stateless processing: {e}")
    
    # Test 5: Test multipart stateless endpoint
    print("\n5. Testing stateless multipart processing...")
    
    try:
        files = {
            'pdf_file': ('test.pdf', test_pdf_content, 'application/pdf'),
            'csv_file': ('test.csv', test_csv_content, 'text/csv')
        }
        
        response = requests.post(f"{API_URL}/upload-stateless-multipart", files=files)
        
        if response.status_code == 200:
            result = response.json()
            print("✅ Stateless multipart processing completed successfully")
            print(f"   Status: {result.get('status', 'Unknown')}")
            print(f"   Request ID: {result.get('request_id', 'Unknown')}")
            print(f"   Has CSV Merge: {result.get('has_csv_merge', False)}")
            
            if 'csv_data' in result:
                csv_lines = result['csv_data'].split('\n')
                print(f"   CSV Lines: {len(csv_lines)}")
                print(f"   Row Count: {result.get('row_count', 'Unknown')}")
        else:
            print(f"❌ Stateless multipart processing failed: {response.status_code}")
            try:
                error = response.json()
                print(f"   Error: {error.get('error', 'Unknown error')}")
            except:
                print(f"   Response: {response.text}")
    
    except Exception as e:
        print(f"❌ Error testing stateless multipart processing: {e}")
    
    # Test 6: Performance comparison
    print("\n6. Performance comparison...")
    
    # Test old session-based approach
    print("   Testing old session-based approach...")
    session_start = time.time()
    session_id = f"test_session_{int(time.time())}"
    
    try:
        # Old way - multiple requests
        requests.post(f"{API_URL}/clear-session?_sid={session_id}")
        requests.post(f"{API_URL}/new-session?_sid={session_id}")
        
        # Note: These will likely fail with our test PDF, but we're measuring the request overhead
        files = {'file': ('test.pdf', test_pdf_content, 'application/pdf')}
        requests.post(f"{API_URL}/upload?_sid={session_id}", files=files)
        
        requests.post(f"{API_URL}/clear-session?_sid={session_id}")
        
        session_time = time.time() - session_start
        print(f"   Session-based approach: {session_time:.2f} seconds (4 requests)")
    except Exception as e:
        print(f"   Session-based approach failed: {e}")
        session_time = 0
    
    # Test new stateless approach
    print("   Testing new stateless approach...")
    stateless_start = time.time()
    
    try:
        files = {
            'pdf_file': ('test.pdf', test_pdf_content, 'application/pdf'),
            'csv_file': ('test.csv', test_csv_content, 'text/csv')
        }
        requests.post(f"{API_URL}/upload-stateless-multipart", files=files)
        
        stateless_time = time.time() - stateless_start
        print(f"   Stateless approach: {stateless_time:.2f} seconds (1 request)")
        
        if session_time > 0:
            improvement = ((session_time - stateless_time) / session_time) * 100
            print(f"   Performance improvement: {improvement:.1f}%")
    except Exception as e:
        print(f"   Stateless approach failed: {e}")
    
    print("\n" + "=" * 50)
    print("🎉 Stateless Processing Test Complete!")
    print("\nRecommendation:")
    print("✅ Use /upload-stateless-multipart for automated processing")
    print("✅ Keep session-based endpoints for web UI interactions")
    print("✅ No session management required for stateless endpoints")
    print("✅ Automatic cleanup prevents contamination issues")
    
    return True

def show_migration_example():
    """Show a practical migration example."""
    
    print("\n📋 Migration Example")
    print("=" * 30)
    
    print("\n🔴 OLD WAY (Session-based):")
    print("""
import requests
import time

API_URL = "https://your-api.com"
session_id = f"session_{int(time.time())}"

# 6 requests needed:
requests.post(f"{API_URL}/clear-session?_sid={session_id}")
requests.post(f"{API_URL}/new-session?_sid={session_id}")
requests.post(f"{API_URL}/upload?_sid={session_id}", files={'file': pdf_file})
requests.post(f"{API_URL}/upload-csv?_sid={session_id}", files={'file': csv_file})
response = requests.get(f"{API_URL}/download?_sid={session_id}")
requests.post(f"{API_URL}/clear-session?_sid={session_id}")

csv_data = response.text
    """)
    
    print("\n🟢 NEW WAY (Stateless):")
    print("""
import requests

API_URL = "https://your-api.com"

# 1 request needed:
files = {
    'pdf_file': ('document.pdf', pdf_file),
    'csv_file': ('data.csv', csv_file)
}
response = requests.post(f"{API_URL}/upload-stateless-multipart", files=files)
result = response.json()

csv_data = result['csv_data']
    """)
    
    print("\n💡 Benefits:")
    print("• 6 requests → 1 request")
    print("• No session management")
    print("• No contamination risk")
    print("• Automatic cleanup")
    print("• Simpler error handling")

if __name__ == "__main__":
    # Run the tests
    test_stateless_processing()
    
    # Show migration example
    show_migration_example() 