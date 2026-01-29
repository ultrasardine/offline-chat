"""Unit tests for AccessLevelValidator."""

from offline_chat.database.access_level import AccessLevel
from offline_chat.database.access_validator import AccessLevelValidator
from offline_chat.database.result import is_err, is_ok, unwrap_err


class TestParseQueryOperation:
    """Tests for _parse_query_operation() method."""

    def test_parse_select(self):
        """Test parsing SELECT query."""
        assert AccessLevelValidator._parse_query_operation("SELECT * FROM users") == "SELECT"

    def test_parse_select_lowercase(self):
        """Test parsing lowercase select query."""
        assert AccessLevelValidator._parse_query_operation("select * from users") == "SELECT"

    def test_parse_select_with_whitespace(self):
        """Test parsing SELECT with leading whitespace."""
        assert AccessLevelValidator._parse_query_operation("  SELECT * FROM users") == "SELECT"

    def test_parse_insert(self):
        """Test parsing INSERT query."""
        assert AccessLevelValidator._parse_query_operation("INSERT INTO users VALUES (1, 'John')") == "INSERT"

    def test_parse_update(self):
        """Test parsing UPDATE query."""
        assert AccessLevelValidator._parse_query_operation("UPDATE users SET name = 'Jane'") == "UPDATE"

    def test_parse_delete(self):
        """Test parsing DELETE query."""
        assert AccessLevelValidator._parse_query_operation("DELETE FROM users WHERE id = 1") == "DELETE"

    def test_parse_create(self):
        """Test parsing CREATE query."""
        assert AccessLevelValidator._parse_query_operation("CREATE TABLE users (id INT)") == "CREATE"

    def test_parse_drop(self):
        """Test parsing DROP query."""
        assert AccessLevelValidator._parse_query_operation("DROP TABLE users") == "DROP"

    def test_parse_alter(self):
        """Test parsing ALTER query."""
        assert AccessLevelValidator._parse_query_operation("ALTER TABLE users ADD COLUMN age INT") == "ALTER"

    def test_parse_with_comment(self):
        """Test parsing query with comment."""
        assert AccessLevelValidator._parse_query_operation("-- comment\nSELECT * FROM users") == "SELECT"

    def test_parse_with_multiline_comment(self):
        """Test parsing query with multiline comment."""
        assert AccessLevelValidator._parse_query_operation("/* comment */SELECT * FROM users") == "SELECT"

    def test_parse_empty_query(self):
        """Test parsing empty query."""
        assert AccessLevelValidator._parse_query_operation("") == ""

    def test_parse_whitespace_only(self):
        """Test parsing whitespace-only query."""
        assert AccessLevelValidator._parse_query_operation("   ") == ""


class TestExtractTableNames:
    """Tests for _extract_table_names() method."""

    def test_extract_from_select(self):
        """Test extracting table from SELECT query."""
        tables = AccessLevelValidator._extract_table_names("SELECT * FROM users")
        assert tables == ["users"]

    def test_extract_from_select_with_join(self):
        """Test extracting tables from SELECT with JOIN."""
        tables = AccessLevelValidator._extract_table_names("SELECT * FROM users u JOIN orders o ON u.id = o.user_id")
        assert set(tables) == {"users", "orders"}

    def test_extract_from_insert(self):
        """Test extracting table from INSERT query."""
        tables = AccessLevelValidator._extract_table_names("INSERT INTO users (name) VALUES ('John')")
        assert tables == ["users"]

    def test_extract_from_update(self):
        """Test extracting table from UPDATE query."""
        tables = AccessLevelValidator._extract_table_names("UPDATE users SET name = 'Jane' WHERE id = 1")
        assert tables == ["users"]

    def test_extract_from_delete(self):
        """Test extracting table from DELETE query."""
        tables = AccessLevelValidator._extract_table_names("DELETE FROM users WHERE id = 1")
        assert tables == ["users"]

    def test_extract_with_schema(self):
        """Test extracting table with schema prefix."""
        tables = AccessLevelValidator._extract_table_names("SELECT * FROM myschema.users")
        assert tables == ["users"]

    def test_extract_multiple_joins(self):
        """Test extracting tables from query with multiple joins."""
        tables = AccessLevelValidator._extract_table_names(
            "SELECT * FROM users u JOIN orders o ON u.id = o.user_id JOIN products p ON o.product_id = p.id"
        )
        assert set(tables) == {"users", "orders", "products"}

    def test_extract_no_duplicates(self):
        """Test that duplicate table names are removed."""
        tables = AccessLevelValidator._extract_table_names(
            "SELECT * FROM users u1 JOIN users u2 ON u1.manager_id = u2.id"
        )
        assert tables == ["users"]

    def test_extract_empty_query(self):
        """Test extracting from empty query."""
        tables = AccessLevelValidator._extract_table_names("")
        assert tables == []


