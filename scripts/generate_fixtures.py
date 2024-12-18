"""
Python script to convert data from a csv file to a fixture file for a django app
This script assumes that the csv file has a header row and that every other row is to be made into a fixture
Each column in the csv file will be a field in the fixture file and the column name will be the field name

This script creates all fixtures, samples, studies, and open columns and writes them to a fixture file

Usage:
    python csv_to_sample_fixture.py -i <csv_file> --db <sqlite database> -o <fixture_file>

Example:
python scripts/generate_fixtures.py 
    -i /home/jack/projects/RiboSeqOrg-DataPortal/data/Cleaned_Metadata_For_Upload.csv   -- Product of scripts/obtain_live_metadata_set.ipynb
    --db riboseqorg/db.sqlite3                                                          -- Sqlite database for Data Protal
    -o data/riboseqorg_metadata.json                                                    -- Output fixture file                      
    -t data/Sample_Matching-Trips-Viz.csv -g data/Sample_Matching-GWIPS-Viz.csv         -- Trips and GWIPS csv files containing sample information for trips and GWIPS (generated with file_matching.ipynb)
    -f data/collapsed_accessions.tsv                                                    -- File containing list of Run accessions that have been collapsed and are available
    -v data/verified.csv                                                                -- CSV file containing manually checked samples (BioProject and Run columns important)
    -c data/RiboSeqOrg_Vocabularies-Main_Name_Cleaning.csv                              -- Csv showing metadata content clean names (eg RFP to Ribo-Seq)

"""
from populate_study_metainfo_dict import get_metainformation_dict
import argparse
import pandas as pd
import sqlite3

import warnings

# Silence specific pandas warnings
warnings.simplefilter(action="ignore", category=pd.errors.PerformanceWarning)
warnings.simplefilter(action="ignore", category=FutureWarning)
warnings.simplefilter(action="ignore", category=pd.errors.SettingWithCopyWarning)


def get_last_pk(model: str, db: str) -> int:
    """
    Get the last primary key of the model in the database

    Inputs:
        model: string
        db: string
    Returns:
        last_pk: int
    """
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute(f"SELECT MAX(id) FROM {model}")
    last_pk = c.fetchone()[0]
    conn.close()

    return last_pk


def get_column_names(db: str, table: str) -> list:
    """
    Get the column names of the table in the database

    Inputs:
        db: string
        table: string

    Returns:
        column_names: list of strings
    """
    conn = sqlite3.connect(db)
    c = conn.cursor()
    c.execute(f"SELECT * FROM {table}")
    column_names = [description[0] for description in c.description]
    conn.close()

    return column_names


def df_to_sample_fixture(df: pd.DataFrame, last_pk: int) -> str:
    """
    Convert cleaned df to fixture string

    Inputs:
        df: pandas dataframe
        last_pk: int

    Returns:
        fixture string
    """
    fixture = []
    accepted_cols = get_column_names(args.db, "main_sample")
    accepted_cols.append("BioProject")
    for i, row in df.iterrows():
        if not last_pk:
            last_pk = 1
        else:
            last_pk += 1
        fixture.append("{\n")
        fixture.append('    "model": "main.sample",\n')
        fixture.append(f'    "pk": {last_pk},\n')
        fixture.append('    "fields": {\n')
        for col in df.columns:
            if col not in accepted_cols:
                continue
            if col in ["spots", "bases", "avgLength", "size_MB"]:
                try:
                    fixture.append(f'        "{col}": {int(row[col])},\n')
                except:
                    pass
            else:
                if isinstance(row[col], str):
                    entry = (
                        row[col]
                        .replace('""""', "'")
                        .replace("\n", " ")
                        .replace('"', "'")
                    )
                    fixture.append(f'        "{col}": "{entry}",\n')
                else:
                    fixture.append(f'        "{col}": "{row[col]}",\n')
        fixture[-1] = fixture[-1][:-2]  # removes trailing comma
        fixture.append("    }\n")
        fixture.append("},\n")

    fixture = " ".join(fixture)
    return fixture


def write_study_fixture(information_dict: dict) -> str:
    """
    Give the accession of the study, return the study fixture

    inputs:
        information_dict: dictionary
        pk: int

    returns:
        fixture: string
    """
    fixture = []

    fixture.append("{\n")
    fixture.append('    "model": "main.study",\n')
    fixture.append(f'    "pk":"{information_dict["BioProject"]}",\n')
    fixture.append('    "fields": {\n')

    for field in information_dict:
        if field not in get_column_names(args.db, "main_study"):
            continue
        if isinstance(information_dict[field], str):
            entry = information_dict[field].replace("\n", " ").replace('"', "'")
            fixture.append(f'        "{field}": "{entry}",\n')
        else:
            fixture.append(f'        "{field}": "{information_dict[field]}",\n')
    fixture[-1] = fixture[-1][:-2]
    fixture.append("    }\n")
    fixture.append("},\n")

    fixture = " ".join(fixture)

    return fixture


