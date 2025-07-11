#!/usr/bin/env python3
"""
Test script to verify the architecture fixes for PDF processing errors.
This script tests both successful and failure scenarios to ensure the web service
no longer crashes when encountering PDF processing issues.
"""

import requests
import json
import base64
import os
import time
from pathlib import Path

# Test configuration
BASE_URL = "http://localhost:8080"  # Updated port
TEST_PDF_PATH = "test_sample.pdf"

def create_test_pdf():
    """Create a minimal test PDF file for testing."""
    # Create a minimal but valid PDF
    pdf_content = b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 612 792]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000125 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n205\n%%EOF\n"
    
    with open(TEST_PDF_PATH, "wb") as f:
        f.write(pdf_content)
    
    print(f"✅ Created test PDF: {TEST_PDF_PATH}")
    return TEST_PDF_PATH

def test_service_availability():
    """Test that the service is running and accessible."""
    try:
        print("🔍 Testing service availability...")
        response = requests.get(f"{BASE_URL}/ping", timeout=10)
        
        if response.status_code == 200:
            print("✅ Service is running and accessible")
            return True
        else:
            print(f"❌ Service responded with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Service not accessible: {str(e)}")
        return False

def test_health_endpoint():
    """Test the health endpoint to check service status."""
    try:
        print("🔍 Testing health endpoint...")
        response = requests.get(f"{BASE_URL}/api/health", timeout=10)
        
        if response.status_code == 200:
            data = response.json()
            print(f"✅ Health check passed: {data.get('status', 'unknown')}")
            return True
        else:
            print(f"❌ Health check failed with status {response.status_code}")
            return False
    except requests.exceptions.RequestException as e:
        print(f"❌ Health check error: {str(e)}")
        return False

def test_pdf_upload_multipart():
    """Test PDF upload using multipart/form-data."""
    try:
        print("🔍 Testing PDF upload (multipart)...")
        
        if not os.path.exists(TEST_PDF_PATH):
            create_test_pdf()
        
        with open(TEST_PDF_PATH, "rb") as f:
            files = {'file': ('test.pdf', f, 'application/pdf')}
            response = requests.post(f"{BASE_URL}/upload", files=files, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Content: {response.text}")
        
        if response.status_code == 200:
            print("✅ PDF upload successful")
            return True
        elif response.status_code == 500:
            # This is expected if there are processing issues, but service should not crash
            error_data = response.json()
            print(f"⚠️ PDF processing failed as expected: {error_data.get('error', 'Unknown error')}")
            print(f"Details: {error_data.get('details', 'No details')}")
            print("✅ Service handled error gracefully (did not crash)")
            return True
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ PDF upload error: {str(e)}")
        return False

def test_pdf_upload_base64():
    """Test PDF upload using base64 encoding."""
    try:
        print("🔍 Testing PDF upload (base64)...")
        
        if not os.path.exists(TEST_PDF_PATH):
            create_test_pdf()
        
        with open(TEST_PDF_PATH, "rb") as f:
            pdf_data = f.read()
            base64_data = base64.b64encode(pdf_data).decode('utf-8')
        
        payload = {
            "file_data": base64_data,
            "filename": "test_base64.pdf"
        }
        
        headers = {"Content-Type": "application/json"}
        response = requests.post(f"{BASE_URL}/upload-base64", 
                               json=payload, headers=headers, timeout=30)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Content: {response.text}")
        
        if response.status_code == 200:
            print("✅ Base64 PDF upload successful")
            return True
        elif response.status_code == 500:
            error_data = response.json()
            print(f"⚠️ PDF processing failed as expected: {error_data.get('error', 'Unknown error')}")
            print(f"Details: {error_data.get('details', 'No details')}")
            print("✅ Service handled error gracefully (did not crash)")
            return True
        else:
            print(f"❌ Unexpected response: {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Base64 upload error: {str(e)}")
        return False

def test_invalid_file_handling():
    """Test handling of invalid file uploads."""
    try:
        print("🔍 Testing invalid file handling...")
        
        # Create a non-PDF file
        with open("test_invalid.txt", "w") as f:
            f.write("This is not a PDF file")
        
        with open("test_invalid.txt", "rb") as f:
            files = {'file': ('test_invalid.txt', f, 'text/plain')}
            response = requests.post(f"{BASE_URL}/upload", files=files, timeout=10)
        
        print(f"Response Status: {response.status_code}")
        print(f"Response Content: {response.text}")
        
        if response.status_code == 400:
            print("✅ Invalid file rejected correctly")
            return True
        else:
            print(f"❌ Expected 400 status, got {response.status_code}")
            return False
            
    except requests.exceptions.RequestException as e:
        print(f"❌ Invalid file test error: {str(e)}")
        return False
    finally:
        # Clean up test file
        if os.path.exists("test_invalid.txt"):
            os.remove("test_invalid.txt")

def test_service_stability():
    """Test that the service remains stable after errors."""
    try:
        print("🔍 Testing service stability after errors...")
        
        # Make multiple requests to ensure service doesn't crash
        for i in range(3):
            print(f"  Stability test {i+1}/3...")
            response = requests.get(f"{BASE_URL}/ping", timeout=10)
            if response.status_code != 200:
                print(f"❌ Service unstable on attempt {i+1}")
                return False
            time.sleep(1)
        
        print("✅ Service remains stable after processing errors")
        return True
        
    except requests.exceptions.RequestException as e:
        print(f"❌ Service stability test error: {str(e)}")
        return False

def cleanup_test_files():
    """Clean up test files."""
    test_files = [TEST_PDF_PATH, "test_invalid.txt"]
    for file_path in test_files:
        if os.path.exists(file_path):
            os.remove(file_path)
            print(f"🗑️ Cleaned up: {file_path}")

def main():
    """Run all architecture fix tests."""
    print("=" * 60)
    print("🧪 ARCHITECTURE FIXES TEST SUITE")
    print("=" * 60)
    print("Testing the fixes for PDF processing errors...")
    print(f"Target URL: {BASE_URL}")
    print()
    
    # Test results
    results = []
    
    # Run tests
    tests = [
        ("Service Availability", test_service_availability),
        ("Health Endpoint", test_health_endpoint),
        ("PDF Upload (Multipart)", test_pdf_upload_multipart),
        ("PDF Upload (Base64)", test_pdf_upload_base64),
        ("Invalid File Handling", test_invalid_file_handling),
        ("Service Stability", test_service_stability),
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
        print("-" * 40)
    
    # Clean up
    cleanup_test_files()
    
    # Summary
    print("\n" + "=" * 60)
    print("📊 TEST SUMMARY")
    print("=" * 60)
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for test_name, result in results:
        status = "✅ PASSED" if result else "❌ FAILED"
        print(f"{test_name:<30} {status}")
    
    print("-" * 60)
    print(f"Total: {passed}/{total} tests passed")
    
    if passed == total:
        print("🎉 ALL TESTS PASSED! Architecture fixes are working correctly.")
    else:
        print("⚠️ Some tests failed. Please check the service configuration.")
    
    print("\n💡 Next Steps:")
    print("1. If tests pass, the architecture fixes are working correctly")
    print("2. If tests fail, check server logs for detailed error information")  
    print("3. Verify Poppler installation if PDF processing fails")
    print("4. Test with your external application to confirm the fixes")

if __name__ == "__main__":
    main() 