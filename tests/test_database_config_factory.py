"""Tests for database configuration factory functions.

This module contains tests for the database MCP configuration factory,
ensuring proper configuration generation for different database types.
"""

import pytest
from hypothesis import given, settings
from hypothesis import strategies as st

from offline_chat.database_config import (
    create_database_mcp_config,
)
from offline_chat.mcp_config import MCPServerConfig


class TestDatabaseTypeValidation:
    """Property 1: Database type validation.

    Feature: database-access, Property 1: Database type validation
    **Validates: Requirements 1.1**

    For any database configuration, the system should accept only "oracle",
    "postgresql", "mysql", or "sqlite" as valid database types and reject
    all other values.
    """

    @settings(max_examples=100)
    @given(
        db_type=st.sampled_from(["oracle", "postgresql", "mysql", "sqlite"]),
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    )
    def test_valid_database_types_accepted(self, db_type: str, name: str):
        """Valid database types should be accepted."""
        # For each database type, provide minimal required parameters
        if db_type == "oracle":
            config = create_database_mcp_config(db_type, name, connection_name="TEST_CONN")
        elif db_type == "sqlite":
            config = create_database_mcp_config(db_type, name, path="/tmp/test.db")
        elif db_type == "postgresql":
            config = create_database_mcp_config(
                db_type,
                name,
                host="localhost",
                port=5432,
                database="testdb",
                username="user",
                password="pass",
            )
        elif db_type == "mysql":
            config = create_database_mcp_config(
                db_type,
                name,
                host="localhost",
                port=3306,
                database="testdb",
                username="user",
                password="pass",
            )

        # Verify the configuration was created with correct type
        assert isinstance(config, MCPServerConfig)
        assert config.database_type == db_type
        assert config.name == name

    @settings(max_examples=50)
    @given(
        invalid_type=st.text(min_size=1, max_size=20).filter(
            lambda s: s not in ["oracle", "postgresql", "mysql", "sqlite"]
        ),
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    )
    def test_invalid_database_types_rejected(self, invalid_type: str, name: str):
        """Invalid database types should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_database_mcp_config(invalid_type, name, path="/tmp/test.db")

        assert "Unsupported database type" in str(exc_info.value)
        assert invalid_type in str(exc_info.value)


class TestOracleConfigurationAcceptance:
    """Property 2: Oracle configuration acceptance.

    Feature: database-access, Property 2: Oracle configuration acceptance
    **Validates: Requirements 1.2, 1.3**

    For any valid Oracle connection (TNS name, SQLcl connection name, or full
    connection details), when configuring an Oracle database, the system should
    accept the configuration and create a valid MCP server configuration.
    """

    @settings(max_examples=50)
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        connection_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    )
    def test_oracle_with_sqlcl_connection_name(self, name: str, connection_name: str):
        """Oracle config with SQLcl connection name should be accepted."""
        config = create_database_mcp_config("oracle", name, connection_name=connection_name)

        assert config.database_type == "oracle"
        assert config.name == name
        assert config.oracle_connection_name == connection_name
        assert config.command == "sql"
        assert "-connection" in config.args
        assert connection_name in config.args

    @settings(max_examples=50)
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        tns_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        username=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        password=st.text(min_size=0, max_size=50),
    )
    def test_oracle_with_tns_name(self, name: str, tns_name: str, username: str, password: str):
        """Oracle config with TNS name should be accepted."""
        config = create_database_mcp_config(
            "oracle", name, tns_name=tns_name, username=username, password=password
        )

        assert config.database_type == "oracle"
        assert config.name == name
        assert config.oracle_tns_name == tns_name
        assert config.database_user == username
        assert config.database_password == password
        assert config.command == "sql"

    @settings(max_examples=50)
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        host=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
        port=st.integers(min_value=1, max_value=65535),
        service_name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        username=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        password=st.text(min_size=0, max_size=50),
    )
    def test_oracle_with_full_connection_details(
        self, name: str, host: str, port: int, service_name: str, username: str, password: str
    ):
        """Oracle config with full connection details should be accepted."""
        config = create_database_mcp_config(
            "oracle",
            name,
            host=host,
            port=port,
            service_name=service_name,
            username=username,
            password=password,
        )

        assert config.database_type == "oracle"
        assert config.name == name
        assert config.database_host == host
        assert config.database_port == port
        assert config.database_name == service_name
        assert config.database_user == username
        assert config.database_password == password
        assert config.command == "sql"

    def test_oracle_missing_required_params_for_tns(self):
        """Oracle TNS config without username/password should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_database_mcp_config("oracle", "test_db", tns_name="PROD")
        assert "username" in str(exc_info.value).lower()
        assert "password" in str(exc_info.value).lower()

    def test_oracle_missing_required_params_for_full_connection(self):
        """Oracle full connection without required params should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_database_mcp_config("oracle", "test_db", host="localhost", username="user")
        assert (
            "service_name" in str(exc_info.value).lower()
            or "password" in str(exc_info.value).lower()
        )


class TestSQLiteConfigurationAcceptance:
    """Property 3: SQLite configuration acceptance.

    Feature: database-access, Property 3: SQLite configuration acceptance
    **Validates: Requirements 1.4**

    For any valid file path string, when configuring a SQLite database, the
    system should accept the path and create a valid MCP server configuration.
    """

    @settings(max_examples=100)
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        path=st.text(min_size=1, max_size=200).filter(lambda s: s.strip()),
    )
    def test_sqlite_with_valid_path(self, name: str, path: str):
        """SQLite config with any path string should be accepted."""
        config = create_database_mcp_config("sqlite", name, path=path)

        assert config.database_type == "sqlite"
        assert config.name == name
        assert config.database_path == path
        assert config.command == "npx"
        assert "mcp-server-sqlite-npx" in config.args
        assert path in config.args

    def test_sqlite_missing_path_raises_error(self):
        """SQLite config without path should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_database_mcp_config("sqlite", "test_db")
        assert "path" in str(exc_info.value).lower()


