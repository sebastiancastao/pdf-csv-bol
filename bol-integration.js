/**
 * BOL Service Integration - Production Ready
 * 
 * Simple, robust integration for BOL PDF+CSV processing
 * Handles all common issues: service sleeping, session management, errors
 * 
 * Usage:
 *   const processor = new BOLServiceIntegration();
 *   await processor.processFiles(pdfData, csvData);
 */

class BOLServiceIntegration {
    constructor(baseUrl = 'https://pdf-csv-bol.onrender.com') {
        this.baseUrl = baseUrl;
        this.sessionId = null;
        this.maxRetries = 3;
        this.wakeUpTimeout = 60000; // 60 seconds
    }

    /**
     * Main processing method - handles everything automatically
     * @param {File|string} pdfData - PDF file or base64 string
     * @param {File|string} csvData - CSV file or CSV string (optional)
     * @param {Object} options - Optional settings
     * @returns {Promise<Blob>} - Processed CSV blob
     */
    async processFiles(pdfData, csvData = null, options = {}) {
        console.log('🚀 Starting BOL processing...');
        
        try {
            // Step 1: Ensure service is awake
            await this.wakeUpService();
            
            // Step 2: Create new session
            this.sessionId = this.generateSessionId();
            await this.createCleanSession();
            
            // Step 3: Upload PDF
            console.log('📄 Uploading PDF...');
            await this.uploadPDF(pdfData, options.pdfFilename);
            
            // Step 4: Upload CSV if provided
            if (csvData) {
                console.log('📊 Uploading CSV...');
                await this.uploadCSV(csvData, options.csvFilename);
            }
            
            // Step 5: Download result
            console.log('📥 Downloading result...');
            const result = await this.downloadResult();
            
            console.log('✅ BOL processing completed successfully!');
            return result;
            
        } catch (error) {
            console.error('❌ BOL processing failed:', error.message);
            throw error;
        } finally {
            // Always cleanup
            await this.cleanup();
        }
    }

    /**
     * Wake up sleeping service
     */
    async wakeUpService() {
        try {
            console.log('🔍 Checking service status...');
            
            // Try quick ping first
            const pingResponse = await this.fetchWithTimeout('/ping', { method: 'GET' }, 10000);
            if (pingResponse.ok) {
                console.log('✅ Service is already awake');
                return;
            }
            
            // Service might be sleeping, try wake-up
            console.log('😴 Service appears to be sleeping, waking up...');
            const wakeResponse = await this.fetchWithTimeout('/wake-up', { method: 'GET' }, this.wakeUpTimeout);
            
            if (wakeResponse.ok) {
                const data = await wakeResponse.json();
                console.log('✅ Service woke up:', data.message);
            } else {
                console.warn('⚠️ Wake-up request failed, continuing anyway...');
            }
            
        } catch (error) {
            console.warn('⚠️ Service check failed, continuing anyway:', error.message);
        }
    }

    /**
     * Create a clean session for processing
     */
    async createCleanSession() {
        try {
            // Clear any existing session first
            await this.fetchWithTimeout(`/clear-session?_sid=${this.sessionId}`, { method: 'POST' }, 15000);
            
            // Create new session
            await this.fetchWithTimeout(`/new-session?_sid=${this.sessionId}`, { method: 'POST' }, 15000);
            
            console.log(`🆕 Created clean session: ${this.sessionId}`);
            
        } catch (error) {
            console.warn('⚠️ Session setup failed, using default session logic:', error.message);
        }
    }

