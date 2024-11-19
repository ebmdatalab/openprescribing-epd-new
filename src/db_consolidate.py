import sqlite3

# Parameters
db_path = "cache_db.sqlite"
year_to_exclude = 2024  # Set the year dynamically

# Connect to the SQLite database
connection = sqlite3.connect(db_path)
cursor = connection.cursor()

# Count total number of rows
cursor.execute("SELECT COUNT(*) FROM cache;")
total_rows = cursor.fetchone()[0]
print(f"Total number of rows: {total_rows}")

# Update RESOURCE_FROM for rows not matching the dynamic year
update_query = f"""
UPDATE cache
SET RESOURCE_FROM = 'EPD_pre_{year_to_exclude}'
WHERE RESOURCE_FROM NOT LIKE 'EPD_{year_to_exclude}%';
"""
cursor.execute(update_query)
connection.commit()
print(f"Number of rows updated: {cursor.rowcount}")

# Remove duplicate rows
remove_duplicates_query = """
DELETE FROM cache
WHERE rowid NOT IN (
    SELECT MIN(rowid)
    FROM cache
    GROUP BY RESOURCE_FROM, BNF_CODE, BNF_DESCRIPTION, CHEMICAL_SUBSTANCE_BNF_DESCR
);
"""

cursor.execute(remove_duplicates_query)
connection.commit()
print(f"Number of duplicate rows removed: {cursor.rowcount}")

# Count total number of rows
cursor.execute("SELECT COUNT(*) FROM cache;")
total_rows = cursor.fetchone()[0]
print(f"Total number of rows: {total_rows}")

# Vacuum the database to reclaim space
print("Running VACUUM to reclaim space...")
cursor.execute("VACUUM;")
connection.close()