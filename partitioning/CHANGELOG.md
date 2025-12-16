# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [0.4.1] - 2025-12-16
### Added
- **CLI**: Added `--verbose` / `-v` flag to switch between INFO (default) and DEBUG logging levels.
- **CLI**: Added `-r` short flag for `--dry-run`.

## [0.4.0] - 2025-12-16
### Added
- **Monitoring**: Added `--discovery` argument for Zabbix Low-Level Discovery (LLD) of partitioned tables.
- **Monitoring**: Added `--check-days` argument to calculate days remaining until partition buffer exhaustion.
- **CLI**: Added `--version` / `-V` flag to display script version.
- **Docker**: Added `RUN_MODE=discovery` and `RUN_MODE=check` support to `entrypoint.py`.
- **Templates**: Added Zabbix 7.0 compatible template `zabbix_partitioning_template.yaml`.

### Removed
- **CLI**: Removed unimplemented `--delete` / `-d` argument.

## [0.3.0] - 2025-12-14
### Changed
- **Refactor**: Complete rewrite of `zabbix_partitioning.py` using Class-based structure (`ZabbixPartitioner`).
- **Configuration**: Extended comments in the configuration file (`zabbix_partitioning.conf`). The config file is self-explanatory now.
- **Docker**: Introduced Docker container support (`Dockerfile`, `entrypoint.py`). The script can be run in a stateless manner using Docker.

### Added
- **Optimization**: Added `initial_partitioning_start` option (`db_min` vs `retention`) to speed up initialization on large DBs.