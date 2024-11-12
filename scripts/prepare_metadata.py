#!/usr/bin/env python3
import argparse
import pandas as pd
import numpy as np


def safe_string_operation(series, operation, *args, **kwargs):
    """
    Safely perform string operations on a series, handling NaN values.
    Returns a boolean mask with NaN values set to False.
    """
    if operation == "contains":
        mask = series.str.contains(*args, **kwargs, na=False)
    elif operation == "startswith":
        mask = series.str.startswith(*args, na=False)
    elif operation == "endswith":
        mask = series.str.endswith(*args, na=False)
    else:
        raise ValueError(f"Unsupported operation: {operation}")
    return mask.fillna(False)


def clean_cell_lines(df):
    """
    Clean and standardize cell line information.
    """
    non_cell_lines = [
        # Mouse/Organism Strains
        'C57BL/6', 'Col-0',
        
        # # Generic Cell Types
        # 'neuron', 'neurons', 'oocyte', 'platelet', 'platelets',
        # 'T-cell', 'macrophage', 'Macrophage', 'hepatocyte',
        # 'Thymocytes', 'CD4+ T cells', 'CD8+ T cells',
        
        # Generic Terms
        'cell line', 'whole cells', 'all cells', 'Suspension cell line',
        'wild type', 'Mutant', 'Wt', 'yeast', 'yeast cells',
        'yeast cell', 'bacterial cell', 'bacteria', 'fungal cells',
        'archaeal cell', 'archaea', 'somatic cells', 'whole organism',
        'blastocyst', 'morula', 'ICM'
    ]
    
    # Create mask for non-cell lines using case-insensitive matching
    non_cell_line_mask = df['CELL_LINE'].str.lower().isin([x.lower() for x in non_cell_lines])
    df.loc[non_cell_line_mask, 'CELL_LINE'] = np.nan
    

    # Standardize common cell types
    cell_type_mapping = {
        "lymphoblastoid": safe_string_operation(
            df["CELL_LINE"], "contains", "lymphoblastoid", case=False
        ),
        "Fibroblast": safe_string_operation(
            df["CELL_LINE"], "contains", "fibroblast", case=False
        ),
        "Neuroblast": safe_string_operation(
            df["CELL_LINE"], "contains", "neuroblast", case=False
        ),
        "Myoblast": safe_string_operation(
            df["CELL_LINE"], "contains", "myoblast", case=False
        ),
        "Ba/F3": safe_string_operation(
            df["CELL_LINE"], "contains", "mouse lymphoid Ba/F3 cells", case=False
        ),
    }

    for cell_type, mask in cell_type_mapping.items():
        df.loc[mask, "CELL_LINE"] = cell_type

    # Fix misidentified cell lines
    misidentified_conditions = [
        (
            df["CELL_LINE"].eq("S2")
            & ~df["ScientificName"].eq("Drosophila melanogaster")
        ),
        df["CELL_LINE"].eq("TSC2"),
        (df["CELL_LINE"].eq("H1") & df["ScientificName"].eq("Escherichia coli")),
        (df["CELL_LINE"].eq("PC3") & df["ScientificName"].eq("Neurospora crassa")),
        (
            df["CELL_LINE"].eq("H1")
            & df["TISSUE"].eq("embryo")
            & ~df["ScientificName"].eq("Homo sapiens")
        ),
        (
            safe_string_operation(df["CELL_LINE"], "endswith", "-cell")
            & df["TISSUE"].eq("embryo")
        ),
        (
            safe_string_operation(df["CELL_LINE"], "endswith", "derived tumor")
            & df["TISSUE"].eq("Glioblastoma")
        ),
    ]

    for condition in misidentified_conditions:
        df.loc[condition.fillna(False), ["CELL_LINE"]] = np.nan

    return df


