#!/usr/bin/env python3
"""
Debug script to find correct table names and interview data
"""
import mysql.connector

DB_CONFIG = {
    'host': 'mysql8-container',
    'database': 'mock_interview_platform',
    'user': 'root',
    'password': 'demopass',
    'port': '3306'
}

try:
    conn = mysql.connector.connect(**DB_CONFIG)
    cursor = conn.cursor()
    
    # Find all tables
    print("=== Available Tables ===")
    cursor.execute("SHOW TABLES")
    tables = cursor.fetchall()
    for table in tables:
        print(f"  {table[0]}")
    
    # Look for user-related tables
    print("\n=== User-related Tables ===")
    user_tables = [t[0] for t in tables if 'user' in t[0].lower()]
    for table in user_tables:
        print(f"  {table}")
        
    # Look for interview tables
    print("\n=== Interview-related Tables ===")
    interview_tables = [t[0] for t in tables if 'interview' in t[0].lower()]
    for table in interview_tables:
        print(f"  {table}")
    
    # Try to find interview 39 data
    print("\n=== Looking for Interview 39 ===")
    for table in interview_tables:
        try:
            cursor.execute(f"SELECT * FROM {table} WHERE id = 39 LIMIT 1")
            result = cursor.fetchone()
            if result:
                print(f"Found in table {table}:")
                cursor.execute(f"DESCRIBE {table}")
                columns = cursor.fetchall()
                column_names = [col[0] for col in columns]
                print(f"  Columns: {column_names}")
                print(f"  Data: {result}")
                break
        except Exception as e:
            continue
    
    cursor.close()
    conn.close()
    
except Exception as e:
    print(f"Database error: {e}")