def write_OpenColumns_fixture(
    column: str, bioproject: str, values: list, pk: int
) -> str:
    """
    Write the OpenColumns fixture string

    Inputs:
        column: string
        bioProject: string
        values: list
        last_pk: int

    Returns:
        fixture: string
    """
    fixture = []
    fixture.append("{\n")
    fixture.append('    "model": "main.opencolumns",\n')
    fixture.append(f'    "pk":{pk},\n')
    fixture.append('    "fields": {\n')
    fixture.append(f'        "column_name": "{column}",\n')
    fixture.append(f'        "bioproject": "{bioproject}",\n')
    fixture.append(f'        "values": "{",".join(values)}",\n')
    fixture[-1] = fixture[-1][:-2]
    fixture.append("    }\n")
    fixture.append("},\n")

    fixture = " ".join(fixture)

    return fixture


def get_existing_studies(db: str) -> dict:
    """Get existing studies and their metadata from database"""
    conn = sqlite3.connect(db)
    c = conn.cursor()
    study_columns = get_column_names(db, "main_study")
    c.execute(f"SELECT {', '.join(study_columns)} FROM main_study")
    studies = {}
    for row in c.fetchall():
        study_dict = dict(zip(study_columns, row))
        studies[study_dict['BioProject']] = study_dict
    conn.close()
    return studies


def should_update_study(existing_study: dict, new_info: dict) -> bool:
    """Compare existing and new study metadata to determine if update needed"""
    return any(
        existing_study.get(key) != new_info.get(key)
        for key in new_info
        if key in existing_study
    )


def add_study_fixtures(df: pd.DataFrame, db: str, core_columns: list, fetch_all: bool = False) -> str:
    existing_studies = get_existing_studies(db) if not fetch_all else {}
    study_fixtures = ""
    processed_studies = set()
    
    last_pk_OpenColumns = get_last_pk("main_opencolumns", db)
    df.fillna(0.0, inplace=True)
    
    for idx, row in df.iterrows():
        bioproject = row["BioProject"]
        if bioproject in processed_studies:
            continue
            
        processed_studies.add(bioproject)
        subset_df = df[df["BioProject"] == bioproject]
        
        if fetch_all:
            core_df = subset_df[core_columns]
            study_info_dict = get_metainformation_dict(core_df)
        else:
            study_info_dict = existing_studies.get(bioproject, {})
            if not study_info_dict:  # If not in DB, fetch it
                core_df = subset_df[core_columns]
                study_info_dict = get_metainformation_dict(core_df)
        
        study_fixture = write_study_fixture(study_info_dict)

        open_df = subset_df.drop([i for i in core_columns if i != "BioProject"], axis=1)
        open_df = open_df.dropna(axis=1, how="all")
        bioproject = open_df["BioProject"].iloc[0]
        open_fixtures = ""
        
        for col in open_df.columns:
            if col == "BioProject":
                continue
            if last_pk_OpenColumns:
                last_pk_OpenColumns += 1
            else:
                last_pk_OpenColumns = 1
            values = open_df[col].dropna().astype(str).unique().tolist()
            open_fixtures += write_OpenColumns_fixture(col, bioproject, values, last_pk_OpenColumns)

        study_fixtures += study_fixture + open_fixtures
        
    return study_fixtures


def fixtures_to_file(fixtures: str, output_file: str):
    """
    Write the fixture string to a file

    Inputs:
        fixtures: string
        output_file: string
    """
    with open(output_file, "w") as f:
        f.write(fixtures)


def generate_open_column_sqlites(df: pd.DataFrame, sqlite_dir_path: str):
    """
    For all studies (unique BioProject) in the dataframe, generate a sqlite database
    that contains a open columns table named after the BioProject. This is to contain
    all the columns that are not in the core columns list

    Inputs:
        df: pandas dataframe no core columns except BioProject
        sqlite_dir_path: string

    """

    grouped = df.groupby("BioProject")
    for group, group_df in grouped:
        group_df = group_df.dropna(axis=1, how="all")
        conn = sqlite3.connect(f"{sqlite_dir_path}/{group}.sqlite")

        group_df.to_sql(group, conn, if_exists="replace")