def clean_inhibitors(df):
    """
    Clean and standardize inhibitor information.
    """
    # Convert to lowercase, handling NaN values
    df["INHIBITOR"] = df["INHIBITOR"].str.lower()

    # Standardize 'untreated' entries
    untreated_mask = (
        df["INHIBITOR"].isin(["no treatment", "none", "no erythromycin"]).fillna(False)
    )
    df.loc[untreated_mask, "INHIBITOR"] = "untreated"

    # Standardize special cases
    thapsigargin_mask = safe_string_operation(
        df["INHIBITOR"], "endswith", "thapsigargin"
    )
    df.loc[thapsigargin_mask, "INHIBITOR"] = "thapsigargin"

    # Define accepted inhibitors
    accepted_inhibitors = [
        "untreated",
        "chx",
        "harr",
        "lactim",
        "chx_harr",
        "chx_lactim",
        "frozen",
        "tetracycline",
        "thapsigargin",
        "anisomycin",
        "tunicamycin",
    ]

    # Set non-standard inhibitors to NaN
    valid_mask = df["INHIBITOR"].isin(accepted_inhibitors) | safe_string_operation(
        df["INHIBITOR"], "endswith", "in"
    )
    df.loc[~valid_mask.fillna(False), "INHIBITOR"] = np.nan

    # Remove time-based entries
    time_mask = safe_string_operation(df["INHIBITOR"], "endswith", "min")
    df.loc[time_mask, "INHIBITOR"] = np.nan

    return df


def clean_library_types(df):
    """
    Clean and standardize library types.
    """
    library_type_mapping = {
        "RFP": [
            safe_string_operation(df["LIBRARYTYPE"], "startswith", "Ribosome"),
            safe_string_operation(df["LIBRARYTYPE"], "contains", "ibosome", case=False),
        ],
        "SSU": [
            safe_string_operation(df["LIBRARYTYPE"], "startswith", "40S"),
            safe_string_operation(
                df["LIBRARYTYPE"], "startswith", "small ribosomal subunit"
            ),
        ],
        "LSU": [
            safe_string_operation(df["LIBRARYTYPE"], "startswith", "80S"),
            safe_string_operation(
                df["LIBRARYTYPE"], "startswith", "large ribosomal subunit"
            ),
        ],
        "RiboTag": [safe_string_operation(df["LIBRARYTYPE"], "startswith", "Ribotag")],
    }

    for lib_type, conditions in library_type_mapping.items():
        for condition in conditions:
            df.loc[condition, "LIBRARYTYPE"] = lib_type

    return df


def clean_scientific_names(df):
    """
    Clean and standardize scientific names.
    """
    organism_list = [
        "Salmonella enterica",
        "Escherichia coli",
        "Saccharomyces cerevisiae",
        "Zymomonas mobilis",
        "Oryza sativa",
        "Streptomyces avermitilis",
        "Mycobacterium tuberculosis",
        "Streptomyces tsukubensis",
        "Staphylococcus aureus",
        "Trypanosoma cruzi",
        "Lacticaseibacillus rhamnosus",
        "Bacillus subtilis",
        "Caulobacter vibrioides",
        "Pseudomonas aeruginosa",
        "Mycobacteroides abscessus",
        "Schizosaccharomyces pombe",
        "Mycoplasmoides gallisepticum",
        "Plasmodium falciparum",
        "Streptomyces coelicolor",
        "Flavobacterium johnsoniae",
        "Mycoplasma pneumoniae",
        "Cryptococcus neoformans",
        "Mycolicibacterium smegmatis",
        "Sinorhizobium meliloti",
        "Bacteroides thetaiotaomicron",
        "Vibrio natriegens",
        "Vibrio vulnificus",
    ]

    # Standardize common organism names
    for organism in organism_list:
        mask = safe_string_operation(df["ScientificName"], "startswith", organism)
        df.loc[mask, "ScientificName"] = organism

    # Special case for SARS-CoV2
    sars_mask = safe_string_operation(
        df["ScientificName"],
        "startswith",
        "Severe acute respiratory syndrome coronavirus 2",
    )
    df.loc[sars_mask, "ScientificName"] = "SARS-CoV2"

    return df


