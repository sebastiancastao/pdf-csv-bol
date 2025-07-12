#!/usr/bin/env python3
"""
Test script to demonstrate session contamination issue and validate fixes.
This script shows how the same session ID can cause contamination without proper cleanup.
"""

import requests
import time
import json
from pathlib import Path

class SessionContaminationTester:
    def __init__(self, base_url='http://localhost:8080'):
        self.base_url = base_url
        self.session_id = 'contamination_test_session'
    
    def test_contamination_scenario(self):
        """Test the scenario that causes session contamination."""
        print("🧪 Testing Session Contamination Scenario")
        print("=" * 50)
        
        # Test 1: Demonstrate the problem (without proper cleanup)
        print("\n❌ Test 1: WRONG Workflow (Causes Contamination)")
        print("-" * 40)
        
        # Simulate first document processing
        print(f"1. Processing first document with session: {self.session_id}")
        self.simulate_document_processing("Document 1", contaminated=True)
        
        # Check session state
        validation1 = self.validate_session()
        print(f"   Session clean after first document: {validation1.get('is_clean', 'Unknown')}")
        
        # Simulate second document processing WITHOUT cleanup
        print(f"2. Processing second document with SAME session: {self.session_id}")
        self.simulate_document_processing("Document 2", contaminated=True)
        
        # Check final session state
        validation2 = self.validate_session()
        print(f"   Session clean after second document: {validation2.get('is_clean', 'Unknown')}")
        print(f"   Contamination risk: {validation2.get('contamination_risk', 'Unknown')}")
        
        return validation1, validation2
    
    def test_clean_workflow(self):
        """Test the correct workflow that prevents contamination."""
        print("\n✅ Test 2: CORRECT Workflow (Prevents Contamination)")
        print("-" * 40)
        
        # Test with proper cleanup
        print(f"1. Processing first document with session: {self.session_id}")
        self.simulate_document_processing("Document 1", contaminated=False)
        
        # Check session state
        validation1 = self.validate_session()
        print(f"   Session clean after first document: {validation1.get('is_clean', 'Unknown')}")
        
        # Process second document with proper cleanup
        print(f"2. Processing second document with PROPER cleanup: {self.session_id}")
        self.simulate_document_processing("Document 2", contaminated=False)
        
        # Check final session state
        validation2 = self.validate_session()
        print(f"   Session clean after second document: {validation2.get('is_clean', 'Unknown')}")
        print(f"   Contamination risk: {validation2.get('contamination_risk', 'Unknown')}")
        
        return validation1, validation2
    
    def simulate_document_processing(self, document_name, contaminated=False):
        """Simulate processing a document with or without proper cleanup."""
        try:
            if not contaminated:
                # Proper workflow: Clean first
                print(f"   🧹 Clearing session...")
                self.clear_session()
                print(f"   🆕 Creating new session...")
                self.create_session()
            
            # Simulate file upload (we'll use a dummy request)
            print(f"   📤 Uploading {document_name}...")
            self.simulate_upload()
            
            # Check what files exist after upload
            files_info = self.get_files_info()
            print(f"   📁 Files in session: {files_info.get('files', [])}")
            
            # Simulate download
            print(f"   📥 Downloading results...")
            self.simulate_download()
            
            if not contaminated:
                # Proper workflow: Clean after
                print(f"   🧹 Cleaning up session...")
                self.clear_session()
            
        except Exception as e:
            print(f"   ❌ Error: {str(e)}")
    
    def clear_session(self):
        """Clear the session."""
        try:
            response = requests.post(f"{self.base_url}/clear-session?_sid={self.session_id}")
            return response.json()
        except Exception as e:
            print(f"Error clearing session: {str(e)}")
            return {}
    
    def create_session(self):
        """Create a new session."""
        try:
            response = requests.post(f"{self.base_url}/new-session?_sid={self.session_id}")
            return response.json()
        except Exception as e:
            print(f"Error creating session: {str(e)}")
            return {}
    
    def validate_session(self):
        """Validate the session state."""
        try:
            response = requests.get(f"{self.base_url}/validate-session?_sid={self.session_id}")
            return response.json()
        except Exception as e:
            print(f"Error validating session: {str(e)}")
            return {}
    
    def get_files_info(self):
        """Get information about files in the session."""
        try:
            response = requests.get(f"{self.base_url}/files?_sid={self.session_id}")
            return response.json()
        except Exception as e:
            print(f"Error getting files info: {str(e)}")
            return {}
    
    def simulate_upload(self):
        """Simulate uploading a file."""
        # We'll just call the status endpoint to trigger session creation
        try:
            response = requests.get(f"{self.base_url}/status?_sid={self.session_id}")
            return response.json()
        except Exception as e:
            print(f"Error simulating upload: {str(e)}")
            return {}
    
    def simulate_download(self):
        """Simulate downloading results."""
        try:
            response = requests.get(f"{self.base_url}/status?_sid={self.session_id}")
            return response.json()
        except Exception as e:
            print(f"Error simulating download: {str(e)}")
            return {}
    
    def run_comprehensive_test(self):
        """Run comprehensive session contamination tests."""
        print("🔬 Session Contamination Test Suite")
        print("=" * 60)
        
        # Test API availability
        try:
            response = requests.get(f"{self.base_url}/ping")
            if response.status_code == 200:
                print("✅ API is available")
            else:
                print("❌ API is not available")
                return
        except Exception as e:
            print(f"❌ Cannot connect to API: {str(e)}")
            return
        
        # Run contamination test
        print("\n🧪 Testing Session Contamination...")
        contaminated_results = self.test_contamination_scenario()
        
        # Run clean workflow test
        print("\n🧪 Testing Clean Workflow...")
        clean_results = self.test_clean_workflow()
        
        # Summary
        print("\n📊 Test Results Summary")
        print("=" * 30)
        
        print(f"Contaminated workflow - Final contamination risk: {contaminated_results[1].get('contamination_risk', 'Unknown')}")
        print(f"Clean workflow - Final contamination risk: {clean_results[1].get('contamination_risk', 'Unknown')}")
        
        # Recommendations
        print("\n💡 Recommendations for External Apps:")
        print("1. Always call /clear-session before processing new documents")
        print("2. Always call /new-session after clearing")
        print("3. Use /validate-session to check session state")
        print("4. Implement proper error handling with cleanup")
        
        # Clean up
        print("\n🧹 Cleaning up test session...")
        self.clear_session()
        
        print("\n✅ Session contamination test completed!")

def main():
    """Run the session contamination test."""
    tester = SessionContaminationTester()
    tester.run_comprehensive_test()

if __name__ == "__main__":
    main() 