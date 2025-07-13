import os
import re
import csv
import io
import uuid
import shutil
from datetime import datetime
from utils import FileUtils  # Removed OpenAI dependency
import gc

class DataProcessor:
    def __init__(self, session_id=None):
        """Initialize the data processor with a session directory."""
        self.base_dir = FileUtils.get_script_dir()
        self.session_id = session_id or self._generate_session_id()
        self.session_dir = os.path.join(self.base_dir, 'processing_sessions', self.session_id)
        self.invoice_data = {}  # Store data for multi-page invoices
        self._setup_session_directory()

    def _generate_session_id(self):
        """Generate a unique session ID using timestamp and UUID."""
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        unique_id = str(uuid.uuid4())[:8]
        return f"session_{timestamp}_{unique_id}"

    def _setup_session_directory(self):
        """Create the session directory if it doesn't exist."""
        try:
            # Ensure parent directories exist first
            parent_dir = os.path.dirname(self.session_dir)
            os.makedirs(parent_dir, exist_ok=True)
            
            # Create the session directory
            os.makedirs(self.session_dir, exist_ok=True)
            
            # Verify the directory was created and is accessible
            if not os.path.exists(self.session_dir):
                raise Exception(f"Failed to create session directory: {self.session_dir}")
            
            if not os.access(self.session_dir, os.W_OK):
                raise Exception(f"Session directory not writable: {self.session_dir}")
            
            print(f"✅ Session directory ready: {self.session_dir}")
            
        except Exception as e:
            error_msg = f"Error setting up session directory: {str(e)}"
            print(f"❌ {error_msg}")
            raise Exception(error_msg)

    @staticmethod
    def cleanup_sessions():
        """Clean up all processing session directories."""
        base_dir = FileUtils.get_script_dir()
        sessions_dir = os.path.join(base_dir, 'processing_sessions')
        if os.path.exists(sessions_dir):
            try:
                shutil.rmtree(sessions_dir)
                print("Cleaned up all processing sessions")
            except Exception as e:
                print(f"Error cleaning up sessions: {str(e)}")

    def process_all_files(self):
        """Process all TXT files in the session directory."""
        # Get all txt files except requirements.txt
        txt_files = [f for f in FileUtils.get_txt_files(self.session_dir) if f != 'requirements.txt']
        if not txt_files:
            print("No TXT files found in the session directory")
            return False

        print(f"Found {len(txt_files)} TXT files to process")
        
        try:
            # Process all files without deleting them first
            print("=== PHASE 1: COLLECTING DATA FROM ALL FILES ===")
            for txt_file in txt_files:
                self._collect_invoice_data(txt_file)
            
            # Validate collected data
            print("=== DATA COLLECTION SUMMARY ===")
            total_collected_rows = 0
            for invoice_no, data in self.invoice_data.items():
                invoice_rows = sum(len(page['rows']) for page in data['pages'])
                total_collected_rows += invoice_rows
                print(f"Invoice {invoice_no}: {len(data['pages'])} pages, {invoice_rows} rows")
            print(f"TOTAL COLLECTED ROWS: {total_collected_rows}")
            
            # Process all collected data
            print("\n=== PHASE 2: PROCESSING COLLECTED DATA ===")
            total_processed_rows = 0
            for invoice_no, pages_data in self.invoice_data.items():
                rows_processed = self._process_invoice_data(invoice_no, pages_data)
                total_processed_rows += rows_processed
            
            print(f"\n=== PROCESSING SUMMARY ===")
            print(f"Total rows collected: {total_collected_rows}")
            print(f"Total rows processed: {total_processed_rows}")
            
            if total_collected_rows != total_processed_rows:
                print(f"⚠️  WARNING: Row count mismatch! {total_collected_rows - total_processed_rows} rows may have been lost!")
            else:
                print("✅ SUCCESS: All collected rows were processed successfully!")
            
            # Clean up TXT files only after successful processing
            print("\n=== PHASE 3: CLEANING UP TXT FILES ===")
            self._cleanup_txt_files()
            
            return True
            
        except Exception as e:
            print(f"Error processing files: {str(e)}")
            return False

    def _cleanup_txt_files(self):
        """Clean up TXT files after successful processing."""
        txt_files = [f for f in FileUtils.get_txt_files(self.session_dir) if f != 'requirements.txt']
        for txt_file in txt_files:
            file_path = os.path.join(self.session_dir, txt_file)
            try:
                os.remove(file_path)
                print(f"Cleaned up {txt_file}")
            except Exception as e:
                print(f"Warning: Could not remove {txt_file}: {str(e)}")

    def _collect_invoice_data(self, txt_file):
        """Collect data from a single TXT file and group by invoice number."""
        file_path = os.path.join(self.session_dir, txt_file)
        print(f"Collecting data from {txt_file}...")
        
        try:
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            invoice_no = self._get_invoice_no(content)
            if not invoice_no:
                print(f"Invoice number not found in {txt_file}")
                return

            # Initialize invoice data if not exists
            if invoice_no not in self.invoice_data:
                self.invoice_data[invoice_no] = {
                    'pages': [],
                    'has_totals': False
                }

            # Extract table rows and check for totals
            table_data = self._extract_table_data(content)
            if table_data:
                rows, has_totals, totals = table_data
                page_data = {
                    'rows': rows,  # Don't store full content, just extracted data
                    'has_totals': has_totals,
                    'totals': totals,
                    'bol_cube': self._extract_bol_cube(content)
                }
                self.invoice_data[invoice_no]['pages'].append(page_data)
                if has_totals:
                    self.invoice_data[invoice_no]['has_totals'] = True
                
                print(f"  Found {len(rows)} rows in {txt_file}, totals: {has_totals}")
            
            # DON'T DELETE THE TXT FILE HERE - wait until all processing is complete
            
        except Exception as e:
            print(f"Error collecting data from {txt_file}: {str(e)}")
        
        # Force garbage collection
        gc.collect()

    def _extract_table_data(self, content):
        """Extract table rows and totals from content."""
        lines = content.splitlines()
        table_start = None
        rows = []
        has_totals = False
        totals = {'pieces': '', 'weight': ''}

        # Find table start
        for i, line in enumerate(lines):
            if "CARTONS" in line.upper() and "STYLE" in line.upper() and "PIECES" in line.upper():
                table_start = i
                print(f"  Found table header at line {i}: {line.strip()}")
                break

        if table_start is None:
            print("  WARNING: Table header not found")
            return None

        # Process rows and look for totals
        print(f"  Processing table data from line {table_start + 1}...")
        for line_num, line in enumerate(lines[table_start+1:], table_start + 2):
            line_stripped = line.strip()
            
            # Check for totals first
            if "TOTAL CARTONS" in line.upper():
                has_totals = True
                tokens = line.split()
                if len(tokens) >= 11:
                    totals['pieces'] = tokens[3].replace(',', '')
                    totals['weight'] = tokens[-1].replace(',', '')
                print(f"  Found totals at line {line_num}: pieces={totals['pieces']}, weight={totals['weight']}")
                break
            
            # Stop at shipping instructions
            if "SHIPPING INSTRUCTIONS:" in line.upper():
                print(f"  Reached shipping instructions at line {line_num}")
                break
            
            # Skip empty lines
            if not line_stripped:
                continue
            
            # Improved row detection - more flexible patterns
            # Look for lines that contain numeric data that could be table rows
            if self._is_valid_table_row(line_stripped):
                tokens = line_stripped.split()
                if len(tokens) >= 3:
                    try:
                        # Try to extract the data - be more flexible with parsing
                        cartons = tokens[0].replace(',', '')
                        style = tokens[1]
                        individual_pieces = tokens[2].replace(',', '')
                        
                        # The weight should be the last numeric token
                        individual_weight = ""
                        for token in reversed(tokens):
                            if re.match(r'^\d+\.?\d*$', token.replace(',', '')):
                                individual_weight = token.replace(',', '')
                                break
                        
                        if individual_weight:  # Only add if we found a weight
                            rows.append([cartons, individual_pieces, individual_weight, style])
                            print(f"  Line {line_num}: Added row - cartons={cartons}, style={style}, pieces={individual_pieces}, weight={individual_weight}")
                        else:
                            print(f"  Line {line_num}: Skipped (no weight found) - {line_stripped}")
                    except (IndexError, ValueError) as e:
                        print(f"  Line {line_num}: Skipped (parsing error) - {line_stripped} - {str(e)}")
                else:
                    print(f"  Line {line_num}: Skipped (insufficient tokens) - {line_stripped}")
            else:
                print(f"  Line {line_num}: Skipped (not a table row) - {line_stripped}")

        print(f"  Extracted {len(rows)} rows total")
        return rows, has_totals, totals

    def _is_valid_table_row(self, line):
        """Check if a line is a valid table row using more flexible criteria."""
        # Remove extra spaces
        line = ' '.join(line.split())
        
        # Skip obviously non-data lines
        if not line:
            return False
        
        # Skip lines that are clearly headers or instructions
        skip_patterns = [
            r'^CARTONS.*STYLE.*PIECES',
            r'^SHIPPING INSTRUCTIONS',
            r'^TOTAL CARTONS',
            r'^Page \d+',
            r'^BILL OF LADING',
            r'^[A-Z\s]+:',  # Lines ending with colon (like labels)
        ]
        
        for pattern in skip_patterns:
            if re.match(pattern, line, re.IGNORECASE):
                return False
        
        # Look for patterns that indicate this is a data row
        # 1. Starts with a number (original logic)
        if re.match(r'^\d+', line):
            return True
        
        # 2. Contains multiple numeric values (could be a table row with formatting issues)
        numbers = re.findall(r'\d+', line)
        if len(numbers) >= 3:  # At least 3 numbers suggests a data row
            return True
        
        # 3. Contains typical style patterns (letters/numbers combination)
        if re.search(r'\b[A-Z]+\d+\b', line) or re.search(r'\b\d+[A-Z]+\b', line):
            tokens = line.split()
            # Check if we have enough tokens and at least one looks like a number
            if len(tokens) >= 3 and any(re.match(r'^\d+', token) for token in tokens):
                return True
        
        return False

    def _extract_bol_cube(self, content):
        """Extract BOL Cube from content."""
        lines = content.splitlines()
        for i, line in enumerate(lines):
            if "SHIPPING INSTRUCTIONS:" in line.upper():
                j = i - 1
                while j >= 0:
                    candidate = lines[j].strip()
                    match = re.search(r'\b\d{1,3}\.\d{2}\b', candidate)
                    if match:
                        return match.group(0)
                    j -= 1
                break
        return ""

    def _process_invoice_data(self, invoice_no, data):
        """Process collected data for an invoice and create CSV."""
        print(f"\n=== Processing Invoice {invoice_no} ===")
        
        # Count total rows across all pages
        total_rows = sum(len(page['rows']) for page in data['pages'])
        print(f"Total rows found across all pages: {total_rows}")
        
        # Get totals from the last page that has non-empty totals
        totals = None
        bol_cube = ""
        print("Looking for totals in pages (reverse order):")
        for i, page in enumerate(reversed(data['pages'])):
            print(f"  Checking page {len(data['pages'])-i}")
            print(f"    Has totals: {page['has_totals']}")
            if page['has_totals'] and page['totals']['pieces'] and page['totals']['weight']:
                totals = page['totals']
                bol_cube = page['bol_cube']
                print(f"    Found valid totals: {totals}")
                print(f"    BOL Cube: {bol_cube}")
                break

        # If no totals found, calculate from individual rows
        if not totals:
            print("No pre-calculated totals found. Calculating from individual rows...")
            totals = self._calculate_totals_from_rows(data['pages'])
            # Use BOL cube from first page that has one
            for page in data['pages']:
                if page['bol_cube']:
                    bol_cube = page['bol_cube']
                    break
            print(f"Calculated totals: {totals}")
            print(f"Using BOL Cube: {bol_cube}")

        # Collect all rows from all pages
        all_rows = []
        for page_num, page in enumerate(data['pages'], 1):
            print(f"Processing page {page_num}: {len(page['rows'])} rows")
            for row in page['rows']:
                # row is [cartons, individual_pieces, individual_weight, style]
                all_rows.append([row[0], bol_cube, row[1], row[2], invoice_no, row[3]])

        print(f"Total rows to process: {len(all_rows)}")

        # Generate CSV
        formatted_data = self._format_csv(all_rows, totals['pieces'], totals['weight'])
        if formatted_data:
            new_filename = f"{invoice_no}.csv"
            new_file_path = os.path.join(self.session_dir, new_filename)
            
            with open(new_file_path, 'w', encoding='utf-8', newline='') as file:
                file.write(formatted_data)
            
            print(f"Successfully processed invoice {invoice_no} with {len(all_rows)} rows")
            return len(all_rows)  # Return the number of rows processed for the summary
        else:
            print(f"ERROR: Failed to generate CSV for invoice {invoice_no}")
            return 0  # Return 0 for failed processing

    def _calculate_totals_from_rows(self, pages):
        """Calculate totals from individual rows when no totals are found."""
        total_pieces = 0
        total_weight = 0.0
        
        for page in pages:
            for row in page['rows']:
                try:
                    # row is [cartons, individual_pieces, individual_weight, style]
                    pieces = int(row[1].replace(',', '')) if row[1] else 0
                    weight = float(row[2].replace(',', '')) if row[2] else 0.0
                    total_pieces += pieces
                    total_weight += weight
                except (ValueError, IndexError) as e:
                    print(f"    Warning: Could not parse row {row}: {str(e)}")
                    continue
        
        return {
            'pieces': str(total_pieces),
            'weight': str(int(total_weight))  # Convert to int for consistency
        }

    def _format_csv(self, rows, total_pieces, total_weight):
        """Format rows into CSV with proper column mapping."""
        output = io.StringIO()
        writer = csv.writer(output)

        # Write header
        header = [""] * 28
        header[0] = "RTS ID"
        header[1] = "RTS Status"
        header[2] = "Load #"
        header[3] = "Wave #"
        header[4] = "Routed Date"
        header[5] = "Ready Date"
        header[6] = "Date of Pickup"
        header[7] = "Time of Pickup"
        header[8] = "Outbound BOL"
        header[9] = "Order Date"              # Column J
        header[10] = "Customer"
        header[11] = "Ship To Name"           # Column L
        header[12] = "Purchase Order No."    # Column M
        header[13] = "Cartons"                # Column N
        header[14] = "Start Date"             # Column O
        header[15] = "Cancel Date"            # Column P
        header[16] = "BOL Cube"               # Column Q
        header[17] = "Final Cube"
        header[18] = "Burlington Cube"
        header[19] = "Pallet"
        header[20] = "Individual Pieces"      # Column U
        header[21] = "Total Pieces"
        header[22] = "Individual Weight"      # Column W
        header[23] = "Total Weight"
        header[24] = "Invoice No."            # Column Y
        header[25] = "Style"                  # Column Z
        header[26] = "Release"                  # Column AA
        header[27] = "Assigned Trucking Co."                  # Column AB
        writer.writerow(header)

        # Sort rows by Invoice No. to ensure consistent grouping
        sorted_rows = sorted(rows, key=lambda x: x[4])  # Sort by Invoice No. (index 4)
        
        # Group rows by invoice number
        current_invoice = None
        is_first_row = True

        # Write data rows
        for row_data in sorted_rows:
            data_row = [""] * 28
            invoice_no = row_data[4]  # Get current row's invoice number
            
            # Check if this is the first row of a new invoice group
            if invoice_no != current_invoice:
                current_invoice = invoice_no
                is_first_row = True
            
            # Fill in the standard fields
            data_row[13] = row_data[0]  # Cartons
            data_row[16] = row_data[1]  # BOL Cube
            data_row[20] = row_data[2]  # Individual Pieces
            data_row[22] = row_data[3]  # Individual Weight
            data_row[24] = row_data[4]  # Invoice No.
            data_row[25] = row_data[5]  # Style
            
            # Only include totals in the first row of each invoice group
            if is_first_row:
                data_row[21] = total_pieces  # Total Pieces
                data_row[23] = total_weight  # Total Weight
                is_first_row = False
            
            writer.writerow(data_row)

        return output.getvalue()

    def _get_invoice_no(self, content):
        """Extract invoice number from content using regex."""
        lines = content.splitlines()
        invoice_no = ""
        for line in lines[:10]:
            if "BILL OF LADING" in line.upper():
                match = re.search(r'BILL OF LADING\s+([A-Z]\d+)', line, re.IGNORECASE)
                if match:
                    invoice_no = match.group(1)
                    break
        return invoice_no

    def _format_data(self, content):
        """Extract and structure shipping information into CSV format with specific column assignments."""
        lines = content.splitlines()
        
        # --- Extract BOL Cube ---
        bol_cube = ""
        for i, line in enumerate(lines):
            if "SHIPPING INSTRUCTIONS:" in line.upper():
                j = i - 1
                while j >= 0:
                    candidate = lines[j].strip()
                    match = re.search(r'\b\d{1,3}\.\d{2}\b', candidate)
                    if match:
                        bol_cube = match.group(0)
                        break
                    j -= 1
                break
        
        # --- Extract Invoice No. ---
        invoice_no = ""
        for line in lines[:10]:
            if "BILL OF LADING" in line.upper():
                match = re.search(r'BILL OF LADING\s+([A-Z]\d+)', line, re.IGNORECASE)
                if match:
                    invoice_no = match.group(1)
                    break

        # --- Locate the Table Header ---
        table_start = None
        for i, line in enumerate(lines):
            if "CARTONS" in line.upper() and "STYLE" in line.upper() and "PIECES" in line.upper():
                table_start = i
                break
        
        if table_start is None:
            print("Table header not found in the document.")
            return None

        # --- Process Table Rows and Extract Summary Totals ---
        rows = []
        summary_total_pieces = ""
        summary_total_weight = ""
        for line in lines[table_start+1:]:
            if "TOTAL CARTONS" in line.upper():
                # Expect a line like: "30 TOTAL CARTONS 2,160 TOTAL PIECES TOTAL VOL / WGT 595.2"
                tokens = line.split()
                if len(tokens) >= 11:
                    summary_total_pieces = tokens[3].replace(',', '')  # Remove commas
                    summary_total_weight = tokens[-1].replace(',', '')  # Remove commas
                break
            if "SHIPPING INSTRUCTIONS:" in line.upper():
                break
            if not line.strip():
                continue
            if re.match(r'^\d+', line.strip()):
                tokens = line.split()
                if len(tokens) < 3:
                    continue
                cartons = tokens[0].replace(',', '')  # Remove commas
                style = tokens[1]
                individual_pieces = tokens[2].replace(',', '')  # Remove commas
                individual_weight = tokens[-1].replace(',', '')  # Remove commas
                rows.append([cartons, bol_cube, individual_pieces, individual_weight, invoice_no, style])
            else:
                continue

        # --- Generate CSV with Specific Column Mapping ---
        # Create a CSV with 28 columns (A-AB)
        output = io.StringIO()
        writer = csv.writer(output)

        header = [""] * 28
        header[0] = "RTS ID"
        header[1] = "RTS Status"
        header[2] = "Load #"
        header[3] = "Wave #"
        header[4] = "Routed Date"
        header[5] = "Ready Date"
        header[6] = "Date of Pickup"
        header[7] = "Time of Pickup"
        header[8] = "Outbound BOL"
        header[9] = "Order Date"              # Column J
        header[10] = "Customer"
        header[11] = "Ship To Name"           # Column L
        header[12] = "Purchase Order No."    # Column M
        header[13] = "Cartons"                # Column N
        header[14] = "Start Date"             # Column O
        header[15] = "Cancel Date"            # Column P
        header[16] = "BOL Cube"               # Column Q
        header[17] = "Final Cube"
        header[18] = "Burlington Cube"
        header[19] = "Pallet"
        header[20] = "Individual Pieces"      # Column U
        header[21] = "Total Pieces"
        header[22] = "Individual Weight"      # Column W
        header[23] = "Total Weight"
        header[24] = "Invoice No."            # Column Y
        header[25] = "Style"                  # Column Z
        header[26] = "Release"                  # Column AA
        header[27] = "Assigned Trucking Co."                  # Column AB

        # Ensure any header cell that is empty is explicitly an empty string.
        header = [col if col else "" for col in header]
        writer.writerow(header)

        # Write each data row, adding the summary totals to the designated columns.
        for row_data in rows:
            # row_data is [cartons, bol_cube, individual_pieces, individual_weight, invoice_no, style]
            data_row = [""] * 28
            data_row[13] = row_data[0]  # Cartons -> Column N
            data_row[16] = row_data[1]  # BOL Cube -> Column Q
            data_row[20] = row_data[2]  # Individual Pieces -> Column U
            data_row[22] = row_data[3]  # Individual Weight -> Column W
            data_row[24] = row_data[4]  # Invoice No. -> Column Y
            data_row[25] = row_data[5]  # Style -> Column Z
            data_row[21] = summary_total_pieces  # Total Pieces -> Column V (index 21)
            data_row[23] = summary_total_weight  # Total Weight -> Column X (index 23)
            writer.writerow(data_row)
        
        return output.getvalue()

if __name__ == "__main__":
    processor = DataProcessor()
    processor.process_all_files()