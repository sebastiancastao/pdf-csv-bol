import os
import csv
import math
import shutil
import time
from pathlib import Path
import platform
import pandas as pd
from io import StringIO
from flask import Flask, render_template, request, send_file, jsonify, session, make_response
from werkzeug.utils import secure_filename
from pdf_processor import PDFProcessor
from data_processor import DataProcessor
from csv_exporter import CSVExporter
from config import OUTPUT_CSV_NAME  # e.g. "combined_data.csv"

app = Flask(__name__)
app.config['UPLOAD_FOLDER'] = os.path.dirname(os.path.abspath(__file__))
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16MB max file size
app.config['SESSION_COOKIE_SAMESITE'] = 'None'  # Allow cookie in iframe
app.config['SESSION_COOKIE_SECURE'] = False  # Set to True in production with HTTPS
app.config['SESSION_COOKIE_HTTPONLY'] = True  # Security best practice
app.config['PERMANENT_SESSION_LIFETIME'] = 3600  # Session expires after 1 hour
app.secret_key = os.environ.get('SECRET_KEY', 'your-secret-key-here')  # Use env var in production

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

def process_csv_file(file_path, session_dir):
    """Process and merge incoming CSV/Excel data with the PDF CSV by matching on:
       - Invoice No.
       - Style
       - Cartons* (renamed to 'Cartons')
       - Pieces* (renamed to 'Individual Pieces')
       
       Then update the following fields using the incoming headers:
       - "Invoice Date" -> "Order Date"
       - "Ship-to Name" -> "Ship To Name"
       - "Order No." -> "Purchase Order No."
       - "Delivery Date" -> "Start Date"
       - "Cancel Date" -> "Cancel Date"
    """
    try:
        # Read input file as DataFrame with all columns as strings
        ext = os.path.splitext(file_path)[1].lower()
        if ext == ".csv":
            incoming_df = pd.read_csv(file_path, dtype=str)
        elif ext in [".xlsx", ".xls"]:
            incoming_df = pd.read_excel(file_path, dtype=str)
        else:
            return False, "Unsupported file extension"
        
        # Rename incoming columns used for matching.
        incoming_df.rename(columns={"Cartons*": "Cartons", "Pieces*": "Individual Pieces"}, inplace=True)
        
        # Define mapping for additional fields using header names:
        additional_mapping = {
            "Invoice Date": "Order Date",
            "Ship-to Name": "Ship To Name",
            "Order No.": "Purchase Order No.",
            "Delivery Date": "Start Date",
            "Cancel Date": "Cancel Date"
        }
        
        # Read existing combined CSV (from PDF processing) from session directory
        combined_csv_path = os.path.join(session_dir, OUTPUT_CSV_NAME)
        if not os.path.exists(combined_csv_path):
            return False, "No PDF data processed yet. Please process PDF first."
        existing_df = pd.read_csv(combined_csv_path, dtype=str)
        
        # Ensure matching columns exist in both DataFrames.
        matching_columns = ["Invoice No.", "Style", "Cartons", "Individual Pieces"]
        for col in matching_columns:
            if col not in existing_df.columns:
                return False, f"Column '{col}' not found in PDF CSV data."
            if col not in incoming_df.columns:
                return False, f"Column '{col}' not found in incoming file."
        
        # Create a composite match key in both DataFrames.
        def create_match_key(df, cols):
            return df[cols].fillna('').apply(
                lambda row: "_".join([str(x).strip().replace(",", "").lower() for x in row]),
                axis=1
            )
        
        key_cols = matching_columns
        existing_df["match_key"] = create_match_key(existing_df, key_cols)
        incoming_df["match_key"] = create_match_key(incoming_df, key_cols)
        
        print("Existing DataFrame match keys:")
        print(existing_df[["Invoice No.", "Style", "Cartons", "Individual Pieces", "match_key"]].head(20))
        print("Incoming DataFrame match keys:")
        print(incoming_df[["Invoice No.", "Style", "Cartons", "Individual Pieces", "match_key"]].head(20))
        
        # Merge: update existing_df rows using incoming additional mapping.
        for idx, inc_row in incoming_df.iterrows():
            key = inc_row["match_key"]
            matches = existing_df[existing_df["match_key"] == key]
            if not matches.empty:
                existing_index = matches.index[0]
                for inc_col, pdf_col in additional_mapping.items():
                    if inc_col in incoming_df.columns and pdf_col in existing_df.columns:
                        value = inc_row.get(inc_col, "")
                        existing_df.at[existing_index, pdf_col] = value
        
        # Drop the match_key columns.
        existing_df.drop(columns=["match_key"], inplace=True)
        incoming_df.drop(columns=["match_key"], inplace=True)
        
        # Compute values for all rows first
        if "BOL Cube" in existing_df.columns:
            pallet_values = existing_df["BOL Cube"].apply(lambda x: compute_pallet(x))
            existing_df["Pallet"] = ""  # Initialize empty column
        else:
            print("Warning: 'BOL Cube' column not found in existing CSV data.")
            pallet_values = pd.Series([""] * len(existing_df))
        
        if "Ship To Name" in existing_df.columns:
            burlington_values = existing_df.apply(
                lambda row: compute_burlington(row["Ship To Name"], pallet_values.iloc[row.name]), 
                axis=1
            )
            final_cube_values = existing_df.apply(
                lambda row: compute_final_cube(row["Ship To Name"], pallet_values.iloc[row.name]), 
                axis=1
            )
            
            existing_df["Burlington Cube"] = ""  # Initialize empty column
            existing_df["Final Cube"] = ""      # Initialize empty column
        else:
            print("Warning: 'Ship To Name' column not found in existing CSV data.")
            burlington_values = pd.Series([""] * len(existing_df))
            final_cube_values = pd.Series([""] * len(existing_df))
        
        # Group by Invoice No. and only set values for first row of each group
        current_invoice = None
        is_first_row = True
        
        for idx in range(len(existing_df)):
            invoice_no = existing_df.iloc[idx]["Invoice No."]
            
            # Check if this is the first row of a new invoice group
            if invoice_no != current_invoice:
                current_invoice = invoice_no
                is_first_row = True
            
            # Only set the values for the first row of each invoice group
            if is_first_row:
                existing_df.iloc[idx, existing_df.columns.get_loc("Pallet")] = pallet_values.iloc[idx]
                existing_df.iloc[idx, existing_df.columns.get_loc("Burlington Cube")] = burlington_values.iloc[idx]
                existing_df.iloc[idx, existing_df.columns.get_loc("Final Cube")] = final_cube_values.iloc[idx]
                is_first_row = False
            
        def parse_cancel_date(date_str):
            """
            Convert a string like '3152025' -> 03/15/2025 or
            '2202025' -> 02/20/2025 into a datetime object.

            Handles:
            - 7-digit format:  MDDYYYY  (e.g. '3152025')
            - 8-digit format: MMDDYYYY  (e.g. '03152025')
            """
            date_str = str(date_str).strip()

            # 7-digit: MDDYYYY
            if len(date_str) == 7:
                month = date_str[0]             # e.g. '3'
                day   = date_str[1:3]          # e.g. '15'
                year  = date_str[3:]           # e.g. '2025'
                try:
                    return pd.to_datetime(f"{month.zfill(2)}/{day}/{year}", format="%m/%d/%Y")
                except:
                    return pd.NaT

            # 8-digit: MMDDYYYY
            elif len(date_str) == 8:
                month = date_str[0:2]          # e.g. '03'
                day   = date_str[2:4]          # e.g. '15'
                year  = date_str[4:]           # e.g. '2025'
                try:
                    return pd.to_datetime(f"{month}/{day}/{year}", format="%m/%d/%Y")
                except:
                    return pd.NaT

            return pd.NaT

        # --- Sorting the output ---
        if "Cancel Date" in existing_df.columns and "Ship To Name" in existing_df.columns:
            # Convert the raw strings in "Cancel Date" to datetime using the custom function:
            existing_df["Cancel Date_dt"] = existing_df["Cancel Date"].apply(parse_cancel_date)

            # Compute the earliest date per "Ship To Name":
            existing_df["min_cancel_date"] = existing_df.groupby("Ship To Name")["Cancel Date_dt"].transform("min")

            # Sort by earliest group date, then Ship To Name, then the individual date:
            existing_df.sort_values(by=["min_cancel_date", "Ship To Name", "Cancel Date_dt"], inplace=True)

            # Drop the helper columns:
            existing_df.drop(columns=["min_cancel_date", "Cancel Date_dt"], inplace=True)

        else:
            print("Warning: 'Cancel Date' or 'Ship To Name' column not found; skipping sort.")
        
        # Save updated DataFrame back to the combined CSV in session directory
        existing_df.to_csv(combined_csv_path, index=False)
        
        return True, f"CSV data merged successfully (processed {len(incoming_df)} rows)"
        
    except pd.errors.EmptyDataError:
        return False, "The uploaded file is empty"
    except pd.errors.ParserError:
        return False, "Error parsing the file. Please ensure it's a valid CSV/Excel file"
    except Exception as e:
        print(f"Error processing CSV: {str(e)}")
        return False, f"Error processing file: {str(e)}"

