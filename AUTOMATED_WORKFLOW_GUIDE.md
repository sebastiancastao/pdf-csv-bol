# Automated Workflow Guide for BOL Extractor

## Overview

This guide provides best practices for automated applications using the BOL Extractor API to prevent session contamination and ensure reliable processing results.

## The Session Contamination Problem

**What is Session Contamination?**
- When old files remain in a session directory from previous processing runs
- Causes new requests to merge with stale data instead of fresh data
- Results in incorrect output that doesn't match the input documents

**Why Does This Happen?**
- Automated workflows often reuse session IDs without proper cleanup
- Session directories accumulate files from multiple processing runs
- CSV upload merges with old `combined_data.csv` instead of fresh PDF data

## Manual vs Automated Workflow Differences

### Manual Workflow (Always Works)
```
1. User visits website → Fresh Flask session created
2. Upload PDF → Clean session directory
3. Upload CSV → Merges with fresh PDF data
4. Download → Auto-reset cleans session
```

### Automated Workflow (Prone to Contamination)
```
1. External app calls API with ?_sid=xyz → May reuse contaminated session
2. Upload PDF → Old files may remain
3. Upload CSV → Merges with STALE data
4. Download → Wrong output
```

## Recommended Automated Workflow

### Option 1: Robust Workflow (Recommended)
```javascript
const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;
const API_BASE = 'https://your-api.com';

// 1. Clean session before starting
await fetch(`${API_BASE}/auto-clean-session?_sid=${sessionId}`, {
  method: 'POST'
});

// 2. Upload PDF
const pdfResponse = await fetch(`${API_BASE}/upload?_sid=${sessionId}`, {
  method: 'POST',
  body: pdfFormData
});

// 3. Upload CSV
const csvResponse = await fetch(`${API_BASE}/upload-csv?_sid=${sessionId}`, {
  method: 'POST',
  body: csvFormData
});

// 4. Download results
const downloadResponse = await fetch(`${API_BASE}/download?_sid=${sessionId}`);

// 5. Clean up
await fetch(`${API_BASE}/clear-session?_sid=${sessionId}`, {
  method: 'POST'
});
```

### Option 2: Ultra-Safe Workflow
```javascript
const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// 1. Clear any existing session
await fetch(`${API_BASE}/clear-session?_sid=${sessionId}`, {
  method: 'POST'
});

// 2. Create fresh session
await fetch(`${API_BASE}/new-session?_sid=${sessionId}`, {
  method: 'POST'
});

// 3. Validate session is clean
const validation = await fetch(`${API_BASE}/validate-session?_sid=${sessionId}`);
const validationData = await validation.json();

if (validationData.contamination_risk !== 'none') {
  throw new Error('Session contamination detected');
}

// 4. Process documents
// ... upload PDF and CSV ...

// 5. Clean up
await fetch(`${API_BASE}/clear-session?_sid=${sessionId}`, {
  method: 'POST'
});
```

## API Enhancements for Automated Workflows

### Automatic Session Cleanup
- **PDF Upload**: Automatically cleans contaminated sessions before processing
- **Smart Detection**: Identifies external vs internal sessions
- **Safe Processing**: Ensures fresh data for each workflow

### New Endpoints for Automation

#### `/auto-clean-session`
```javascript
POST /auto-clean-session?_sid=your_session_id
```
- Automatically detects and removes contaminated files
- Safe to call before any processing workflow
- Returns detailed cleanup results

#### Enhanced `/upload` Response
```json
{
  "message": "PDF processed successfully",
  "filename": "document.pdf",
  "session_id": "your_session_id",
  "session_cleaned": true,
  "ready_for_csv": true
}
```

#### Enhanced `/upload-csv` Validation
```json
{
  "message": "CSV data mapped successfully",
  "status": "success",
  "session_id": "your_session_id",
  "session_validation": {
    "session_type": "external",
    "has_pdf_data": true,
    "contamination_risk": "low"
  }
}
```

## Best Practices for Automated Workflows

### 1. Always Use Unique Session IDs
```javascript
// Good: Always unique
const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// Bad: Static session ID
const sessionId = 'my-app-session';
```

### 2. Clean Sessions Before Processing
```javascript
// Always clean before starting
await fetch(`${API_BASE}/auto-clean-session?_sid=${sessionId}`, {
  method: 'POST'
});
```

### 3. Validate Session State
```javascript
const validation = await fetch(`${API_BASE}/validate-session?_sid=${sessionId}`);
const data = await validation.json();

if (data.contamination_risk === 'high') {
  // Clean and retry
}
```

### 4. Handle Errors Gracefully
```javascript
try {
  const response = await fetch(`${API_BASE}/upload?_sid=${sessionId}`, {
    method: 'POST',
    body: formData
  });
  
  if (!response.ok) {
    const error = await response.json();
    if (error.requires_pdf_first) {
      // Handle missing PDF data
    }
  }
} catch (error) {
  // Clean up on error
  await fetch(`${API_BASE}/clear-session?_sid=${sessionId}`, {
    method: 'POST'
  });
}
```

