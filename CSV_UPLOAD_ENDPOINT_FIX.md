# CSV Upload Endpoint Fix Summary

## Problem Analysis

The external app was getting a **400 Bad Request** error when calling the `/upload-csv` endpoint:

```
POST https://pdf-bol-extractor.onrender.com/upload-csv?_t=1752198454087&_sid=session_1752198451088_8fei6p5kn
[HTTP/2 400  289ms]

❌ Sequential BOL API processing failed: Error: CSV upload failed with status: 400
```

## Root Cause

The original `/upload-csv` endpoint was **too restrictive** and only accepted one specific format:
- **Required**: `multipart/form-data` with a `file` field
- **Required**: File upload with proper filename
- **Required**: Valid CSV file extension

But external apps often send CSV data in different formats:
- JSON with CSV content as a string
- Raw CSV data in request body
- Base64-encoded CSV data
- Form data with CSV content

## Solution Implemented

### Enhanced `/upload-csv` Endpoint

The endpoint now supports **5 different input formats**:

#### 1. File Upload (Original Method)
```http
POST /upload-csv
Content-Type: multipart/form-data

file: [CSV_FILE]
```

#### 2. JSON with csv_data Field
```http
POST /upload-csv
Content-Type: application/json

{
  "csv_data": "Company Name,Ship To Name,Ship To Address,BOL#,Delivery Date,Pallet Count,Cube\nTest Company,Test Location,123 Test St,BOL123,2024-01-15,5,100.5",
  "filename": "data.csv"
}
```

#### 3. JSON with Base64 file_data Field
```http
POST /upload-csv
Content-Type: application/json

{
  "file_data": "data:text/csv;base64,Q29tcGFueS4uLg==",
  "filename": "data.csv"
}
```

#### 4. Form Data with csv_data Field
```http
POST /upload-csv
Content-Type: application/x-www-form-urlencoded

csv_data=Company Name,Ship To Name...&filename=data.csv
```

#### 5. Raw CSV Data
```http
POST /upload-csv
Content-Type: text/csv

Company Name,Ship To Name,Ship To Address,BOL#,Delivery Date,Pallet Count,Cube
Test Company,Test Location,123 Test St,BOL123,2024-01-15,5,100.5
```

### Added Debug Capabilities

#### Debug Request Endpoint
```http
POST /debug-request
```

This endpoint captures and returns:
- Request method and URL
- All headers
- Content type and length
- JSON data (if present)
- Form data (if present)
- Raw request body
- File uploads (if present)

**Use this endpoint to troubleshoot what your external app is sending!**

### Enhanced Error Handling

The endpoint now provides detailed error messages:

```json
{
  "error": "No CSV data provided",
  "expected_formats": [
    "multipart/form-data with file field",
    "application/json with csv_data field",
    "application/json with file_data field",
    "form data with csv_data field",
    "text/csv content-type with CSV in body"
  ]
}
```

### Comprehensive Logging

The endpoint now logs detailed information:

```
📄 CSV Upload Request - Session: session_20250710_123456_abc123
Content-Type: application/json
Request method: POST
Files: []
Form data: []
JSON data: True
✅ CSV data saved from JSON
🧹 Cleaned up temporary file: /path/to/temp_file.csv
```

## Testing

Created comprehensive test suite (`test_csv_upload.py`) that verifies:

1. **File upload** (multipart/form-data)
2. **JSON with csv_data** field
3. **JSON with base64 file_data** field
4. **Form data with csv_data** field
5. **Raw CSV data** with text/csv content-type
6. **Debug request** endpoint functionality

## Usage for External Apps

### Recommended Approach (JSON with csv_data)

```javascript
// External app code
const csvData = "Company Name,Ship To Name,Ship To Address,BOL#,Delivery Date,Pallet Count,Cube\nTest Company,Test Location,123 Test St,BOL123,2024-01-15,5,100.5";

const response = await fetch('https://pdf-bol-extractor.onrender.com/upload-csv?_t=1752198454087&_sid=session_1752198451088_8fei6p5kn', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    csv_data: csvData,
    filename: 'exported_data.csv'
  })
});

const result = await response.json();
if (result.status === 'success') {
  console.log('✅ CSV uploaded successfully');
} else {
  console.log('❌ Upload failed:', result.error);
}
```

### Alternative: Form Data Approach

```javascript
// External app code
const formData = new FormData();
formData.append('csv_data', csvData);
formData.append('filename', 'exported_data.csv');

const response = await fetch('https://pdf-bol-extractor.onrender.com/upload-csv?_t=1752198454087&_sid=session_1752198451088_8fei6p5kn', {
  method: 'POST',
  body: formData
});
```

### Debug Your Request

If you're still getting 400 errors, use the debug endpoint first:

```javascript
// Test what your app is sending
const response = await fetch('https://pdf-bol-extractor.onrender.com/debug-request?_t=1752198454087&_sid=session_1752198451088_8fei6p5kn', {
  method: 'POST',
  headers: {
    'Content-Type': 'application/json'
  },
  body: JSON.stringify({
    csv_data: csvData,
    filename: 'debug_test.csv'
  })
});

const debugInfo = await response.json();
console.log('Debug info:', debugInfo.request_info);
```

## Files Modified

- `app.py`: Enhanced `/upload-csv` endpoint with multiple input format support
- `app.py`: Added `/debug-request` endpoint for troubleshooting
- `test_csv_upload.py`: Comprehensive test suite (new file)

## Expected Behavior Now

1. **Multiple Input Formats**: The endpoint accepts CSV data in 5 different formats
2. **Better Error Messages**: Clear indication of what formats are supported
3. **Comprehensive Logging**: Detailed logs for debugging
4. **Debug Endpoint**: Separate endpoint to troubleshoot request format issues
5. **Session Management**: Proper handling of external session parameters

## Troubleshooting Steps

1. **Check the endpoint URL**: Make sure you're calling `/upload-csv` not `/upload-csv/`
2. **Verify content format**: Use `/debug-request` to see what your app is sending
3. **Check session parameters**: Include `_sid` and `_action=new_session` in query parameters
4. **Review server logs**: The enhanced logging will show exactly what format was detected
5. **Test with different formats**: Try the JSON approach if file upload isn't working

The external app should now be able to upload CSV data successfully using any of the supported formats! 