def compute_pallet(bol_cube):
    """Compute pallet value from BOL Cube."""
    try:
        value = float(str(bol_cube).replace(",", "").strip())
        return math.ceil(value / 80)
    except Exception:
        return ""

def compute_burlington(ship_to_name, pallet):
    """Compute Burlington Cube value."""
    try:
        if isinstance(ship_to_name, str) and "burlington" in ship_to_name.lower():
            if pd.isna(pallet) or pallet == "":
                return ""
            return int(pallet) * 93
    except Exception:
        return ""
    return ""

def compute_final_cube(ship_to_name, pallet):
    """Compute Final Cube value."""
    try:
        if isinstance(ship_to_name, str) and "burlington" not in ship_to_name.lower():
            if pd.isna(pallet) or pallet == "":
                return ""
            return int(pallet) * 130
    except Exception:
        return ""
    return ""

def cleanup_old_files():
    """Clean up old PDFs and combined CSV file when page is loaded/refreshed."""
    try:
        script_dir = app.config['UPLOAD_FOLDER']
        
        # Delete old PDFs
        for file in os.listdir(script_dir):
            if file.lower().endswith('.pdf'):
                try:
                    os.remove(os.path.join(script_dir, file))
                    print(f"Cleaned up old PDF: {file}")
                except Exception as e:
                    print(f"Error deleting PDF {file}: {str(e)}")
        
        # Delete old combined CSV
        combined_csv = os.path.join(script_dir, OUTPUT_CSV_NAME)
        if os.path.exists(combined_csv):
            try:
                os.remove(combined_csv)
                print(f"Cleaned up old combined CSV: {OUTPUT_CSV_NAME}")
            except Exception as e:
                print(f"Error deleting combined CSV: {str(e)}")
                
    except Exception as e:
        print(f"Error during cleanup: {str(e)}")

