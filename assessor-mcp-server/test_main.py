import main
import db

# Test the tool logic directly
def test_lookup_parcel():
    print("Testing lookup_parcel tool logic directly...")
    
    # Verify the database has the data first
    conn = main.get_connection()
    c = conn.cursor()
    c.execute("SELECT * FROM parcels WHERE apn = '123-45-678'")
    row = c.fetchone()
    conn.close()
    
    print(f"Database row for 123-45-678: {row}")
    if not row:
        print("Data not found in database! Seeding database might be needed or data is missing.")
        # Try to seed it if needed, or assume it's there.
        # Let's check if we can call the tool function directly.
    
    # Call the tool function from main.py
    # In main.py, lookup_parcel is registered as a tool.
    
    result = main.lookup_parcel("123-45-678")
    
    # Assertions for standard unit test
    assert "apn" in result, f"Expected 'apn' in result, got {result}"
    assert result["apn"] == "123-45-678", f"Expected apn '123-45-678', got {result.get('apn')}"
    assert "address" in result, f"Expected 'address' in result, got {result}"
    assert result["address"] == "123 Main St, Santa Clara, CA 95050", f"Expected address '123 Main St, Santa Clara, CA 95050', got {result.get('address')}"

if __name__ == "__main__":
    test_lookup_parcel()
