import pandas as pd
import os
import sys

def analyze_column_counts(file_path, output_dir):
    """
    Read a CSV file and write value counts for specified columns to separate files.
    
    Args:
        file_path (str): Path to the CSV file
        output_dir (str): Directory to write output files
    """
    try:
        # Create output directory if it doesn't exist
        os.makedirs(output_dir, exist_ok=True)
        
        # Read the CSV file
        print(f"Reading file: {file_path}")
        df = pd.read_csv(file_path)
        
        # List of columns to analyze
        columns_to_analyze = ["CELL_LINE", "TISSUE", "INHIBITOR", "CONDITION", "AUTHOR"]
        
        # Check which requested columns are actually in the dataframe
        available_columns = [col for col in columns_to_analyze if col in df.columns]
        
        if not available_columns:
            print("None of the specified columns were found in the CSV file.")
            print("Available columns are:", list(df.columns))
            return
            
        # Analyze each column and write to file
        for column in available_columns:
            print(f"Processing column: {column}")
            
            # Get value counts
            value_counts = df[column].value_counts()
            
            # Create a summary string
            summary = [
                f"=== Value counts for {column} ===\n",
                f"Total unique values: {len(value_counts)}\n",
                "\nComplete value counts:\n",
                value_counts.to_string(),
                "\n\nTop 3 most common values:\n",
                value_counts.head(3).to_string()
            ]
            
            # Write to file
            output_file = os.path.join(output_dir, f"{column.lower()}_counts.txt")
            with open(output_file, 'w') as f:
                f.write('\n'.join(summary))
            
            print(f"Results written to: {output_file}")
            
    except FileNotFoundError:
        print(f"Error: File '{file_path}' not found.")
    except pd.errors.EmptyDataError:
        print(f"Error: File '{file_path}' is empty.")
    except Exception as e:
        print(f"An error occurred: {str(e)}")

if __name__ == "__main__":
    if len(sys.argv) != 3:
        print("Usage: python script.py <input_csv_path> <output_directory>")
        sys.exit(1)
        
    file_path = sys.argv[1]
    output_dir = sys.argv[2]
    analyze_column_counts(file_path, output_dir)