import os
import sqlite3
import requests
import pandas as pd
import gzip
import io
import urllib.parse
from datetime import datetime
import logging
import time
import warnings

warnings.simplefilter("ignore", category=UserWarning)

logging.basicConfig(level=logging.INFO)

class Config:
    """
    Configuration class to set up API endpoints and directory paths.
    """
    def __init__(self):
        self.base_endpoint = 'https://opendata.nhsbsa.net/api/3/action/'
        self.package_list_method = 'package_list'
        self.package_show_method = 'package_show?id='
        self.action_method = 'datastore_search_sql?'

        # Create data directory if it doesn't exist
        self.DATA_DIR = os.path.join(os.getcwd(), "data")

        self.create_directories()

    def create_directories(self):
        os.makedirs(self.DATA_DIR, exist_ok=True)

CONFIG_OBJ = Config()

class ResourceNames:
    """
    Handles fetching and filtering resource names based on date ranges.
    """
    def __init__(self, resource, date_from=False, date_to=False):
        self.resource = resource
        self.resources_table = None
        self.resource_from = None
        self.resource_to = None

        self.get_resource_names()
        if date_from and date_to:
            self.resource_from = self.set_date(date_from, date_type="from")
            self.resource_to = self.set_date(date_to, date_type="to")
            self.resource_name_list_filter()

    def get_resource_names(self):
        response = requests.get(f"{CONFIG_OBJ.base_endpoint}{CONFIG_OBJ.package_show_method}{self.resource}")
        response.raise_for_status()  # Ensure the request was successful
        metadata_response = response.json()
        self.resources_table = pd.json_normalize(metadata_response['result']['resources'])
        self.resources_table['date'] = pd.to_datetime(
            self.resources_table['bq_table_name'].str.extract(r'(\d{6})')[0], format='%Y%m', errors='coerce'
        )
        #sort the table by date in ascending order
        #self.resources_table = self.resources_table.sort_values(by='date')

    @staticmethod
    def validate_date(date_str):
        try:
            datetime.strptime(date_str, "%Y%m")
            return True
        except ValueError:
            return False

    @staticmethod
    def convert_YYMM_to_date(date_str):
        date = datetime.strptime(date_str, "%Y%m")
        return date.strftime("%Y-%m-%d")

    def get_nth_date(self, date_type, n, ascending=True):
        sorted_dates = self.resources_table['date'].sort_values(ascending=ascending).unique()
        if n < len(sorted_dates):
            return sorted_dates[n]
        max_val = len(sorted_dates) - 1
        raise ValueError(f"The value '{date_type}{n}' is out of range. Maximum allowable is '{date_type}{max_val}'.")

    def set_date(self, date, date_type):
        if date == "earliest":
            return self.resources_table['date'].min()
        if date == "latest":
            return self.resources_table['date'].max()
        if date.startswith("latest-"):
            try:
                n = int(date.split('-')[1])
                if n > 0:
                    return self.get_nth_date('latest-', n, ascending=False)
                raise ValueError("The value after 'latest-' must be a positive integer.")
            except ValueError as e:
                raise ValueError("Invalid format for 'latest-n'. Expected 'latest-1', 'latest-2', etc.") from e
        if date.startswith("earliest+"):
            try:
                n = int(date.split('+')[1])
                if n > 0:
                    return self.get_nth_date('earliest+', n, ascending=True)
                raise ValueError("The value after 'earliest+' must be a positive integer.")
            except ValueError as e:
                raise ValueError("Invalid format for 'earliest+n'. Expected 'earliest+1', 'earliest+2', etc.") from e
        if date == "" and date_type == "from":
            return self.resources_table['date'].min()
        if date == "" and date_type == "to":
            return self.resources_table['date'].max()
        if self.validate_date(date):
            return self.convert_YYMM_to_date(date)
        raise ValueError(
            "Unexpected date format. Expected one of the following: 'YYYYMM', 'earliest', 'latest', 'latest-n', or 'earliest+n' "
            "(e.g., 'latest-1', 'earliest+1')."
        )

    def resource_name_list_filter(self):
        filtered_df = self.resources_table[
            (self.resources_table['date'] >= self.resource_from) & 
            (self.resources_table['date'] <= self.resource_to)
        ]

        filtered_df = filtered_df.copy()
        
        self.resource_name_list = list(set(filtered_df['bq_table_name'].tolist()))
        self.date_list = filtered_df['date'].tolist()

    def return_latest_resource(self):
        #Get the latest date and bq_table_name for the latest date
        latest_date = self.resources_table['date'].max()
        latest_table_name = self.resources_table[self.resources_table['date'] == latest_date]['bq_table_name'].values[0]
        return latest_date
    
    def return_date_list(self):
        return self.date_list
    
    def return_resources_from(self):
        return self.resource_from
    
    def return_resources_to(self):
        return self.resource_to

