import unittest
import unittest.mock
import sys

# We don't mock 'opentelemetry' entirely because fastmcp internally tries to import 'opentelemetry.context'.
# Instead, we just mock the things main.py imports from opentelemetry.
unittest.mock.patch.dict('sys.modules', {
    'google.auth': unittest.mock.MagicMock(),
    'google.auth.transport': unittest.mock.MagicMock(),
    'google.auth.transport.grpc': unittest.mock.MagicMock(),
    'google.auth.transport.requests': unittest.mock.MagicMock(),
    'opentelemetry.exporter': unittest.mock.MagicMock(),
    'opentelemetry.exporter.otlp.proto.grpc.trace_exporter': unittest.mock.MagicMock(),
    'opentelemetry.sdk': unittest.mock.MagicMock(),
    'opentelemetry.sdk.trace': unittest.mock.MagicMock(),
    'opentelemetry.sdk.trace.export': unittest.mock.MagicMock(),
    'opentelemetry.resourcedetector': unittest.mock.MagicMock(),
    'opentelemetry.resourcedetector.gcp_resource_detector': unittest.mock.MagicMock(),
    'opentelemetry.sdk.resources': unittest.mock.MagicMock(),
    'opentelemetry.instrumentation.mcp': unittest.mock.MagicMock(),
}).start()

import sqlite3
import db
import main
import asyncio