def get_or_create_session():
    """Get existing processor or create new one with session management."""
    # Check for action parameter to force new session creation
    action = request.args.get('_action')
    force_new_session = action == 'new_session'
    
    # Check for session ID in query parameters first (for external apps)
    external_session_id = request.args.get('_sid') or request.args.get('session_id')
    
    # If force new session is requested, always create a new session
    if force_new_session:
        processor = DataProcessor()  # Creates new session
        print(f"🆕 Force creating new session due to _action=new_session: {processor.session_id}")
        return processor
    
    # Use external session ID if provided, otherwise use Flask session
    if external_session_id:
        # Check if this session exists and has data
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'processing_sessions', external_session_id)
        if os.path.exists(session_dir):
            processor = DataProcessor(session_id=external_session_id)
            print(f"♻️ Reusing existing external session: {external_session_id}")
        else:
            # External session doesn't exist, create new one with the requested ID
            processor = DataProcessor(session_id=external_session_id)
            print(f"🆕 Creating new external session with requested ID: {external_session_id}")
        return processor
    
    if 'session_id' not in session:
        # Only clean up old sessions when creating a new one AND no session exists
        base_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'processing_sessions')
        if os.path.exists(base_dir):
            # Check if there are any existing sessions with combined_data.csv
            existing_sessions = []
            for session_dir in os.listdir(base_dir):
                full_path = os.path.join(base_dir, session_dir)
                if os.path.isdir(full_path):
                    csv_path = os.path.join(full_path, OUTPUT_CSV_NAME)
                    if os.path.exists(csv_path):
                        existing_sessions.append(session_dir)
            
            if existing_sessions:
                # Use the most recent session that has a combined_data.csv
                most_recent = sorted(existing_sessions)[-1]
                session['session_id'] = most_recent
                processor = DataProcessor(session_id=most_recent)
                print(f"Reusing existing session with data: {most_recent}")
                return processor
            else:
                # No valid sessions found, clean up and create new
                DataProcessor.cleanup_sessions()
        
        # Create new session if none exists or no valid sessions found
        processor = DataProcessor()
        session['session_id'] = processor.session_id
        print(f"Created new session: {processor.session_id}")
    else:
        processor = DataProcessor(session_id=session['session_id'])
        print(f"Using existing session: {session['session_id']}")
    return processor

@app.route('/', methods=['GET'])
def index():
    # Get or create session without cleaning up existing valid sessions
    processor = get_or_create_session()
    
    # For external apps requesting JSON response
    if request.headers.get('Accept') == 'application/json' or request.args.get('format') == 'json':
        return jsonify({
            'status': 'ready',
            'session_id': processor.session_id,
            'message': 'BOL Extractor ready for processing',
            'endpoints': {
                'upload': '/upload',
                'upload_base64': '/upload-base64',
                'upload_attachment': '/upload-attachment',
                'status': '/status',
                'files': '/files'
            }
        })
    
    return render_template('index.html')

@app.route('/process', methods=['POST'])
def process():
    # Use existing session instead of creating new one
    processor = get_or_create_session()
    
    # Process the files
    processor.process_all_files()
    
    # Create exporter with the same session directory
    exporter = CSVExporter(session_dir=processor.session_dir)
    exporter.combine_to_csv()
    
    return jsonify({"status": "success"})

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
    # Get existing processor with session directory
    processor = get_or_create_session()
    
    print(f"📤 PDF Upload Request - Session: {processor.session_id}")
    
    if 'file' not in request.files:
        print("❌ No file part in request")
        return jsonify({'error': 'No file part in request'}), 400
        
    file = request.files['file']
    if file.filename == '':
        print("❌ No file selected")
        return jsonify({'error': 'No file selected'}), 400
        
    if not allowed_file(file.filename, ALLOWED_PDF_EXTENSIONS):
        print(f"❌ Invalid file type: {file.filename}")
        return jsonify({'error': 'Invalid file type (PDF required)'}), 400
        
    try:
        # Save the uploaded PDF directly to session directory
        filename = secure_filename(file.filename)
        file_path = os.path.join(processor.session_dir, filename)
        file.save(file_path)
        
        print(f"📏 Saved PDF size: {os.path.getsize(file_path)} bytes")
        print(f"📄 PDF saved to: {file_path}")
        print(f"📁 Session directory: {processor.session_dir}")
        
        # Process the PDF through our pipeline
        print("🔄 Initializing PDF processor...")
        pdf_processor = PDFProcessor(session_dir=processor.session_dir)
        
        print("🔄 Processing PDF...")
        if not pdf_processor.process_first_pdf():
            print("❌ PDF processing failed - check logs for details")
            return jsonify({
                'error': 'PDF processing failed',
                'details': 'Could not extract text from PDF. Check server logs for more details.',
                'session_id': processor.session_id
            }), 500
        
        print("🔄 Processing extracted text files...")
        if not processor.process_all_files():
            print("❌ Text processing failed - check logs for details")
            return jsonify({
                'error': 'Text processing failed',
                'details': 'Could not process extracted text files. Check server logs for more details.',
                'session_id': processor.session_id
            }), 500
            
        # Create exporter with the same session directory
        print("🔄 Creating final CSV...")
        exporter = CSVExporter(session_dir=processor.session_dir)
        if not exporter.combine_to_csv():
            print("❌ CSV creation failed - check logs for details")
            return jsonify({
                'error': 'CSV creation failed',
                'details': 'Could not create final CSV file. Check server logs for more details.',
                'session_id': processor.session_id
            }), 500
            
        print("✅ PDF processed successfully!")
        return jsonify({
            'message': 'PDF processed successfully',
            'filename': filename,
            'session_id': processor.session_id
        }), 200
        
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Unexpected error during PDF processing: {error_msg}")
        return jsonify({
            'error': 'Unexpected error during PDF processing',
            'details': error_msg,
            'session_id': processor.session_id if 'processor' in locals() else None
        }), 500

