import pandas as pd
import os

class CompareLatest:
    def __init__(self, df_existing, df_latest, exclude_chapters=[]):
        self.df_existing = df_existing
        self.df_latest = df_latest
        self.exclude_chapters = exclude_chapters
        self.new_chem_subs = None
        self.new_bnf_codes = None
        self.new_bnf_descriptions = None
        if self.exclude_chapters:
            self.df_existing = self.exclude_these_chapters(self.df_existing, self.exclude_chapters)
            self.df_latest = self.exclude_these_chapters(self.df_latest, self.exclude_chapters)
        self.find_bnf_code_only_in_latest()
        self.find_bnf_description_only_in_latest()
        self.find_chemical_substance_bnf_descr_only_in_latest()
        self.new_desc_only = self.find_unique_rows(self.new_bnf_descriptions, self.new_bnf_codes)

    def find_bnf_code_only_in_latest(self):
        latest_codes = set(self.df_latest['BNF_CODE'])
        existing_codes = set(self.df_existing['BNF_CODE'])
        unique_codes = latest_codes - existing_codes

        result = self.df_latest[self.df_latest['BNF_CODE'].isin(unique_codes)]
        result = self.sort_by_bnf_code(result)
        self.new_bnf_codes = result
        #self.new_bnf_codes.to_csv('new_bnf_codes.csv')

    def find_bnf_description_only_in_latest(self):
        latest_descriptions = set(self.df_latest['BNF_DESCRIPTION'])
        existing_descriptions = set(self.df_existing['BNF_DESCRIPTION'])
        unique_descriptions = latest_descriptions - existing_descriptions

        result = self.df_latest[self.df_latest['BNF_DESCRIPTION'].isin(unique_descriptions)]
        result = self.sort_by_bnf_code(result)
        self.new_bnf_descriptions = result

    def find_chemical_substance_bnf_descr_only_in_latest(self):
        latest_substances = set(self.df_latest['CHEMICAL_SUBSTANCE_BNF_DESCR'])
        existing_substances = set(self.df_existing['CHEMICAL_SUBSTANCE_BNF_DESCR'])
        unique_substances = latest_substances - existing_substances

        result = self.df_latest[self.df_latest['CHEMICAL_SUBSTANCE_BNF_DESCR'].isin(unique_substances)]
        result = self.sort_by_bnf_code(result)
        self.new_chem_subs = result

    @staticmethod
    def exclude_these_chapters(df, codes):
        # Separate codes starting with '~' and others
        exclude_codes = [code for code in codes if not code.startswith('~')]
        except_codes = [code[1:] for code in codes if code.startswith('~')]

        # Copy the DataFrame to avoid modifying the original
        df = df.copy()

        # Filter out rows based on the conditions
        condition_exclude_2 = df['BNF_CODE'].str[:2].isin(exclude_codes)
        condition_exclude_4 = df['BNF_CODE'].str[:4].isin(exclude_codes)
        condition_except = df['BNF_CODE'].str[:4].isin(except_codes)

        # Exclude rows meeting the exclude condition but not the except condition
        df = df[~(condition_exclude_2 | condition_exclude_4) | condition_except]

        # Reset the index of the resulting DataFrame
        df = df.reset_index(drop=True)

        return df

    @staticmethod
    def sort_by_bnf_code(df):
        df = df.copy()
        df.loc[:, 'BNF_CHAPTER'] = df['BNF_CODE'].str[:2]
        df.loc[:, 'BNF_SECTION'] = df['BNF_CODE'].str[2:4]
        df.loc[:, 'BNF_PARAGRAPH'] = df['BNF_CODE'].str[4:6]
        df.loc[:, 'BNF_SUBPARAGRAPH'] = df['BNF_CODE'].str[6]

        df = df.sort_values(by=['BNF_CHAPTER', 'BNF_SECTION', 'BNF_PARAGRAPH', 'BNF_SUBPARAGRAPH'])
        df = df.drop(columns=['BNF_CHAPTER', 'BNF_SECTION', 'BNF_PARAGRAPH', 'BNF_SUBPARAGRAPH'])
        df = df.reset_index(drop=True)

        return df
    
    @staticmethod
    def find_unique_rows(df1, df2):
        # Merge the two dataframes with indicator to identify the source of each row
        merged_df = df1.merge(df2, how='outer', indicator=True)

        # Select the rows that are only in one of the dataframes
        unique_rows = merged_df[merged_df['_merge'] != 'both']

        # Drop the indicator column before returning
        unique_rows = unique_rows.drop(columns=['_merge'])

        return unique_rows
      
    def return_new_chem_subs(self):
        return self.new_chem_subs
    
    def return_new_bnf_codes(self):
        return self.new_bnf_codes
    
    def return_new_bnf_descriptions(self):
        return self.new_bnf_descriptions
    
    def return_new_desc_only(self):
        return self.new_desc_only

