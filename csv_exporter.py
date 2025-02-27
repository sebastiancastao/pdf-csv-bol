import os
import csv
from io import StringIO
from utils import FileUtils
from config import OUTPUT_CSV_NAME

class CSVExporter:
    def __init__(self):
        """Initialize the CSV exporter."""
        self.script_dir = FileUtils.get_script_dir()

    def combine_to_csv(self):
        """Combines all CSV files in the directory into a single CSV file and deletes the originals."""
        # Look for files ending with .csv, but skip the combined output file if it exists.
        csv_files = [
            f for f in os.listdir(self.script_dir)
            if f.lower().endswith('.csv') and f != OUTPUT_CSV_NAME
        ]
        
        if not csv_files:
            print("No CSV files found in the directory")
            return False
            
        # Initialize variables to store combined data
        header = None
        all_rows = []
        
        print(f"Found {len(csv_files)} CSV files to process")
        
        # Process each CSV file
        for csv_file in csv_files:
            file_path = os.path.join(self.script_dir, csv_file)
            print(f"Processing {csv_file}...")
            
            try:
                with open(file_path, 'r', encoding='utf-8') as file:
                    content = file.read().strip()
                    
                # Use CSV reader to properly handle the content
                csv_reader = csv.reader(StringIO(content))
                rows = list(csv_reader)
                
                if not rows:
                    print(f"Warning: {csv_file} appears to be empty")
                    continue
                    
                # For the first file with content, capture the header as is.
                if header is None:
                    header = rows[0]
                    print(f"Using header: {header}")
                
                # Add all rows except header
                for row in rows[1:]:
                    if row:  # Skip empty rows
                        all_rows.append(row)
                        
            except Exception as e:
                print(f"Error processing {csv_file}: {str(e)}")
                continue
        
        if not header or not all_rows:
            print("No valid data found to combine")
            return False
            
        # Create the output CSV file
        output_file = os.path.join(self.script_dir, OUTPUT_CSV_NAME)
        
        try:
            with open(output_file, 'w', newline='', encoding='utf-8') as csvfile:
                csv_writer = csv.writer(csvfile)
                
                # Write the header
                csv_writer.writerow(header)
                
                # Write all data rows
                csv_writer.writerows(all_rows)
                
            print(f"\nSuccessfully created {output_file}")
            print(f"Combined {len(all_rows)} data rows from {len(csv_files)} files")
        except Exception as e:
            print(f"Error creating CSV file: {str(e)}")
            return False

        # Delete the individual CSV files after successful creation of the combined file.
        for csv_file in csv_files:
            file_path = os.path.join(self.script_dir, csv_file)
            try:
                os.remove(file_path)
                print(f"Deleted {csv_file}")
            except Exception as e:
                print(f"Error deleting {csv_file}: {str(e)}")
        
        return True

if __name__ == "__main__":
    exporter = CSVExporter()
    exporter.combine_to_csv()
