"""Property-based tests for access level validation.

Feature: database-connection-management
Properties: 28, 29, 30, 31

This module contains property-based tests for validating SQL queries against
assigned access levels. These tests verify that the AccessLevelValidator
correctly enforces access restrictions for different access levels.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.database.access_level import AccessLevel
from offline_chat.database.access_validator import AccessLevelValidator
from offline_chat.database.result import is_ok, is_err, unwrap_err


# Custom strategies for generating SQL queries
@st.composite
def sql_select_query(draw, table_name=None):
    """Generate a SELECT query."""
    if table_name is None:
        table_name = draw(st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']))
    return f"SELECT * FROM {table_name}"


@st.composite
def sql_insert_query(draw, table_name=None):
    """Generate an INSERT query."""
    if table_name is None:
        table_name = draw(st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']))
    value = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'))))
    return f"INSERT INTO {table_name} (name) VALUES ('{value}')"


@st.composite
def sql_update_query(draw, table_name=None):
    """Generate an UPDATE query."""
    if table_name is None:
        table_name = draw(st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']))
    value = draw(st.text(min_size=1, max_size=20, alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'))))
    return f"UPDATE {table_name} SET name = '{value}' WHERE id = 1"


@st.composite
def sql_delete_query(draw, table_name=None):
    """Generate a DELETE query."""
    if table_name is None:
        table_name = draw(st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']))
    return f"DELETE FROM {table_name} WHERE id = 1"



@st.composite
def sql_ddl_query(draw, table_name=None):
    """Generate a DDL query (CREATE, DROP, ALTER)."""
    if table_name is None:
        table_name = draw(st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']))
    operation = draw(st.sampled_from(['CREATE', 'DROP', 'ALTER']))
    
    if operation == 'CREATE':
        return f"CREATE TABLE {table_name} (id INT, name VARCHAR(100))"
    elif operation == 'DROP':
        return f"DROP TABLE {table_name}"
    else:  # ALTER
        return f"ALTER TABLE {table_name} ADD COLUMN age INT"


class TestProperty28ReadOnlyAccessLevel:
    """Property-based tests for READ_ONLY access level.
    
    Feature: database-connection-management
    Property 28: Access Level Query Validation - Read Only
    
    **Validates: Requirements 12.3, 12.7, 12.8**
    """
    
    @given(
        table_name=st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices', 'accounts', 'transactions'])
    )
    @settings(max_examples=100)
    def test_property_28_read_only_allows_select(self, table_name):
        """
        Property 28: Access Level Query Validation - Read Only
        
        For any agent with read-only access to a connection, SELECT queries
        should be allowed.
        
        **Validates: Requirements 12.3, 12.7, 12.8**
        """
        # Generate SELECT query
        query = f"SELECT * FROM {table_name}"
        
        # Validate with READ_ONLY access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.READ_ONLY,
            []
        )
        
        # SELECT should be allowed
        assert is_ok(result), \
            f"SELECT query should be allowed with READ_ONLY access, but got error: {unwrap_err(result) if is_err(result) else 'N/A'}"
    
    @given(
        table_name=st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']),
        operation=st.sampled_from(['INSERT', 'UPDATE', 'DELETE'])
    )
    @settings(max_examples=100)
    def test_property_28_read_only_rejects_write_operations(self, table_name, operation):
        """
        Property 28: Access Level Query Validation - Read Only
        
        For any agent with read-only access to a connection, INSERT, UPDATE,
        and DELETE queries should fail with an access denied error.
        
        **Validates: Requirements 12.3, 12.7, 12.8**
        """
        # Generate write query based on operation
        if operation == 'INSERT':
            query = f"INSERT INTO {table_name} (name) VALUES ('test')"
        elif operation == 'UPDATE':
            query = f"UPDATE {table_name} SET name = 'test' WHERE id = 1"
        else:  # DELETE
            query = f"DELETE FROM {table_name} WHERE id = 1"
        
        # Validate with READ_ONLY access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.READ_ONLY,
            []
        )
        
        # Write operations should be rejected
        assert is_err(result), \
            f"{operation} query should be rejected with READ_ONLY access"
        
        error_msg = unwrap_err(result)
        assert "read-only" in error_msg.lower(), \
            f"Error message should mention 'read-only', got: {error_msg}"
        assert operation in error_msg, \
            f"Error message should mention operation '{operation}', got: {error_msg}"

    
    @given(
        table_name=st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']),
        ddl_operation=st.sampled_from(['CREATE', 'DROP', 'ALTER', 'TRUNCATE'])
    )
    @settings(max_examples=100)
    def test_property_28_read_only_rejects_ddl_operations(self, table_name, ddl_operation):
        """
        Property 28: Access Level Query Validation - Read Only
        
        For any agent with read-only access to a connection, DDL queries
        (CREATE, DROP, ALTER, TRUNCATE) should fail with an access denied error.
        
        **Validates: Requirements 12.3, 12.7, 12.8**
        """
        # Generate DDL query based on operation
        if ddl_operation == 'CREATE':
            query = f"CREATE TABLE {table_name} (id INT, name VARCHAR(100))"
        elif ddl_operation == 'DROP':
            query = f"DROP TABLE {table_name}"
        elif ddl_operation == 'ALTER':
            query = f"ALTER TABLE {table_name} ADD COLUMN age INT"
        else:  # TRUNCATE
            query = f"TRUNCATE TABLE {table_name}"
        
        # Validate with READ_ONLY access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.READ_ONLY,
            []
        )
        
        # DDL operations should be rejected
        assert is_err(result), \
            f"{ddl_operation} query should be rejected with READ_ONLY access"
        
        error_msg = unwrap_err(result)
        assert "read-only" in error_msg.lower(), \
            f"Error message should mention 'read-only', got: {error_msg}"
        assert ddl_operation in error_msg, \
            f"Error message should mention operation '{ddl_operation}', got: {error_msg}"


class TestProperty29ReadWriteAccessLevel:
    """Property-based tests for READ_WRITE access level.
    
    Feature: database-connection-management
    Property 29: Access Level Query Validation - Read Write
    
    **Validates: Requirements 12.4, 12.7, 12.8**
    """
    
    @given(
        table_name=st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']),
        operation=st.sampled_from(['SELECT', 'INSERT', 'UPDATE', 'DELETE'])
    )
    @settings(max_examples=100)
    def test_property_29_read_write_allows_dml_operations(self, table_name, operation):
        """
        Property 29: Access Level Query Validation - Read Write
        
        For any agent with read-write access to a connection, SELECT, INSERT,
        UPDATE, and DELETE queries should be allowed.
        
        **Validates: Requirements 12.4, 12.7, 12.8**
        """
        # Generate query based on operation
        if operation == 'SELECT':
            query = f"SELECT * FROM {table_name}"
        elif operation == 'INSERT':
            query = f"INSERT INTO {table_name} (name) VALUES ('test')"
        elif operation == 'UPDATE':
            query = f"UPDATE {table_name} SET name = 'test' WHERE id = 1"
        else:  # DELETE
            query = f"DELETE FROM {table_name} WHERE id = 1"
        
        # Validate with READ_WRITE access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.READ_WRITE,
            []
        )
        
        # DML operations should be allowed
        assert is_ok(result), \
            f"{operation} query should be allowed with READ_WRITE access, but got error: {unwrap_err(result) if is_err(result) else 'N/A'}"

    
    @given(
        table_name=st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']),
        ddl_operation=st.sampled_from(['CREATE', 'DROP', 'ALTER', 'TRUNCATE'])
    )
    @settings(max_examples=100)
    def test_property_29_read_write_rejects_ddl_operations(self, table_name, ddl_operation):
        """
        Property 29: Access Level Query Validation - Read Write
        
        For any agent with read-write access to a connection, DDL queries
        (CREATE, DROP, ALTER) should be rejected.
        
        **Validates: Requirements 12.4, 12.7, 12.8**
        """
        # Generate DDL query based on operation
        if ddl_operation == 'CREATE':
            query = f"CREATE TABLE {table_name} (id INT, name VARCHAR(100))"
        elif ddl_operation == 'DROP':
            query = f"DROP TABLE {table_name}"
        elif ddl_operation == 'ALTER':
            query = f"ALTER TABLE {table_name} ADD COLUMN age INT"
        else:  # TRUNCATE
            query = f"TRUNCATE TABLE {table_name}"
        
        # Validate with READ_WRITE access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.READ_WRITE,
            []
        )
        
        # DDL operations should be rejected
        assert is_err(result), \
            f"{ddl_operation} query should be rejected with READ_WRITE access"
        
        error_msg = unwrap_err(result)
        assert "read-write" in error_msg.lower(), \
            f"Error message should mention 'read-write', got: {error_msg}"
        assert ddl_operation in error_msg, \
            f"Error message should mention operation '{ddl_operation}', got: {error_msg}"
        assert "DDL" in error_msg, \
            f"Error message should mention 'DDL', got: {error_msg}"


class TestProperty30TableSpecificReadAccessLevel:
    """Property-based tests for TABLE_SPECIFIC_READ access level.
    
    Feature: database-connection-management
    Property 30: Access Level Query Validation - Table Specific Read
    
    **Validates: Requirements 12.5, 12.7, 12.8**
    """
    
    @given(
        allowed_tables=st.lists(
            st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']),
            min_size=1,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_property_30_table_specific_read_allows_select_on_allowed_tables(self, allowed_tables):
        """
        Property 30: Access Level Query Validation - Table Specific Read
        
        For any agent with table-specific-read access, SELECT queries on
        allowed tables should succeed.
        
        **Validates: Requirements 12.5, 12.7, 12.8**
        """
        # Pick a table from the allowed list
        table_name = allowed_tables[0]
        query = f"SELECT * FROM {table_name}"
        
        # Validate with TABLE_SPECIFIC_READ access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        
        # SELECT on allowed table should be allowed
        assert is_ok(result), \
            f"SELECT query on allowed table '{table_name}' should be allowed with TABLE_SPECIFIC_READ access, but got error: {unwrap_err(result) if is_err(result) else 'N/A'}"

    
    @given(
        allowed_tables=st.lists(
            st.sampled_from(['users', 'orders', 'products']),
            min_size=1,
            max_size=2,
            unique=True
        ),
        disallowed_table=st.sampled_from(['customers', 'invoices', 'payments', 'shipments'])
    )
    @settings(max_examples=100)
    def test_property_30_table_specific_read_rejects_select_on_disallowed_tables(self, allowed_tables, disallowed_table):
        """
        Property 30: Access Level Query Validation - Table Specific Read
        
        For any agent with table-specific-read access, SELECT queries on
        non-allowed tables should fail.
        
        **Validates: Requirements 12.5, 12.7, 12.8**
        """
        # Ensure disallowed table is not in allowed list
        if disallowed_table in allowed_tables:
            return  # Skip this test case
        
        query = f"SELECT * FROM {disallowed_table}"
        
        # Validate with TABLE_SPECIFIC_READ access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        
        # SELECT on disallowed table should be rejected
        assert is_err(result), \
            f"SELECT query on disallowed table '{disallowed_table}' should be rejected with TABLE_SPECIFIC_READ access"
        
        error_msg = unwrap_err(result)
        assert "table-specific-read" in error_msg.lower(), \
            f"Error message should mention 'table-specific-read', got: {error_msg}"
        assert disallowed_table in error_msg, \
            f"Error message should mention disallowed table '{disallowed_table}', got: {error_msg}"
    
    @given(
        allowed_tables=st.lists(
            st.sampled_from(['users', 'orders', 'products']),
            min_size=1,
            max_size=3,
            unique=True
        ),
        operation=st.sampled_from(['INSERT', 'UPDATE', 'DELETE'])
    )
    @settings(max_examples=100)
    def test_property_30_table_specific_read_rejects_write_operations(self, allowed_tables, operation):
        """
        Property 30: Access Level Query Validation - Table Specific Read
        
        For any agent with table-specific-read access, any write operations
        (INSERT, UPDATE, DELETE) should fail, even on allowed tables.
        
        **Validates: Requirements 12.5, 12.7, 12.8**
        """
        # Use an allowed table
        table_name = allowed_tables[0]
        
        # Generate write query based on operation
        if operation == 'INSERT':
            query = f"INSERT INTO {table_name} (name) VALUES ('test')"
        elif operation == 'UPDATE':
            query = f"UPDATE {table_name} SET name = 'test' WHERE id = 1"
        else:  # DELETE
            query = f"DELETE FROM {table_name} WHERE id = 1"
        
        # Validate with TABLE_SPECIFIC_READ access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        
        # Write operations should be rejected
        assert is_err(result), \
            f"{operation} query should be rejected with TABLE_SPECIFIC_READ access, even on allowed table"
        
        error_msg = unwrap_err(result)
        assert "table-specific-read" in error_msg.lower(), \
            f"Error message should mention 'table-specific-read', got: {error_msg}"
        assert operation in error_msg, \
            f"Error message should mention operation '{operation}', got: {error_msg}"

    
    @given(
        allowed_tables=st.lists(
            st.sampled_from(['users', 'orders', 'products']),
            min_size=2,
            max_size=3,
            unique=True
        )
    )
    @settings(max_examples=100)
    def test_property_30_table_specific_read_allows_join_on_allowed_tables(self, allowed_tables):
        """
        Property 30: Access Level Query Validation - Table Specific Read
        
        For any agent with table-specific-read access, SELECT queries with
        JOINs on allowed tables should succeed.
        
        **Validates: Requirements 12.5, 12.7, 12.8**
        """
        # Use two allowed tables for JOIN
        table1 = allowed_tables[0]
        table2 = allowed_tables[1]
        query = f"SELECT * FROM {table1} t1 JOIN {table2} t2 ON t1.id = t2.{table1}_id"
        
        # Validate with TABLE_SPECIFIC_READ access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        
        # JOIN on allowed tables should be allowed
        assert is_ok(result), \
            f"SELECT with JOIN on allowed tables should be allowed with TABLE_SPECIFIC_READ access, but got error: {unwrap_err(result) if is_err(result) else 'N/A'}"
    
    @given(
        allowed_tables=st.lists(
            st.sampled_from(['users', 'orders']),
            min_size=1,
            max_size=2,
            unique=True
        ),
        disallowed_table=st.sampled_from(['products', 'customers', 'invoices'])
    )
    @settings(max_examples=100)
    def test_property_30_table_specific_read_rejects_join_with_disallowed_table(self, allowed_tables, disallowed_table):
        """
        Property 30: Access Level Query Validation - Table Specific Read
        
        For any agent with table-specific-read access, SELECT queries with
        JOINs that include non-allowed tables should fail.
        
        **Validates: Requirements 12.5, 12.7, 12.8**
        """
        # Ensure disallowed table is not in allowed list
        if disallowed_table in allowed_tables:
            return  # Skip this test case
        
        # Use an allowed table and a disallowed table for JOIN
        table1 = allowed_tables[0]
        query = f"SELECT * FROM {table1} t1 JOIN {disallowed_table} t2 ON t1.id = t2.{table1}_id"
        
        # Validate with TABLE_SPECIFIC_READ access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.TABLE_SPECIFIC_READ,
            allowed_tables
        )
        
        # JOIN with disallowed table should be rejected
        assert is_err(result), \
            f"SELECT with JOIN including disallowed table '{disallowed_table}' should be rejected with TABLE_SPECIFIC_READ access"
        
        error_msg = unwrap_err(result)
        assert disallowed_table in error_msg, \
            f"Error message should mention disallowed table '{disallowed_table}', got: {error_msg}"


class TestProperty31TableSpecificReadWriteAccessLevel:
    """Property-based tests for TABLE_SPECIFIC_READ_WRITE access level.
    
    Feature: database-connection-management
    Property 31: Access Level Query Validation - Table Specific Read Write
    
    **Validates: Requirements 12.6, 12.7, 12.8**
    """
    
    @given(
        allowed_tables=st.lists(
            st.sampled_from(['users', 'orders', 'products', 'customers', 'invoices']),
            min_size=1,
            max_size=3,
            unique=True
        ),
        operation=st.sampled_from(['SELECT', 'INSERT', 'UPDATE', 'DELETE'])
    )
    @settings(max_examples=100)
    def test_property_31_table_specific_read_write_allows_all_dml_on_allowed_tables(self, allowed_tables, operation):
        """
        Property 31: Access Level Query Validation - Table Specific Read Write
        
        For any agent with table-specific-read-write access, all operations
        (SELECT, INSERT, UPDATE, DELETE) on allowed tables should succeed.
        
        **Validates: Requirements 12.6, 12.7, 12.8**
        """
        # Use an allowed table
        table_name = allowed_tables[0]
        
        # Generate query based on operation
        if operation == 'SELECT':
            query = f"SELECT * FROM {table_name}"
        elif operation == 'INSERT':
            query = f"INSERT INTO {table_name} (name) VALUES ('test')"
        elif operation == 'UPDATE':
            query = f"UPDATE {table_name} SET name = 'test' WHERE id = 1"
        else:  # DELETE
            query = f"DELETE FROM {table_name} WHERE id = 1"
        
        # Validate with TABLE_SPECIFIC_READ_WRITE access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        
        # All DML operations on allowed tables should be allowed
        assert is_ok(result), \
            f"{operation} query on allowed table '{table_name}' should be allowed with TABLE_SPECIFIC_READ_WRITE access, but got error: {unwrap_err(result) if is_err(result) else 'N/A'}"

    
    @given(
        allowed_tables=st.lists(
            st.sampled_from(['users', 'orders', 'products']),
            min_size=1,
            max_size=2,
            unique=True
        ),
        disallowed_table=st.sampled_from(['customers', 'invoices', 'payments', 'shipments']),
        operation=st.sampled_from(['SELECT', 'INSERT', 'UPDATE', 'DELETE'])
    )
    @settings(max_examples=100)
    def test_property_31_table_specific_read_write_rejects_operations_on_disallowed_tables(self, allowed_tables, disallowed_table, operation):
        """
        Property 31: Access Level Query Validation - Table Specific Read Write
        
        For any agent with table-specific-read-write access, operations on
        non-allowed tables should fail.
        
        **Validates: Requirements 12.6, 12.7, 12.8**
        """
        # Ensure disallowed table is not in allowed list
        if disallowed_table in allowed_tables:
            return  # Skip this test case
        
        # Generate query based on operation
        if operation == 'SELECT':
            query = f"SELECT * FROM {disallowed_table}"
        elif operation == 'INSERT':
            query = f"INSERT INTO {disallowed_table} (name) VALUES ('test')"
        elif operation == 'UPDATE':
            query = f"UPDATE {disallowed_table} SET name = 'test' WHERE id = 1"
        else:  # DELETE
            query = f"DELETE FROM {disallowed_table} WHERE id = 1"
        
        # Validate with TABLE_SPECIFIC_READ_WRITE access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        
        # Operations on disallowed tables should be rejected
        assert is_err(result), \
            f"{operation} query on disallowed table '{disallowed_table}' should be rejected with TABLE_SPECIFIC_READ_WRITE access"
        
        error_msg = unwrap_err(result)
        assert "table-specific-read-write" in error_msg.lower(), \
            f"Error message should mention 'table-specific-read-write', got: {error_msg}"
        assert disallowed_table in error_msg, \
            f"Error message should mention disallowed table '{disallowed_table}', got: {error_msg}"
    
    @given(
        allowed_tables=st.lists(
            st.sampled_from(['users', 'orders', 'products']),
            min_size=1,
            max_size=3,
            unique=True
        ),
        ddl_operation=st.sampled_from(['CREATE', 'DROP', 'ALTER', 'TRUNCATE'])
    )
    @settings(max_examples=100)
    def test_property_31_table_specific_read_write_rejects_ddl_operations(self, allowed_tables, ddl_operation):
        """
        Property 31: Access Level Query Validation - Table Specific Read Write
        
        For any agent with table-specific-read-write access, DDL queries
        should be rejected, even on allowed tables.
        
        **Validates: Requirements 12.6, 12.7, 12.8**
        """
        # Use an allowed table
        table_name = allowed_tables[0]
        
        # Generate DDL query based on operation
        if ddl_operation == 'CREATE':
            query = f"CREATE TABLE {table_name} (id INT, name VARCHAR(100))"
        elif ddl_operation == 'DROP':
            query = f"DROP TABLE {table_name}"
        elif ddl_operation == 'ALTER':
            query = f"ALTER TABLE {table_name} ADD COLUMN age INT"
        else:  # TRUNCATE
            query = f"TRUNCATE TABLE {table_name}"
        
        # Validate with TABLE_SPECIFIC_READ_WRITE access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        
        # DDL operations should be rejected
        assert is_err(result), \
            f"{ddl_operation} query should be rejected with TABLE_SPECIFIC_READ_WRITE access, even on allowed table"
        
        error_msg = unwrap_err(result)
        assert "table-specific-read-write" in error_msg.lower(), \
            f"Error message should mention 'table-specific-read-write', got: {error_msg}"
        assert ddl_operation in error_msg, \
            f"Error message should mention operation '{ddl_operation}', got: {error_msg}"
        assert "DDL" in error_msg, \
            f"Error message should mention 'DDL', got: {error_msg}"
    
    @given(
        allowed_tables=st.lists(
            st.sampled_from(['users', 'orders', 'products']),
            min_size=2,
            max_size=3,
            unique=True
        ),
        operation=st.sampled_from(['SELECT', 'UPDATE', 'DELETE'])
    )
    @settings(max_examples=100)
    def test_property_31_table_specific_read_write_allows_operations_with_joins_on_allowed_tables(self, allowed_tables, operation):
        """
        Property 31: Access Level Query Validation - Table Specific Read Write
        
        For any agent with table-specific-read-write access, operations with
        JOINs on allowed tables should succeed.
        
        **Validates: Requirements 12.6, 12.7, 12.8**
        """
        # Use two allowed tables for JOIN
        table1 = allowed_tables[0]
        table2 = allowed_tables[1]
        
        # Generate query based on operation
        if operation == 'SELECT':
            query = f"SELECT * FROM {table1} t1 JOIN {table2} t2 ON t1.id = t2.{table1}_id"
        elif operation == 'UPDATE':
            query = f"UPDATE {table1} t1 JOIN {table2} t2 ON t1.id = t2.{table1}_id SET t1.name = 'test'"
        else:  # DELETE
            query = f"DELETE t1 FROM {table1} t1 JOIN {table2} t2 ON t1.id = t2.{table1}_id"
        
        # Validate with TABLE_SPECIFIC_READ_WRITE access level
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE,
            allowed_tables
        )
        
        # Operations with JOINs on allowed tables should be allowed
        assert is_ok(result), \
            f"{operation} with JOIN on allowed tables should be allowed with TABLE_SPECIFIC_READ_WRITE access, but got error: {unwrap_err(result) if is_err(result) else 'N/A'}"



class TestAccessLevelValidationEdgeCases:
    """Edge case tests for access level validation.
    
    These tests verify that the validator handles edge cases correctly
    across all access levels.
    """
    
    @given(
        access_level=st.sampled_from([
            AccessLevel.READ_ONLY,
            AccessLevel.READ_WRITE,
            AccessLevel.TABLE_SPECIFIC_READ,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE
        ])
    )
    @settings(max_examples=50)
    def test_empty_query_rejected_for_all_access_levels(self, access_level):
        """Test that empty queries are rejected for all access levels."""
        result = AccessLevelValidator.validate_query(
            "",
            access_level,
            ["users", "orders"]
        )
        
        assert is_err(result), \
            f"Empty query should be rejected for {access_level.value} access"
        
        error_msg = unwrap_err(result)
        assert "empty" in error_msg.lower(), \
            f"Error message should mention 'empty', got: {error_msg}"
    
    @given(
        access_level=st.sampled_from([
            AccessLevel.TABLE_SPECIFIC_READ,
            AccessLevel.TABLE_SPECIFIC_READ_WRITE
        ])
    )
    @settings(max_examples=50)
    def test_table_specific_access_requires_allowed_tables(self, access_level):
        """Test that table-specific access levels require allowed_tables to be specified."""
        result = AccessLevelValidator.validate_query(
            "SELECT * FROM users",
            access_level,
            []  # Empty allowed_tables
        )
        
        assert is_err(result), \
            f"Query should be rejected when allowed_tables is empty for {access_level.value} access"
        
        error_msg = unwrap_err(result)
        assert "allowed_tables" in error_msg, \
            f"Error message should mention 'allowed_tables', got: {error_msg}"
    
    @given(
        query_case=st.sampled_from(['lower', 'upper', 'mixed']),
        access_level=st.sampled_from([
            AccessLevel.READ_ONLY,
            AccessLevel.READ_WRITE
        ])
    )
    @settings(max_examples=50)
    def test_case_insensitive_query_parsing(self, query_case, access_level):
        """Test that query parsing is case-insensitive."""
        # Generate query with different cases
        if query_case == 'lower':
            query = "select * from users"
        elif query_case == 'upper':
            query = "SELECT * FROM USERS"
        else:  # mixed
            query = "SeLeCt * FrOm UsErS"
        
        result = AccessLevelValidator.validate_query(
            query,
            access_level,
            []
        )
        
        # SELECT should be allowed for both READ_ONLY and READ_WRITE
        assert is_ok(result), \
            f"SELECT query should be allowed regardless of case for {access_level.value} access, but got error: {unwrap_err(result) if is_err(result) else 'N/A'}"
    
    @given(
        table_name=st.text(
            alphabet=st.characters(whitelist_categories=('Ll', 'Lu', 'Nd'), whitelist_characters='_'),
            min_size=1,
            max_size=30
        ).filter(lambda s: s[0].isalpha())
    )
    @settings(max_examples=100)
    def test_various_table_names_with_read_only(self, table_name):
        """Test that various valid table names work with READ_ONLY access."""
        query = f"SELECT * FROM {table_name}"
        
        result = AccessLevelValidator.validate_query(
            query,
            AccessLevel.READ_ONLY,
            []
        )
        
        # SELECT should be allowed for any valid table name
        assert is_ok(result), \
            f"SELECT query on table '{table_name}' should be allowed with READ_ONLY access, but got error: {unwrap_err(result) if is_err(result) else 'N/A'}"