def write_monthly_report_html(chem_subs, bnf_codes, bnf_descriptions, date):
    reports_dir = os.path.join(os.getcwd(), "reports")
    os.makedirs(reports_dir, exist_ok=True)

    image_path = os.path.join(os.getcwd(), "src", "base64_image.txt")
    with open(image_path, "r") as file:
        base64_image = file.read()

    # Create an alert if January data to explain BNF structure changes
    if date[-2:] == '01':
        jan_alert = f'<p><b>Please note:</b> January data often includes a larger number of "changes" as BNF structure changes are generally made in January data - <a href="https://www.nhsbsa.nhs.uk/bnf-code-changes-january-{date[:4]}">more information here</a></p>'
    else:
        jan_alert = ''

    # Write a function to generate the HTML report
    report = f"""
    <html>
    <head>
    <title>Monthly New Item Report for {date}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f8f9fa;
            margin: 20px;
            color: #333;
        }}
        .container {{
            max-width: 900px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.1);
        }}
        header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        header img {{
            max-width: 650px;
            margin-bottom: 10px;
        }}
        h2 {{
            color: #333;
        }}
        h3 {{
            color: #333;
            margin-top: 30px;
        }}
        p {{
            margin-bottom: 15px;
        }}
        table {{
            width: 100%;
            border-collapse: collapse;
            margin-top: 20px;
            margin-bottom: 20px;
        }}
        table, th, td {{
            border: 1px solid #333;
        }}
        th {{
            background-color: #0485d1;
            color: white;
            padding: 10px;
            text-align: left;
        }}
        td {{
            padding: 8px;
            text-align: left;
        }}
        tr:nth-child(even) {{
            background-color: #f2f2f2;
        }}
        a {{
            text-decoration: none;
            color: #0485d1;
        }}
        a:hover {{
            text-decoration: underline;
        }}
    </style>
    </head>
    <body>
    <div class="container">
        <header>
            <img src="{base64_image}" alt="OpenPrescribing logo">
            <h2>Monthly New Item Report for {date}</h2>
        </header>
        <p>This report details items appearing in the English Prescribing Data for {date} that have not previously appeared in the data (from Jan 2014).</p>
        {jan_alert}
        <p><a href="https://html-preview.github.io/?url=https://github.com/ebmdatalab/openprescribing-epd-new/blob/main/reports/list_reports.html">View previous reports</a></p>
        
        <h3>New Chemical Substances</h3>
        <p>Identify "chemical substances" prescribed for the first time</p>
        {chem_subs.to_html(index=False, classes='table')}
        
        <h3>New BNF Codes</h3>
        <p>Identify BNF codes used for the first time</p>
        {bnf_codes.to_html(index=False, classes='table')}
        
        <h3>New BNF Descriptions</h3>
        <p>Identify new descriptions only (not new BNF code)</p>
        {bnf_descriptions.to_html(index=False, classes='table')}
    </div>
    </body>
    </html>
    """

    # Write the report to a file
    with open(f"{reports_dir}/monthly_report_{date}.html", "w") as file:
        file.write(report)

    print(f"Report written to {reports_dir}/monthly_report_{date}.html")

def generate_list_reports_html():
    reports_dir = os.path.join(os.getcwd(), "reports")
    
    # Read the base64 image string from the file
    image_path = os.path.join(os.getcwd(), "src", "base64_image.txt")
    with open(image_path, "r") as file:
        base64_image = file.read()

    # Get all HTML files in the directory, except list_reports.html
    html_files = [f for f in os.listdir(reports_dir) if f.endswith('.html') and f != 'list_reports.html' and f != 'list_test_reports.html' and not f.startswith('monthly_test_report')]

    # Start the HTML content with the Base64 logo embedded in the header
    html_content = f"""
    <html>
    <head>
    <title>English Prescribing Data - Monthly New Items Reports</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background-color: #f8f9fa;
            margin: 20px;
        }}
        a {{
            text-decoration: none;
            color: #0485d1;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        h2 {{
            color: #333;
        }}
        li {{
            margin: 10px 0;
        }}
        header {{
            text-align: center;
            margin-bottom: 40px;
        }}
        header img {{
            max-width: 650px;
            margin-bottom: 10px;
        }}
        .container {{
            max-width: 800px;
            margin: 0 auto;
            padding: 20px;
            background-color: white;
            border-radius: 10px;
            box-shadow: 0px 2px 5px rgba(0, 0, 0, 0.1);
        }}
    </style>
    </head>
    <body>
    <div class="container">
        <header>
            <img src="{base64_image}" alt="OpenPrescribing logo">
            <h2>English Prescribing Data - Monthly New Items Reports</h2>
        </header>
        <ul>
    """

    # Function to extract the date portion (YYYY-MM) for sorting
    def extract_date(filename):
        # Split by underscores and get the last part, then remove '.html'
        date_part = filename.split('_')[-1].replace('.html', '')
        return date_part

    # Sort the list using the extracted date as the key so the index page appears in correct order
    html_files = sorted(html_files, key=extract_date)

    # Add links to all HTML files
    for html_file in html_files:
        title = os.path.splitext(html_file)[0]
        # Create title for month and year
        title = title.split('_')[-1]
        title = pd.to_datetime(title).strftime('%B %Y')
        link = f"https://html-preview.github.io/?url=https://github.com/ebmdatalab/openprescribing-epd-new/blob/main/reports/{html_file}"
        html_content += f'<li><a href="{link}">{title}</a></li>\n'

    # End the HTML content
    html_content += """
    </ul>
    </div>
    </body>
    </html>
    """

    # Write the HTML content to list_reports.html
    with open(os.path.join(reports_dir, 'list_reports.html'), 'w') as f:
        f.write(html_content)