@app.route('/upload-base64', methods=['POST'])
def upload_base64():
    """Handle file upload with base64 encoded data (for email attachments)."""
    try:
        # Get existing processor with session directory
        processor = get_or_create_session()
        
        print(f"📤 Base64 Upload Request - Session: {processor.session_id}")
        
        # Parse JSON request
        data = request.get_json()
        if not data:
            print("❌ No JSON data provided")
            return jsonify({'error': 'No JSON data provided'}), 400
            
        # Get file data from request
        file_data = data.get('file_data') or data.get('attachmentData')
        filename = data.get('filename') or data.get('name', 'attachment.pdf')
        
        if not file_data:
            print("❌ No file data provided")
            return jsonify({'error': 'No file data provided'}), 400
        
        # Handle base64 encoded data
        import base64
        try:
            # Remove data URL prefix if present
            if ',' in file_data:
                file_data = file_data.split(',')[1]
            
            # Decode base64 data
            decoded_data = base64.b64decode(file_data)
            
            # Secure filename
            filename = secure_filename(filename)
            
            # Ensure PDF extension
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            # Save file to session directory
            file_path = os.path.join(processor.session_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(decoded_data)
            
            print(f"📄 Base64 PDF saved to: {file_path} ({len(decoded_data)} bytes)")
            print(f"📁 Session directory: {processor.session_dir}")
            
            # Process the PDF through our pipeline
            print("🔄 Initializing PDF processor...")
            pdf_processor = PDFProcessor(session_dir=processor.session_dir)
            
            print("🔄 Processing PDF...")
            if not pdf_processor.process_first_pdf():
                print("❌ PDF processing failed - check logs for details")
                return jsonify({
                    'error': 'PDF processing failed',
                    'details': 'Could not extract text from PDF. Check server logs for more details.',
                    'session_id': processor.session_id
                }), 500
                
            print("🔄 Processing extracted text files...")
            if not processor.process_all_files():
                print("❌ Text processing failed - check logs for details")
                return jsonify({
                    'error': 'Text processing failed',
                    'details': 'Could not process extracted text files. Check server logs for more details.',
                    'session_id': processor.session_id
                }), 500
                
            # Create exporter with the same session directory
            print("🔄 Creating final CSV...")
            exporter = CSVExporter(session_dir=processor.session_dir)
            if not exporter.combine_to_csv():
                print("❌ CSV creation failed - check logs for details")
                return jsonify({
                    'error': 'CSV creation failed',
                    'details': 'Could not create final CSV file. Check server logs for more details.',
                    'session_id': processor.session_id
                }), 500
                
            print("✅ Base64 PDF processed successfully!")
            return jsonify({
                'message': 'Base64 PDF processed successfully',
                'filename': filename,
                'file_size': len(decoded_data),
                'session_id': processor.session_id
            }), 200
            
        except Exception as decode_error:
            print(f"❌ Failed to decode base64 data: {str(decode_error)}")
            return jsonify({'error': f'Failed to decode file data: {str(decode_error)}'}), 400
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Unexpected error during base64 upload: {error_msg}")
        return jsonify({
            'error': 'Unexpected error during base64 upload',
            'details': error_msg,
            'session_id': processor.session_id if 'processor' in locals() else None
        }), 500

@app.route('/upload-attachment', methods=['POST'])
def upload_attachment():
    """Handle attachment upload with flexible data formats."""
    try:
        # Get existing processor with session directory
        processor = get_or_create_session()
        
        print(f"📤 Attachment Upload Request - Session: {processor.session_id}")
        
        # Try to get data from different sources
        data = None
        
        # Check if it's JSON data
        if request.is_json:
            data = request.get_json()
        elif request.form:
            # Form data
            data = request.form.to_dict()
        
        if not data:
            print("❌ No data provided")
            return jsonify({'error': 'No data provided'}), 400
        
        # Get file information
        attachment_data = data.get('attachmentData') or data.get('file_data') or data.get('data')
        filename = data.get('filename') or data.get('name', 'attachment.pdf')
        
        if not attachment_data:
            print("❌ No attachment data provided")
            return jsonify({'error': 'No attachment data provided'}), 400
        
        # Handle different data formats
        import base64
        try:
            # If it's already bytes, use as is
            if isinstance(attachment_data, bytes):
                file_bytes = attachment_data
            else:
                # Try to decode as base64
                if isinstance(attachment_data, str):
                    # Remove data URL prefix if present
                    if ',' in attachment_data:
                        attachment_data = attachment_data.split(',')[1]
                    file_bytes = base64.b64decode(attachment_data)
                else:
                    print("❌ Invalid attachment data format")
                    return jsonify({'error': 'Invalid attachment data format'}), 400
            
            # Secure filename
            filename = secure_filename(filename)
            
            # Ensure PDF extension
            if not filename.lower().endswith('.pdf'):
                filename += '.pdf'
            
            # Save file to session directory
            file_path = os.path.join(processor.session_dir, filename)
            with open(file_path, 'wb') as f:
                f.write(file_bytes)
            
            print(f"📄 Attachment saved to: {file_path} ({len(file_bytes)} bytes)")
            print(f"📁 Session directory: {processor.session_dir}")
            
            # Process the PDF through our pipeline
            print("🔄 Initializing PDF processor...")
            pdf_processor = PDFProcessor(session_dir=processor.session_dir)
            
            print("🔄 Processing PDF...")
            if not pdf_processor.process_first_pdf():
                print("❌ PDF processing failed - check logs for details")
                return jsonify({
                    'error': 'PDF processing failed',
                    'details': 'Could not extract text from PDF. Check server logs for more details.',
                    'session_id': processor.session_id
                }), 500
                
            print("🔄 Processing extracted text files...")
            if not processor.process_all_files():
                print("❌ Text processing failed - check logs for details")
                return jsonify({
                    'error': 'Text processing failed',
                    'details': 'Could not process extracted text files. Check server logs for more details.',
                    'session_id': processor.session_id
                }), 500
                
            # Create exporter with the same session directory
            print("🔄 Creating final CSV...")
            exporter = CSVExporter(session_dir=processor.session_dir)
            if not exporter.combine_to_csv():
                print("❌ CSV creation failed - check logs for details")
                return jsonify({
                    'error': 'CSV creation failed',
                    'details': 'Could not create final CSV file. Check server logs for more details.',
                    'session_id': processor.session_id
                }), 500
                
            print("✅ Attachment processed successfully!")
            return jsonify({
                'message': 'Attachment processed successfully',
                'filename': filename,
                'file_size': len(file_bytes),
                'session_id': processor.session_id,
                'status': 'success'
            }), 200
            
        except Exception as decode_error:
            print(f"❌ Failed to process attachment data: {str(decode_error)}")
            return jsonify({'error': f'Failed to process attachment data: {str(decode_error)}'}), 400
            
    except Exception as e:
        error_msg = str(e)
        print(f"❌ Unexpected error during attachment upload: {error_msg}")
        return jsonify({
            'error': 'Unexpected error during attachment upload',
            'details': error_msg,
            'session_id': processor.session_id if 'processor' in locals() else None
        }), 500

@app.route('/upload-csv', methods=['POST'])
def upload_csv():
    try:
        # Get existing processor with session directory
        processor = get_or_create_session()
        
        print(f"📄 CSV Upload Request - Session: {processor.session_id}")
        print(f"Content-Type: {request.content_type}")
        print(f"Request method: {request.method}")
        print(f"Files: {list(request.files.keys())}")
        print(f"Form data: {list(request.form.keys())}")
        print(f"JSON data: {request.is_json}")
        
        file_path = None
        
        try:
            # Method 1: Handle file upload (multipart/form-data)
            if 'file' in request.files:
                file = request.files['file']
                if file.filename != '':
                    if not allowed_file(file.filename, ALLOWED_CSV_EXTENSIONS):
                        return jsonify({'error': 'Invalid file type. Please upload a CSV or Excel file'}), 400
                    
                    filename = secure_filename(f"temp_{file.filename}")
                    file_path = os.path.join(processor.session_dir, filename)
                    file.save(file_path)
                    print(f"✅ CSV file saved via multipart upload")
                    
            # Method 2: Handle JSON data with CSV content
            elif request.is_json:
                json_data = request.get_json()
                print(f"📄 JSON data keys: {list(json_data.keys()) if json_data else 'None'}")
                
                if json_data and 'csv_data' in json_data:
                    csv_content = json_data['csv_data']
                    filename = json_data.get('filename', 'uploaded_data.csv')
                    
                    # Save CSV content to file
                    filename = secure_filename(f"temp_{filename}")
                    file_path = os.path.join(processor.session_dir, filename)
                    
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        f.write(csv_content)
                    print(f"✅ CSV data saved from JSON")
                    
                elif json_data and 'file_data' in json_data:
                    # Handle base64 encoded CSV
                    import base64
                    file_data = json_data['file_data']
                    filename = json_data.get('filename', 'uploaded_data.csv')
                    
                    # Decode base64 if needed
                    if isinstance(file_data, str) and file_data.startswith('data:'):
                        # Handle data URL format
                        header, data = file_data.split(',', 1)
                        csv_content = base64.b64decode(data).decode('utf-8')
                    else:
                        csv_content = file_data
                    
                    filename = secure_filename(f"temp_{filename}")
                    file_path = os.path.join(processor.session_dir, filename)
                    
                    with open(file_path, 'w', newline='', encoding='utf-8') as f:
                        f.write(csv_content)
                    print(f"✅ CSV data saved from base64")
                    
            # Method 3: Handle raw CSV data in form field
            elif 'csv_data' in request.form:
                csv_content = request.form['csv_data']
                filename = request.form.get('filename', 'uploaded_data.csv')
                
                filename = secure_filename(f"temp_{filename}")
                file_path = os.path.join(processor.session_dir, filename)
                
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    f.write(csv_content)
                print(f"✅ CSV data saved from form field")
                
            # Method 4: Handle raw CSV data in request body
            elif request.content_type and 'text/csv' in request.content_type:
                csv_content = request.get_data(as_text=True)
                filename = 'uploaded_data.csv'
                
                filename = secure_filename(f"temp_{filename}")
                file_path = os.path.join(processor.session_dir, filename)
                
                with open(file_path, 'w', newline='', encoding='utf-8') as f:
                    f.write(csv_content)
                print(f"✅ CSV data saved from raw body")
                
            else:
                return jsonify({
                    'error': 'No CSV data provided',
                    'expected_formats': [
                        'multipart/form-data with file field',
                        'application/json with csv_data field',
                        'application/json with file_data field',
                        'form data with csv_data field',
                        'text/csv content-type with CSV in body'
                    ]
                }), 400
            
            # Process the CSV file
            if file_path and os.path.exists(file_path):
                success, message = process_csv_file(file_path, processor.session_dir)
                
                if not success:
                    return jsonify({'error': message}), 400
                    
                return jsonify({
                    'message': 'CSV data mapped successfully',
                    'status': 'success',
                    'session_id': processor.session_id
                }), 200
            else:
                return jsonify({'error': 'Failed to save CSV data'}), 500
                
        finally:
            # Clean up temporary file
            if file_path and os.path.exists(file_path):
                os.remove(file_path)
                print(f"🧹 Cleaned up temporary file: {file_path}")
                
    except Exception as e:
        print(f"❌ CSV Upload error: {str(e)}")
        import traceback
        traceback.print_exc()
        return jsonify({'error': f'An unexpected error occurred: {str(e)}'}), 500

@app.route('/download')
def download_file():
    try:
        # Get existing processor with session directory
        processor = get_or_create_session()
        csv_path = os.path.join(processor.session_dir, OUTPUT_CSV_NAME)
        return send_file(csv_path, as_attachment=True)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-bol')
def download_bol_file():
    """Download the processed BOL CSV file."""
    try:
        # Get existing processor with session directory
        processor = get_or_create_session()
        csv_path = os.path.join(processor.session_dir, OUTPUT_CSV_NAME)
        
        if not os.path.exists(csv_path):
            return jsonify({'error': 'No processed file available'}), 404
            
        return send_file(csv_path, as_attachment=True, download_name='BOL_processed.csv')
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/download-bol/<filename>')
def download_bol_file_by_name(filename):
    """Download a specific BOL file by name."""
    try:
        # Get existing processor with session directory
        processor = get_or_create_session()
        
        # Secure the filename to prevent directory traversal
        secure_name = secure_filename(filename)
        file_path = os.path.join(processor.session_dir, secure_name)
        
        # Check if it's the main CSV file
        if secure_name == OUTPUT_CSV_NAME:
            file_path = os.path.join(processor.session_dir, OUTPUT_CSV_NAME)
        
        if not os.path.exists(file_path):
            return jsonify({'error': f'File {secure_name} not found'}), 404
            
        return send_file(file_path, as_attachment=True, download_name=secure_name)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/status')
def get_status():
    """Get the current processing status."""
    try:
        # Get existing processor with session directory
        processor = get_or_create_session()
        csv_path = os.path.join(processor.session_dir, OUTPUT_CSV_NAME)
        
        status = {
            'session_id': processor.session_id,
            'has_processed_data': os.path.exists(csv_path),
            'session_dir': processor.session_dir,
            'session_exists': os.path.exists(processor.session_dir),
            'query_params': {
                '_sid': request.args.get('_sid'),
                '_action': request.args.get('_action'),
                '_t': request.args.get('_t')
            }
        }
        
        # Check for available files
        if os.path.exists(processor.session_dir):
            files = []
            for file in os.listdir(processor.session_dir):
                if file.endswith(('.csv', '.pdf')):
                    file_path = os.path.join(processor.session_dir, file)
                    files.append({
                        'name': file,
                        'size': os.path.getsize(file_path),
                        'type': 'csv' if file.endswith('.csv') else 'pdf'
                    })
            status['available_files'] = files
        else:
            status['available_files'] = []
        
        # Add session age information
        try:
            session_creation_time = os.path.getctime(processor.session_dir) if os.path.exists(processor.session_dir) else None
            if session_creation_time:
                import time
                status['session_age_seconds'] = time.time() - session_creation_time
        except:
            status['session_age_seconds'] = None
        
        return jsonify(status)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/files')
def list_files():
    """List all available files in the current session."""
    try:
        # Get existing processor with session directory
        processor = get_or_create_session()
        
        files = []
        if os.path.exists(processor.session_dir):
            for file in os.listdir(processor.session_dir):
                if not file.startswith('.'):  # Skip hidden files
                    file_path = os.path.join(processor.session_dir, file)
                    files.append({
                        'name': file,
                        'size': os.path.getsize(file_path),
                        'type': 'csv' if file.endswith('.csv') else 'pdf' if file.endswith('.pdf') else 'other',
                        'download_url': f'/download-bol/{file}'
                    })
        
        return jsonify({'files': files})
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/process-workflow', methods=['POST'])
def process_workflow():
    """Handle the complete processing workflow."""
    try:
        # Get existing processor with session directory
        processor = get_or_create_session()
        
        # Check if there are any PDF files to process
        pdf_files = []
        if os.path.exists(processor.session_dir):
            for file in os.listdir(processor.session_dir):
                if file.lower().endswith('.pdf'):
                    pdf_files.append(file)
        
        if not pdf_files:
            return jsonify({'error': 'No PDF files found to process'}), 400
        
        # Process all PDFs
        pdf_processor = PDFProcessor(session_dir=processor.session_dir)
        if not pdf_processor.process_first_pdf():
            return jsonify({'error': 'Failed to process PDF files'}), 500
        
        # Process text files
        if not processor.process_all_files():
            return jsonify({'error': 'Failed to process extracted text'}), 500
        
        # Create CSV
        exporter = CSVExporter(session_dir=processor.session_dir)
        if not exporter.combine_to_csv():
            return jsonify({'error': 'Failed to create CSV output'}), 500
        
        # Get result info
        csv_path = os.path.join(processor.session_dir, OUTPUT_CSV_NAME)
        result = {
            'status': 'success',
            'message': 'Processing completed successfully',
            'output_file': OUTPUT_CSV_NAME,
            'download_url': '/download-bol',
            'session_id': processor.session_id
        }
        
        if os.path.exists(csv_path):
            result['file_size'] = os.path.getsize(csv_path)
            # Count rows (excluding header)
            with open(csv_path, 'r', encoding='utf-8') as f:
                reader = csv.reader(f)
                row_count = sum(1 for row in reader) - 1  # Subtract header
                result['row_count'] = row_count
        
        return jsonify(result)
        
    except Exception as e:
        return jsonify({'error': f'Processing failed: {str(e)}'}), 500

@app.route('/clear-session', methods=['POST'])
def clear_session():
    """Clear the current session and start fresh."""
    try:
        old_session_id = None
        
        # Get session ID from multiple sources
        if 'session_id' in session:
            old_session_id = session['session_id']
            session.pop('session_id', None)
        
        # Also check query parameters for external sessions
        external_session_id = request.args.get('_sid') or request.args.get('session_id')
        if external_session_id:
            old_session_id = external_session_id
        
        # Clean up old session directory
        if old_session_id:
            old_session_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'processing_sessions', old_session_id)
            if os.path.exists(old_session_dir):
                import shutil
                shutil.rmtree(old_session_dir)
                print(f"🧹 Cleaned up session directory: {old_session_id}")
        
        # Create new session
        processor = get_or_create_session()
        
        return jsonify({
            'status': 'success',
            'message': 'Session cleared and ready for new workflow',
            'old_session_id': old_session_id,
            'new_session_id': processor.session_id,
            'cleanup_completed': True
        })
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to clear session properly'
        }), 500

