import os

# Define the directory and strings to replace
reports_dir = os.path.join(os.getcwd(), "reports")

# Read the configuration from config.ini
config = configparser.ConfigParser()
config.read('src/config.ini')

# Get the preview_base_url from the DEFAULT section
preview_base_url = config['DEFAULT'].get('preview_base_url', '').strip()
preview_base_url_OLD = config['DEFAULT'].get('preview_base_url_OLD', '').strip()

string_OLD = preview_base_url_OLD
string_NEW = preview_base_url

# Ensure the directory exists
if os.path.exists(reports_dir) and os.path.isdir(reports_dir):
    # List all files in the directory
    files = os.listdir(reports_dir)

    for file_name in files:
        file_path = os.path.join(reports_dir, file_name)

        # Process only files (ignore directories)
        if os.path.isfile(file_path):
            try:
                # Open the file, read its content, replace the string, and write back
                with open(file_path, 'r', encoding='utf-8') as f:
                    content = f.read()
                
                # Replace occurrences of string_OLD with string_NEW
                updated_content = content.replace(string_OLD, string_NEW)
                
                # Write the updated content back to the file
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(updated_content)

                print(f"Processed file: {file_name}")

            except Exception as e:
                print(f"Error processing file {file_name}: {e}")
else:
    print(f"Directory '{reports_dir}' does not exist.")
