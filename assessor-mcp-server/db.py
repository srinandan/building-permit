# Copyright 2026 Google LLC
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import sqlite3
import os

DB_PATH = os.path.join(os.path.dirname(__file__), "assessor.db")

def get_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_connection()
    c = conn.cursor()

    # Create Parcels Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS parcels (
            apn TEXT PRIMARY KEY,
            address TEXT NOT NULL,
            lot_size_sqft INTEGER,
            owner TEXT,
            assessed_value INTEGER
        )
    ''')

    # Create Zoning By Address Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS zoning_by_address (
            address TEXT PRIMARY KEY,
            zoning_code TEXT NOT NULL
        )
    ''')

    # Create Zoning Rules Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS zoning_rules (
            zoning_code TEXT PRIMARY KEY,
            description TEXT,
            max_height_ft INTEGER,
            max_lot_coverage_percent INTEGER,
            front_setback_ft INTEGER,
            rear_setback_ft INTEGER,
            side_setback_ft INTEGER
        )
    ''')

    # Check if empty, then seed
    c.execute("SELECT COUNT(*) FROM parcels")
    if c.fetchone()[0] == 0:
        seed_data(c)

    conn.commit()
    conn.close()

def seed_data(c):
    parcels = [
        ("123-45-678", "123 Main St, San Paloma, CA 95050", 6000, "John Doe", 1200000),
        ("987-65-432", "456 Elm St, San Jose, CA 95112", 8000, "Jane Smith", 1500000)
    ]
    c.executemany('INSERT INTO parcels VALUES (?,?,?,?,?)', parcels)

    zoning_by_address = [
        ("123 Main St, San Paloma, CA 95050", "R-1"),
        ("456 Elm St, San Jose, CA 95112", "R-1-8")
    ]
    c.executemany('INSERT INTO zoning_by_address VALUES (?,?)', zoning_by_address)

    zoning_rules = [
        ("R-1", "Single-Family Residential", 30, 40, 20, 20, 5),
        ("R-1-8", "Single-Family Residential (8,000 sq ft min lot)", 35, 35, 25, 25, 8)
    ]
    c.executemany('INSERT INTO zoning_rules VALUES (?,?,?,?,?,?,?)', zoning_rules)

if __name__ == "__main__":
    init_db()