class APICall:
    """
    Represents a single API call with caching capabilities.
    """
    def __init__(self, resource_id, sql):
        self.resource_id = resource_id
        self.sql = sql
        self.api_url = None
        self.set_table_name()
        self.generate_url()

    def set_table_name(self):
        placeholder = "{FROM_TABLE}"
        if placeholder not in self.sql:
            raise ValueError(f"Placeholder {placeholder} not found in the SQL query.")
        self.sql = self.sql.replace(placeholder, f"FROM `{self.resource_id}`")

    def generate_url(self):
        self.api_url = (
            f"{CONFIG_OBJ.base_endpoint}{CONFIG_OBJ.action_method}"
            f"resource_id={self.resource_id}&"
            f"sql={urllib.parse.quote(self.sql)}"
        )
    

class FetchData:
    """
    Orchestrates the fetching of data from the API, including handling
    of API calls, and data processing.
    """
    def __init__(self, resource, sql, date_from, date_to = False, max_attempts = 3):
        logging.info(f"Initializing FetchData for resource: {resource} from {date_from} to {date_to if date_to else 'latest'}")
        self.resource = resource
        self.sql = sql
        self.max_attempts = max_attempts
        self.resource_names_obj = ResourceNames(resource, date_from, date_to)
        self.api_calls_list = []
        self.returned_json_list = []
        self.returned_df_list = []
        self.requests_map = []
        self.resource_list = []
        self.full_results_df = None
        self.returned_df = None
        self.generate_api_calls()
        self.generate_request_map()
        self.request_data()
        self.join_results()
        logging.info(f"Data fetch complete.")

    def generate_api_calls(self):
        for resource_id in self.resource_names_obj.resource_name_list:
            self.api_calls_list.append(APICall(resource_id, self.sql))

    def generate_request_map(self):
        for api_call in self.api_calls_list:
            request_entry = {"resource_id": api_call.resource_id, "api_url": api_call.api_url}
            self.requests_map.append(request_entry)
            self.resource_list.append(api_call.resource_id)

    def request_data(self):
        for resource in list(self.requests_map):
            url = resource['api_url']
            resource_id = resource['resource_id']
            url_pending=True
            retry_counter = 0
            while url_pending and retry_counter <= self.max_attempts:       
                try:
                    logging.info(f"Requesting data for resource {resource_id}")
                    response = requests.get(url, timeout=120)
                    if response.status_code == 200:
                        
                        tmp_df = self.process_data(response.json())
                        self.returned_df_list.append(tmp_df)
                        
                        logging.info(f"Success for {response.url}")
                        url_pending = False  # Exit retry loop
                    else:
                        logging.error(f"Error {response.status_code} for {response.url}. Will retry.")
                        retry_counter += 1
                        time.sleep(2 ** retry_counter)  # Exponential backoff
                except requests.RequestException as e:
                    logging.error(f"Request error for {url}: {e}. Will retry.")
                    retry_counter += 1
                    time.sleep(2 ** retry_counter)  # Exponential backoff

    def process_data(self, json_data):
        if 'records_truncated' in json_data['result'] and json_data['result']['records_truncated'] == 'true':
            download_url = json_data['result']['gc_urls'][0]['url']
            logging.info(f"Downloading truncated data from URL: {download_url}")
            r = requests.get(download_url)
            with gzip.open(io.BytesIO(r.content), 'rt') as f:
                tmp_df = pd.read_csv(f)
        else:
            tmp_df = pd.json_normalize(json_data['result']['result']['records'])

        tmp_df.drop_duplicates(inplace=True)
        return tmp_df
    
    def join_results(self):
        try:
            if len(self.returned_df_list) > 0:
                self.returned_df = pd.concat(self.returned_df_list)
            if self.full_results_df is None or self.full_results_df.empty:
                self.full_results_df = self.returned_df
            else:
                self.full_results_df = pd.concat([self.full_results_df, self.returned_df])
            self.full_results_df = self.full_results_df.drop_duplicates()
        except Exception as e:
            logging.error(f"Error joining results: {e}")
        
    def results(self):
        return self.full_results_df
    
    def count_results(self):
        return len(self.full_results_df)
    
    def return_resources_from(self):
        # Given Timestamp
        timestamp = pd.Timestamp(self.resource_names_obj.return_resources_from())

        # Convert to string in the format YYYY-MM
        formatted_string = timestamp.strftime('%Y-%m')

        return formatted_string
    
    def return_resources_to(self):
        # Given Timestamp
        timestamp = pd.Timestamp(self.resource_names_obj.return_resources_to())

        # Convert to string in the format YYYY-MM
        formatted_string = timestamp.strftime('%Y-%m')

        return formatted_string

def show_available_datasets():
    # Extract list of datasets
    datasets_response = requests.get(CONFIG_OBJ.base_endpoint +  CONFIG_OBJ.package_list_method).json()
    
    # Get as a list
    dataset_list=datasets_response['result']
    
    # Excluse FOIs from the results
    list_to_exclude=["foi"]
    filtered_list = [item for item in dataset_list if not any(item.startswith(prefix) for prefix in list_to_exclude)]
    
    # Print available datasets
    for item in filtered_list:
        print (item)