#!/usr/bin/env python3
import argparse
import pandas as pd
import numpy as np
from typing import List, Dict, Any
import sys
from tabulate import tabulate


class CSVDiffAnalyzer:
    def __init__(self, csv1_path: str, csv2_path: str):
        """Initialize with paths to two CSV files to compare."""
        print(f"Loading CSV files...")
        self.df1 = pd.read_csv(csv1_path, low_memory=False)
        self.df2 = pd.read_csv(csv2_path, low_memory=False)
        self.csv1_name = csv1_path.split("/")[-1]
        self.csv2_name = csv2_path.split("/")[-1]
        print(f"Loaded {self.csv1_name} with {len(self.df1)} rows")
        print(f"Loaded {self.csv2_name} with {len(self.df2)} rows")

    def compare_column_presence(self) -> Dict[str, List[str]]:
        """Compare which columns are present in each DataFrame."""
        cols1 = set(self.df1.columns)
        cols2 = set(self.df2.columns)

        return {
            "unique_to_first": sorted(list(cols1 - cols2)),
            "unique_to_second": sorted(list(cols2 - cols1)),
            "common": sorted(list(cols1 & cols2)),
        }

    def analyze_nan_differences(self, column: str) -> Dict[str, Any]:
        """Analyze NaN value differences for a specific column."""
        if column not in self.df1.columns or column not in self.df2.columns:
            return {"error": "Column not present in both DataFrames"}

        nan_count1 = self.df1[column].isna().sum()
        nan_count2 = self.df2[column].isna().sum()

        return {
            "nan_count_1": nan_count1,
            "nan_percent_1": (nan_count1 / len(self.df1)) * 100,
            "nan_count_2": nan_count2,
            "nan_percent_2": (nan_count2 / len(self.df2)) * 100,
        }

    def analyze_value_distributions(self, column: str) -> Dict[str, Any]:
        """Analyze value distributions for a specific column."""
        if column not in self.df1.columns or column not in self.df2.columns:
            return {"error": "Column not present in both DataFrames"}

        dist1 = self.df1[column].value_counts().head(10)
        dist2 = self.df2[column].value_counts().head(10)

        return {"top_values_1": dist1.to_dict(), "top_values_2": dist2.to_dict()}

    def find_mismatched_values(
        self, column: str, sample_size: int = 5, output_file: str = None
    ) -> Dict[str, Any]:
        """
        Find rows where values don't match between DataFrames.
        Optionally writes all mismatches to a file.

        Parameters:
        -----------
        column : str
            Column name to compare
        sample_size : int
            Number of samples to return in the result dictionary
        output_file : str, optional
            If provided, writes all mismatches to this file
        """
        if column not in self.df1.columns or column not in self.df2.columns:
            return {"error": "Column not present in both DataFrames"}

        # Merge on 'Run' column assuming it's the unique identifier
        merged = pd.merge(
            self.df1[["Run", column]],
            self.df2[["Run", column]],
            on="Run",
            suffixes=("_1", "_2"),
        )

        # Find mismatches (ignoring cases where both are NaN)
        mismatches = merged[
            (
                (merged[f"{column}_1"] != merged[f"{column}_2"])
                & (~(merged[f"{column}_1"].isna() & merged[f"{column}_2"].isna()))
            )
        ]

        # Write to file if output_file is provided
        if output_file and len(mismatches) > 0:
            with open(output_file, "a") as f:  # 'a' for append mode
                f.write(f"\n=== Mismatches in {column} ===\n")
                f.write(f"Total mismatches: {len(mismatches)}\n")
                f.write(
                    f"{'Run':<15} | {'Value in ' + self.csv1_name:<30} | {'Value in ' + self.csv2_name:<30}\n"
                )
                f.write("-" * 80 + "\n")

                for idx, row in mismatches.iterrows():
                    f.write(
                        f"{row['Run']:<15} | {str(row[f'{column}_1']):<30} | {str(row[f'{column}_2']):<30}\n"
                    )

                f.write("\n")  # Add blank line between sections

        return {
            "total_mismatches": len(mismatches),
            "sample_mismatches": mismatches.head(sample_size).to_dict("records"),
        }

    def compare_identical_columns(self) -> Dict[str, Any]:
        """Compare values in each column to find completely identical columns."""
        common_cols = set(self.df1.columns) & set(self.df2.columns)
        identical_cols = []
        different_cols = []

        for col in common_cols:
            # Check if the columns are identical (considering NaN values)
            if self.df1[col].equals(self.df2[col]):
                identical_cols.append(col)
            else:
                different_cols.append(col)

        return {
            "identical": sorted(identical_cols),
            "different": sorted(different_cols),
            "identical_count": len(identical_cols),
            "different_count": len(different_cols),
        }

    def find_identical_rows(self) -> Dict[str, Any]:
        """Find rows that are completely identical and different between the two DataFrames."""
        # Merge on 'Run' column and compare all common columns
        common_cols = list(set(self.df1.columns) & set(self.df2.columns))
        merged = pd.merge(
            self.df1[common_cols],
            self.df2[common_cols],
            on="Run",
            suffixes=("_1", "_2"),
        )

        # Find identical rows
        identical_mask = True
        for col in common_cols:
            if col != "Run":  # Skip the merge column
                identical_mask &= (merged[f"{col}_1"] == merged[f"{col}_2"]) | (
                    merged[f"{col}_1"].isna() & merged[f"{col}_2"].isna()
                )

        # Get identical and different runs
        identical_runs = merged[identical_mask]["Run"].tolist()
        different_runs = merged[~identical_mask]["Run"].tolist()

        return {
            "identical_count": len(identical_runs),
            "different_count": len(different_runs),
            "total_rows": len(self.df1),
            "identical_percentage": (len(identical_runs) / len(self.df1)) * 100,
            "different_percentage": (len(different_runs) / len(self.df1)) * 100,
            "identical_runs": identical_runs,
            "different_runs": different_runs,
        }

    def generate_difference_report(self, output_file: str):
        """Generate a comprehensive difference report."""
        with open(output_file, "w") as f:
            # Column presence analysis
            cols = self.compare_column_presence()
            f.write("=== Column Presence Analysis ===\n")
            f.write(
                f"Columns unique to {self.csv1_name}: {len(cols['unique_to_first'])}\n"
            )
            f.write(f"{cols['unique_to_first']}\n\n")
            f.write(
                f"Columns unique to {self.csv2_name}: {len(cols['unique_to_second'])}\n"
            )
            f.write(f"{cols['unique_to_second']}\n\n")

            # Identical columns analysis
            identical = self.compare_identical_columns()
            f.write("=== Identical Columns Analysis ===\n")
            f.write(f"Number of identical columns: {identical['identical_count']}\n")
            f.write(f"Identical columns: {identical['identical']}\n\n")
            f.write(f"Number of different columns: {identical['different_count']}\n")
            f.write(f"Different columns: {identical['different']}\n\n")

            # Row comparison
            identical_rows = self.find_identical_rows()
            f.write("=== Row Comparison Analysis ===\n")
            f.write(f"Total rows: {identical_rows['total_rows']}\n")
            f.write(f"Identical rows: {identical_rows['identical_count']}\n")
            f.write(
                f"Percentage identical: {identical_rows['identical_percentage']:.2f}%\n\n"
            )

            # Value differences in key columns
            f.write("=== Value Differences in Key Columns ===\n")
            key_columns = [
                "CELL_LINE",
                "TISSUE",
                "INHIBITOR",
                "CONDITION",
                "LIBRARYTYPE",
                "ScientificName",
                "AUTHOR",
            ]

            # First write summary
            f.write("Summary of differences:\n")
            for col in key_columns:
                if col in identical["different"]:
                    mismatches = self.find_mismatched_values(col, sample_size=5)
                    f.write(f"{col}: {mismatches['total_mismatches']} differences\n")
            f.write("\n")

            # Then write detailed mismatches to same file
            for col in key_columns:
                if col in identical["different"]:
                    self.find_mismatched_values(
                        col, sample_size=None, output_file=output_file
                    )

    def interactive_analysis(self):
        """Run interactive analysis of the CSV differences."""
        while True:
            print("\nCSV Difference Analysis Menu:")
            print("1. Compare column presence")
            print("2. Analyze NaN differences")
            print("3. Analyze value distributions")
            print("4. Find mismatched values")
            print("5. Find identical columns")
            print("6. Compare identical rows")
            print("7. Generate comprehensive difference report")
            print("8. Exit")

            choice = input("\nEnter your choice (1-8): ")
            if choice == "1":
                columns = self.compare_column_presence()
                print("\nColumns unique to", self.csv1_name)
                print(columns["unique_to_first"])
                print("\nColumns unique to", self.csv2_name)
                print(columns["unique_to_second"])
                print("\nCommon columns:")
                print(columns["common"])

            elif choice == "2":
                column = input("Enter column name to analyze NaN differences: ")
                results = self.analyze_nan_differences(column)
                if "error" in results:
                    print(results["error"])
                    continue

                print(f"\nNaN Analysis for {column}:")
                print(
                    tabulate(
                        [
                            [
                                self.csv1_name,
                                results["nan_count_1"],
                                f"{results['nan_percent_1']:.2f}%",
                            ],
                            [
                                self.csv2_name,
                                results["nan_count_2"],
                                f"{results['nan_percent_2']:.2f}%",
                            ],
                        ],
                        headers=["File", "NaN Count", "NaN Percentage"],
                    )
                )

            elif choice == "3":
                column = input("Enter column name to analyze value distributions: ")
                results = self.analyze_value_distributions(column)
                if "error" in results:
                    print(results["error"])
                    continue

                print(f"\nTop values in {self.csv1_name}:")
                for value, count in results["top_values_1"].items():
                    print(f"{value}: {count}")

                print(f"\nTop values in {self.csv2_name}:")
                for value, count in results["top_values_2"].items():
                    print(f"{value}: {count}")

            elif choice == "4":
                column = input("Enter column name to find mismatches: ")
                sample_size = int(input("Enter number of example mismatches to show: "))
                results = self.find_mismatched_values(column, sample_size)

                if "error" in results:
                    print(results["error"])
                    continue

                print(f"\nTotal mismatches: {results['total_mismatches']}")
                if results["total_mismatches"] > 0:
                    print("\nExample mismatches:")
                    mismatches_df = pd.DataFrame(results["sample_mismatches"])
                    print(tabulate(mismatches_df, headers="keys", tablefmt="psql"))

            if choice == "5":
                results = self.compare_identical_columns()
                print(f"\nFound {results['identical_count']} identical columns:")
                print("\nIdentical columns:")
                for col in results["identical"]:
                    print(f"- {col}")
                print(f"\nFound {results['different_count']} different columns:")
                print("\nDifferent columns:")
                for col in results["different"]:
                    print(f"- {col}")

            elif choice == "6":
                results = self.find_identical_rows()
                print(
                    f"\nFound {results['identical_count']} identical rows "
                    f"({results['identical_percentage']:.2f}%) and "
                    f"{results['different_count']} different rows "
                    f"({results['different_percentage']:.2f}%) "
                    f"out of {results['total_rows']} total rows"
                )

                print(
                    "\nWould you like to see the Run IDs? (i=identical/d=different/b=both/n=none): "
                )
                view_choice = input().lower()

                if view_choice == "i":
                    print("\nIdentical Run IDs:")
                    for run in results["identical_runs"]:
                        print(run)
                elif view_choice == "d":
                    print("\nDifferent Run IDs:")
                    for run in results["different_runs"]:
                        print(run)
                elif view_choice == "b":
                    print("\nIdentical Run IDs:")
                    for run in results["identical_runs"]:
                        print(run)
                    print("\nDifferent Run IDs:")
                    for run in results["different_runs"]:
                        print(run)

            elif choice == "7":
                output_file = input("Enter output filename for difference report: ")
                print(f"\nGenerating comprehensive difference report...")
                self.generate_difference_report(output_file)
                print(f"Report saved to: {output_file}")

            elif choice == "8":
                print("Exiting...")
                break
            else:
                print("Invalid choice. Please try again.")


def main():
    parser = argparse.ArgumentParser(
        description="Interactive tool to analyze differences between two CSV files."
    )
    parser.add_argument("csv1", help="Path to first CSV file")
    parser.add_argument("csv2", help="Path to second CSV file")
    args = parser.parse_args()

    analyzer = CSVDiffAnalyzer(args.csv1, args.csv2)
    analyzer.interactive_analysis()


if __name__ == "__main__":
    main()
