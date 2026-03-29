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
import random

DB_NAME = os.getenv("DB_NAME", "")

if DB_NAME == "":
    DB_NAME = os.path.join(os.path.dirname(__file__), "assessor.db")

def get_connection():
    conn = sqlite3.connect(DB_NAME)
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

    # Create Users Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            email TEXT PRIMARY KEY,
            name TEXT NOT NULL
        )
    ''')

    # Create User Properties Table
    c.execute('''
        CREATE TABLE IF NOT EXISTS user_properties (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_email TEXT NOT NULL,
            address TEXT NOT NULL,
            FOREIGN KEY(user_email) REFERENCES users(email),
            FOREIGN KEY(address) REFERENCES parcels(address)
        )
    ''')

    # Check if empty, then seed
    c.execute("SELECT COUNT(*) FROM parcels")
    if c.fetchone()[0] == 0:
        seed_data(c)

    conn.commit()
    conn.close()

def generate_addresses():
    # 50 real addresses in Santa Clara County
    addresses = [
        "200 E Santa Clara St, San Jose, CA 95113",
        "1600 Amphitheatre Pkwy, Mountain View, CA 94043",
        "1 Apple Park Way, Cupertino, CA 95014",
        "1000 Enterprise Way, Sunnyvale, CA 94089",
        "3000 Hanover St, Palo Alto, CA 94304",
        "500 El Camino Real, Santa Clara, CA 95050",
        "1000 N 1st St, San Jose, CA 95112",
        "111 W Saint John St, San Jose, CA 95113",
        "10 Almaden Blvd, San Jose, CA 95113",
        "2500 El Camino Real, Palo Alto, CA 94306",
        "400 Castro St, Mountain View, CA 94041",
        "1100 N Mathilda Ave, Sunnyvale, CA 94089",
        "394 E Evelyn Ave, Sunnyvale, CA 94086",
        "111 N Market St, San Jose, CA 95113",
        "200 W Santa Clara St, San Jose, CA 95113",
        "500 W Middlefield Rd, Mountain View, CA 94043",
        "800 E Middlefield Rd, Mountain View, CA 94043",
        "1 Hacker Way, Menlo Park, CA 94025", # Close enough to SC county influence
        "400 N 1st St, San Jose, CA 95112",
        "100 S Murphy Ave, Sunnyvale, CA 94086",
        "200 S Murphy Ave, Sunnyvale, CA 94086",
        "300 S Murphy Ave, Sunnyvale, CA 94086",
        "400 S Murphy Ave, Sunnyvale, CA 94086",
        "2855 Stevens Creek Blvd, Santa Clara, CA 95050",
        "2200 Mission College Blvd, Santa Clara, CA 95054",
        "3901 Lick Mill Blvd, Santa Clara, CA 95054",
        "4900 Marie P DeBartolo Way, Santa Clara, CA 95054",
        "1500 Blossom Hill Rd, San Jose, CA 95118",
        "925 Blossom Hill Rd, San Jose, CA 95123",
        "1000 Lafayette St, Santa Clara, CA 95050",
        "1500 Lafayette St, Santa Clara, CA 95050",
        "2000 Lafayette St, Santa Clara, CA 95050",
        "100 E Hamilton Ave, Campbell, CA 95008",
        "200 E Hamilton Ave, Campbell, CA 95008",
        "300 E Hamilton Ave, Campbell, CA 95008",
        "400 E Hamilton Ave, Campbell, CA 95008",
        "500 E Hamilton Ave, Campbell, CA 95008",
        "100 W Campbell Ave, Campbell, CA 95008",
        "200 W Campbell Ave, Campbell, CA 95008",
        "300 W Campbell Ave, Campbell, CA 95008",
        "100 S Main St, Milpitas, CA 95035",
        "200 S Main St, Milpitas, CA 95035",
        "300 S Main St, Milpitas, CA 95035",
        "400 S Main St, Milpitas, CA 95035",
        "500 S Main St, Milpitas, CA 95035",
        "100 N Main St, Milpitas, CA 95035",
        "200 N Main St, Milpitas, CA 95035",
        "300 N Main St, Milpitas, CA 95035",
        "400 N Main St, Milpitas, CA 95035",
        "500 N Main St, Milpitas, CA 95035",
        "123 Main St, San Paloma, CA 95050", # Keep original mock addresses
        "456 Elm St, San Jose, CA 95112"     # Keep original mock addresses
    ]
    return addresses

def seed_data(c):
    addresses = generate_addresses()
    parcels = []
    zoning_by_address = []

    owners = [
        "John Doe", "Jane Smith", "Alice Johnson", "Bob Williams",
        "Tech Corp LLC", "Real Estate Ventures", "Michael Brown",
        "Emily Davis", "David Wilson", "Sarah Martinez"
    ]

    zoning_codes = ["R-1", "R-1-8", "C-1", "M-1"]

    for i, address in enumerate(addresses):
        # Generate mock APN like 123-45-001
        apn = f"{random.randint(100, 999)}-{random.randint(10, 99)}-{i+1:03d}"
        lot_size = random.choice([5000, 6000, 8000, 10000, 20000, 40000, 100000])
        owner = random.choice(owners)
        value = random.randint(800, 5000) * 1000 # 800k to 5m

        parcels.append((apn, address, lot_size, owner, value))

        # Determine zoning based somewhat on lot size or random
        if lot_size >= 40000:
            zoning = "M-1" # Industrial/Commercial
        elif lot_size >= 20000:
            zoning = "C-1" # Commercial
        elif lot_size >= 8000:
            zoning = "R-1-8"
        else:
            zoning = "R-1"

        zoning_by_address.append((address, zoning))

    c.executemany('INSERT INTO parcels VALUES (?,?,?,?,?)', parcels)
    c.executemany('INSERT INTO zoning_by_address VALUES (?,?)', zoning_by_address)

    zoning_rules = [
        ("R-1", "Single-Family Residential", 30, 40, 20, 20, 5),
        ("R-1-8", "Single-Family Residential (8,000 sq ft min lot)", 35, 35, 25, 25, 8),
        ("C-1", "Neighborhood Commercial", 45, 60, 10, 10, 0),
        ("M-1", "Light Industrial", 60, 75, 20, 20, 10)
    ]
    c.executemany('INSERT INTO zoning_rules VALUES (?,?,?,?,?,?,?)', zoning_rules)

    # Seed hardcoded users
    users = [
        ("testuser@example.com", "Test User"),
        ("admin@example.com", "Admin User")
    ]
    c.executemany('INSERT INTO users VALUES (?,?)', users)

    # Map users to some properties
    user_properties = [
        ("testuser@example.com", "1600 Amphitheatre Pkwy, Mountain View, CA 94043"),
        ("testuser@example.com", "1 Apple Park Way, Cupertino, CA 95014"),
        ("testuser@example.com", "123 Main St, San Paloma, CA 95050"),
        ("admin@example.com", "200 E Santa Clara St, San Jose, CA 95113")
    ]
    c.executemany('INSERT INTO user_properties (user_email, address) VALUES (?,?)', user_properties)

if __name__ == "__main__":
    init_db()
