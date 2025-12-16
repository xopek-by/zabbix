# Code Documentation: ZabbixPartitioner

## Class: ZabbixPartitioner

### Core Methods

#### `__init__(self, config: Dict[str, Any], dry_run: bool = False)`
Initializes the partitioner with configuration and runtime mode.
- **config**: Dictionary containing database connection and partitioning rules.
- **dry_run**: If True, SQL queries are logged but not executed.

#### `connect_db(self)`
Context manager for database connections.
- Handles connection lifecycle (open/close).
- Sets strict session variables:
  - `wait_timeout = 86400` (24h) to prevent timeouts during long operations.
  - `sql_log_bin = 0` (if configured) to prevent replication of partitioning commands.

#### `run(self, mode: str)`
Main entry point for execution.
- **mode**: 
  - `'init'`: Initial setup. Calls `initialize_partitioning`.
  - `'maintenance'` (default): Routine operation. Calls `create_future_partitions` and `drop_old_partitions`.

### Logic Methods

#### `initialize_partitioning(table: str, period: str, premake: int, retention_str: str)`
Converts a standard table to a partitioned table.
- **Strategies** (via `initial_partitioning_start` config):
  - `retention`: Starts from (Now - Retention). Creates `p_archive` for older data. FAST.
  - `db_min`: Queries `SELECT MIN(clock)`. PRECISE but SLOW.

#### `create_future_partitions(table: str, period: str, premake: int)`
Ensures sufficient future partitions exist.
- Calculates required partitions based on current time + `premake` count.
- Checks `information_schema` for existing partitions.
- Adds missing partitions using `ALTER TABLE ... ADD PARTITION`.

#### `drop_old_partitions(table: str, period: str, retention_str: str)`
Removes partitions older than the retention period.
- Parses partition names (e.g., `p2023_01_01`) to extract their date.
- Compares against the calculated retention cutoff date.
- Drops qualifiers using `ALTER TABLE ... DROP PARTITION`.

### Helper Methods

#### `get_table_min_clock(table: str) -> Optional[datetime]`
- Queries the table for the oldest timestamp. Used in `db_min` initialization strategy.

#### `has_incompatible_primary_key(table: str) -> bool`
- **Safety Critical**: Verifies that the table's Primary Key includes the `clock` column.
- Returns `True` if incompatible (prevents partitioning to avoid MySQL errors).

#### `get_partition_name(dt: datetime, period: str) -> str`
- Generates standard partition names:
  - Daily: `pYYYY_MM_DD`
  - Monthly: `pYYYY_MM`

#### `get_partition_description(dt: datetime, period: str) -> str`
- Generates the `VALUES LESS THAN` expression for the partition (Start of NEXT period).
