import pandas as pd
import bsa_utils
#import utils
#import testing_utils
#import os

def main():
    dataset_id = "english-prescribing-data-epd"  # Dataset ID

    # FIND NEW PRODUCTS
    sql = (
        "SELECT DISTINCT BNF_CODE, BNF_DESCRIPTION, CHEMICAL_SUBSTANCE_BNF_DESCR "
        "{FROM_TABLE}"
    )

    # Extract existing data from EPD
    date_from = "earliest"  # Can be "YYYYMM" or "earliest" or "latest", default="earliest"
    date_to = "latest-1"  # Can be "YYYYMM" or "latest" or "latest-1", default="latest"

    # Fetch existing data using BSA API
    existing_data_extract = bsa_utils.FetchData(resource=dataset_id, date_from=date_from, date_to=date_to, sql=sql, cache=True)

    # Extract latest data from EPD
    date_from = "latest"  # Can be "YYYYMM" or "earliest" or "latest", default="earliest"
    date_to = "latest"  # Can be "YYYYMM" or "latest" or "latest-1", default="latest"

    # Fetch latest data using BSA API
    #latest_data_extract = bsa_utils.FetchData(resource=dataset_id, date_from=date_from, date_to=date_to, sql=sql)

if __name__ == "__main__":
    main()