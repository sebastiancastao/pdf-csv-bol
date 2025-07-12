# Session Contamination Issue - External App Guide

## 🚨 **CRITICAL ISSUE: Same Output for Different Input Files**

Your external application is successfully calling the BOL Extractor API, but you're getting the same output file even when processing completely different input files. This is caused by **session contamination**.

## 🔍 **Root Cause Analysis**

### **What's Happening:**
1. **First Document**: External app calls API with `?_sid=abc123`
2. **Session Directory Created**: `processing_sessions/abc123/` with processed files
3. **Second Document**: External app calls API with **same** `?_sid=abc123`
4. **Session Directory Reused**: Old files still exist in the directory
5. **Contaminated Processing**: New processing mixes with old cached data
6. **Same Output**: Returns cached/mixed results instead of fresh processing

### **The Problem:**
```
processing_sessions/abc123/
├── old_document.pdf          # From first processing
├── page1.txt                 # From first processing
├── page2.txt                 # From first processing
├── invoice_123.csv           # From first processing
├── combined_data.csv         # From first processing (CACHED!)
└── new_document.pdf          # From second processing
```

When the second document is processed, the old files interfere with the new processing, causing mixed or cached results.

## ✅ **Solution: Proper Session Management Workflow**

### **❌ WRONG Workflow (Causes Contamination):**
```http
# Document 1
POST /upload?_sid=abc123          # Creates session directory
GET /download?_sid=abc123         # Downloads results

# Document 2 (SAME SESSION ID - CONTAMINATED!)
POST /upload?_sid=abc123          # Reuses dirty session directory
GET /download?_sid=abc123         # Returns cached/mixed results
```

### **✅ CORRECT Workflow (Prevents Contamination):**
```http
# Document 1
POST /clear-session?_sid=abc123   # Clean any existing session
POST /new-session?_sid=abc123     # Create fresh session
POST /upload?_sid=abc123          # Process document
GET /download?_sid=abc123         # Download results
POST /clear-session?_sid=abc123   # Clean up

# Document 2 (SAME SESSION ID - CLEAN!)
POST /clear-session?_sid=abc123   # Clean any existing session
POST /new-session?_sid=abc123     # Create fresh session
POST /upload?_sid=abc123          # Process document
GET /download?_sid=abc123         # Download results
POST /clear-session?_sid=abc123   # Clean up
```

## 🛠️ **Implementation Examples**

### **JavaScript/Node.js Example:**
```javascript
class BOLProcessor {
    constructor(apiUrl) {
        this.apiUrl = apiUrl;
    }
    
    async processDocument(file, sessionId) {
        try {
            // Step 1: Clear any existing session
            await this.clearSession(sessionId);
            
            // Step 2: Create fresh session
            await this.createSession(sessionId);
            
            // Step 3: Upload and process document
            const uploadResult = await this.uploadDocument(file, sessionId);
            
            // Step 4: Download results
            const results = await this.downloadResults(sessionId);
            
            // Step 5: Clean up
            await this.clearSession(sessionId);
            
            return results;
            
        } catch (error) {
            // Always clean up on error
            await this.clearSession(sessionId);
            throw error;
        }
    }
    
    async clearSession(sessionId) {
        const response = await fetch(`${this.apiUrl}/clear-session?_sid=${sessionId}`, {
            method: 'POST'
        });
        return response.json();
    }
    
    async createSession(sessionId) {
        const response = await fetch(`${this.apiUrl}/new-session?_sid=${sessionId}`, {
            method: 'POST'
        });
        return response.json();
    }
    
    async uploadDocument(file, sessionId) {
        const formData = new FormData();
        formData.append('file', file);
        
        const response = await fetch(`${this.apiUrl}/upload?_sid=${sessionId}`, {
            method: 'POST',
            body: formData
        });
        return response.json();
    }
    
    async downloadResults(sessionId) {
        const response = await fetch(`${this.apiUrl}/download?_sid=${sessionId}`);
        return response.blob();
    }
}

// Usage
const processor = new BOLProcessor('https://your-bol-api.com');

// Process different documents with same session ID (but properly cleaned)
const result1 = await processor.processDocument(file1, 'external_session_001');
const result2 = await processor.processDocument(file2, 'external_session_001');
// result1 and result2 will be different based on their respective input files
```

