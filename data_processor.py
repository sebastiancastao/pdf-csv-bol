import os
import re
import csv
import io
from utils import FileUtils  # Removed OpenAI dependency

class DataProcessor:
    def __init__(self):
        """Initialize the data processor."""
        self.script_dir = FileUtils.get_script_dir()

    def process_all_files(self):
        """Process all TXT files in the directory."""
        txt_files = FileUtils.get_txt_files(self.script_dir)
        if not txt_files:
            print("No TXT files found in the directory")
            return False

        print(f"Found {len(txt_files)} TXT files to process")
        
        for txt_file in txt_files:
            self._process_single_file(txt_file)
        
        return True

    def _process_single_file(self, txt_file):
        """Process a single TXT file - extract invoice number and format data."""
        file_path = os.path.join(self.script_dir, txt_file)
        print(f"Processing {txt_file}...")
        
        try:
            # Read the content
            with open(file_path, 'r', encoding='utf-8') as file:
                content = file.read()

            # Get invoice number instead of order number
            invoice_no = self._get_invoice_no(content)
            if invoice_no:
                # Format the data (CSV output)
                formatted_data = self._format_data(content)
                if formatted_data:
                    # Save with new filename (using invoice number)
                    new_filename = f"{invoice_no}.csv"
                    new_file_path = os.path.join(self.script_dir, new_filename)
                    
                    with open(new_file_path, 'w', encoding='utf-8', newline='') as file:
                        file.write(formatted_data)
                    
                    # Optionally, delete the original TXT file if the name has changed
                    if new_filename != txt_file:
                        os.remove(file_path)
                        
                    print(f"Processed and renamed to {new_filename}")
            else:
                print(f"Invoice number not found in {txt_file}")
                    
        except Exception as e:
            print(f"Error processing {txt_file}: {str(e)}")

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

        # --- Process Table Rows ---
        # We assume table rows start immediately after the header until a line with "TOTAL CARTONS" or "SHIPPING INSTRUCTIONS:" appears.
        rows = []
        for line in lines[table_start+1:]:
            if "TOTAL CARTONS" in line.upper() or "SHIPPING INSTRUCTIONS:" in line.upper():
                break
            if not line.strip():
                continue
            if re.match(r'^\d+', line.strip()):
                tokens = line.split()
                if len(tokens) < 3:
                    continue
                # Token assumptions:
                cartons = tokens[0]
                style = tokens[1]
                individual_pieces = tokens[2]
                # Use the last token as the individual weight.
                individual_weight = tokens[-1]
                rows.append([cartons, bol_cube, individual_pieces, individual_weight, invoice_no, style])
            else:
                # Skip continuation lines for simplicity.
                continue

        # --- Generate CSV with Specific Column Mapping ---
        # We need 26 columns corresponding to A-Z.
        output = io.StringIO()
        writer = csv.writer(output)

        # Create header row with 26 columns (A to Z) and assign headers at the desired positions.
        header = [""] * 26
        # Fill in header names for the specific columns
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
        header[12] = "Purchase Order No.#"    # Column M
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

        # Ensure any header cell that is empty is explicitly an empty string.
        header = [col if col else "" for col in header]
        writer.writerow(header)

        # Process each data row to assign values to the specific columns.
        for row_data in rows:
            # row_data is [cartons, bol_cube, individual_pieces, individual_weight, invoice_no, style]
            data_row = [""] * 26
            data_row[13] = row_data[0]  # Cartons -> Column N
            data_row[16] = row_data[1]  # BOL Cube -> Column Q
            data_row[20] = row_data[2]  # Individual Pieces -> Column U
            data_row[22] = row_data[3]  # Individual Weight -> Column W
            data_row[24] = row_data[4]  # Invoice No. -> Column Y
            data_row[25] = row_data[5]  # Style -> Column Z
            writer.writerow(data_row)
        
        return output.getvalue()

if __name__ == "__main__":
    processor = DataProcessor()
    processor.process_all_files()
