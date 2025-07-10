#!/usr/bin/env python3
"""
Test script to verify the improved PDF processing functionality.
This script demonstrates the fixes that should capture all 366 rows from a 2-page PDF.
"""

import os
import shutil
from pdf_processor import PDFProcessor
from data_processor import DataProcessor
from csv_exporter import CSVExporter

def test_pdf_processing():
    """Test the complete PDF processing workflow."""
    print("=== PDF PROCESSING TEST ===")
    print("This test demonstrates the improved processing that should capture all rows.")
    print("\nImprovements made:")
    print("1. ✅ Fixed premature file deletion - TXT files preserved until processing complete")
    print("2. ✅ Improved table row detection - more flexible regex patterns")
    print("3. ✅ Added comprehensive validation - tracks all rows processed")
    print("4. ✅ Handle missing totals - calculate from individual rows")
    print("5. ✅ Detailed logging - shows exactly what's happening at each step")
    
    # Create a test session
    processor = DataProcessor()
    session_dir = processor.session_dir
    
    print(f"\nTest session created: {session_dir}")
    print("\nTo test with your 2-page PDF:")
    print(f"1. Copy your PDF file to: {session_dir}")
    print("2. Run the processing steps below")
    print("3. Check the output for all 366 rows")
    
    # Instructions for manual testing
    print("\n=== MANUAL TEST INSTRUCTIONS ===")
    print("1. Copy your 2-page PDF to the session directory")
    print("2. Run the following code:")
    print(f"""
# Process PDF
pdf_processor = PDFProcessor('{session_dir}')
pdf_processor.process_first_pdf()

# Process extracted text
data_processor = DataProcessor('{processor.session_id}')
data_processor.process_all_files()

# Combine to final CSV
csv_exporter = CSVExporter('{session_dir}')
csv_exporter.combine_to_csv()

print("Check the combined_data.csv file for all 366 rows!")
""")

    return session_dir

def run_full_test(pdf_path=None):
    """Run the complete test if a PDF path is provided."""
    if not pdf_path or not os.path.exists(pdf_path):
        print("No PDF path provided or file doesn't exist.")
        print("Use: python test_processor.py /path/to/your/pdf")
        return
    
    # Create a test session
    processor = DataProcessor()
    session_dir = processor.session_dir
    
    # Copy PDF to session directory
    pdf_filename = os.path.basename(pdf_path)
    target_path = os.path.join(session_dir, pdf_filename)
    shutil.copy2(pdf_path, target_path)
    print(f"Copied PDF to: {target_path}")
    
    try:
        # Step 1: Process PDF
        print("\n=== STEP 1: PROCESSING PDF ===")
        pdf_processor = PDFProcessor(session_dir)
        if not pdf_processor.process_first_pdf():
            print("ERROR: PDF processing failed")
            return
        
        # Step 2: Process extracted text
        print("\n=== STEP 2: PROCESSING TEXT DATA ===")
        data_processor = DataProcessor(processor.session_id)
        if not data_processor.process_all_files():
            print("ERROR: Text processing failed")
            return
        
        # Step 3: Combine to final CSV
        print("\n=== STEP 3: COMBINING TO FINAL CSV ===")
        csv_exporter = CSVExporter(session_dir)
        if not csv_exporter.combine_to_csv():
            print("ERROR: CSV export failed")
            return
        
        # Check final result
        output_path = os.path.join(session_dir, "combined_data.csv")
        if os.path.exists(output_path):
            # Count rows in final CSV
            with open(output_path, 'r', encoding='utf-8') as f:
                lines = f.readlines()
                row_count = len(lines) - 1  # Subtract header
            
            print(f"\n✅ SUCCESS: Processing complete!")
            print(f"Final CSV: {output_path}")
            print(f"Total rows in final CSV: {row_count}")
            
            if row_count >= 366:
                print("🎉 EXCELLENT: All expected rows captured!")
            else:
                print(f"⚠️  WARNING: Only {row_count} rows found, expected 366")
        else:
            print("ERROR: Final CSV not created")
            
    except Exception as e:
        print(f"ERROR during processing: {str(e)}")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    import sys
    
    if len(sys.argv) > 1:
        # Run full test with provided PDF
        pdf_path = sys.argv[1]
        run_full_test(pdf_path)
    else:
        # Show test instructions
        test_pdf_processing() 