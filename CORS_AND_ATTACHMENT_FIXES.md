# CORS and Attachment Processing Fixes

## Summary of Issues Resolved

Based on the error logs from the external app, we identified and fixed several critical issues:

### 1. CORS Header Duplication Issue
**Problem**: `CORS header 'Access-Control-Allow-Origin' does not match '*, *'`
**Root Cause**: Duplicate CORS headers were being sent
**Solution**: Implemented proper header management to prevent duplicates

### 2. Query Parameter Support
**Problem**: External app sending `?_t=1752187166972&_sid=session_1752187158003_uuut4svqy`
**Root Cause**: Our session management didn't handle external session IDs
**Solution**: Added support for `_sid` and `session_id` query parameters

### 3. Attachment Data Processing
**Problem**: `ReferenceError: attachmentData is not defined`
**Root Cause**: External app expects specific attachment handling functions
**Solution**: Added multiple upload endpoints and JavaScript functions

### 4. Email Attachment Format Support
**Problem**: Gmail attachments come as base64 encoded data
**Root Cause**: Only supported multipart form uploads
**Solution**: Added base64 and flexible attachment data handling

## Detailed Fixes Implemented

### CORS Configuration Fixes

#### Before (Problematic):
```python
response.headers.add('Access-Control-Allow-Origin', '*')
```

#### After (Fixed):
```python
# Remove any existing CORS headers to prevent duplicates
response.headers.pop('Access-Control-Allow-Origin', None)
# ... remove other headers
# Add fresh CORS headers
response.headers['Access-Control-Allow-Origin'] = '*'
```

### New Endpoints Added

#### 1. `/upload-base64` - Base64 File Upload
Handles base64 encoded PDF files (common with email attachments):

```javascript
// Usage from external app
const payload = {
  file_data: "base64DataHere...",
  filename: "attachment.pdf"
};
fetch('/upload-base64', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(payload)
});
```

#### 2. `/upload-attachment` - Flexible Attachment Upload
Handles various attachment data formats:

```javascript
// Usage from external app
const payload = {
  attachmentData: "base64DataOrBytes...",
  filename: "attachment.pdf"
};
fetch('/upload-attachment', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify(payload)
});
```

### Session Management Enhancement

#### External Session ID Support
The `get_or_create_session()` function now checks for:
- `_sid` query parameter (for external session management)
- `session_id` query parameter (alternative format)
- Falls back to Flask session if no external ID provided

```python
def get_or_create_session():
    # Check for session ID in query parameters first (for external apps)
    external_session_id = request.args.get('_sid') or request.args.get('session_id')
    
    if external_session_id:
        processor = DataProcessor(session_id=external_session_id)
        return processor
    # ... rest of function
```

### JavaScript Functions for External Apps

#### Enhanced Upload Function
```javascript
window.uploadBOLFile = function(file, options = {}) {
  // Handles File objects, Blob objects, base64 strings, and attachment data
  if (file instanceof File || file instanceof Blob) {
    // Standard multipart upload
  } else if (typeof file === 'string' || file.attachmentData) {
    // Base64 or attachment data upload
  }
};
```

#### Dedicated Processor Function
```javascript
window.processBOLWithDedicatedProcessor = function(attachmentData, filename) {
  // Specifically for external apps that call this function
  return window.uploadBOLAttachment(attachmentData, filename);
};
```

#### Complete Function Set Available
```javascript
// All these functions are now globally available:
window.downloadBOLFile(filename)
window.getBOLStatus()
window.getBOLFiles()
window.processBOLWorkflow()
window.clearBOLSession()
window.pingBOLService()
window.uploadBOLFile(file)
window.uploadBOLBase64(base64Data, filename)
window.uploadBOLAttachment(attachmentData, filename)
window.processBOLWithDedicatedProcessor(attachmentData, filename)

// Also available through BOLProcessor object:
window.BOLProcessor.uploadFile(file)
window.BOLProcessor.processDedicated(attachmentData, filename)
// ... etc
```

## Error Handling Improvements

### Before:
- Generic error messages
- No handling of missing attachment data
- Limited error context

### After:
- Specific error messages for each failure type
- Proper handling of missing `attachmentData`
- Detailed logging for debugging
- Graceful fallbacks

## Usage Examples for External Apps