class TestValidateQueryReadOnly:
    """Tests for validate_query() with READ_ONLY access level."""

    def test_read_only_allows_select(self):
        """Test that READ_ONLY allows SELECT queries."""
        result = AccessLevelValidator.validate_query("SELECT * FROM users", AccessLevel.READ_ONLY, [])
        assert is_ok(result)

    def test_read_only_rejects_insert(self):
        """Test that READ_ONLY rejects INSERT queries."""
        result = AccessLevelValidator.validate_query(
            "INSERT INTO users (name) VALUES ('John')", AccessLevel.READ_ONLY, []
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "read-only" in error_msg.lower()
        assert "INSERT" in error_msg

    def test_read_only_rejects_update(self):
        """Test that READ_ONLY rejects UPDATE queries."""
        result = AccessLevelValidator.validate_query("UPDATE users SET name = 'Jane'", AccessLevel.READ_ONLY, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "read-only" in error_msg.lower()
        assert "UPDATE" in error_msg

    def test_read_only_rejects_delete(self):
        """Test that READ_ONLY rejects DELETE queries."""
        result = AccessLevelValidator.validate_query("DELETE FROM users", AccessLevel.READ_ONLY, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "read-only" in error_msg.lower()
        assert "DELETE" in error_msg

    def test_read_only_rejects_create(self):
        """Test that READ_ONLY rejects CREATE queries."""
        result = AccessLevelValidator.validate_query("CREATE TABLE users (id INT)", AccessLevel.READ_ONLY, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "read-only" in error_msg.lower()
        assert "CREATE" in error_msg

    def test_read_only_rejects_drop(self):
        """Test that READ_ONLY rejects DROP queries."""
        result = AccessLevelValidator.validate_query("DROP TABLE users", AccessLevel.READ_ONLY, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "read-only" in error_msg.lower()
        assert "DROP" in error_msg


class TestValidateQueryReadWrite:
    """Tests for validate_query() with READ_WRITE access level."""

    def test_read_write_allows_select(self):
        """Test that READ_WRITE allows SELECT queries."""
        result = AccessLevelValidator.validate_query("SELECT * FROM users", AccessLevel.READ_WRITE, [])
        assert is_ok(result)

    def test_read_write_allows_insert(self):
        """Test that READ_WRITE allows INSERT queries."""
        result = AccessLevelValidator.validate_query(
            "INSERT INTO users (name) VALUES ('John')", AccessLevel.READ_WRITE, []
        )
        assert is_ok(result)

    def test_read_write_allows_update(self):
        """Test that READ_WRITE allows UPDATE queries."""
        result = AccessLevelValidator.validate_query("UPDATE users SET name = 'Jane'", AccessLevel.READ_WRITE, [])
        assert is_ok(result)

    def test_read_write_allows_delete(self):
        """Test that READ_WRITE allows DELETE queries."""
        result = AccessLevelValidator.validate_query("DELETE FROM users WHERE id = 1", AccessLevel.READ_WRITE, [])
        assert is_ok(result)

    def test_read_write_rejects_create(self):
        """Test that READ_WRITE rejects CREATE queries (DDL)."""
        result = AccessLevelValidator.validate_query("CREATE TABLE users (id INT)", AccessLevel.READ_WRITE, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "read-write" in error_msg.lower()
        assert "CREATE" in error_msg
        assert "DDL" in error_msg

    def test_read_write_rejects_drop(self):
        """Test that READ_WRITE rejects DROP queries (DDL)."""
        result = AccessLevelValidator.validate_query("DROP TABLE users", AccessLevel.READ_WRITE, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "read-write" in error_msg.lower()
        assert "DROP" in error_msg

    def test_read_write_rejects_alter(self):
        """Test that READ_WRITE rejects ALTER queries (DDL)."""
        result = AccessLevelValidator.validate_query("ALTER TABLE users ADD COLUMN age INT", AccessLevel.READ_WRITE, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "read-write" in error_msg.lower()
        assert "ALTER" in error_msg


class TestValidateQueryTableSpecificRead:
    """Tests for validate_query() with TABLE_SPECIFIC_READ access level."""

    def test_table_specific_read_allows_select_on_allowed_table(self):
        """Test that TABLE_SPECIFIC_READ allows SELECT on allowed tables."""
        result = AccessLevelValidator.validate_query(
            "SELECT * FROM users", AccessLevel.TABLE_SPECIFIC_READ, ["users", "orders"]
        )
        assert is_ok(result)

    def test_table_specific_read_rejects_select_on_disallowed_table(self):
        """Test that TABLE_SPECIFIC_READ rejects SELECT on non-allowed tables."""
        result = AccessLevelValidator.validate_query(
            "SELECT * FROM products", AccessLevel.TABLE_SPECIFIC_READ, ["users", "orders"]
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "table-specific-read" in error_msg.lower()
        assert "products" in error_msg

    def test_table_specific_read_rejects_insert(self):
        """Test that TABLE_SPECIFIC_READ rejects INSERT queries."""
        result = AccessLevelValidator.validate_query(
            "INSERT INTO users (name) VALUES ('John')", AccessLevel.TABLE_SPECIFIC_READ, ["users"]
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "table-specific-read" in error_msg.lower()
        assert "INSERT" in error_msg

    def test_table_specific_read_requires_allowed_tables(self):
        """Test that TABLE_SPECIFIC_READ requires allowed_tables to be specified."""
        result = AccessLevelValidator.validate_query("SELECT * FROM users", AccessLevel.TABLE_SPECIFIC_READ, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "allowed_tables" in error_msg

    def test_table_specific_read_allows_join_on_allowed_tables(self):
        """Test that TABLE_SPECIFIC_READ allows JOIN on allowed tables."""
        result = AccessLevelValidator.validate_query(
            "SELECT * FROM users u JOIN orders o ON u.id = o.user_id",
            AccessLevel.TABLE_SPECIFIC_READ,
            ["users", "orders"],
        )
        assert is_ok(result)

    def test_table_specific_read_rejects_join_with_disallowed_table(self):
        """Test that TABLE_SPECIFIC_READ rejects JOIN with non-allowed table."""
        result = AccessLevelValidator.validate_query(
            "SELECT * FROM users u JOIN products p ON u.id = p.owner_id",
            AccessLevel.TABLE_SPECIFIC_READ,
            ["users", "orders"],
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "products" in error_msg


class TestValidateQueryTableSpecificReadWrite:
    """Tests for validate_query() with TABLE_SPECIFIC_READ_WRITE access level."""

    def test_table_specific_read_write_allows_select_on_allowed_table(self):
        """Test that TABLE_SPECIFIC_READ_WRITE allows SELECT on allowed tables."""
        result = AccessLevelValidator.validate_query(
            "SELECT * FROM users", AccessLevel.TABLE_SPECIFIC_READ_WRITE, ["users", "orders"]
        )
        assert is_ok(result)

    def test_table_specific_read_write_allows_insert_on_allowed_table(self):
        """Test that TABLE_SPECIFIC_READ_WRITE allows INSERT on allowed tables."""
        result = AccessLevelValidator.validate_query(
            "INSERT INTO users (name) VALUES ('John')", AccessLevel.TABLE_SPECIFIC_READ_WRITE, ["users", "orders"]
        )
        assert is_ok(result)

    def test_table_specific_read_write_allows_update_on_allowed_table(self):
        """Test that TABLE_SPECIFIC_READ_WRITE allows UPDATE on allowed tables."""
        result = AccessLevelValidator.validate_query(
            "UPDATE users SET name = 'Jane'", AccessLevel.TABLE_SPECIFIC_READ_WRITE, ["users", "orders"]
        )
        assert is_ok(result)

    def test_table_specific_read_write_allows_delete_on_allowed_table(self):
        """Test that TABLE_SPECIFIC_READ_WRITE allows DELETE on allowed tables."""
        result = AccessLevelValidator.validate_query(
            "DELETE FROM users WHERE id = 1", AccessLevel.TABLE_SPECIFIC_READ_WRITE, ["users", "orders"]
        )
        assert is_ok(result)

    def test_table_specific_read_write_rejects_insert_on_disallowed_table(self):
        """Test that TABLE_SPECIFIC_READ_WRITE rejects INSERT on non-allowed tables."""
        result = AccessLevelValidator.validate_query(
            "INSERT INTO products (name) VALUES ('Widget')", AccessLevel.TABLE_SPECIFIC_READ_WRITE, ["users", "orders"]
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "table-specific-read-write" in error_msg.lower()
        assert "products" in error_msg

    def test_table_specific_read_write_rejects_ddl(self):
        """Test that TABLE_SPECIFIC_READ_WRITE rejects DDL queries."""
        result = AccessLevelValidator.validate_query(
            "CREATE TABLE users (id INT)", AccessLevel.TABLE_SPECIFIC_READ_WRITE, ["users"]
        )
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "table-specific-read-write" in error_msg.lower()
        assert "CREATE" in error_msg
        assert "DDL" in error_msg

    def test_table_specific_read_write_requires_allowed_tables(self):
        """Test that TABLE_SPECIFIC_READ_WRITE requires allowed_tables."""
        result = AccessLevelValidator.validate_query("SELECT * FROM users", AccessLevel.TABLE_SPECIFIC_READ_WRITE, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "allowed_tables" in error_msg


class TestValidateQueryEdgeCases:
    """Tests for edge cases in validate_query()."""

    def test_empty_query(self):
        """Test that empty query is rejected."""
        result = AccessLevelValidator.validate_query("", AccessLevel.READ_ONLY, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "empty" in error_msg.lower()

    def test_whitespace_only_query(self):
        """Test that whitespace-only query is rejected."""
        result = AccessLevelValidator.validate_query("   ", AccessLevel.READ_ONLY, [])
        assert is_err(result)
        error_msg = unwrap_err(result)
        assert "empty" in error_msg.lower()

    def test_query_with_lowercase_operation(self):
        """Test that lowercase operations are handled correctly."""
        result = AccessLevelValidator.validate_query("select * from users", AccessLevel.READ_ONLY, [])
        assert is_ok(result)

    def test_query_with_mixed_case_operation(self):
        """Test that mixed case operations are handled correctly."""
        result = AccessLevelValidator.validate_query("SeLeCt * FrOm users", AccessLevel.READ_ONLY, [])
        assert is_ok(result)