def add_trips_booleans(df: pd.DataFrame, trips_df: pd.DataFrame) -> pd.DataFrame:
    """
    If the sample is in the trips_df, add a boolean to the sample dataframe

    Inputs:
        df: pandas dataframe
        trips_df: pandas dataframe

    Returns:
        df: pandas dataframe
    """
    df["trips_id"] = False
    for idx, row in df.iterrows():
        if row["Run"] in trips_df["Run"].tolist():
            df.loc[idx, "trips_id"] = True
    return df


def add_gwips_booleans(df: pd.DataFrame, gwips_df: pd.DataFrame) -> pd.DataFrame:
    """
    If the sample is in the gwips_df, add a boolean to the sample dataframe

    Inputs:
        df: pandas dataframe
        gwips_df: pandas dataframe

    Returns:
        df: pandas dataframe
    """
    df["gwips_id"] = False
    for idx, row in df.iterrows():
        if row["BioProject"] in gwips_df["BioProject"].tolist():
            df.loc[idx, "gwips_id"] = True
    return df


def add_ribocrypt_booleans(
    df: pd.DataFrame, ribocrypt_df: pd.DataFrame
) -> pd.DataFrame:
    """
    If the sample is in the ribocrypt_df, add a boolean to the sample dataframe
    and update the process status.

    Inputs:
        df: pandas dataframe
        ribocrypt_df: pandas dataframe

    Returns:
        df: pandas dataframe
    """
    df["ribocrypt_id"] = False
    df["process_status"] = "Not Yet Started"

    # Create lists of Run accessions
    all_run = ribocrypt_df["Run"].tolist()
    success = ribocrypt_df[ribocrypt_df["complete"] == True]["Run"].tolist()
    failed = ribocrypt_df[ribocrypt_df["complete"] == False]["Run"].tolist()

    for idx, row in df.iterrows():
        if row["Run"] in all_run:
            df.loc[idx, "ribocrypt_id"] = True
            if row["Run"] in success:
                df.loc[idx, "process_status"] = "Completed"
            elif row["Run"] in failed:
                df.loc[idx, "process_status"] = "Failed"

    return df


def add_readfile_booleans(df: pd.DataFrame, readfile_df: pd.DataFrame) -> pd.DataFrame:
    """
    If the sample is in the readfile_df, add a boolean to the sample dataframe

    Inputs:
        df: pandas dataframe
        readfile_df: pandas dataframe

    Returns:
        df: pandas dataframe
    """
    df["FASTA_file"] = False
    for idx, row in df.iterrows():
        if row["Run"] in readfile_df["Run"].tolist():
            df.loc[idx, "FASTA_file"] = True
    return df


def clean_column_content(df: pd.DataFrame, clean_df: pd.DataFrame) -> pd.DataFrame:
    """
    Clean values in the dataframe according to the clean_df

    Inputs:
        df: pandas dataframe
        clean_df: pandas dataframe

    Returns:
        df: pandas dataframe
    """

    clean_name_dict = {}
    clean_df = pd.read_csv(args.clean)
    for column, column_df in clean_df.groupby("Column"):
        for idx, row in column_df.iterrows():
            if column not in clean_name_dict:
                clean_name_dict[column] = [(row["Main Name"], row["Clean Name"])]
            else:
                clean_name_dict[column].append((row["Main Name"], row["Clean Name"]))

    for idx, row in df.iterrows():
        for column in clean_name_dict:
            if column in df.columns:
                for main_name, clean_name in clean_name_dict[column]:
                    if row[column] == main_name:
                        df.loc[idx, column] = clean_name
    return df


def add_verification(df: pd.DataFrame, verified_df: pd.DataFrame) -> pd.DataFrame:
    """
    Add verification boolean to the dataframe

    Inputs:
        df: pandas dataframe
        verified_df: pandas dataframe

    Returns:
        df: pandas dataframe
    """
    # drop where checekd is auto
    verified_df = verified_df[verified_df["CHECKED"] != "auto"]

    df["verified"] = False
    for idx, row in df.iterrows():
        if row["Run"] in verified_df["Run"].tolist():
            df.loc[idx, "verified"] = True
    return df


