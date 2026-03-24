from google.cloud import bigquery
from google.oauth2 import service_account
import pandas as pd
import re
import os
import json
import logging

def make_bq_client():
    env_json = os.getenv("BQ_SERVICE_ACCOUNT_KEY")
    if env_json:
        creds_info = json.loads(env_json)  # this must be the full JSON, not base64
        credentials = service_account.Credentials.from_service_account_info(creds_info)
        project_id = creds_info.get("project_id")
        return bigquery.Client(project=project_id, credentials=credentials)

    # Fallback to a file if present (useful for local dev)
    key_path = os.getenv("GOOGLE_APPLICATION_CREDENTIALS", "bq-service-account.json")
    if os.path.exists(key_path):
        return bigquery.Client.from_service_account_json(key_path)

def retrieve_historic_drugs(before_year_month: str | int) -> pd.DataFrame:
    """
    Return distinct drug rows from BigQuery where YEAR_MONTH < before_year_month.
    Reads credentials from bq-service-account.json and returns a pandas DataFrame.
    """

    # Normalise and validate the cutoff like 'YYYYMM'
    s = str(before_year_month).strip()
    if not re.fullmatch(r"\d{6}", s):
        raise ValueError("before_year_month must be a 6-digit string or int like 202506")
    cutoff = int(s)

    client = make_bq_client()

    sql = """
        SELECT DISTINCT
            BNF_CHEMICAL_SUBSTANCE,
            CHEMICAL_SUBSTANCE_BNF_DESCR,
            BNF_CODE,
            BNF_DESCRIPTION
        FROM `ebmdatalab.hscic.raw_prescribing_v2`
        WHERE SAFE_CAST(REGEXP_REPLACE(YEAR_MONTH, r'[^0-9]', '') AS INT64) < @cutoff
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("cutoff", "INT64", cutoff)]
    )

    df = client.query(sql, job_config=job_config).to_dataframe()
    return df

def retrieve_historic_drugs_scmd(before_year_month: str | int) -> pd.DataFrame:
    """
    Return distinct drug rows from BigQuery where YEAR_MONTH < before_year_month.
    Reads credentials from bq-service-account.json and returns a pandas DataFrame.
    """

    # Normalise and validate the cutoff like 'YYYYMM'
    s = str(before_year_month).strip()
    if not re.fullmatch(r"\d{6}", s):
        raise ValueError("before_year_month must be a 6-digit string or int like 202506")

    cutoff = f"{s[:4]}-{s[4:6]}-01"

    client = make_bq_client()

    sql = """
        SELECT DISTINCT
            vmp_snomed_code,
            vmp_product_name
        FROM `ebmdatalab.scmd_pipeline.scmd_raw_provisional`
        WHERE year_month < @cutoff
        UNION DISTINCT
        SELECT DISTINCT
            vmp_snomed_code,
            vmp_product_name
        FROM `ebmdatalab.scmd_pipeline.scmd_raw_finalised`
        WHERE year_month < @cutoff
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("cutoff", "DATE", cutoff)]
    )

    df = client.query(sql, job_config=job_config).to_dataframe()
    return df

def join_vtms(existing_df, latest_df):
    client = make_bq_client()

    unique_vmp_codes = list(
        set(existing_df['vmp_snomed_code']).union(set(latest_df['vmp_snomed_code']))
    )

    sql = """
        SELECT CAST(vmp.id AS STRING) AS id, CAST(vtm.id AS STRING) AS vtm_id, vtm.nm AS vtm_nm
        FROM `ebmdatalab.dmd.vmp` vmp
        LEFT JOIN `ebmdatalab.dmd.vtm` vtm ON vmp.vtm = vtm.id
        WHERE CAST(vmp.id AS STRING) IN UNNEST(@vmp_codes)
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[
            bigquery.ArrayQueryParameter("vmp_codes", "STRING", unique_vmp_codes)
        ]
    )

    df = client.query(sql, job_config=job_config).to_dataframe()

    existing_df = existing_df.merge(df, left_on='vmp_snomed_code', right_on='id', how='left')
    existing_df.drop(columns=['id'], inplace=True)
    latest_df = latest_df.merge(df, left_on='vmp_snomed_code', right_on='id', how='left')
    latest_df.drop(columns=['id'], inplace=True)

    return existing_df, latest_df

if __name__ == "__main__":
    df = retrieve_historic_drugs("202506")
    print(df.head())
