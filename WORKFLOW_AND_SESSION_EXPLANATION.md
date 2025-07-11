# Complete BOL Processing Workflow and Session Management

## Overview
The BOL (Bill of Lading) processing system follows a structured workflow where session management is crucial for maintaining data integrity, isolation, and proper state tracking throughout the entire process.

## 🔄 Complete Workflow Steps

### 1. **Session Initialization Phase**

#### Step 1a: Clear Session (Optional)
```http
POST /clear-session?_sid=abc123
```
**Purpose**: Clean up any existing session data
**Session Role**: 
- Removes session directory: `processing_sessions/session_xxx_abc123/`
- Clears Flask session data
- Ensures fresh start for new workflow

#### Step 1b: New Session (Required)
```http
POST /new-session?_sid=abc123
```
**Purpose**: Create isolated processing environment
**Session Role**:
- Creates unique session directory with timestamp
- Initializes session state with empty data structures
- Sets up isolated workspace for this specific workflow

**Session State After**:
```python
{
    'session_id': 'abc123',
    'created_at': '2025-01-09T10:30:00Z',
    'status': 'initialized',
    'filename': None,
    'processed_data': None
}
```

### 2. **File Upload Phase**

#### Step 2: Upload PDF
```http
POST /upload?_sid=abc123
Content-Type: multipart/form-data
```
**Purpose**: Store PDF file in session-specific location
**Session Role**:
- Saves PDF to session directory: `processing_sessions/session_xxx_abc123/filename.pdf`
- Updates session state with file information
- Validates file and stores metadata

**Session State After**:
```python
{
    'session_id': 'abc123',
    'created_at': '2025-01-09T10:30:00Z',
    'status': 'file_uploaded',
    'filename': 'BOL_Document.pdf',
    'file_size': 1024567,
    'processed_data': None
}
```

### 3. **Processing Phase**

#### Step 3: Process PDF
```http
POST /process?_sid=abc123
```
**Purpose**: Extract and process BOL data from uploaded PDF
**Session Role**:
- Retrieves PDF from session directory
- Stores all processing results in session state
- Maintains processing status and error information

**Processing Sub-steps**:
1. **PDF Text Extraction**
   - Uses Poppler (preferred) or pdfplumber (fallback)
   - Extracts raw text from PDF pages
   
2. **BOL Data Processing**
   - Parses structured data from extracted text
   - Identifies tables, fields, and BOL-specific information
   - Validates and normalizes data

3. **Data Storage**
   - Stores processed data in session state
   - Keeps both raw and processed data for debugging

**Session State After**:
```python
{
    'session_id': 'abc123',
    'created_at': '2025-01-09T10:30:00Z',
    'status': 'processed',
    'filename': 'BOL_Document.pdf',
    'file_size': 1024567,
    'processed_data': {
        'tables': [...],
        'fields': {...},
        'metadata': {...}
    }
}
```

### 4. **Download Phase**

#### Step 4: Download CSV
```http
GET /download?_sid=abc123
```
**Purpose**: Generate and download CSV from processed data
**Session Role**:
- Retrieves processed data from session state
- Generates CSV on-demand from stored data
- Provides download without re-processing

**CSV Generation Process**:
1. Retrieve processed data from session
2. Format data according to CSV structure
3. Generate CSV content with proper headers
4. Return as downloadable file

### 5. **Cleanup Phase**

#### Step 5: Clear Session (Optional)
```http
POST /clear-session?_sid=abc123
```
**Purpose**: Clean up session resources
**Session Role**:
- Removes session directory and all files
- Clears session state from memory
- Frees up storage space

## 🗂️ Session Management Deep Dive

### Session Directory Structure
```
processing_sessions/
└── session_20250109_103000_abc123/
    ├── uploaded_file.pdf          # Original PDF
    ├── extracted_text.txt         # Raw extracted text (debug)
    └── processing_log.txt         # Processing debug info
```

### Session State Management
The session state is maintained in Flask's session object and includes:

```python
session_data = {
    'session_id': 'abc123',              # External session ID
    'created_at': '2025-01-09T10:30:00Z', # Session creation time
    'status': 'initialized',             # Current processing status
    'filename': None,                    # Uploaded file name
    'file_size': None,                   # File size in bytes
    'processed_data': None,              # Processed BOL data
    'error': None,                       # Error information if any
    'processing_time': None              # Time taken for processing
}
```

### Session Isolation Benefits

1. **Data Integrity**
   - Each workflow gets isolated storage
   - No data contamination between concurrent users
   - Clean state for each processing session

2. **Concurrent Processing**
   - Multiple users can process PDFs simultaneously
   - Each session has its own directory and state
   - No conflicts between different workflows

3. **Debug and Audit**
   - Each session maintains its own processing history
   - Files are preserved during the workflow
   - Easy to debug issues with specific sessions

4. **Resource Management**
   - Session cleanup removes temporary files
   - Prevents storage from growing indefinitely
   - Controlled resource usage

## 🔧 Technical Implementation Details

### Session ID Flow
```python
# Frontend provides session ID via query parameter
session_id = request.args.get('_sid')

# Backend uses this ID consistently across all operations
session_dir = f"processing_sessions/session_{timestamp}_{session_id}"
```

### Error Handling with Sessions
```python
try:
    # Process PDF
    result = process_pdf(session_data)
    session['processed_data'] = result
    session['status'] = 'processed'
except Exception as e:
    session['error'] = str(e)
    session['status'] = 'error'
    # Session state preserved for debugging
```

### Session Cleanup Strategy
```python
def clear_session(session_id):
    # 1. Remove session directory and files
    if os.path.exists(session_dir):
        shutil.rmtree(session_dir)
    
    # 2. Clear Flask session data
    session.clear()
    
    # 3. Log cleanup for audit
    logger.info(f"Session {session_id} cleaned up")
```

## 🎯 Key Benefits of This Architecture

1. **Predictable Workflow**: Clear step-by-step process
2. **Session Isolation**: Each workflow is completely isolated
3. **Error Recovery**: Sessions preserve state for debugging
4. **Resource Management**: Automatic cleanup prevents resource leaks
5. **Concurrent Processing**: Multiple users can process simultaneously
6. **Data Integrity**: No cross-contamination between workflows

## 🐛 Common Issues and Solutions

### Issue 1: Session Not Found
**Cause**: Session ID not provided or session expired
**Solution**: Always provide `_sid` parameter and create new session if needed

### Issue 2: File Not Found
**Cause**: Trying to process before uploading
**Solution**: Follow workflow order: upload → process → download

### Issue 3: Data Contamination
**Cause**: Reusing sessions between workflows
**Solution**: Use `/clear-session` and `/new-session` for fresh workflows

### Issue 4: Storage Bloat
**Cause**: Not cleaning up sessions
**Solution**: Call `/clear-session` after download completion

## 📊 Session Lifecycle Summary

```
New Session → Upload PDF → Process PDF → Download CSV → Clear Session
     ↓            ↓            ↓            ↓            ↓
   Session      File         Data        CSV         Session
   Created      Stored     Processed   Generated     Cleaned
```

This architecture ensures that each BOL processing workflow is completely isolated, traceable, and efficient while maintaining data integrity throughout the entire process. 