class TestPostgreSQLMySQLConfigurationAcceptance:
    """Property 4: PostgreSQL/MySQL configuration acceptance.

    Feature: database-access, Property 4: PostgreSQL/MySQL configuration acceptance
    **Validates: Requirements 1.5**

    For any set of connection parameters (host, port, database name, username,
    password), when configuring PostgreSQL or MySQL, the system should accept
    all parameters and create a valid MCP server configuration.
    """

    @settings(max_examples=50)
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        host=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
        port=st.integers(min_value=1, max_value=65535),
        database=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        username=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        password=st.text(min_size=0, max_size=50),
    )
    def test_postgresql_with_all_params(
        self, name: str, host: str, port: int, database: str, username: str, password: str
    ):
        """PostgreSQL config with all parameters should be accepted."""
        config = create_database_mcp_config(
            "postgresql",
            name,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
        )

        assert config.database_type == "postgresql"
        assert config.name == name
        assert config.database_host == host
        assert config.database_port == port
        assert config.database_name == database
        assert config.database_user == username
        assert config.database_password == password
        assert config.command == "npx"
        assert "-y" in config.args
        assert "@modelcontextprotocol/server-postgres" in config.args
        # Connection string should be in args
        connection_string = f"postgresql://{username}:{password}@{host}:{port}/{database}"
        assert connection_string in config.args

    @settings(max_examples=50)
    @given(
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        host=st.text(min_size=1, max_size=100).filter(lambda s: s.strip()),
        port=st.integers(min_value=1, max_value=65535),
        database=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        username=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
        password=st.text(min_size=0, max_size=50),
    )
    def test_mysql_with_all_params(
        self, name: str, host: str, port: int, database: str, username: str, password: str
    ):
        """MySQL config with all parameters should be accepted."""
        config = create_database_mcp_config(
            "mysql",
            name,
            host=host,
            port=port,
            database=database,
            username=username,
            password=password,
        )

        assert config.database_type == "mysql"
        assert config.name == name
        assert config.database_host == host
        assert config.database_port == port
        assert config.database_name == database
        assert config.database_user == username
        assert config.database_password == password
        assert config.command == "uvx"
        assert "mysql-mcp-server" in config.args

    def test_postgresql_missing_required_params(self):
        """PostgreSQL config without required params should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_database_mcp_config("postgresql", "test_db", host="localhost")
        error_msg = str(exc_info.value).lower()
        assert any(word in error_msg for word in ["database", "username", "password"])

    def test_mysql_missing_required_params(self):
        """MySQL config without required params should raise ValueError."""
        with pytest.raises(ValueError) as exc_info:
            create_database_mcp_config("mysql", "test_db", host="localhost", database="testdb")
        error_msg = str(exc_info.value).lower()
        assert any(word in error_msg for word in ["username", "password"])


class TestMCPServerConfigGeneration:
    """Property 5: MCP server config generation.

    Feature: database-access, Property 5: MCP server config generation
    **Validates: Requirements 1.6**

    For any valid database configuration, providing it to the system should
    result in exactly one MCP server configuration entry being created.
    """

    @settings(max_examples=100)
    @given(
        db_type=st.sampled_from(["oracle", "postgresql", "mysql", "sqlite"]),
        name=st.text(min_size=1, max_size=50).filter(lambda s: s.strip()),
    )
    def test_single_config_created_for_valid_input(self, db_type: str, name: str):
        """Each valid database configuration should create exactly one MCPServerConfig."""
        # Provide appropriate parameters for each database type
        if db_type == "oracle":
            config = create_database_mcp_config(db_type, name, connection_name="TEST_CONN")
        elif db_type == "sqlite":
            config = create_database_mcp_config(db_type, name, path="/tmp/test.db")
        elif db_type == "postgresql":
            config = create_database_mcp_config(
                db_type,
                name,
                host="localhost",
                port=5432,
                database="testdb",
                username="user",
                password="pass",
            )
        elif db_type == "mysql":
            config = create_database_mcp_config(
                db_type,
                name,
                host="localhost",
                port=3306,
                database="testdb",
                username="user",
                password="pass",
            )

        # Verify exactly one config object is returned
        assert isinstance(config, MCPServerConfig)
        assert config.name == name
        assert config.database_type == db_type

        # Verify it's a single object, not a list or collection
        assert not isinstance(config, (list, tuple, dict))


class TestSpecificDatabaseConfigurations:
    """Unit tests for specific database configuration scenarios."""

    def test_oracle_with_sqlcl_connection(self):
        """Oracle with SQLcl connection should create correct config."""
        config = create_database_mcp_config("oracle", "prod_db", connection_name="PROD_CONN")

        assert config.name == "prod_db"
        assert config.database_type == "oracle"
        assert config.oracle_connection_name == "PROD_CONN"
        assert config.command == "sql"
        assert config.args == ["-mcp", "-connection", "PROD_CONN"]

    def test_oracle_with_tns(self):
        """Oracle with TNS should create correct config."""
        config = create_database_mcp_config(
            "oracle", "prod_db", tns_name="PROD_TNS", username="admin", password="secret"
        )

        assert config.name == "prod_db"
        assert config.database_type == "oracle"
        assert config.oracle_tns_name == "PROD_TNS"
        assert config.database_user == "admin"
        assert config.database_password == "secret"
        assert "admin/secret@PROD_TNS" in config.args[1]

    def test_oracle_with_full_details(self):
        """Oracle with full connection details should create correct config."""
        config = create_database_mcp_config(
            "oracle",
            "prod_db",
            host="db.example.com",
            port=1521,
            service_name="ORCL",
            username="admin",
            password="secret",
        )

        assert config.name == "prod_db"
        assert config.database_type == "oracle"
        assert config.database_host == "db.example.com"
        assert config.database_port == 1521
        assert config.database_name == "ORCL"
        assert config.database_user == "admin"
        assert config.database_password == "secret"
        assert "admin/secret@db.example.com:1521/ORCL" in config.args[1]

    def test_sqlite_basic(self):
        """SQLite with path should create correct config."""
        config = create_database_mcp_config("sqlite", "local_db", path="/data/app.db")

        assert config.name == "local_db"
        assert config.database_type == "sqlite"
        assert config.database_path == "/data/app.db"
        assert config.command == "npx"
        assert config.args == ["-y", "mcp-server-sqlite-npx", "/data/app.db"]

    def test_postgresql_basic(self):
        """PostgreSQL with all params should create correct config."""
        config = create_database_mcp_config(
            "postgresql",
            "analytics_db",
            host="localhost",
            port=5432,
            database="analytics",
            username="analyst",
            password="secret",
        )

        assert config.name == "analytics_db"
        assert config.database_type == "postgresql"
        assert config.database_host == "localhost"
        assert config.database_port == 5432
        assert config.database_name == "analytics"
        assert config.database_user == "analyst"
        assert config.database_password == "secret"
        # PostgreSQL now uses connection string in args, not env
        assert config.command == "npx"
        assert "-y" in config.args
        assert "@modelcontextprotocol/server-postgres" in config.args
        # Connection string should be in args
        connection_string = "postgresql://analyst:secret@localhost:5432/analytics"
        assert connection_string in config.args

    def test_mysql_basic(self):
        """MySQL with all params should create correct config."""
        config = create_database_mcp_config(
            "mysql",
            "sales_db",
            host="localhost",
            port=3306,
            database="sales",
            username="sales_user",
            password="secret",
        )

        assert config.name == "sales_db"
        assert config.database_type == "mysql"
        assert config.database_host == "localhost"
        assert config.database_port == 3306
        assert config.database_name == "sales"
        assert config.database_user == "sales_user"
        assert config.database_password == "secret"

    def test_empty_password_accepted(self):
        """Empty passwords should be accepted for databases that allow it."""
        config = create_database_mcp_config(
            "postgresql",
            "test_db",
            host="localhost",
            port=5432,
            database="testdb",
            username="testuser",
            password="",
        )

        assert config.database_password == ""
        # PostgreSQL now uses connection string, not env
        connection_string = "postgresql://testuser:@localhost:5432/testdb"
        assert connection_string in config.args

    def test_default_ports_used(self):
        """Default ports should be used when not specified."""
        # PostgreSQL default port
        pg_config = create_database_mcp_config(
            "postgresql",
            "pg_db",
            host="localhost",
            database="testdb",
            username="user",
            password="pass",
        )
        assert pg_config.database_port == 5432

        # MySQL default port
        mysql_config = create_database_mcp_config(
            "mysql",
            "mysql_db",
            host="localhost",
            database="testdb",
            username="user",
            password="pass",
        )
        assert mysql_config.database_port == 3306

        # Oracle default port
        oracle_config = create_database_mcp_config(
            "oracle",
            "oracle_db",
            host="localhost",
            service_name="ORCL",
            username="user",
            password="pass",
        )
        assert oracle_config.database_port == 1521