### 5. Always Clean Up After Processing
```javascript
// Always clean up, even on error
try {
  // ... processing workflow ...
} finally {
  await fetch(`${API_BASE}/clear-session?_sid=${sessionId}`, {
    method: 'POST'
  });
}
```

## Common Pitfalls to Avoid

### ❌ Don't Do This
```javascript
// Bad: Reusing session IDs
const sessionId = 'my-fixed-session';

// Bad: No cleanup
await fetch(`${API_BASE}/upload?_sid=${sessionId}`, {...});
// Session remains contaminated for next use

// Bad: Ignoring validation
await fetch(`${API_BASE}/upload-csv?_sid=${sessionId}`, {...});
// May merge with stale data
```

### ✅ Do This Instead
```javascript
// Good: Unique session IDs
const sessionId = `session_${Date.now()}_${Math.random().toString(36).substr(2, 9)}`;

// Good: Always clean first
await fetch(`${API_BASE}/auto-clean-session?_sid=${sessionId}`, {
  method: 'POST'
});

// Good: Validate responses
const response = await fetch(`${API_BASE}/upload-csv?_sid=${sessionId}`, {...});
const data = await response.json();
if (data.session_validation.contamination_risk !== 'low') {
  // Handle contamination
}
```

## Error Handling and Recovery

### Session Contamination Recovery
```javascript
async function processWithRecovery(sessionId, pdfData, csvData) {
  try {
    // Try normal processing
    await processDocuments(sessionId, pdfData, csvData);
  } catch (error) {
    if (error.message.includes('contamination')) {
      // Clean and retry
      await fetch(`${API_BASE}/clear-session?_sid=${sessionId}`, {
        method: 'POST'
      });
      
      // Wait a moment and retry
      await new Promise(resolve => setTimeout(resolve, 1000));
      await processDocuments(sessionId, pdfData, csvData);
    } else {
      throw error;
    }
  }
}
```

### Validation Before Processing
```javascript
async function validateBeforeProcess(sessionId) {
  const validation = await fetch(`${API_BASE}/validate-session?_sid=${sessionId}`);
  const data = await validation.json();
  
  if (data.contamination_risk === 'high') {
    await fetch(`${API_BASE}/auto-clean-session?_sid=${sessionId}`, {
      method: 'POST'
    });
  }
  
  return data;
}
```

## Testing Your Automated Workflow

### Unit Test Example
```javascript
describe('BOL Processing Workflow', () => {
  it('should process documents without contamination', async () => {
    const sessionId = `test_${Date.now()}`;
    
    // Clean start
    await fetch(`${API_BASE}/auto-clean-session?_sid=${sessionId}`, {
      method: 'POST'
    });
    
    // Process documents
    const pdfResponse = await fetch(`${API_BASE}/upload?_sid=${sessionId}`, {
      method: 'POST',
      body: testPdfData
    });
    
    expect(pdfResponse.ok).toBe(true);
    
    const csvResponse = await fetch(`${API_BASE}/upload-csv?_sid=${sessionId}`, {
      method: 'POST',
      body: testCsvData
    });
    
    expect(csvResponse.ok).toBe(true);
    
    // Verify session is clean
    const validation = await fetch(`${API_BASE}/validate-session?_sid=${sessionId}`);
    const validationData = await validation.json();
    
    expect(validationData.contamination_risk).toBe('low');
    
    // Clean up
    await fetch(`${API_BASE}/clear-session?_sid=${sessionId}`, {
      method: 'POST'
    });
  });
});
```

## Monitoring and Logging

### Log Session Activities
```javascript
async function loggedProcessing(sessionId, pdfData, csvData) {
  console.log(`Starting processing for session: ${sessionId}`);
  
  try {
    // Clean session
    const cleanResponse = await fetch(`${API_BASE}/auto-clean-session?_sid=${sessionId}`, {
      method: 'POST'
    });
    const cleanData = await cleanResponse.json();
    
    if (cleanData.cleanup_performed) {
      console.log(`Cleaned contaminated session: ${sessionId}`);
    }
    
    // Process documents
    const pdfResponse = await fetch(`${API_BASE}/upload?_sid=${sessionId}`, {
      method: 'POST',
      body: pdfData
    });
    
    if (pdfResponse.ok) {
      console.log(`PDF processed successfully for session: ${sessionId}`);
    }
    
    // Continue with CSV processing...
    
  } catch (error) {
    console.error(`Processing failed for session ${sessionId}:`, error);
    throw error;
  }
}
```

## Summary

The key to reliable automated workflows is **proper session management**:

1. **Always use unique session IDs** for each processing run
2. **Clean sessions before processing** using `/auto-clean-session`
3. **Validate session state** before critical operations
4. **Handle errors gracefully** and clean up on failures
5. **Monitor and log** session activities for debugging

Following these practices will eliminate session contamination issues and ensure your automated workflows produce consistent, reliable results. 