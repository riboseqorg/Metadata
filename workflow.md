
# Workflow to Populate RDP with Metadata

## Required Input Files

- Cleaned Metadata with all required columns [Code](https://github.com/Roleren/riboseq_metadata)
- The initialised sqlite db 
- The csvs with info on:
    - GWIPS
    - Trips
    - RiboCrypt 
    - Verification 
- The RiboSeqOrg Controlled Volcabularies main name cleaning sheet 

## Generate fixtures
```
python scripts/generate_fixtures.py -i /home/jack/projects/RiboSeqOrg-DataPortal/data/Cleaned_Metadata_For_Upload.csv \
                                    --db riboseqorg/db.sqlite3 \
                                    -o data/riboseqorg_metadata.json \
                                    -t data/Sample_Matching-Trips-Viz.csv \
                                    -g data/Sample_Matching-GWIPS-Viz.csv \
                                    -f data/collapsed_accessions.tsv \
                                    -v data/verified.csv \
                                    -c data/RiboSeqOrg_Vocabularies-Main_Name_Cleaning.csv

python scripts/csv_to_fixtures.py -i data/rc_supported_samples.csv -m RiboCrypt -o data/ribocrypt_model_fixtures.json
python scripts/csv_to_fixtures.py -i data/Sample_Matching-GWIPS-Viz.csv -m GWIPS -o data/gwips_model_fixtures.json
python scripts/csv_to_fixtures.py -i data/Sample_Matching-Trips-Viz.csv -m Trips -o data/trips_model_fixtures.json
```

## Load Data into DB 
This is to be run within the Data Portal project 
```
python riboseqorg/manage.py loaddata data/gwips_model_fixtures.json 
python riboseqorg/manage.py loaddata data/ribocrypt_model_fixtures.json
python riboseqorg/manage.py loaddata data/gwips_model_fixtures.json 
python riboseqorg/manage.py loaddata data/gwips_model_fixtures.json 

```