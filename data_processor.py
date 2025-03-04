import os
import re
import csv
import io
from utils import FileUtils  # Removed OpenAI dependency

class DataProcessor:
    def __init__(self):
        """Initialize the data processor."""
        self.script_dir = FileUtils.get_script_dir()
        self.invoice_data = {}  # Store data for multi-page invoices

    def process_all_files(self):
        """Process all TXT files in the directory."""
        txt_files = FileUtils.get_txt_files(self.script_dir)
        if not txt_files:
            print("No TXT files found in the directory")
            return False

        print(f"Found {len(txt_files)} TXT files to process")
        print("Processing files in order:", txt_files)  # Debug: Show file processing order
        
        # First pass: Collect all data by invoice number
        for txt_file in txt_files:
            self._collect_invoice_data(txt_file)
        
        # Debug: Print collected invoice data summary
        print("\nCollected Invoice Data Summary:")
        for invoice_no, data in self.invoice_data.items():
            print(f"\nInvoice {invoice_no}:")
            print(f"Number of pages: {len(data['pages'])}")
            print(f"Has totals: {data['has_totals']}")
            for i, page in enumerate(data['pages']):
                print(f"  Page {i+1}:")
                print(f"    Rows: {len(page['rows'])}")
                print(f"    Has totals: {page['has_totals']}")
                if page['has_totals']:
                    print(f"    Totals: {page['totals']}")
                print(f"    BOL Cube: {page['bol_cube']}")
        
        # Second pass: Process collected data by invoice
        for invoice_no, pages_data in self.invoice_data.items():
            self._process_invoice_data(invoice_no, pages_data)
        
        return True

    def _collect_invoice_data(self, txt_file):
        """Collect data from a single TXT file and group by invoice number."""
        file_path = os.path.join(self.script_dir, txt_file)
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
                    'content': content,
                    'rows': rows,
                    'has_totals': has_totals,
                    'totals': totals,
                    'bol_cube': self._extract_bol_cube(content)
                }
                self.invoice_data[invoice_no]['pages'].append(page_data)
                if has_totals:
                    self.invoice_data[invoice_no]['has_totals'] = True

            # Delete the processed txt file
            os.remove(file_path)
            
        except Exception as e:
            print(f"Error collecting data from {txt_file}: {str(e)}")

    def _extract_table_data(self, content):
        """Extract table rows and totals from content."""
        lines = content.splitlines()
        table_start = None
        rows = []
        has_totals = False
        totals = {'pieces': '', 'weight': ''}

        # Debug: Print the first few lines to verify content
        print("\nFirst few lines of content:")
        for i, line in enumerate(lines[:10]):
            print(f"Line {i+1}: {line}")

        # Find table start
        for i, line in enumerate(lines):
            if "CARTONS" in line.upper() and "STYLE" in line.upper() and "PIECES" in line.upper():
                table_start = i
                print(f"\nFound table header at line {i+1}: {line}")  # Debug
                break

        if table_start is None:
            print("WARNING: Table header not found in content")
            return None

        # Process rows and look for totals
        print("\nProcessing table rows:")  # Debug
        for line in lines[table_start+1:]:
            if "TOTAL CARTONS" in line.upper():
                has_totals = True
                print(f"\nFound totals line: {line}")  # Debug
                tokens = line.split()
                print(f"Tokens in totals line: {tokens}")  # Debug
                if len(tokens) >= 11:
                    totals['pieces'] = tokens[3].replace(',', '')
                    totals['weight'] = tokens[-1].replace(',', '')
                    print(f"Extracted totals - Pieces: {totals['pieces']}, Weight: {totals['weight']}")  # Debug
                break
            if "SHIPPING INSTRUCTIONS:" in line.upper():
                print("\nReached shipping instructions - stopping table processing")  # Debug
                break
            if not line.strip():
                continue
            if re.match(r'^\d+', line.strip()):
                tokens = line.split()
                if len(tokens) >= 3:
                    cartons = tokens[0].replace(',', '')
                    style = tokens[1]
                    individual_pieces = tokens[2].replace(',', '')
                    individual_weight = tokens[-1].replace(',', '')
                    rows.append([cartons, individual_pieces, individual_weight, style])
                    print(f"Added row: {[cartons, individual_pieces, individual_weight, style]}")  # Debug

        print(f"\nExtracted {len(rows)} rows, has_totals: {has_totals}")  # Debug
        if has_totals:
            print(f"Final totals: {totals}")  # Debug

        return rows, has_totals, totals

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
        print(f"\nProcessing invoice {invoice_no}")  # Debug
        
        if not data['has_totals']:
            print(f"Warning: No totals found for invoice {invoice_no}")
            return

        # Get totals from the last page that has non-empty totals
        totals = None
        bol_cube = ""
        print("\nLooking for totals in pages (reverse order):")  # Debug
        for i, page in enumerate(reversed(data['pages'])):
            print(f"  Checking page {len(data['pages'])-i}")  # Debug
            print(f"    Has totals: {page['has_totals']}")
            if page['has_totals'] and page['totals']['pieces'] and page['totals']['weight']:
                totals = page['totals']
                bol_cube = page['bol_cube']
                print(f"    Found valid totals: {totals}")
                print(f"    BOL Cube: {bol_cube}")
                break

        if not totals:
            print(f"ERROR: No valid totals found in any page for invoice {invoice_no}")
            return

        # Collect all rows from all pages
        all_rows = []
        print("\nCollecting rows from all pages:")  # Debug
        for i, page in enumerate(data['pages']):
            print(f"  Page {i+1}: {len(page['rows'])} rows")
            for row in page['rows']:
                all_rows.append([row[0], bol_cube, row[1], row[2], invoice_no, row[3]])

        print(f"\nTotal rows collected: {len(all_rows)}")  # Debug
        print(f"Using totals - Pieces: {totals['pieces']}, Weight: {totals['weight']}")  # Debug

        # Generate CSV
        formatted_data = self._format_csv(all_rows, totals['pieces'], totals['weight'])
        if formatted_data:
            new_filename = f"{invoice_no}.csv"
            new_file_path = os.path.join(self.script_dir, new_filename)
            
            with open(new_file_path, 'w', encoding='utf-8', newline='') as file:
                file.write(formatted_data)
            
            print(f"Successfully processed multi-page invoice {invoice_no}")

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

        # Write data rows
        for row_data in rows:
            data_row = [""] * 28
            data_row[13] = row_data[0]  # Cartons
            data_row[16] = row_data[1]  # BOL Cube
            data_row[20] = row_data[2]  # Individual Pieces
            data_row[22] = row_data[3]  # Individual Weight
            data_row[24] = row_data[4]  # Invoice No.
            data_row[25] = row_data[5]  # Style
            data_row[21] = total_pieces  # Total Pieces
            data_row[23] = total_weight  # Total Weight
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