class TestAssessorMCP(unittest.TestCase):
    def setUp(self):
        # Create an in-memory SQLite database
        self.conn = sqlite3.connect(":memory:", check_same_thread=False)
        self.conn.row_factory = sqlite3.Row

        # Override the get_connection function in main to use our in-memory DB
        self._original_get_connection = main.get_connection
        main.get_connection = lambda: self.conn

        # Initialize schema and seed data
        cursor = self.conn.cursor()
        cursor.executescript('''
            CREATE TABLE parcels (
                apn TEXT PRIMARY KEY,
                address TEXT,
                lot_size_sqft INTEGER,
                owner TEXT,
                assessed_value INTEGER
            );
            CREATE TABLE zoning_by_address (
                address TEXT PRIMARY KEY,
                zoning_code TEXT
            );
            CREATE TABLE zoning_rules (
                zoning_code TEXT PRIMARY KEY,
                description TEXT,
                max_height_ft INTEGER,
                max_lot_coverage_percent INTEGER,
                front_setback_ft INTEGER,
                rear_setback_ft INTEGER,
                side_setback_ft INTEGER
            );
            CREATE TABLE user_properties (
                user_email TEXT,
                address TEXT,
                PRIMARY KEY (user_email, address)
            );
        ''')

        # Seed test data
        cursor.execute("INSERT INTO parcels VALUES ('123-456', '123 Test St', 5000, 'Test Owner', 100000)")
        cursor.execute("INSERT INTO zoning_by_address VALUES ('123 Test St', 'R-1')")
        cursor.execute("INSERT INTO zoning_rules VALUES ('R-1', 'Single Family', 35, 40, 20, 15, 5)")
        cursor.execute("INSERT INTO user_properties VALUES ('user@test.com', '123 Test St')")
        self.conn.commit()

    def tearDown(self):
        main.get_connection = self._original_get_connection
        self.conn.close()

    def test_lookup_parcel(self):
        result = main.lookup_parcel('123-456')
        self.assertEqual(result.get('apn'), '123-456')
        self.assertEqual(result.get('address'), '123 Test St')

    def test_lookup_parcel_not_found(self):
        result = main.lookup_parcel('999-999')
        self.assertIn("error", result)

    def test_get_zoning_classification(self):
        result = main.get_zoning_classification('123 Test St')
        self.assertEqual(result, 'R-1')

    def test_get_zoning_classification_not_found(self):
        result = main.get_zoning_classification('Unknown St')
        self.assertEqual(result, 'Unknown')

    def test_get_setback_requirements(self):
        result = main.get_setback_requirements('R-1')
        self.assertEqual(result.get('front_setback_ft'), 20)

    def test_get_setback_requirements_not_found(self):
        result = main.get_setback_requirements('C-1')
        self.assertIn("error", result)

    def test_add_parcel(self):
        result = main.add_parcel('789-012', '456 New St', 6000, 'New Owner', 200000)
        self.assertEqual(result.get('status'), 'success')

        # Verify it was added
        cursor = self.conn.cursor()
        cursor.execute("SELECT * FROM parcels WHERE apn='789-012'")
        self.assertIsNotNone(cursor.fetchone())

    def test_add_parcel_error(self):
        # Insert duplicate APN to trigger error
        result = main.add_parcel('123-456', 'Duplicate', 1000, 'Dup', 10)
        self.assertIn("error", result)

    def test_rezone_address_existing(self):
        result = main.rezone_address('123 Test St', 'R-2')
        self.assertEqual(result.get('status'), 'success')

        cursor = self.conn.cursor()
        cursor.execute("SELECT zoning_code FROM zoning_by_address WHERE address='123 Test St'")
        self.assertEqual(cursor.fetchone()[0], 'R-2')

    def test_rezone_address_new(self):
        result = main.rezone_address('789 New St', 'C-1')
        self.assertEqual(result.get('status'), 'success')

        cursor = self.conn.cursor()
        cursor.execute("SELECT zoning_code FROM zoning_by_address WHERE address='789 New St'")
        self.assertEqual(cursor.fetchone()[0], 'C-1')

    def test_add_zoning_rule(self):
        result = main.add_zoning_rule('C-2', 'Commercial', 50, 80, 10, 10, 0)
        self.assertEqual(result.get('status'), 'success')

        cursor = self.conn.cursor()
        cursor.execute("SELECT max_height_ft FROM zoning_rules WHERE zoning_code='C-2'")
        self.assertEqual(cursor.fetchone()[0], 50)

    def test_add_zoning_rule_error(self):
        mock_conn = unittest.mock.MagicMock()
        mock_c = unittest.mock.MagicMock()
        mock_conn.cursor.return_value = mock_c
        mock_c.execute.side_effect = Exception("DB Error")
        with unittest.mock.patch('main.get_connection', return_value=mock_conn):
            result = main.add_zoning_rule('C-2', 'Commercial', 50, 80, 10, 10, 0)
            self.assertIn("error", result)

    def test_rezone_address_error(self):
        mock_conn = unittest.mock.MagicMock()
        mock_c = unittest.mock.MagicMock()
        mock_conn.cursor.return_value = mock_c
        mock_c.execute.side_effect = Exception("DB Error")
        with unittest.mock.patch('main.get_connection', return_value=mock_conn):
            result = main.rezone_address('789 New St', 'C-1')
            self.assertIn("error", result)

    def test_get_user_properties(self):
        result = main.get_user_properties('user@test.com')
        self.assertIn('properties', result)
        self.assertIn('123 Test St', result['properties'])

    def test_get_user_properties_error(self):
        mock_conn = unittest.mock.MagicMock()
        mock_c = unittest.mock.MagicMock()
        mock_conn.cursor.return_value = mock_c
        mock_c.execute.side_effect = Exception("DB Error")
        with unittest.mock.patch('main.get_connection', return_value=mock_conn):
            result = main.get_user_properties('user@test.com')
            self.assertIn("error", result)

    def test_trace_middleware(self):
        middleware = main.TraceMiddleware()
        mock_context = unittest.mock.MagicMock()
        mock_context.method = "test_method"
        mock_context.message.name = "test_tool"
        mock_context.type = "test_type"

        async def mock_call_next(ctx):
            return "success"

        result = asyncio.run(middleware.on_call_tool(mock_context, mock_call_next))
        self.assertEqual(result, "success")

class TestDB(unittest.TestCase):
    def test_init_db_and_seed_data(self):
        # We'll use an in-memory DB for db testing too, instead of touching file system
        # Override the db.DB_NAME temporarily
        original_db_name = db.DB_NAME
        original_global_conn = db._global_conn
        db.DB_NAME = ":memory:"
        db._global_conn = None # force re-init

        try:
            db.init_db()
            conn = db.get_connection()
            self.assertIsNotNone(conn)

            # Verify seed data ran
            c = conn.cursor()
            c.execute("SELECT count(*) FROM parcels")
            count = c.fetchone()[0]
            self.assertGreater(count, 0)
        finally:
            db.DB_NAME = original_db_name
            db._global_conn = original_global_conn

if __name__ == '__main__':
    unittest.main()