### **Python Example:**
```python
import requests
import time

class BOLClient:
    def __init__(self, base_url):
        self.base_url = base_url
    
    def process_document(self, file_path, session_id):
        """Process a document with proper session management."""
        try:
            # Step 1: Clear any existing session
            self.clear_session(session_id)
            
            # Step 2: Create fresh session
            self.create_session(session_id)
            
            # Step 3: Upload and process document
            self.upload_document(file_path, session_id)
            
            # Step 4: Download results
            results = self.download_results(session_id)
            
            # Step 5: Clean up
            self.clear_session(session_id)
            
            return results
            
        except Exception as error:
            # Always clean up on error
            self.clear_session(session_id)
            raise error
    
    def clear_session(self, session_id):
        response = requests.post(f"{self.base_url}/clear-session?_sid={session_id}")
        return response.json()
    
    def create_session(self, session_id):
        response = requests.post(f"{self.base_url}/new-session?_sid={session_id}")
        return response.json()
    
    def upload_document(self, file_path, session_id):
        with open(file_path, 'rb') as f:
            files = {'file': f}
            response = requests.post(f"{self.base_url}/upload?_sid={session_id}", files=files)
        return response.json()
    
    def download_results(self, session_id):
        response = requests.get(f"{self.base_url}/download?_sid={session_id}")
        return response.content

# Usage
client = BOLClient('https://your-bol-api.com')

# Process different documents with same session ID (but properly cleaned)
result1 = client.process_document('document1.pdf', 'external_session_001')
result2 = client.process_document('document2.pdf', 'external_session_001')
# result1 and result2 will be different based on their respective input files
```

## 🔧 **New Debugging Tools**

### **1. Session Validation Endpoint**
Check if your session is contaminated before processing:

```http
GET /validate-session?_sid=abc123
```

**Response:**
```json
{
    "session_id": "abc123",
    "is_clean": false,
    "contamination_risk": "high",
    "files_found": ["old_document.pdf", "combined_data.csv"],
    "recommendations": [
        "Call /clear-session before processing new documents",
        "Call /new-session to ensure clean processing environment"
    ],
    "proper_workflow": [
        "POST /clear-session?_sid=abc123",
        "POST /new-session?_sid=abc123",
        "POST /upload?_sid=abc123",
        "GET /download?_sid=abc123",
        "POST /clear-session?_sid=abc123"
    ]
}
```

### **2. Enhanced Logging**
The BOL Extractor now automatically detects and logs session contamination:

```
⚠️  SESSION CONTAMINATION DETECTED!
⚠️  Session abc123 contains existing files: ['old_document.pdf', 'combined_data.csv']
⚠️  This may cause same output for different inputs!
🧹 Removed old file: old_document.pdf
🧹 Removed old file: combined_data.csv
```

## 📊 **Session Management Best Practices**

### **1. Use Unique Session IDs**
```javascript
// Generate unique session ID per workflow
const sessionId = `external_${Date.now()}_${Math.random().toString(36).substr(2, 5)}`;
```

### **2. Always Clean Sessions**
```javascript
// Always start with clean session
await clearSession(sessionId);
await createSession(sessionId);
```

### **3. Implement Error Handling**
```javascript
try {
    const result = await processDocument(file, sessionId);
    return result;
} catch (error) {
    // Always clean up on error
    await clearSession(sessionId);
    throw error;
}
```

### **4. Validate Sessions Before Processing**
```javascript
// Check session state before processing
const validation = await validateSession(sessionId);
if (!validation.is_clean) {
    await clearSession(sessionId);
    await createSession(sessionId);
}
```

## 🚀 **Quick Fix for Your External App**

### **Step 1: Add Session Cleanup**
Add calls to `/clear-session` and `/new-session` before each document processing:

```javascript
// Before processing each document
await fetch(`${apiUrl}/clear-session?_sid=${sessionId}`, { method: 'POST' });
await fetch(`${apiUrl}/new-session?_sid=${sessionId}`, { method: 'POST' });
```

### **Step 2: Verify the Fix**
Use the validation endpoint to confirm your sessions are clean:

```javascript
const validation = await fetch(`${apiUrl}/validate-session?_sid=${sessionId}`);
const result = await validation.json();
console.log('Session is clean:', result.is_clean);
```

### **Step 3: Test with Different Files**
Process two completely different PDF files and verify you get different outputs:

```javascript
const result1 = await processDocument(file1, 'test_session_001');
const result2 = await processDocument(file2, 'test_session_001');
// These should now be different!
```

## 📋 **Troubleshooting Checklist**

- [ ] **Are you calling `/clear-session` before each new document?**
- [ ] **Are you calling `/new-session` after clearing?**
- [ ] **Are you using the same session ID parameter (`?_sid=abc123`) in all calls?**
- [ ] **Are you handling errors properly and cleaning up sessions?**
- [ ] **Have you verified with `/validate-session` that sessions are clean?**

## 🎯 **Expected Behavior After Fix**

1. **Different input files** → **Different output files**
2. **No cached results** → **Fresh processing every time**
3. **Clean sessions** → **Isolated processing**
4. **Predictable behavior** → **Reliable API responses**

## 🔗 **Additional Resources**

- **Session Validation**: `GET /validate-session?_sid=your_session_id`
- **Debug Sessions**: `GET /debug-sessions?_sid=your_session_id`
- **API Documentation**: `GET /api/docs`

This guide should resolve the session contamination issue and ensure your external application gets unique results for each input file processed. 