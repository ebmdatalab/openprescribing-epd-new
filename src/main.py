import pandas as pd
import bsa_utils
import utils
import testing_utils
import op_utils
import os
from datetime import datetime
import argparse
import logging



def check_latest_published_report():
    def sort_files_by_date_desc(html_files):
        return sorted(
            html_files,
            key=lambda filename: filename.split('_')[-1].split('.')[0] if '-' in filename else '',
            reverse=True
        )

    def extract_date(filename):
            # Extract the date portion (YYYY-MM) from the filename
            return filename.split('_')[-1].split('.')[0] if '-' in filename else None

    reports_dir = os.path.join(os.getcwd(), "reports")
    report_html_files = [f for f in os.listdir(reports_dir) if f.endswith('.html') and f.startswith('monthly_report')]
    test_report_html_files = [f for f in os.listdir(reports_dir) if f.endswith('.html') and f.startswith('monthly_test_report')]
    sorted_report_html_files = sort_files_by_date_desc(report_html_files)
    sorted_test_report_html_files = sort_files_by_date_desc(test_report_html_files)
    if extract_date(sorted_report_html_files[0]) == extract_date(sorted_test_report_html_files[0]):
        return extract_date(sorted_report_html_files[0])
    else:
        return False

def check_latest_published_data(dataset_id):
    resources = bsa_utils.ResourceNames(resource=dataset_id)
    latest_published_data_date = resources.return_latest_resource()
    return latest_published_data_date
    
def check_if_up_to_date(dataset_id):
    logging.info(f"Checking if reports are up to date.")
    latest_published_report = check_latest_published_report()
    try:
        latest_published_report = datetime.strptime(latest_published_report, "%Y-%m")
        logging.info(f"Latest published report is {latest_published_report.strftime('%Y-%m')}.")
    except ValueError as e:
        raise ValueError(f"Invalid date format in latest_published_report: {latest_published_report}") from e

    latest_published_data = check_latest_published_data(dataset_id)
    logging.info(f"Latest published data is {latest_published_data.strftime('%Y-%m')}.")
    
    if latest_published_report >= latest_published_data:
        logging.info(f"Reports are up to date.")
        return True
    else:
        logging.info(f"New data is available.")
        return False
    
def convert_to_yyyymm(date):
    ts = pd.Timestamp(date)
    yyyymm_str = ts.strftime('%Y%m')
    return yyyymm_str

def update_reports(dataset_id):
    logging.info(f"Updating reports.")
    latest_published_data = check_latest_published_data(dataset_id)
    latest_published_yyyymm = convert_to_yyyymm(latest_published_data)
    logging.info(f"Latest published data {latest_published_yyyymm}")

    # FIND NEW PRODUCTS
    #sql = (
    #    "SELECT DISTINCT BNF_CODE, BNF_DESCRIPTION, CHEMICAL_SUBSTANCE_BNF_DESCR "
    #    "{FROM_TABLE}"
    #)
    sql = (
        "SELECT DISTINCT "
        "BNF_PRESENTATION_CODE AS BNF_CODE, "
        "BNF_PRESENTATION_NAME AS BNF_DESCRIPTION, "
        "BNF_CHEMICAL_SUBSTANCE AS CHEMICAL_SUBSTANCE_BNF_DESCR "
        "{FROM_TABLE} "
    )

    try:
        # Fetch existing data using BSA API
        #date_from = "earliest"  # Can be "YYYYMM" or "earliest" or "latest", default="earliest"
        #date_to = "latest-1"  # Can be "YYYYMM" or "latest" or "latest-1", default="latest"

        #existing_data_extract = bsa_utils.FetchData(resource=dataset_id, date_from=date_from, date_to=date_to, sql=sql, cache=True)
        existing_data_extract = op_utils.retrieve_historic_drugs(latest_published_yyyymm)
        logging.info(f"Fetched {len(existing_data_extract)} existing records.")

        # Extract latest data from EPD
        date_from = "latest"  # Can be "YYYYMM" or "earliest" or "latest", default="earliest"
        date_to = "latest"  # Can be "YYYYMM" or "latest" or "latest-1", default="latest"

        # Fetch latest data using BSA API
        latest_data_extract = bsa_utils.FetchData(resource=dataset_id, date_from=date_from, date_to=date_to, sql=sql)
        logging.info(f"Fetched {latest_data_extract.count_results()} new records.")

    except Exception as e:
        print(f"Error fetching existing data: {e}")
        return

    # Validate fetched data
    if len(existing_data_extract) == 0 and latest_data_extract.count_results() == 0:
        logging.error("Both existing and new data fetches failed. Exiting...")
        return
    elif len(existing_data_extract) == 0:
        logging.error("Failed to fetch existing data. Exiting...")
        return
    elif latest_data_extract.count_results() == 0:
        logging.error("Failed to fetch new data. Exiting...")
        return
    else:
        print("Data fetched successfully")
    
    try:
        compare_data = utils.CompareLatest(
            existing_data_extract,
            latest_data_extract.results(),
            exclude_chapters=[]
        )

        chem_subs = compare_data.return_new_chem_subs()
        bnf_codes = compare_data.return_new_bnf_codes()
        return_new_desc_only = compare_data.return_new_desc_only()
        data_for = latest_data_extract.return_resources_to()
        utils.write_monthly_report_html(chem_subs, bnf_codes, return_new_desc_only, data_for)
        utils.generate_list_reports_html()
        testing_utils.run_tests(bnf_codes, data_for)
    except Exception as e:
        print(f"Error comparing data: {e}")
        return


def main():
    dataset_id = "english-prescribing-dataset-epd-with-snomed-code"  # Dataset ID
    # Create the parser
    parser = argparse.ArgumentParser(description="Process an optional mode argument.")
    
    # Add the optional mode argument
    parser.add_argument(
        "--mode", 
        choices=["auto", "force"], 
        default="auto", 
        help="Specify the mode of operation. Choices are 'auto' (default) or 'force'."
    )
    
    # Parse the command-line arguments
    args = parser.parse_args()
    
    # Access the mode argument
    mode = args.mode

    if mode == "force":
        update_reports(dataset_id)
    elif mode == "auto":
        if check_if_up_to_date(dataset_id):
            print("The reports are up to date.")
        else:
            update_reports(dataset_id)

if __name__ == "__main__":
    main()
