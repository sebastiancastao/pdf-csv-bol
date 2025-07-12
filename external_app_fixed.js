/**
 * CORRECTED BOL Processor External App Integration
 * 
 * CRITICAL: PDF and CSV must use the SAME session to work together!
 * The CSV processing depends on data created by the PDF processing.
 */

class BOLProcessor {
    constructor(baseUrl = 'https://your-bol-service.render.com') {
        this.baseUrl = baseUrl;
        this.sessionId = null;
    }

    /**
     * SIMPLIFIED WORKFLOW - Maintains sessions automatically
     * 
     * Step 1: Upload PDF (creates session and processes PDF)
     * Step 2: Upload CSV (uses SAME session to merge data)  
     * Step 3: Download (gets final result from SAME session)
     */

    // Generate a unique session ID for this workflow
    generateSessionId() {
        const timestamp = Date.now();
        const random = Math.random().toString(36).substring(2, 15);
        return `external_${timestamp}_${random}`;
    }

    // Step 1: Upload and process PDF
    async uploadPDF(pdfData, filename = 'document.pdf') {
        try {
            // Generate new session for this workflow
            this.sessionId = this.generateSessionId();
            
            console.log(`📤 Starting PDF upload with session: ${this.sessionId}`);
            
            const formData = new FormData();
            
            // Handle different data types
            if (pdfData instanceof File) {
                formData.append('file', pdfData);
            } else if (typeof pdfData === 'string') {
                // Convert base64 to blob
                const base64Data = pdfData.includes(',') ? pdfData.split(',')[1] : pdfData;
                const byteCharacters = atob(base64Data);
                const byteNumbers = new Array(byteCharacters.length);
                for (let i = 0; i < byteCharacters.length; i++) {
                    byteNumbers[i] = byteCharacters.charCodeAt(i);
                }
                const byteArray = new Uint8Array(byteNumbers);
                const blob = new Blob([byteArray], { type: 'application/pdf' });
                formData.append('file', blob, filename);
            }
            
            // CRITICAL: Use session ID in query parameter
            const url = `${this.baseUrl}/upload?_sid=${this.sessionId}`;
            
            const response = await fetch(url, {
                method: 'POST',
                body: formData
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'PDF upload failed');
            }
            
            console.log(`✅ PDF processed successfully with session: ${this.sessionId}`);
            return result;
            
        } catch (error) {
            console.error('❌ PDF upload failed:', error);
            throw error;
        }
    }

