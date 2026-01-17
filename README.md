# grovectl

A command-line tool for managing macOS virtual machines on remote hosts via SSH.

grovectl enables you to orchestrate macOS VMs running on remote Mac hosts using the [tart](https://github.com/cirruslabs/tart) virtualization tool. It provides a unified interface for managing VMs across multiple hosts with features like connection pooling, retry logic, and rich terminal output.

## Features

- **Multi-host Management**: Configure and manage VMs across multiple remote macOS hosts
- **SSH Connection Pooling**: Efficient reuse of SSH connections for batch operations
- **Rich Terminal Output**: Beautiful tables, progress bars, and color-coded status
- **Multiple Output Formats**: Table, JSON, and YAML output for scripting
- **Dry-run Mode**: Test commands without executing them
- **Verbose Logging**: Multiple verbosity levels for debugging
- **Batch Operations**: Start/stop multiple VMs with glob patterns
- **Configuration Validation**: Pydantic-based config validation

## Installation

### From Source

```bash
# Clone the repository
git clone https://github.com/yourusername/grovectl.git
cd grovectl

# Install in development mode
make install-dev

# Or install normally
pip install .
```

### Requirements

- Python 3.10+
- Remote hosts must have [tart](https://github.com/cirruslabs/tart) installed
- SSH access to remote hosts (key-based auth recommended)

## Quick Start

### 1. Initialize Configuration

```bash
grovectl config init
```

This creates a sample configuration at `~/.grovectl/config.yaml`.

### 2. Edit Configuration

```bash
grovectl config edit
```

Or manually edit `~/.grovectl/config.yaml`:

```yaml
hosts:
  - name: mac-builder-1
    hostname: 192.168.1.100
    username: admin
    ssh_key: ~/.ssh/id_rsa
    port: 22
  - name: mac-builder-2
    hostname: 192.168.1.101
    username: admin
    ssh_key: ~/.ssh/id_rsa

defaults:
  vm_cpu: 4
  vm_memory: 8192
  vm_disk: 50
  timeout: 300

logging:
  level: INFO
  file: ~/.grovectl/logs/grovectl.log
```

### 3. Test Connectivity

```bash
grovectl hosts test mac-builder-1
```

### 4. List VMs

```bash
grovectl vm list
grovectl vm list --host mac-builder-1
grovectl vm list --format json
```

## Usage

### Host Management

```bash
# Add a host
grovectl hosts add mac-builder-3 192.168.1.102 --username admin --ssh-key ~/.ssh/id_rsa

# List hosts
grovectl hosts list
grovectl hosts list --format json

# Test SSH connectivity
grovectl hosts test mac-builder-1

# Remove a host
grovectl hosts remove mac-builder-3
```

### VM Operations

```bash
# List VMs
grovectl vm list
grovectl vm list --host mac-builder-1 --pattern "test-*"

# Create a VM
grovectl vm create my-vm --host mac-builder-1 --image ghcr.io/cirruslabs/macos-sonoma-base:latest
grovectl vm create my-vm --host mac-builder-1 --image base-template --cpu 8 --memory 16384

# Start/stop VMs
grovectl vm start my-vm --host mac-builder-1
grovectl vm stop my-vm --host mac-builder-1
grovectl vm stop my-vm --host mac-builder-1 --force

# Get VM status and IP
grovectl vm status my-vm --host mac-builder-1
grovectl vm ip my-vm --host mac-builder-1

# Clone a VM
grovectl vm clone source-vm new-vm --host mac-builder-1

# Delete a VM
grovectl vm delete my-vm --host mac-builder-1 --yes
```

### Batch Operations

```bash
# Start all VMs matching a pattern
grovectl batch start --pattern "test-*"
grovectl batch start --pattern "builder-*" --host mac-builder-1

# Stop all VMs matching a pattern
grovectl batch stop --pattern "test-*"
grovectl batch stop --pattern "*" --force

# Preview which VMs would be affected
grovectl batch list --pattern "test-*"
```

### Configuration

```bash
# Show current configuration
grovectl config show
grovectl config show --format json

# Validate configuration
grovectl config validate

# Create default configuration
grovectl config init
grovectl config init --force  # Overwrite existing

# Open in editor
grovectl config edit
grovectl config edit --editor nano
```

### Global Options

```bash
# Verbose output
grovectl -v vm list          # INFO level
grovectl -vv vm list         # DEBUG level
grovectl -vvv vm list        # DEBUG + SSH debug

# Dry-run mode
grovectl --dry-run vm start my-vm --host mac-builder-1

# Debug mode (show tracebacks)
grovectl --debug vm list

# Custom config file
grovectl --config /path/to/config.yaml vm list

# Version
grovectl --version
```

## Output Formats

grovectl supports three output formats:

### Table (default)
```
┏━━━━━━━━━━━━┳━━━━━━━━━━━━━━━━┳━━━━━━━━━┳━━━━━┳━━━━━━━━━━┳━━━━━━━━━━━━━━━━┓
┃ Name       ┃ Host           ┃ Status  ┃ CPU ┃ Memory   ┃ IP Address     ┃
┡━━━━━━━━━━━━╇━━━━━━━━━━━━━━━━╇━━━━━━━━━╇━━━━━╇━━━━━━━━━━╇━━━━━━━━━━━━━━━━┩
│ vm-1       │ mac-builder-1  │ ● running│  4  │ 8 GB     │ 192.168.64.10  │
│ vm-2       │ mac-builder-1  │ ○ stopped│  2  │ 4 GB     │ -              │
└────────────┴────────────────┴─────────┴─────┴──────────┴────────────────┘
```

### JSON
```bash
grovectl vm list --format json
```

### YAML
```bash
grovectl vm list --format yaml
```

## Development

### Setup

```bash
# Install development dependencies
make install-dev

# Run tests
make test

# Run tests with coverage
make test-cov

# Format code
make format

# Lint code
make lint

# Type check
make type-check

# Run pre-commit hooks
make pre-commit
```

### Project Structure

```
grovectl/
├── src/grovectl/
│   ├── cli/                # CLI commands (Click)
│   │   ├── main.py         # Main CLI group
│   │   ├── hosts.py        # Host management commands
│   │   ├── vm.py           # VM operation commands
│   │   ├── batch.py        # Batch operation commands
│   │   └── config_cmd.py   # Config management commands
│   ├── core/               # Core business logic
│   │   ├── config.py       # Configuration management
│   │   ├── ssh.py          # SSH connection manager
│   │   ├── vm_manager.py   # VM operations
│   │   └── exceptions.py   # Custom exceptions
│   ├── models/             # Data models (Pydantic)
│   │   ├── host.py         # Host model
│   │   └── vm.py           # VM model
│   └── utils/              # Utilities
│       ├── logging.py      # Logging configuration
│       ├── output.py       # Rich output formatting
│       └── retry.py        # Retry with backoff
├── tests/                  # Test suite
├── pyproject.toml          # Project configuration
├── Makefile                # Development tasks
└── README.md               # This file
```

### Running Tests

```bash
# Run all tests
pytest

# Run specific test file
pytest tests/test_config.py

# Run with coverage
pytest --cov=grovectl --cov-report=html

# Run only unit tests (not integration)
pytest -m "not integration"
```

## Configuration Reference

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `GROVECTL_CONFIG` | Path to config file | `~/.grovectl/config.yaml` |
| `EDITOR` | Editor for `config edit` | `vim` |

### Configuration File

```yaml
# List of remote hosts
hosts:
  - name: string           # Unique identifier (required)
    hostname: string       # IP address or hostname (required)
    username: string       # SSH username (optional, defaults to current user)
    port: int              # SSH port (optional, default: 22)
    ssh_key: string        # Path to SSH key (optional)

# Default values for VM creation
defaults:
  vm_cpu: int              # Default CPU cores (default: 4)
  vm_memory: int           # Default memory in MB (default: 8192)
  vm_disk: int             # Default disk size in GB (default: 50)
  timeout: int             # Operation timeout in seconds (default: 300)

# Logging configuration
logging:
  level: string            # Log level: DEBUG, INFO, WARNING, ERROR (default: INFO)
  file: string             # Log file path (optional)
```

## Troubleshooting

### Connection Issues

1. **Test SSH connectivity manually:**
   ```bash
   ssh -i ~/.ssh/id_rsa admin@192.168.1.100
   ```

2. **Check SSH key permissions:**
   ```bash
   chmod 600 ~/.ssh/id_rsa
   ```

3. **Use verbose mode:**
   ```bash
   grovectl -vvv hosts test mac-builder-1
   ```

### Configuration Issues

1. **Validate configuration:**
   ```bash
   grovectl config validate
   ```

2. **Check config path:**
   ```bash
   grovectl config path
   ```

3. **Reset configuration:**
   ```bash
   grovectl config init --force
   ```

## License

MIT License - see LICENSE file for details.

## Contributing

1. Fork the repository
2. Create a feature branch
3. Make your changes
4. Run tests and linting
5. Submit a pull request

## Acknowledgments

- [tart](https://github.com/cirruslabs/tart) - macOS VM management
- [Click](https://click.palletsprojects.com/) - CLI framework
- [Rich](https://rich.readthedocs.io/) - Terminal formatting
- [Paramiko](https://www.paramiko.org/) - SSH client
- [Pydantic](https://docs.pydantic.dev/) - Data validation