@app.route('/auto-reset', methods=['POST'])
def auto_reset():
    """Endpoint specifically for automatic reset after download completion."""
    try:
        print("🔄 Auto-reset triggered after download completion")
        
        # Get current session info
        processor = get_or_create_session()
        current_session = processor.session_id
        
        # Clear current session
        if 'session_id' in session:
            session.pop('session_id', None)
            
        # Clean up session directory
        session_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'processing_sessions', current_session)
        if os.path.exists(session_dir):
            import shutil
            shutil.rmtree(session_dir)
            print(f"🧹 Auto-cleanup completed for session: {current_session}")
        
        # Create fresh session
        new_processor = get_or_create_session()
        
        return jsonify({
            'status': 'success',
            'message': 'Auto-reset completed successfully',
            'old_session_id': current_session,
            'new_session_id': new_processor.session_id,
            'ready_for_next_workflow': True
        })
        
    except Exception as e:
        print(f"❌ Auto-reset failed: {str(e)}")
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Auto-reset failed'
        }), 500

@app.route('/new-session', methods=['GET', 'POST'])
def new_session():
    """Create a new session explicitly (for external apps)."""
    try:
        # Always create a new session
        processor = DataProcessor()
        
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
        
    except Exception as e:
        return jsonify({
            'status': 'error',
            'error': str(e),
            'message': 'Failed to create new session'
        }), 500