def main(args):
    df = pd.read_csv(args.input, low_memory=False)

    geo_df = pd.read_csv(args.geo)
    bioproject_to_geo = dict(zip(geo_df["BioProject"], geo_df["GEO"]))

    df["GEO"] = df["BioProject"].map(bioproject_to_geo)

    df["Study_Pubmed_id"] = df["Study_Pubmed_id"].astype("Int64").astype(str)
    df["Study_Pubmed_id"] = df["Study_Pubmed_id"].replace("1", "")
    df["YEAR"] = df["YEAR"].astype("Int64").astype(str)

    core_columns = [
        "BioProject",
        "GEO",
        "Run",
        "spots",
        "bases",
        "avgLength",
        "size_MB",
        "Experiment",
        "LibraryName",
        "LibraryStrategy",
        "LibrarySelection",
        "LibrarySource",
        "LibraryLayout",
        "InsertSize",
        "InsertDev",
        "Platform",
        "Model",
        "SRAStudy",
        "Study_Pubmed_id",
        "Sample",
        "BioSample",
        "SampleType",
        "TaxID",
        "ScientificName",
        "SampleName",
        "CenterName",
        "Submission",
        "MONTH",
        "YEAR",
        "AUTHOR",
        "sample_source",
        "sample_title",
        "LIBRARYTYPE",
        "REPLICATE",
        "CONDITION",
        "INHIBITOR",
        "TIMEPOINT",
        "TISSUE",
        "CELL_LINE",
        "FRACTION",
    ]

    core_columns = list(df.columns)

    last_pk_sample = get_last_pk("main_sample", args.db)

    if args.trips:
        trips_df = pd.read_csv(args.trips)
        df = add_trips_booleans(df, trips_df)

    if args.gwips:
        gwips_df = pd.read_csv(args.gwips)
        df = add_gwips_booleans(df, gwips_df)

    if args.ribocrypt:
        ribocrypt_df = pd.read_csv(args.ribocrypt)
        df = add_ribocrypt_booleans(df, ribocrypt_df)

    if args.readfile:
        readfile_df = pd.read_csv(args.readfile, sep="\t")
        df = add_readfile_booleans(df, readfile_df)

    if args.clean:
        df = clean_column_content(df, args.clean)

    if args.verified:
        verified_df = pd.read_csv(args.verified)
        df = add_verification(df, verified_df)

    print("generating sample fixtures")
    print("generating study fixtures")
    fixtures = "[\n"
    fixtures += add_study_fixtures(df, args.db, core_columns, args.fetch)
    fixtures += df_to_sample_fixture(df, last_pk_sample)

    print("Done!")

    fixtures = fixtures[:-2]
    fixtures += "\n]"
    print("writing fixtures to file")
    fixtures_to_file(fixtures, args.output)
    open_df = df.drop(
        [i for i in core_columns if i not in ["Run", "BioProject"]], axis=1
    )
    generate_open_column_sqlites(
        open_df, "/home/jack/projects/RiboSeqOrg-DataPortal/sqlites"
    )
    print("Done!")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Convert csv file to fixture file")
    parser.add_argument(
        "-i", "--input", help="Input csv file", required=True
    )  # filtered and standardized csv file containing sample metadata
    parser.add_argument(
        "-t", "--trips", help="Trips CSV", required=False
    )  # trips csv file containing sample information for trips (generated with file_matching.ipynb)
    parser.add_argument(
        "-g", "--gwips", help="GWIPS CSV", required=False
    )  # GWIPS csv file containing sample information for GWIPS manually generated https://docs.google.com/spreadsheets/d/1oQDNpkVTbKptdPksgpX9qg5dsp5f0NYcp20fppNGEjg/edit?usp=sharing
    parser.add_argument(
        "-r", "--ribocrypt", help="RiboCrypt CSV", required=False
    )  # Yet to be designed
    parser.add_argument(
        "-f", "--readfile", help="Readfile CSV", required=False
    )  # File containing list of Run accessions that have been collapsed and are available
    parser.add_argument(
        "-v", "--verified", help="Verified CSV - Manually checked", required=False
    )  # CSV file containing manually checked samples (BioProject and Run columns important)
    parser.add_argument(
        "-c", "--clean", help="Clean Names file", required=False
    )  # Csv showing metadata content clean names (eg RFP to Ribo-Seq)
    parser.add_argument(
        "--db", help="Sqlite database", required=True
    )  # Sqlite database for Data Protal
    parser.add_argument("-o", "--output", help="Output fixture file", required=True)
    parser.add_argument(
        "--geo", help="CSV of Bioprojects and Corresponding GSE", required=True
    )
    parser.add_argument('--fetch', action='store_true', default=False,
                   help='Fetch metadata for all studies, ignoring existing database entries')
    args = parser.parse_args()

    main(args)

"""
python scripts/generate_fixtures.py -i data/filtered_riboseq_done_260623.csv --db riboseqorg/db.sqlite3 -o data/riboseqorg_metadata.json -t data/Sample_Matching-Trips-Viz.csv -g data/Sample_Matching-GWIPS-Viz.csv -f data/collapsed_accessions.tsv -v data/verified.csv -c data/RiboSeqOrg_Vocabularies-Main_Name_Cleaning.csv \
    
    -r data/ribocrypt_metadata.csv \
"""
