import os
import csv
from pathlib import Path
import platform
import pandas as pd
from io import StringIO
from flask import Flask, render_template, request, send_file, jsonify
from werkzeug.utils import secure_filename
from pdf_processor import PDFProcessor
from data_processor import DataProcessor
from csv_exporter import CSVExporter
from config import OUTPUT_CSV_NAME  # e.g. "combined_data.csv"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.dirname(os.path.abspath(__file__))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size

# Allowed extensions for PDF upload
ALLOWED_PDF_EXTENSIONS = {'pdf'}
# Allowed extensions for CSV/XLSX upload
ALLOWED_CSV_EXTENSIONS = {'csv', 'xlsx', 'xls'}

# Check if poppler is installed or install it if on Render
if os.environ.get('RENDER') and platform.system() != 'Windows':
    try:
        # Try to use poppler
        from pdf2image import convert_from_path
        test_pdf = Path(__file__).parent / "test.pdf"
        if not test_pdf.exists():
            # Create a valid test file with actual content
            with open(test_pdf, "wb") as f:
                # This is a minimal but valid PDF with one page
                f.write(b"%PDF-1.4\n1 0 obj<</Type/Catalog/Pages 2 0 R>>endobj 2 0 obj<</Type/Pages/Kids[3 0 R]/Count 1>>endobj 3 0 obj<</Type/Page/MediaBox[0 0 3 3]/Parent 2 0 R/Resources<<>>>>endobj\nxref\n0 4\n0000000000 65535 f\n0000000010 00000 n\n0000000053 00000 n\n0000000102 00000 n\ntrailer<</Size 4/Root 1 0 R>>\nstartxref\n180\n%%EOF\n")
        
        # Test if poppler works
        pages = convert_from_path(str(test_pdf), dpi=72)
        print(f"Poppler working correctly. Detected {len(pages)} pages.")
    except Exception as e:
        print(f"Error with poppler: {e}")
        print("Poppler not available, functionality will be limited")


def allowed_file(filename, allowed_set):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in allowed_set

def process_pdf():
    """Process the PDF file through our pipeline."""
    try:
        # Initialize processors
        pdf_processor = PDFProcessor()
        data_processor = DataProcessor()
        csv_exporter = CSVExporter()
        
        # Process through pipeline
        if not pdf_processor.process_first_pdf():
            return False, "Failed to process PDF"
            
        if not data_processor.process_all_files():
            return False, "Failed to process text files"
            
        if not csv_exporter.combine_to_csv():
            return False, "Failed to create CSV file"
            
        return True, "Processing completed successfully"
        
    except Exception as e:
        return False, str(e)