    // Step 2: Upload and merge CSV (REQUIRES PDF to be processed first!)
    async uploadCSV(csvData, filename = 'data.csv') {
        if (!this.sessionId) {
            throw new Error('❌ No active session! Must upload PDF first.');
        }
        
        try {
            console.log(`📄 Uploading CSV to session: ${this.sessionId}`);
            
            let body;
            let contentType;
            
            if (csvData instanceof File) {
                // File upload
                const formData = new FormData();
                formData.append('file', csvData);
                body = formData;
                contentType = undefined; // Let browser set multipart boundary
            } else if (typeof csvData === 'string') {
                // JSON upload with CSV content
                body = JSON.stringify({
                    csv_data: csvData,
                    filename: filename
                });
                contentType = 'application/json';
            } else {
                throw new Error('Invalid CSV data format');
            }
            
            // CRITICAL: Use SAME session ID
            const url = `${this.baseUrl}/upload-csv?_sid=${this.sessionId}`;
            
            const response = await fetch(url, {
                method: 'POST',
                body: body,
                ...(contentType && { headers: { 'Content-Type': contentType } })
            });
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(result.error || 'CSV upload failed');
            }
            
            console.log(`✅ CSV merged successfully with session: ${this.sessionId}`);
            return result;
            
        } catch (error) {
            console.error('❌ CSV upload failed:', error);
            throw error;
        }
    }

    // Step 3: Download final processed file
    async download() {
        if (!this.sessionId) {
            throw new Error('❌ No active session! Must process files first.');
        }
        
        try {
            console.log(`📥 Downloading from session: ${this.sessionId}`);
            
            // CRITICAL: Use SAME session ID
            const url = `${this.baseUrl}/download-bol?_sid=${this.sessionId}`;
            
            const response = await fetch(url);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Download failed');
            }
            
            // Return the blob for download
            const blob = await response.blob();
            
            // Trigger download in browser
            const downloadUrl = window.URL.createObjectURL(blob);
            const a = document.createElement('a');
            a.href = downloadUrl;
            a.download = 'BOL_processed.csv';
            document.body.appendChild(a);
            a.click();
            document.body.removeChild(a);
            window.URL.revokeObjectURL(downloadUrl);
            
            console.log(`✅ Download completed from session: ${this.sessionId}`);
            
            // Auto-cleanup after successful download
            await this.cleanup();
            
            return blob;
            
        } catch (error) {
            console.error('❌ Download failed:', error);
            throw error;
        }
    }

    // Optional: Clean up session after processing
    async cleanup() {
        if (!this.sessionId) return;
        
        try {
            console.log(`🧹 Cleaning up session: ${this.sessionId}`);
            
            const url = `${this.baseUrl}/auto-reset?_sid=${this.sessionId}`;
            await fetch(url, { method: 'POST' });
            
            this.sessionId = null;
            console.log('✅ Session cleaned up');
            
        } catch (error) {
            console.warn('⚠️ Cleanup failed (non-critical):', error);
        }
    }

    // Get status of current session
    async getStatus() {
        if (!this.sessionId) {
            return { error: 'No active session' };
        }
        
        try {
            const url = `${this.baseUrl}/status?_sid=${this.sessionId}`;
            const response = await fetch(url);
            return await response.json();
        } catch (error) {
            console.error('❌ Status check failed:', error);
            return { error: error.message };
        }
    }

    // Complete workflow: PDF + CSV + Download
    async processComplete(pdfData, csvData, pdfFilename = 'document.pdf', csvFilename = 'data.csv') {
        try {
            console.log('🚀 Starting complete BOL processing workflow...');
            
            // Step 1: Process PDF
            await this.uploadPDF(pdfData, pdfFilename);
            
            // Step 2: Merge CSV (optional - only if CSV data provided)
            if (csvData) {
                await this.uploadCSV(csvData, csvFilename);
            }
            
            // Step 3: Download result
            const result = await this.download();
            
            console.log('✅ Complete workflow finished successfully!');
            return result;
            
        } catch (error) {
            console.error('❌ Complete workflow failed:', error);
            await this.cleanup(); // Clean up on failure
            throw error;
        }
    }
}

// Usage Examples:

// Example 1: PDF only
async function processPDFOnly(pdfData) {
    const processor = new BOLProcessor('https://your-bol-service.render.com');
    
    try {
        await processor.uploadPDF(pdfData);
        await processor.download();
    } catch (error) {
        console.error('Processing failed:', error);
    }
}

// Example 2: PDF + CSV workflow  
async function processPDFWithCSV(pdfData, csvData) {
    const processor = new BOLProcessor('https://your-bol-service.render.com');
    
    try {
        // CRITICAL: Must be in this exact order with same session
        await processor.uploadPDF(pdfData);      // Creates session, processes PDF
        await processor.uploadCSV(csvData);      // Uses SAME session, merges data  
        await processor.download();              // Downloads from SAME session
    } catch (error) {
        console.error('Processing failed:', error);
    }
}

// Example 3: Complete workflow (recommended)
async function processCompleteWorkflow(pdfData, csvData = null) {
    const processor = new BOLProcessor('https://your-bol-service.render.com');
    
    try {
        await processor.processComplete(pdfData, csvData);
    } catch (error) {
        console.error('Processing failed:', error);
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = BOLProcessor;
} else {
    window.BOLProcessor = BOLProcessor;
} 