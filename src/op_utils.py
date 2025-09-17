from google.cloud import bigquery
import pandas as pd
import re

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

    client = bigquery.Client.from_service_account_json("bq-service-account.json")

    sql = """
    SELECT DISTINCT
        BNF_CHEMICAL_SUBSTANCE,
        CHEMICAL_SUBSTANCE_BNF_DESCR,
        BNF_CODE,
        BNF_DESCRIPTION
    FROM `ebmdatalab.hscic.raw_prescribing_v2`
    WHERE SAFE_CAST(YEAR_MONTH AS INT64) < @cutoff
    """

    job_config = bigquery.QueryJobConfig(
        query_parameters=[bigquery.ScalarQueryParameter("cutoff", "INT64", cutoff)]
    )

    df = client.query(sql, job_config=job_config).to_dataframe()
    return df

if __name__ == "__main__":
    df = retrieve_historic_drugs("202506")
    print(df.head())
