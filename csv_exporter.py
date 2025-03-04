import os
import glob
import pandas as pd
from config import OUTPUT_CSV_NAME

class CSVExporter:
    def __init__(self, session_dir):
        """Initialize the CSV exporter with a session directory."""
        self.session_dir = session_dir

    def combine_to_csv(self):
        """Combine all CSV files in the session directory into one."""
        try:
            # Get all CSV files in the session directory except the output file
            csv_files = [f for f in glob.glob(os.path.join(self.session_dir, "*.csv"))
                        if os.path.basename(f) != OUTPUT_CSV_NAME]

            if not csv_files:
                print("No CSV files found to combine")
                return False

            print(f"Found {len(csv_files)} CSV files to combine")

            # Read and combine all CSV files
            all_data = []
            for file in csv_files:
                try:
                    df = pd.read_csv(file)
                    all_data.append(df)
                    # Delete the individual CSV file after reading
                    os.remove(file)
                except Exception as e:
                    print(f"Error processing {file}: {str(e)}")
                    continue

            if not all_data:
                print("No data to combine")
                return False

            # Combine all dataframes
            combined_df = pd.concat(all_data, ignore_index=True)

            # Save the combined data to the output file in the session directory
            output_path = os.path.join(self.session_dir, OUTPUT_CSV_NAME)
            combined_df.to_csv(output_path, index=False)
            print(f"Successfully combined {len(csv_files)} files into {OUTPUT_CSV_NAME}")
            return True

        except Exception as e:
            print(f"Error combining CSV files: {str(e)}")
            return False

if __name__ == "__main__":
    exporter = CSVExporter()
    exporter.combine_to_csv()
