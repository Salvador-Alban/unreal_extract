import mysql.connector
import os
import yaml

with open('info.yaml', 'r') as file:
    info = yaml.safe_load(file)

# MySQL connection details
config = {
    "host": info["DATABASE"]['host'],
    "user": info["DATABASE"]['user'],
    "password": info["DATABASE"]['password'],
    "database": info["DATABASE"]['database']
}

# Path to your schema folder
schema_dir = 'schema'

try:
    # Connect to MySQL
    conn = mysql.connector.connect(**config)
    cursor = conn.cursor()

    # Get all .sql files in the folder
    sql_files = [f for f in os.listdir(schema_dir) if f.endswith('.sql')]

    # Sort files if you want to control execution order
    sql_files.sort()

    for file in sql_files:
        file_path = os.path.join(schema_dir, file)
        print(f"Executing {file_path}...")

        with open(file_path, 'r') as f:
            sql = f.read()

            # Split and execute each statement
            for statement in sql.strip().split(';'):
                if statement.strip():
                    cursor.execute(statement + ';')
    
    conn.commit()
    print("All schema files executed successfully!")

except mysql.connector.Error as err:
    print(f"MySQL Error: {err}")
finally:
    if conn.is_connected():
        cursor.close()
        conn.close()