    /**
     * Upload PDF file
     */
    async uploadPDF(pdfData, filename = 'document.pdf') {
        const formData = new FormData();
        
        if (pdfData instanceof File) {
            formData.append('file', pdfData);
        } else if (typeof pdfData === 'string') {
            // Handle base64 data
            const base64Data = pdfData.includes(',') ? pdfData.split(',')[1] : pdfData;
            const blob = this.base64ToBlob(base64Data, 'application/pdf');
            formData.append('file', blob, filename);
        } else {
            throw new Error('Invalid PDF data format. Expected File or base64 string.');
        }
        
        return await this.retryOperation(async () => {
            const response = await this.fetchWithTimeout(
                `/upload?_sid=${this.sessionId}`, 
                { method: 'POST', body: formData }, 
                90000 // 90 seconds for PDF processing
            );
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(`PDF upload failed: ${response.status} - ${JSON.stringify(result)}`);
            }
            
            console.log('✅ PDF processed successfully');
            return result;
        });
    }

    /**
     * Upload CSV file
     */
    async uploadCSV(csvData, filename = 'data.csv') {
        if (!this.sessionId) {
            throw new Error('No active session. PDF must be uploaded first.');
        }

        let body, headers = {};
        
        if (csvData instanceof File) {
            const formData = new FormData();
            formData.append('file', csvData);
            body = formData;
        } else if (typeof csvData === 'string') {
            body = JSON.stringify({ csv_data: csvData, filename: filename });
            headers['Content-Type'] = 'application/json';
        } else {
            throw new Error('Invalid CSV data format. Expected File or string.');
        }
        
        return await this.retryOperation(async () => {
            const response = await this.fetchWithTimeout(
                `/upload-csv?_sid=${this.sessionId}`, 
                { method: 'POST', body: body, headers: headers }, 
                60000 // 60 seconds for CSV processing
            );
            
            const result = await response.json();
            
            if (!response.ok) {
                throw new Error(`CSV upload failed: ${response.status} - ${JSON.stringify(result)}`);
            }
            
            console.log('✅ CSV merged successfully');
            return result;
        });
    }

    /**
     * Download processed result
     */
    async downloadResult() {
        if (!this.sessionId) {
            throw new Error('No active session. Files must be processed first.');
        }
        
        const response = await this.fetchWithTimeout(
            `/download-bol?_sid=${this.sessionId}`, 
            { method: 'GET' }, 
            30000
        );
        
        if (!response.ok) {
            const error = await response.json();
            throw new Error(`Download failed: ${response.status} - ${JSON.stringify(error)}`);
        }
        
        const blob = await response.blob();
        
        // Auto-download in browser
        if (typeof window !== 'undefined') {
            this.triggerBrowserDownload(blob, 'BOL_processed.csv');
        }
        
        console.log('✅ Download completed');
        return blob;
    }

    /**
     * Helper Methods
     */

    generateSessionId() {
        const timestamp = Date.now();
        const random = Math.random().toString(36).substring(2, 15);
        return `external_${timestamp}_${random}`;
    }

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

    async retryOperation(operation) {
        let lastError;
        
        for (let attempt = 1; attempt <= this.maxRetries; attempt++) {
            try {
                return await operation();
            } catch (error) {
                lastError = error;
                console.warn(`⚠️ Attempt ${attempt}/${this.maxRetries} failed:`, error.message);
                
                if (attempt < this.maxRetries) {
                    const delay = attempt * 2000; // Exponential backoff
                    console.log(`⏳ Retrying in ${delay}ms...`);
                    await new Promise(resolve => setTimeout(resolve, delay));
                }
            }
        }
        
        throw new Error(`Operation failed after ${this.maxRetries} attempts. Last error: ${lastError.message}`);
    }

    base64ToBlob(base64, mimeType) {
        const byteCharacters = atob(base64);
        const byteNumbers = new Array(byteCharacters.length);
        
        for (let i = 0; i < byteCharacters.length; i++) {
            byteNumbers[i] = byteCharacters.charCodeAt(i);
        }
        
        const byteArray = new Uint8Array(byteNumbers);
        return new Blob([byteArray], { type: mimeType });
    }

    triggerBrowserDownload(blob, filename) {
        const url = window.URL.createObjectURL(blob);
        const a = document.createElement('a');
        a.href = url;
        a.download = filename;
        document.body.appendChild(a);
        a.click();
        document.body.removeChild(a);
        window.URL.revokeObjectURL(url);
    }

    async cleanup() {
        if (this.sessionId) {
            try {
                await this.fetchWithTimeout(`/clear-session?_sid=${this.sessionId}`, { method: 'POST' }, 10000);
                console.log('🧹 Session cleaned up');
            } catch (error) {
                console.warn('⚠️ Cleanup failed (non-critical):', error.message);
            }
            this.sessionId = null;
        }
    }

    /**
     * Utility method to check service health
     */
    async checkServiceHealth() {
        try {
            const response = await this.fetchWithTimeout('/health', { method: 'GET' }, 10000);
            const data = await response.json();
            
            return {
                healthy: response.ok,
                status: data.status,
                details: data
            };
        } catch (error) {
            return {
                healthy: false,
                status: 'unavailable',
                error: error.message
            };
        }
    }
}

/**
 * Simplified usage functions
 */

// Process PDF only
async function processPDF(pdfData, options = {}) {
    const processor = new BOLServiceIntegration();
    return await processor.processFiles(pdfData, null, options);
}

// Process PDF + CSV
async function processPDFWithCSV(pdfData, csvData, options = {}) {
    const processor = new BOLServiceIntegration();
    return await processor.processFiles(pdfData, csvData, options);
}

// Check if service is available
async function isBOLServiceAvailable() {
    const processor = new BOLServiceIntegration();
    const health = await processor.checkServiceHealth();
    return health.healthy;
}

/**
 * Example usage:
 * 
 * // Simple PDF processing
 * try {
 *     await processPDF(myPdfFile);
 *     console.log('Success!');
 * } catch (error) {
 *     console.error('Failed:', error.message);
 * }
 * 
 * // PDF + CSV processing
 * try {
 *     await processPDFWithCSV(myPdfFile, myCsvFile);
 *     console.log('Success!');
 * } catch (error) {
 *     console.error('Failed:', error.message);
 * }
 * 
 * // Custom processing with options
 * const processor = new BOLServiceIntegration();
 * try {
 *     await processor.processFiles(pdfData, csvData, {
 *         pdfFilename: 'custom.pdf',
 *         csvFilename: 'custom.csv'
 *     });
 * } catch (error) {
 *     console.error('Failed:', error.message);
 * }
 */

// Export for different environments
if (typeof module !== 'undefined' && module.exports) {
    // Node.js
    module.exports = { 
        BOLServiceIntegration, 
        processPDF, 
        processPDFWithCSV, 
        isBOLServiceAvailable 
    };
} else if (typeof window !== 'undefined') {
    // Browser
    window.BOLServiceIntegration = BOLServiceIntegration;
    window.processPDF = processPDF;
    window.processPDFWithCSV = processPDFWithCSV;
    window.isBOLServiceAvailable = isBOLServiceAvailable;
}

console.log('✅ BOL Service Integration loaded - Production ready!'); 