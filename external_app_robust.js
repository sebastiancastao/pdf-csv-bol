/**
 * ROBUST BOL Processor External App Integration
 * 
 * Handles:
 * - Service sleeping (Render.com free tier)
 * - Session contamination 
 * - PDF+CSV workflow dependencies
 * - Comprehensive error handling
 * - Automatic retries and fallbacks
 */

class RobustBOLProcessor {
    constructor(baseUrl = 'https://pdf-csv-bol.onrender.com') {
        this.baseUrl = baseUrl;
        this.sessionId = null;
        this.maxRetries = 3;
        this.wakeUpTimeout = 60000; // 60 seconds for service wake-up
    }

    /**
     * Check if service is awake and wake it up if needed
     */
    async ensureServiceAwake() {
        try {
            console.log('🔍 Checking if BOL service is awake...');
            
            // Try ping first (faster)
            const pingResponse = await this.fetchWithTimeout('/ping', { method: 'GET' }, 10000);
            
            if (pingResponse.ok) {
                console.log('✅ BOL service is already awake');
                return true;
            }
            
            console.log('😴 Service appears to be sleeping, attempting wake-up...');
            
            // Try wake-up endpoint
            const wakeResponse = await this.fetchWithTimeout('/wake-up', { method: 'GET' }, this.wakeUpTimeout);
            
            if (wakeResponse.ok) {
                const wakeData = await wakeResponse.json();
                console.log('✅ Service woke up successfully:', wakeData.message);
                return true;
            }
            
            throw new Error('Service failed to wake up');
            
        } catch (error) {
            console.warn('⚠️ Service wake-up check failed:', error.message);
            console.log('🔄 Will proceed with processing and handle errors as they come...');
            return false; // Continue anyway - might work
        }
    }

    /**
     * Fetch with timeout and retry logic
     */
    async fetchWithTimeout(endpoint, options = {}, timeout = 30000) {
        const controller = new AbortController();
        const id = setTimeout(() => controller.abort(), timeout);
        
        try {
            const url = endpoint.startsWith('http') ? endpoint : `${this.baseUrl}${endpoint}`;
            const response = await fetch(url, {
                ...options,
                signal: controller.signal
            });
            clearTimeout(id);
            return response;
        } catch (error) {
            clearTimeout(id);
            if (error.name === 'AbortError') {
                throw new Error(`Request timeout after ${timeout}ms`);
            }
            throw error;
        }
    }

    /**
     * Generate a unique session ID for this workflow
     */
    generateSessionId() {
        const timestamp = Date.now();
        const random = Math.random().toString(36).substring(2, 15);
        return `external_${timestamp}_${random}`;
    }

    /**
     * Clear any existing contaminated session
     */
    async clearSession(sessionId = null) {
        try {
            const clearUrl = sessionId ? `/clear-session?_sid=${sessionId}` : '/clear-session';
            const response = await this.fetchWithTimeout(clearUrl, { method: 'POST' }, 15000);
            
            if (response.ok) {
                const result = await response.json();
                console.log('🧹 Session cleared:', result.message);
                return true;
            }
            
            console.warn('⚠️ Session clear request failed, continuing anyway...');
            return false;
            
        } catch (error) {
            console.warn('⚠️ Session clear failed:', error.message);
            return false;
        }
    }

    /**
     * Create a new clean session
     */
    async createNewSession(sessionId) {
        try {
            const response = await this.fetchWithTimeout(`/new-session?_sid=${sessionId}`, { method: 'POST' }, 15000);
            
            if (response.ok) {
                const result = await response.json();
                console.log('🆕 New session created:', result.message);
                return true;
            }
            
            console.warn('⚠️ New session creation failed, using existing session logic...');
            return false;
            
        } catch (error) {
            console.warn('⚠️ New session creation failed:', error.message);
            return false;
        }
    }

    /**
     * Upload PDF with robust error handling
     */
    async uploadPDF(pdfData, filename = 'document.pdf') {
        let lastError = null;
        
        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                console.log(`📤 PDF upload attempt ${attempt}/${this.maxRetries}`);
                
                // Generate new session for this workflow
                this.sessionId = this.generateSessionId();
                console.log(`🔧 Using session: ${this.sessionId}`);
                
                // Clear any existing contaminated session
                await this.clearSession(this.sessionId);
                
                // Create new clean session 
                await this.createNewSession(this.sessionId);
                
                // Prepare form data
                const formData = new FormData();
                
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
                } else {
                    throw new Error('Invalid PDF data format');
                }
                
