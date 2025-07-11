# Example: More restrictive CORS configuration for production
# Add this to your app.py if you want to restrict origins

import os
from urllib.parse import urlparse

# Define allowed origins for production
ALLOWED_ORIGINS = [
    'https://yourdomain.com',
    'https://app.yourdomain.com',
    'https://localhost:3000',  # For development
    'http://localhost:3000',   # For development
]

def get_cors_origin(request_origin):
    """Get appropriate CORS origin based on environment."""
    if os.environ.get('ENVIRONMENT') == 'production':
        # Production: Only allow specific origins
        return request_origin if request_origin in ALLOWED_ORIGINS else None
    else:
        # Development: Allow all origins
        return '*'

# Modified CORS handler for production
@app.after_request
def after_request_production(response):
    """Add headers to allow iframe embedding and CORS with origin restriction."""
    request_origin = request.headers.get('Origin')
    allowed_origin = get_cors_origin(request_origin)
    
    if allowed_origin:
        # Remove any existing CORS headers to prevent duplicates
        response.headers.pop('Access-Control-Allow-Origin', None)
        response.headers.pop('Access-Control-Allow-Headers', None)
        response.headers.pop('Access-Control-Allow-Methods', None)
        response.headers.pop('Access-Control-Allow-Credentials', None)
        response.headers.pop('Access-Control-Expose-Headers', None)
        
        # Add fresh CORS headers
        response.headers['Access-Control-Allow-Origin'] = allowed_origin
        response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,Cache-Control,Pragma,Expires,X-API-Key,X-Custom-Header,X-Session-ID'
        response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
        response.headers['Access-Control-Allow-Credentials'] = 'false'
        response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
        response.headers['X-Frame-Options'] = 'SAMEORIGIN'  # More restrictive in production
        response.headers['X-Content-Type-Options'] = 'nosniff'
    
    return response

# Example usage with session parameters
"""
External app can still use session parameters normally:

const response = await fetch('https://your-bol-api.com/upload?_sid=abc123', {
    method: 'POST',
    headers: {
        'Content-Type': 'application/json',
        'X-API-Key': 'your-api-key'  # Now allowed in CORS
    },
    body: JSON.stringify({
        file_data: base64EncodedPDF,
        filename: 'document.pdf'
    })
});
"""

# Testing CORS with session parameters
"""
# Test CORS preflight
curl -X OPTIONS \
  'https://your-bol-api.com/upload?_sid=test123' \
  -H 'Origin: https://yourdomain.com' \
  -H 'Access-Control-Request-Method: POST' \
  -H 'Access-Control-Request-Headers: Content-Type,X-API-Key'

# Should return:
# Access-Control-Allow-Origin: https://yourdomain.com
# Access-Control-Allow-Methods: GET, POST, OPTIONS, PUT, DELETE
# Access-Control-Allow-Headers: Content-Type,Authorization,X-Requested-With,Cache-Control,Pragma,Expires,X-API-Key,X-Custom-Header,X-Session-ID
""" 