@app.route('/debug-sessions')
def debug_sessions():
    """Debug endpoint to show session information."""
    try:
        sessions_info = []
        base_dir = os.path.join(app.config['UPLOAD_FOLDER'], 'processing_sessions')
        
        if os.path.exists(base_dir):
            for session_dir in os.listdir(base_dir):
                full_path = os.path.join(base_dir, session_dir)
                if os.path.isdir(full_path):
                    # Get session info
                    files = []
                    for file in os.listdir(full_path):
                        file_path = os.path.join(full_path, file)
                        files.append({
                            'name': file,
                            'size': os.path.getsize(file_path),
                            'modified': os.path.getmtime(file_path)
                        })
                    
                    sessions_info.append({
                        'session_id': session_dir,
                        'created': os.path.getctime(full_path),
                        'modified': os.path.getmtime(full_path),
                        'files': files,
                        'has_combined_csv': any(f['name'] == OUTPUT_CSV_NAME for f in files)
                    })
        
        current_session = get_or_create_session()
        
        return jsonify({
            'current_session_id': current_session.session_id,
            'total_sessions': len(sessions_info),
            'sessions': sessions_info,
            'query_params': dict(request.args),
            'request_headers': dict(request.headers),
            'timestamp': time.time()
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Debug endpoint failed'
        }), 500