def process_csv_file(file_path):
    """Process and map incoming CSV/Excel data to combined_data.csv"""
    try:
        # Read input file - ensure all columns are read as strings
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            incoming_df = pd.read_csv(file_path, dtype=str)
        elif ext in [".xlsx", ".xls"]:
            incoming_df = pd.read_excel(file_path, dtype=str)
        else:
            return False, "Unsupported file extension"
        
        # Define target column indices (0-based)
        target_columns = {
            'J': 9,   # Index for column J
            'L': 11,  # Index for column L
            'M': 12,  # Index for column M
            'O': 14,  # Index for column O
            'P': 15   # Index for column P
        }
        
        # Column mappings from source to target columns
        column_mappings = {
            'P': target_columns['J'],  # Invoice Date -> Column J
            'D': target_columns['L'],  # Ship-to Name -> Column L
            'F': target_columns['M'],  # Pieces* -> Column M
            'M': target_columns['O'],  # Delivery Date -> Column O
            'N': target_columns['P']   # Cancel Date -> Column P
        }
        
        # Read existing combined_data.csv
        combined_csv_path = os.path.join(app.config['UPLOAD_FOLDER'], OUTPUT_CSV_NAME)
        if not os.path.exists(combined_csv_path):
            return False, "No PDF data processed yet. Please process PDF first."
            
        existing_df = pd.read_csv(combined_csv_path, dtype=str)
        
        # Ensure DataFrame has enough columns
        required_columns = max(target_columns.values()) + 1
        while len(existing_df.columns) < required_columns:
            col_name = chr(65 + len(existing_df.columns))  # A, B, C, etc.
            existing_df[col_name] = ''
        
        # Handle size mismatch
        max_rows = min(len(existing_df), len(incoming_df))
        
        # Map columns using numeric indices
        for src_col, target_idx in column_mappings.items():
            try:
                # Convert source column letter to index (0-based)
                src_idx = ord(src_col) - ord('A')
                
                if src_idx >= incoming_df.shape[1]:
                    print(f"Warning: Source column {src_col} does not exist in incoming file")
                    continue
                
                # Get source data as strings
                src_data = incoming_df.iloc[:, src_idx].astype(str)
                
                # Map the data to the correct target column index
                existing_df.iloc[:max_rows, target_idx] = src_data.iloc[:max_rows].values
                
            except Exception as e:
                print(f"Warning: Error mapping column {src_col} to index {target_idx}: {str(e)}")
                continue
        
        # Save updated DataFrame
        existing_df.to_csv(combined_csv_path, index=False)
        
        return True, f"CSV data mapped successfully (processed {max_rows} rows)"
        
    except pd.errors.EmptyDataError:
        return False, "The uploaded file is empty"
    except pd.errors.ParserError:
        return False, "Error parsing the file. Please ensure it's a valid CSV/Excel file"
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")  # For debugging
        return False, f"Error processing file: {str(e)}"



@app.route('/')
def index():
    return render_template('index.html')

# Add near your other routes
@app.route('/health')
def health():
    # Check if poppler is working
    poppler_status = "working" if os.environ.get('POPPLER_WORKING') else "not working"
    
    return jsonify({
        "status": "healthy",
        "poppler_status": poppler_status,
        "environment": os.environ.get('RENDER', 'local')
    }), 200

@app.route('/upload', methods=['POST'])
def upload_file():
    # This endpoint is for PDF files only.
    if 'file' not in request.files:
        return jsonify({'error': 'No file part'}), 400
        
    file = request.files['file']
    if file.filename == '':
        return jsonify({'error': 'No selected file'}), 400
        
    if not allowed_file(file.filename, ALLOWED_PDF_EXTENSIONS):
        return jsonify({'error': 'Invalid file type (PDF required)'}), 400
        
    try:
        # Save the uploaded PDF
        filename = secure_filename(file.filename)
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(file_path)
        
        # Process the PDF through our pipeline
        success, message = process_pdf()
        if not success:
            return jsonify({'error': message}), 500
            
        return jsonify({'message': 'File processed successfully'}), 200
        
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    try:
        if 'file' not in request.files:
            return jsonify({'error': 'No file uploaded'}), 400
            
        file = request.files['file']
        if file.filename == '':
            return jsonify({'error': 'No selected file'}), 400
            
        if not allowed_file(file.filename, ALLOWED_CSV_EXTENSIONS):
            return jsonify({'error': 'Invalid file type. Please upload a CSV or Excel file'}), 400
            
        # Save uploaded file with unique name to prevent conflicts
        filename = secure_filename(f"temp_{file.filename}")
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        
        try:
            file.save(file_path)
            success, message = process_csv_file(file_path)
            
            if not success:
                return jsonify({'error': message}), 400
                
            return jsonify({
                'message': 'CSV data mapped successfully',
                'status': 'success'
            }), 200
            
        finally:
            # Clean up temporary file
            if os.path.exists(file_path):
                os.remove(file_path)
                
    except Exception as e:
        print(f"Upload error: {str(e)}")  # For debugging
        return jsonify({'error': 'An unexpected error occurred'}), 500
@app.route('/download')
def download_file():
    try:
        csv_path = os.path.join(app.config['UPLOAD_FOLDER'], OUTPUT_CSV_NAME)
        return send_file(csv_path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port)