                // Upload with session ID
                const url = `/upload?_sid=${this.sessionId}`;
                const response = await this.fetchWithTimeout(url, {
                    method: 'POST',
                    body: formData
                }, 90000); // 90 seconds for PDF processing
                
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(`${response.status} - ${JSON.stringify(result)}`);
                }
                
                console.log(`✅ PDF processed successfully: ${result.message}`);
                return result;
                
            } catch (error) {
                lastError = error;
                console.error(`❌ PDF upload attempt ${attempt} failed:`, error.message);
                
                if (attempt < this.maxRetries) {
                    const delay = attempt * 2000; // Increasing delay
                    console.log(`⏳ Retrying in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
        
        throw new Error(`PDF upload failed after ${this.maxRetries} attempts. Last error: ${lastError.message}`);
    }

    /**
     * Upload CSV with robust error handling
     */
    async uploadCSV(csvData, filename = 'data.csv') {
        if (!this.sessionId) {
            throw new Error('❌ No active session! Must upload PDF first.');
        }

        let lastError = null;
        
        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                console.log(`📄 CSV upload attempt ${attempt}/${this.maxRetries} to session: ${this.sessionId}`);
                
                let body;
                let contentType;
                
                if (csvData instanceof File) {
                    const formData = new FormData();
                    formData.append('file', csvData);
                    body = formData;
                    contentType = undefined;
                } else if (typeof csvData === 'string') {
                    body = JSON.stringify({
                        csv_data: csvData,
                        filename: filename
                    });
                    contentType = 'application/json';
                } else {
                    throw new Error('Invalid CSV data format');
                }
                
                const url = `/upload-csv?_sid=${this.sessionId}`;
                const response = await this.fetchWithTimeout(url, {
                    method: 'POST',
                    body: body,
                    ...(contentType && { headers: { 'Content-Type': contentType } })
                }, 60000); // 60 seconds for CSV processing
                
                const result = await response.json();
                
                if (!response.ok) {
                    throw new Error(`${response.status} - ${JSON.stringify(result)}`);
                }
                
                console.log(`✅ CSV merged successfully: ${result.message}`);
                return result;
                
            } catch (error) {
                lastError = error;
                console.error(`❌ CSV upload attempt ${attempt} failed:`, error.message);
                
                if (attempt < this.maxRetries) {
                    const delay = attempt * 1000;
                    console.log(`⏳ Retrying in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
        
        throw new Error(`CSV upload failed after ${this.maxRetries} attempts. Last error: ${lastError.message}`);
    }

    /**
     * Download processed file
     */
    async download() {
        if (!this.sessionId) {
            throw new Error('❌ No active session! Must process files first.');
        }
        
        try {
            console.log(`📥 Downloading from session: ${this.sessionId}`);
            
            const url = `/download-bol?_sid=${this.sessionId}`;
            const response = await this.fetchWithTimeout(url, { method: 'GET' }, 30000);
            
            if (!response.ok) {
                const error = await response.json();
                throw new Error(error.error || 'Download failed');
            }
            
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

    /**
     * Clean up session after processing
     */
    async cleanup() {
        if (!this.sessionId) return;
        
        try {
            console.log(`🧹 Cleaning up session: ${this.sessionId}`);
            
            await this.clearSession(this.sessionId);
            this.sessionId = null;
            console.log('✅ Session cleaned up');
            
        } catch (error) {
            console.warn('⚠️ Cleanup failed (non-critical):', error);
        }
    }

    /**
     * Complete robust workflow with comprehensive error handling
     */
    async processComplete(pdfData, csvData = null, pdfFilename = 'document.pdf', csvFilename = 'data.csv') {
        try {
            console.log('🚀 Starting robust BOL processing workflow...');
            
            // Step 1: Ensure service is awake
            await this.ensureServiceAwake();
            
            // Step 2: Process PDF
            console.log('📄 Step 1: Processing PDF...');
            await this.uploadPDF(pdfData, pdfFilename);
            
            // Step 3: Merge CSV (optional)
            if (csvData) {
                console.log('📊 Step 2: Merging CSV data...');
                await this.uploadCSV(csvData, csvFilename);
            }
            
            // Step 4: Download result
            console.log('📥 Step 3: Downloading result...');
            const result = await this.download();
            
            console.log('✅ Complete robust workflow finished successfully!');
            return result;
            
        } catch (error) {
            console.error('❌ Robust workflow failed:', error);
            await this.cleanup(); // Clean up on failure
            throw error;
        }
    }

    /**
     * Get detailed status for debugging
     */
    async getDetailedStatus() {
        try {
            const url = this.sessionId ? `/status?_sid=${this.sessionId}` : '/status';
            const response = await this.fetchWithTimeout(url, { method: 'GET' }, 10000);
            return await response.json();
        } catch (error) {
            return { error: error.message };
        }
    }
}

// Usage Examples:

// Example 1: Simple PDF processing
async function processSimplePDF(pdfData) {
    const processor = new RobustBOLProcessor();
    
    try {
        const result = await processor.processComplete(pdfData);
        console.log('✅ Processing completed successfully');
        return result;
    } catch (error) {
        console.error('❌ Processing failed:', error.message);
        throw error;
    }
}

// Example 2: PDF + CSV workflow
async function processPDFWithCSV(pdfData, csvData) {
    const processor = new RobustBOLProcessor();
    
    try {
        const result = await processor.processComplete(pdfData, csvData);
        console.log('✅ Processing completed successfully');
        return result;
    } catch (error) {
        console.error('❌ Processing failed:', error.message);
        throw error;
    }
}

// Example 3: Manual step-by-step processing with error handling
async function processManualSteps(pdfData, csvData = null) {
    const processor = new RobustBOLProcessor();
    
    try {
        // Wake up service
        await processor.ensureServiceAwake();
        
        // Upload PDF
        await processor.uploadPDF(pdfData);
        
        // Upload CSV if provided
        if (csvData) {
            await processor.uploadCSV(csvData);
        }
        
        // Download result
        await processor.download();
        
        console.log('✅ Manual processing completed successfully');
        
    } catch (error) {
        console.error('❌ Manual processing failed:', error.message);
        
        // Get detailed status for debugging
        const status = await processor.getDetailedStatus();
        console.log('🔍 Service status:', status);
        
        throw error;
    }
}

// Export for use
if (typeof module !== 'undefined' && module.exports) {
    module.exports = RobustBOLProcessor;
} else {
    window.RobustBOLProcessor = RobustBOLProcessor;
}

console.log('🚀 Robust BOL Processor loaded - handles service sleeping, session contamination, and errors!'); 