@app.route('/debug-request', methods=['GET', 'POST', 'PUT', 'DELETE'])
def debug_request():
    """Debug endpoint to show what the external app is sending."""
    try:
        debug_info = {
            'method': request.method,
            'url': request.url,
            'path': request.path,
            'query_params': dict(request.args),
            'headers': dict(request.headers),
            'content_type': request.content_type,
            'content_length': request.content_length,
            'is_json': request.is_json,
            'timestamp': time.time()
        }
        
        # Try to get request data in different formats
        try:
            if request.is_json:
                debug_info['json_data'] = request.get_json()
            else:
                debug_info['json_data'] = None
        except:
            debug_info['json_data'] = 'Error parsing JSON'
        
        try:
            debug_info['form_data'] = dict(request.form)
        except:
            debug_info['form_data'] = 'Error parsing form data'
        
        try:
            debug_info['files'] = list(request.files.keys())
        except:
            debug_info['files'] = 'Error parsing files'
        
        try:
            raw_data = request.get_data(as_text=True)
            debug_info['raw_data'] = raw_data[:500] + '...' if len(raw_data) > 500 else raw_data
            debug_info['raw_data_length'] = len(raw_data)
        except:
            debug_info['raw_data'] = 'Error getting raw data'
        
        print(f"🔍 Debug Request: {debug_info}")
        
        return jsonify({
            'status': 'debug_complete',
            'request_info': debug_info,
            'message': 'Request debugging information captured'
        })
        
    except Exception as e:
        return jsonify({
            'error': str(e),
            'message': 'Debug request failed'
        }), 500

@app.route('/ping')
def ping():
    """Simple ping endpoint to check if the service is alive."""
    return jsonify({'status': 'alive', 'message': 'BOL Extractor service is running'})