def drop_unwanted_columns(df):
    """
    Remove unnecessary columns from the dataset.
    """
    unwanted = [
        "Run.1",
        "BioProject.1",
        "name",
        "not_unique",
        "translation inhibitor",
        "mouse line",
        "type",
        "disease state",
        "diagnosis",
        "cell status",
        "isolates",
        "lncrna probes",
        "sequencing type",
        "knockdown or knockout",
        "input",
        "fragmentation",
        "lentivirus",
        "animal group",
        "cell stage",
        "biol replicate",
        "tech replicate",
        "tretment",
        "progenitor cell type",
        "geographic location (country and/or sea)",
        "specimen with known storage state",
        "rnasei treatment",
        "model",
        "identity",
        "cdna type",
        "primer set",
        "lentivirally transduced transgenes",
        "genotype/variaion",
    ]

    # Create list of columns to drop
    drop_list = [col for col in df.columns if col in unwanted]

    # Add experimental columns to drop list
    drop_list.extend([col for col in df.columns if "Experimental" in col])

    # Drop the columns
    return df.drop(columns=drop_list)


def update_standardized_columns(df):
    """
    Update main columns with values from their standardized versions and drop the source columns.
    """
    # List of tuples containing (main column, standardized column) pairs
    column_pairs = [
        ("TISSUE", "TISSUE_st"),
        ("CELL_LINE", "CELL_LINE_st"),
        ("INHIBITOR", "INHIBITOR_st"),
        ("CONDITION", "CONDITION_st"),
        ("REPLICATE", "REPLICATE_st"),
        ("LIBRARYTYPE", "LIBRARYTYPE_st"),
        ("FRACTION", "FRACTION_st"),
        ("TIMEPOINT", "TIMEPOINT_st"),
        ("ScientificName", "scientific_name"),
    ]

    # Update main columns with non-NaN values from their standardized versions
    for main_col, source_col in column_pairs:
        if source_col in df.columns:
            df.loc[df[source_col].notnull(), main_col] = df.loc[
                df[source_col].notnull(), source_col
            ]

    # Drop the standardized columns
    std_columns_to_drop = [col for _, col in column_pairs if col in df.columns]
    df.drop(columns=std_columns_to_drop, inplace=True)

    return df


def update_from_ribocrypt(df, ribocrypt_path):
    """
    Update metadata with values from RiboCrypt metadata where appropriate.
    Never replaces existing information with NaN values.
    """
    print(f"Reading RiboCrypt metadata from: {ribocrypt_path}")
    ribocrypt = pd.read_csv(ribocrypt_path)
    incorrect_annotation_mask = ribocrypt['CELL_LINE'] == "C57BL/6"
    ribocrypt.loc[incorrect_annotation_mask, "CELL_LINE"] = np.nan

    print(ribocrypt[ribocrypt['CELL_LINE'] == "C57BL/6"])
    
    # Create backup of original values for change tracking
    original_values = {
        "CELL_LINE": df["CELL_LINE"].copy(),
        "INHIBITOR": df["INHIBITOR"].copy(),
        "AUTHOR": df["AUTHOR"].copy(),
        "CONDITION": df["CONDITION"].copy(),
    }

    # Merge the dataframes on Run column
    merged = pd.merge(
        df,
        ribocrypt[["Run", "CELL_LINE", "TISSUE", "INHIBITOR", "CONDITION", "AUTHOR"]],
        on="Run",
        how="inner",
        suffixes=("_x", "_y"),
    )

    # Track changes for reporting
    changes = {
        col: 0 for col in ["CELL_LINE", "TISSUE", "INHIBITOR", "AUTHOR", "CONDITION"]
    }

    # Update values based on specified conditions
    for idx, row in merged.iterrows():
        for col in ["CELL_LINE", "INHIBITOR", "AUTHOR"]:
            original_value = row[f"{col}_x"]
            new_value = row[f"{col}_y"]

            # Only update if:
            # 1. New value is not "NONE"
            # 2. Values are different
            # 3. Never replace real value with NaN
            if (
                new_value not in ["NONE", "nan"]
                and original_value != new_value
                and not (pd.notna(original_value) and pd.isna(new_value))
            ):  # Don't replace real value with NaN

                df.loc[df["Run"] == row["Run"], col] = new_value
                changes[col] += 1

        # Special handling for CONDITION
        if row["CONDITION_y"] != "NONE":
            original_value = row["CONDITION_x"]
            new_condition = "Control" if row["CONDITION_y"] == "WT" else "Test"

            # Only update if not replacing real value with NaN
            if original_value != new_condition and not (
                pd.notna(original_value) and pd.isna(new_condition)
            ):

                df.loc[df["Run"] == row["Run"], "CONDITION"] = new_condition
                changes["CONDITION"] += 1

    # Print summary of changes
    print("\nSummary of updates:")
    for col in changes:
        print(f"{col}: {changes[col]} values updated")
        if changes[col] > 0:
            print("\nSample of changes for", col)
            changed_mask = df[col] != original_values[col]
            sample_changes = pd.DataFrame(
                {
                    "Run": df[changed_mask].index,
                    "Original": original_values[col][changed_mask],
                    "New": df.loc[changed_mask, col],
                }
            ).head()
            print(sample_changes)

    return df