### 1. Processing Gmail PDF Attachment
```javascript
// Gmail API download gives you base64 data
const attachmentData = "JVBERi0xLjQKMSAwIG9iago..."; // base64 PDF
const filename = "BOL_Document.pdf";

// Option 1: Using dedicated processor (recommended for your app)
window.processBOLWithDedicatedProcessor(attachmentData, filename)
  .then(result => {
    console.log('Processing complete:', result);
  })
  .catch(error => {
    console.error('Processing failed:', error);
  });

// Option 2: Using attachment upload
window.uploadBOLAttachment(attachmentData, filename);

// Option 3: Using base64 upload
window.uploadBOLBase64(attachmentData, filename);
```

### 2. Using External Session Management
```javascript
// Your app can maintain its own session IDs
const sessionId = "session_1752187158003_uuut4svqy";
const timestamp = Date.now();

// All requests will use your session ID
fetch(`/status?_sid=${sessionId}&_t=${timestamp}`)
  .then(response => response.json())
  .then(data => console.log('Status:', data));
```

### 3. Checking Service Availability
```javascript
// Before processing, check if service is available
window.pingBOLService()
  .then(result => {
    if (result && result.status === 'alive') {
      // Service is available, proceed with processing
      return window.processBOLWithDedicatedProcessor(attachmentData, filename);
    }
  })
  .catch(error => {
    console.log('Service unavailable, using local fallback');
  });
```

## Testing the Fixes

### Running Tests
```bash
# Test all endpoints
python test_endpoints.py

# Expected output shows all tests passing including:
# - CORS preflight requests
# - Query parameter handling
# - New upload endpoints
# - Error handling
```

### Manual Testing from External App
```javascript
// Test CORS
fetch('https://pdf-bol-extractor.onrender.com/ping')
  .then(response => response.json())
  .then(data => console.log('CORS working:', data));

// Test attachment processing
const testAttachment = "base64DataHere";
fetch('https://pdf-bol-extractor.onrender.com/upload-attachment', {
  method: 'POST',
  headers: {'Content-Type': 'application/json'},
  body: JSON.stringify({
    attachmentData: testAttachment,
    filename: 'test.pdf'
  })
})
.then(response => response.json())
.then(data => console.log('Attachment processing:', data));
```

## Migration Guide for External Apps

### If your app was calling:
```javascript
this.downloadBOLFile(filename)  // ❌ This was undefined
```

### Now use:
```javascript
window.downloadBOLFile(filename)  // ✅ This works
// or
window.BOLProcessor.downloadFile(filename)  // ✅ This also works
```

### If your app was sending:
```javascript
fetch('/upload', { /* file data */ })  // ❌ CORS blocked
```

### Now it works:
```javascript
fetch('/upload', { /* file data */ })  // ✅ CORS fixed
// or use new endpoints:
fetch('/upload-attachment', { /* attachment data */ })  // ✅ Better for emails
```

## Environment-Specific Configuration

### Development
```python
app.config['SESSION_COOKIE_SECURE'] = False  # HTTP allowed
```

### Production
```python
app.config['SESSION_COOKIE_SECURE'] = True   # HTTPS required
SECRET_KEY = os.environ.get('SECRET_KEY')     # Use environment variable
```

## Troubleshooting Common Issues

### Issue: Still getting CORS errors
**Solution**: Clear browser cache and check for cached preflight responses

### Issue: `attachmentData is not defined`
**Solution**: Use `window.processBOLWithDedicatedProcessor(attachmentData, filename)`

### Issue: Session not persisting
**Solution**: Pass `_sid` parameter: `/upload?_sid=your_session_id`

### Issue: File upload fails
**Solution**: Check file format and use appropriate endpoint:
- PDF files: `/upload-attachment`
- Base64 data: `/upload-base64`
- Regular files: `/upload`

## Conclusion

All the issues identified in the error logs have been resolved:

✅ **CORS fixed**: Proper header management prevents duplication  
✅ **Functions available**: `downloadBOLFile` and all other functions now exist  
✅ **Attachment handling**: Multiple endpoints support different data formats  
✅ **Session management**: External session IDs supported via query parameters  
✅ **Error handling**: Better error messages and graceful fallbacks  
✅ **Testing**: Comprehensive test suite validates all functionality  

The BOL Extractor API now works seamlessly with external applications that process Gmail attachments and require cross-origin access. 