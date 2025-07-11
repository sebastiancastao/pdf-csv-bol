# Auto-Reset Functionality for BOL Extractor

## Overview

The BOL Extractor application now includes comprehensive auto-reset functionality that automatically cleans up and resets the application state after the complete workflow is finished. This ensures a fresh start for each new processing cycle.

## How It Works

### Complete Workflow Process
1. **PDF Upload**: User uploads a PDF file
2. **PDF Processing**: System extracts data and creates text files
3. **CSV Upload**: User uploads CSV/Excel file for data mapping
4. **CSV Processing**: System merges and processes the data
5. **Download**: User downloads the final combined data CSV
6. **Auto-Reset**: System automatically cleans up and resets ✨

### Auto-Reset Trigger Points

The auto-reset functionality is triggered after:
- ✅ PDF processing is complete
- ✅ CSV processing is complete
- ✅ Combined data file is downloaded
- ✅ Download has been initiated (2-second delay)

## Technical Implementation

### Frontend (Vue.js)
- **`initiateDownloadAndCleanup()`**: Starts download and schedules cleanup
- **`performAutoReset()`**: Calls the backend auto-reset endpoint
- **`resetAppState()`**: Resets all Vue component state to initial values
- **Global access**: Vue app available as `window.vueApp`

### Backend (Flask)
- **`/auto-reset`**: New dedicated endpoint for automatic reset
- **`/clear-session`**: Enhanced session clearing with multi-source support
- **Session management**: Improved handling of external session IDs

### Key Features
1. **Automatic Cleanup**: Removes session files and directories
2. **State Reset**: Clears all frontend form data and progress
3. **Fresh Session**: Creates new session ID for next workflow
4. **Error Handling**: Graceful fallback if auto-reset fails
5. **External App Support**: Works with external applications via API

## API Endpoints

### POST /auto-reset
Dedicated endpoint for automatic reset after download completion.

**Response:**
```json
{
  "status": "success",
  "message": "Auto-reset completed successfully",
  "old_session_id": "session_20250101_123456_abc123",
  "new_session_id": "session_20250101_123500_def456",
  "ready_for_next_workflow": true
}
```

### POST /clear-session
Enhanced session clearing with multi-source support.

**Response:**
```json
{
  "status": "success",
  "message": "Session cleared and ready for new workflow",
  "old_session_id": "session_20250101_123456_abc123",
  "new_session_id": "session_20250101_123500_def456",
  "cleanup_completed": true
}
```

## JavaScript Functions

### For Main Application
- `downloadCSV()`: Triggers download with auto-reset
- `initiateDownloadAndCleanup()`: Manages the download and cleanup process
- `performAutoReset()`: Calls backend auto-reset endpoint
- `resetAppState()`: Resets Vue component state

### For External Applications
- `window.downloadBOLFileAndReset(filename)`: Download and auto-reset
- `window.resetBOLApplication()`: Full application reset
- `window.completeBOLWorkflow(filename)`: Complete workflow with cleanup
- `window.BOLProcessor.downloadAndReset`: Available in BOLProcessor object

## User Experience

### What Users See
1. **Download Initiated**: "Download started. Preparing for next workflow..."
2. **Auto-Reset**: "🎉 Process complete! Ready for next workflow."
3. **Fresh State**: Form returns to initial state with Step 1 visible
4. **Clear Interface**: All file inputs cleared, progress reset to 0%

### Timing
- **Download starts**: Immediately when download button is clicked
- **Cleanup delay**: 2-second delay to ensure download initiates
- **Reset completion**: ~3-5 seconds total
- **Success message**: Shows for 3 seconds then clears

## Error Handling

### Graceful Degradation
- If auto-reset fails, user gets error message
- Fallback: "Please refresh the page manually"
- Backend session still gets cleaned up if possible
- No data loss - files are already downloaded

### Error Messages
- "Auto-reset failed. Please refresh the page manually."
- "Download completed, but cleanup failed. You may need to refresh manually."
- "Failed to clear session properly"

## Benefits

### For Users
- **Seamless Experience**: No manual refresh needed
- **Clean Start**: Fresh interface for each workflow
- **No Confusion**: Clear state between different BOL processes
- **Faster Workflow**: Immediate readiness for next task

### For Developers
- **Clean State**: No leftover data between sessions
- **Memory Management**: Automatic cleanup prevents memory leaks
- **Session Isolation**: Each workflow gets its own session
- **API Consistency**: Same behavior for web and external apps

## External App Integration

External applications can use the auto-reset functionality:

```javascript
// Basic download and reset
window.downloadBOLFileAndReset('my_bol_file.csv');

// Complete workflow with cleanup
window.completeBOLWorkflow();

// Full application reset
window.resetBOLApplication();

// Using BOLProcessor object
window.BOLProcessor.downloadAndReset('file.csv');
window.BOLProcessor.completeWorkflow();
window.BOLProcessor.resetApplication();
```

## Configuration

### Session Management
- **Session timeout**: 1 hour (3600 seconds)
- **Cookie settings**: Configured for cross-origin access
- **External sessions**: Supported via `_sid` or `session_id` query parameters

### File Cleanup
- **Automatic**: Session directories completely removed
- **Timing**: Immediate upon reset trigger
- **Scope**: Only current session files, not other active sessions

## Testing

### Manual Testing
1. Upload a PDF file
2. Upload a CSV file  
3. Download the combined data
4. Verify auto-reset occurs
5. Confirm interface returns to Step 1
6. Verify fresh session ID created

### API Testing
```bash
# Test auto-reset endpoint
curl -X POST http://localhost:5000/auto-reset

# Test enhanced clear-session
curl -X POST http://localhost:5000/clear-session
```

## Future Enhancements

### Possible Improvements
- **Configurable timing**: Allow adjustment of reset delay
- **User preference**: Option to disable auto-reset
- **Progress indicator**: Show countdown to reset
- **Batch processing**: Handle multiple files with single reset
- **Analytics**: Track reset success/failure rates

### Integration Options
- **Webhook support**: Notify external systems of reset
- **Queue management**: Handle multiple concurrent resets
- **Backup options**: Optional file retention before cleanup
- **Audit logging**: Track all reset operations

## Summary

The auto-reset functionality provides a seamless, automated experience that ensures the BOL Extractor application is always ready for the next workflow. It combines robust backend session management with intuitive frontend state management, creating a professional and user-friendly processing experience.

**Key Benefits:**
- ✅ Automatic cleanup after download
- ✅ Fresh state for each workflow
- ✅ No manual refresh required
- ✅ Works with external applications
- ✅ Comprehensive error handling
- ✅ Professional user experience 