def fix_makar_entries(df):
    """
    Fix entries where AUTHOR is 'Makar' and Study_Pubmed_id is 1.00 by setting them to NaN.

    Parameters:
    -----------
    df : pandas.DataFrame
        The metadata DataFrame to update

    Returns:
    --------
    pandas.DataFrame
        Updated metadata DataFrame
    """
    # Fix Study_Pubmed_id values of 1
    df.loc[df["Study_Pubmed_id"] == 1, "Study_Pubmed_id"] = np.nan

    # Fix 'Makar' author entries
    df.loc[df["AUTHOR"] == "Makar", "AUTHOR"] = np.nan
    return df


def main():
    parser = argparse.ArgumentParser(
        description="Clean and standardize metadata for RiboSeq experiments."
    )
    parser.add_argument("input_file", help="Path to the input CSV file")
    parser.add_argument("output_file", help="Path to save the cleaned CSV file")
    parser.add_argument("--ribocrypt", help="Path to RiboCrypt metadata CSV file")
    args = parser.parse_args()

    # Read the input file
    print(f"Reading input file: {args.input_file}")
    df = pd.read_csv(args.input_file, low_memory=False)
    print(df[df["Run"] == "SRR2535268"][["CELL_LINE", "TISSUE"]])

    if args.ribocrypt:
        print("Updating from RiboCrypt metadata...")
        df = update_from_ribocrypt(df, args.ribocrypt)
    print(df[df["Run"] == "SRR2535268"][["CELL_LINE", "TISSUE"]])

    print("Updating standardized columns...")
    df = update_standardized_columns(df)
    print(df[df["Run"] == "SRR2535268"][["CELL_LINE", "TISSUE"]])

    # Apply cleaning functions
    print("Cleaning cell line information...")
    df = clean_cell_lines(df)
    print(df[df["Run"] == "SRR2535268"][["CELL_LINE", "TISSUE"]])

    print("Cleaning inhibitor information...")
    df = clean_inhibitors(df)
    print(df[df["Run"] == "SRR2535268"][["CELL_LINE", "TISSUE"]])

    print("Cleaning library types...")
    df = clean_library_types(df)
    print(df[df["Run"] == "SRR2535268"][["CELL_LINE", "TISSUE"]])

    print("Cleaning scientific names...")
    df = clean_scientific_names(df)
    print(df[df["Run"] == "SRR2535268"][["CELL_LINE", "TISSUE"]])

    print("Removing unwanted columns...")
    df = drop_unwanted_columns(df)
    print(df[df["Run"] == "SRR2535268"][["CELL_LINE", "TISSUE"]])

    print("Fixing Makar entries...")
    df = fix_makar_entries(df)

    # Save the cleaned data
    print(f"Saving cleaned data to: {args.output_file}")
    df.to_csv(args.output_file, index=False)
    print("Done!")


if __name__ == "__main__":
    main()