@app.route('/api/health')
def api_health():
    """API health check endpoint."""
    try:
        # Get existing processor to test session creation
        processor = get_or_create_session()
        
        return jsonify({
            'status': 'healthy',
            'service': 'BOL Extractor API',
            'session_id': processor.session_id,
            'endpoints': {
                'upload': '/upload',
                'upload_csv': '/upload-csv',
                'upload_base64': '/upload-base64',
                'upload_attachment': '/upload-attachment',
                'download': '/download',
                'download_bol': '/download-bol',
                'status': '/status',
                'files': '/files',
                'process_workflow': '/process-workflow',
                'clear_session': '/clear-session',
                'new_session': '/new-session',
                'ping': '/ping',
                'api_docs': '/api/docs',
                'debug': '/debug-sessions',
                'debug_request': '/debug-request'
            }
        })
    except Exception as e:
        return jsonify({
            'status': 'unhealthy',
            'error': str(e)
        }), 500

@app.route('/api/docs')
def api_docs():
    """API documentation endpoint."""
    return jsonify({
        'service': 'BOL Extractor API',
        'version': '1.0.0',
        'description': 'API for processing BOL (Bill of Lading) PDF files and CSV data',
        'endpoints': {
            'GET /': {
                'description': 'Main application page',
                'response': 'HTML page'
            },
            'POST /upload': {
                'description': 'Upload and process a PDF file',
                'parameters': {
                    'file': 'PDF file (multipart/form-data)'
                },
                'response': 'Processing result'
            },
            'POST /upload-csv': {
                'description': 'Upload and merge CSV/Excel data',
                'parameters': {
                    'file': 'CSV/Excel file (multipart/form-data)'
                },
                'response': 'Merge result'
            },
            'POST /upload-base64': {
                'description': 'Upload and process base64 encoded PDF file',
                'parameters': {
                    'file_data': 'Base64 encoded file data (JSON)',
                    'filename': 'Optional filename (JSON)'
                },
                'response': 'Processing result'
            },
            'POST /upload-attachment': {
                'description': 'Upload and process attachment data (flexible format)',
                'parameters': {
                    'attachmentData': 'Attachment data (base64 or bytes)',
                    'filename': 'Optional filename'
                },
                'response': 'Processing result'
            },
            'GET /download': {
                'description': 'Download processed CSV file',
                'response': 'CSV file download'
            },
            'GET /download-bol': {
                'description': 'Download processed BOL CSV file',
                'response': 'CSV file download'
            },
            'GET /download-bol/<filename>': {
                'description': 'Download specific file by name',
                'parameters': {
                    'filename': 'Name of file to download'
                },
                'response': 'File download'
            },
            'GET /status': {
                'description': 'Get current processing status',
                'response': 'Status information'
            },
            'GET /files': {
                'description': 'List available files in current session',
                'response': 'List of available files'
            },
            'POST /process-workflow': {
                'description': 'Process complete workflow',
                'response': 'Workflow processing result'
            },
            'POST /clear-session': {
                'description': 'Clear current session and start fresh',
                'response': 'Session clearing result'
            },
            'GET /ping': {
                'description': 'Simple ping to check service availability',
                'response': 'Service status'
            },
            'GET /health': {
                'description': 'Health check endpoint',
                'response': 'Health status'
            },
            'GET /api/health': {
                'description': 'API health check endpoint',
                'response': 'API health status'
            }
        },
        'cors': {
            'enabled': True,
            'allow_origin': '*',
            'allow_methods': ['GET', 'POST', 'OPTIONS', 'PUT', 'DELETE'],
            'allow_headers': ['Content-Type', 'Authorization', 'X-Requested-With']
        }
    })

@app.before_request
def handle_preflight():
    """Handle CORS preflight requests."""
    if request.method == "OPTIONS":
        response = make_response()
        response.headers["Access-Control-Allow-Origin"] = "*"
        response.headers['Access-Control-Allow-Headers'] = "Content-Type,Authorization,X-Requested-With,Cache-Control,Pragma,Expires"
        response.headers['Access-Control-Allow-Methods'] = "GET,PUT,POST,DELETE,OPTIONS"
        response.headers['Access-Control-Max-Age'] = '86400'
        return response

@app.route('/<path:path>', methods=['OPTIONS'])
def handle_options(path):
    """Handle OPTIONS requests for all paths."""
    response = make_response()
    response.headers["Access-Control-Allow-Origin"] = "*"
    response.headers['Access-Control-Allow-Headers'] = "Content-Type,Authorization,X-Requested-With,Cache-Control,Pragma,Expires"
    response.headers['Access-Control-Allow-Methods'] = "GET,PUT,POST,DELETE,OPTIONS"
    response.headers['Access-Control-Max-Age'] = '86400'
    return response

@app.after_request
def after_request(response):
    """Add headers to allow iframe embedding and CORS."""
    # Remove any existing CORS headers to prevent duplicates
    response.headers.pop('Access-Control-Allow-Origin', None)
    response.headers.pop('Access-Control-Allow-Headers', None)
    response.headers.pop('Access-Control-Allow-Methods', None)
    response.headers.pop('Access-Control-Allow-Credentials', None)
    response.headers.pop('Access-Control-Expose-Headers', None)
    
    # Add fresh CORS headers
    response.headers['Access-Control-Allow-Origin'] = '*'
    response.headers['Access-Control-Allow-Headers'] = 'Content-Type,Authorization,X-Requested-With,Cache-Control,Pragma,Expires'
    response.headers['Access-Control-Allow-Methods'] = 'GET, POST, OPTIONS, PUT, DELETE'
    response.headers['Access-Control-Allow-Credentials'] = 'false'
    response.headers['Access-Control-Expose-Headers'] = 'Content-Disposition'
    response.headers['X-Frame-Options'] = 'ALLOWALL'
    response.headers['X-Content-Type-Options'] = 'nosniff'
    return response

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port)