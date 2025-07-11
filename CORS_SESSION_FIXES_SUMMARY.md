# CORS and Session Management Fixes Summary

## Problem Analysis

The external app was experiencing the following issues:

1. **CORS Header Issue**: `header 'cache-control' is not allowed according to header 'Access-Control-Allow-Headers'`
2. **Session Reuse Issue**: The app was "generating results of saved session over and over again"
3. **External Session Management**: The app sends parameters like `?_t=1752196031760&_sid=session_1752196031760_7gpks1k94&_action=new_session`

## Root Causes

1. **Missing CORS Headers**: The `Access-Control-Allow-Headers` didn't include `Cache-Control`, `Pragma`, and `Expires`
2. **Session Management Logic**: The app wasn't properly handling the `_action=new_session` parameter
3. **External App Integration**: No dedicated endpoints for external app session management

## Solutions Implemented

### 1. CORS Headers Fix

**Updated all CORS header definitions to include cache-related headers:**

```python
# Before
response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With'

# After  
response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,Cache-Control,Pragma,Expires'
```

**Fixed in three places:**
- `after_request()` function
- `@app.before_request` preflight handler
- `handle_options()` route

### 2. Session Management Enhancement

**Enhanced `get_or_create_session()` function:**

```python
def get_or_create_session():
    # Check for action parameter to force new session creation
    action = request.args.get('_action')
    force_new_session = action == 'new_session'
    
    # If force new session is requested, always create a new session
    if force_new_session:
        processor = DataProcessor()  # Creates new session
        print(f"🆕 Force creating new session due to _action=new_session: {processor.session_id}")
        return processor
    
    # Enhanced external session ID handling
    external_session_id = request.args.get('_sid') or request.args.get('session_id')
    
    if external_session_id:
        # Check if session exists and has data
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'processing_sessions', external_session_id)
        if os.path.exists(session_dir):
            processor = DataProcessor(session_id=external_session_id)
            print(f"♻️ Reusing existing external session: {external_session_id}")
        else:
            # Create new session with requested ID
            processor = DataProcessor(session_id=external_session_id)
            print(f"🆕 Creating new external session with requested ID: {external_session_id}")
        return processor
    
    # ... rest of function
```

### 3. New API Endpoints

**Added `/new-session` endpoint:**

```python
@app.route('/new-session', methods=['GET', 'POST'])
def new_session():
    """Create a new session explicitly (for external apps)."""
    processor = DataProcessor()  # Always creates new session
    
    return jsonify({
        'status': 'success',
        'session_id': processor.session_id,
        'message': 'New session created successfully',
        'ready_for_upload': True,
        'endpoints': {
            'upload': '/upload',
            'upload_base64': '/upload-base64',
            'upload_attachment': '/upload-attachment',
            'status': f'/status?_sid={processor.session_id}',
            'files': f'/files?_sid={processor.session_id}'
        }
    })
```

**Added `/debug-sessions` endpoint** for troubleshooting:
- Shows all active sessions
- Displays session files and metadata
- Shows current request parameters
- Helps debug session reuse issues

### 4. Enhanced Base Route

**Updated `/` route to handle external app requests:**

```python
@app.route('/', methods=['GET'])
def index():
    processor = get_or_create_session()
    
    # For external apps requesting JSON response
    if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
        return jsonify({
            'status': 'ready',
            'session_id': processor.session_id,
            'message': 'BOL Extractor ready for processing',
            'endpoints': { ... }
        })
    
    return render_template('index.html')
```

### 5. Enhanced Status Endpoint

**Added detailed session information:**

```python
@app.route('/status')
def get_status():
    status = {
        'session_id': processor.session_id,
        'has_processed_data': os.path.exists(csv_path),
        'session_dir': processor.session_dir,
        'session_exists': os.path.exists(processor.session_dir),
        'query_params': {
            '_sid': request.args.get('_sid'),
            '_action': request.args.get('_action'),
            '_t': request.args.get('_t')
        },
        'session_age_seconds': ...
    }
```

### 6. JavaScript Functions

**Added new global functions:**

```javascript
// Create new session explicitly
window.createNewBOLSession = function() {
    return axios.post('/new-session')
        .then(response => {
            console.log('✅ New session created:', response.data);
            return response.data;
        });
};

// Enhanced status with debugging
window.getBOLStatusDetailed = function(sessionId = null) {
    const url = sessionId ? `/status?_sid=${sessionId}` : '/status';
    return axios.get(url)
        .then(response => {
            console.log('📊 Detailed BOL Status:', response.data);
            return response.data;
        });
};
```

**Updated `BOLProcessor` object:**

```javascript
window.BOLProcessor = {
    // ... existing functions
    createNewSession: window.createNewBOLSession,
    getStatusDetailed: window.getBOLStatusDetailed,
    // ... other functions
};
```

## Testing

Created `test_cors_and_sessions.py` to verify:

1. **CORS preflight with cache-control headers**
2. **New session creation endpoint**
3. **Base URL with `_action=new_session` parameter**
4. **Status endpoint with session parameters**
5. **Debug sessions endpoint**
6. **External app simulation with cache headers**

## How External Apps Should Use This

### Option 1: Explicit New Session Creation
```javascript
// Create a new session explicitly
const sessionData = await fetch('/new-session', {method: 'POST'}).then(r => r.json());
console.log('New session:', sessionData.session_id);
```

### Option 2: Force New Session with Parameters
```javascript
// Force new session with URL parameters
const response = await fetch(`/?_action=new_session&format=json`);
const data = await response.json();
console.log('New session:', data.session_id);
```

### Option 3: Use JavaScript Functions
```javascript
// Use the global functions
const sessionData = await window.createNewBOLSession();
console.log('New session:', sessionData.session_id);
```

## Expected Behavior Now

1. **CORS Headers**: All cache-related headers (`Cache-Control`, `Pragma`, `Expires`) are now allowed
2. **Session Management**: 
   - `_action=new_session` parameter forces creation of new sessions
   - External session IDs are properly handled
   - No more session reuse when new session is explicitly requested
3. **External App Integration**: 
   - Multiple endpoints for session management
   - JSON responses for external apps
   - Debugging capabilities

## Troubleshooting

Use the new endpoints to debug issues:

```bash
# Check CORS headers
curl -X OPTIONS -H "Access-Control-Request-Headers: Cache-Control" http://localhost:5000/

# Create new session
curl -X POST http://localhost:5000/new-session

# Check session status
curl "http://localhost:5000/status?_sid=your_session_id"

# Debug all sessions
curl http://localhost:5000/debug-sessions
```

## Files Modified

- `app.py`: Main fixes for CORS headers and session management
- `templates/index.html`: Added new JavaScript functions
- `test_cors_and_sessions.py`: Comprehensive testing script (new file)

The external app should now work without CORS errors and properly create new sessions when needed. 