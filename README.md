# my-schwab-reports

A Python script to process Charles Schwab CSV exports and generate consolidated tax reports for Indian residents with US investments.

## What does this do?

This script processes CSV exports from Charles Schwab accounts (Employee Stock Award Center/EAC and Individual trading accounts) and generates consolidated reports required for Indian tax filing:

- **Dividend report** - All dividend earnings with TDS details
- **Interest earned report** - Interest from cash holdings and savings
- **Sale report** - Stock sales with cost basis and gains/losses
- **TDS report** - Tax Deducted at Source from dividends and interest

The generated reports help streamline the process of filing taxes in India for income earned from US investments.

## Prerequisites

- Python 3.12+ (tested on Python 3.12)
- Access to Charles Schwab online account
- Basic familiarity with command line

**Tested on:**
- Ubuntu 24.04
- Python 3.12
- Pip 24.0

## Setup

### 1. Clone and prepare environment
```bash
git clone https://github.com/varunjm/my-schwab-reports.git
cd my-schwab-reports
mkdir -p transactions reports
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Configure the application

The application uses a `config.yaml` file for configuration. The default configuration is set up for 2024 processing, but you can modify it as needed:

```yaml
# Processing Year
year: 2024

# Stock Split Information
stock_splits:
  - date: "2024-06-07"
    ratio: 10

# File Paths and Patterns
directories:
  transactions: "transactions"
  reports: "reports"

# File naming patterns (use {year} placeholder)
file_patterns:
  eac_transactions: "EAC_transactions_{year}.csv"
  individual_transactions: "Individual_transactions_{year}.csv"
  individual_realized_gains: "Individual_realized_gains_{year}.csv"
```

**To process a different year:**
- Update `year: 2025` in `config.yaml`
- The script will automatically look for files with the new year

**To add stock splits:**
- Add new entries to the `stock_splits` list with the split date and ratio
- The script will automatically adjust quantities for transactions before the split date

### 3. Download Schwab reports

**Important:** File names must follow the pattern specified in `config.yaml`. By default:

#### For Employee Stock Award Center (EAC) account:
1. Go to **Transaction History (EAC)**
2. Select your desired date range (typically full financial year)
3. Filter by transaction types: **Share sales, Cash transactions**
4. Click **Export**
5. Save as: `EAC_transactions_YYYY.csv` (e.g., `EAC_transactions_2024.csv`)

#### For Individual trading account (skip if you don't have one):
1. Go to **Transaction History (Individual)**
2. Select the same date range
3. Filter by transaction types: **Dividends, Interest, Misc, Taxes**
4. Click **Export**
5. Save as: `Individual_transactions_YYYY.csv`
6. Go to **Realized Gain/Loss (Individual)**
7. Select the same date range
8. Click **Export** → **Export Details Only**
9. Save as: `Individual_realized_gains_YYYY.csv`

### 4. Place files in transactions directory

Place all downloaded CSV files in the `transactions/` directory.

### 5. Run the script

```bash
python schwab_reports.py
```

The script will:
1. Load configuration from `config.yaml`
2. Process all CSV files for the specified year
3. Apply stock split adjustments automatically
4. Generate consolidated reports in the `reports/` directory

## Configuration Options

### Changing Processing Year
```yaml
year: 2025  # Process 2025 transactions
```

### Custom File Patterns
```yaml
file_patterns:
  eac_transactions: "EAC_export_{year}.csv"
  individual_transactions: "Individual_export_{year}.csv"
  individual_realized_gains: "Gains_export_{year}.csv"
```

### Custom Directory Structure
```yaml
directories:
  transactions: "input_files"
  reports: "output_reports"
```

## Output Files

The script generates the following CSV files in the `reports/` directory:
- `dividend_transactions.csv` - All dividend transactions with dates and amounts
- `interest_transactions.csv` - All interest earnings
- `tax_deducted_transactions.csv` - All tax withholdings (TDS)
- `sale_transactions.csv` - All stock sales with cost basis and gains/losses

## Features

✅ **Configurable processing year** - Easy to switch between tax years  
✅ **Automatic stock split handling** - Configurable split dates and ratios  
✅ **Flexible file naming** - Customize input file patterns  
✅ **Multiple account support** - EAC and Individual accounts  
✅ **Type-safe code** - Full type hints for better maintainability  
✅ **Error handling** - Graceful handling of missing files and data issues  
✅ **Comprehensive test suite** - Unit and integration tests with high coverage  
✅ **Code quality tools** - Pre-commit hooks, linting, and type checking  

## Development and Testing

### Running Tests

To run the test suite, first install development dependencies:

```bash
pip install -r requirements-dev.txt
```

Run all tests:
```bash
pytest
```

**Quick test runner script:**
```bash
# Run all tests
python run_tests.py

# Run with coverage
python run_tests.py --test-type coverage

# Run with code quality checks
python run_tests.py --quality

# Install deps and run everything
python run_tests.py --install-deps --quality
```

Run tests with coverage report:
```bash
pytest --cov=schwab_reports --cov-report=html
```

Run specific test files:
```bash
pytest tests/test_config.py
pytest tests/test_data_processing.py
pytest tests/test_integration.py
```

### Code Quality

Install pre-commit hooks for automatic code quality checks:

```bash
pre-commit install
```

Run code quality checks manually:
```bash
# Format code
black schwab_reports.py

# Sort imports
isort schwab_reports.py

# Lint code
ruff check schwab_reports.py

# Type checking
mypy schwab_reports.py

# Security scan
bandit -r schwab_reports.py
```

### Test Coverage

The test suite includes:
- **Configuration tests**: Loading and validation of config files
- **Data processing tests**: Stock splits, amount conversion, data loading
- **Integration tests**: Complete pipeline execution and file output
- **Edge case tests**: Error handling and boundary conditions

Current test coverage: **80%+** (enforced by pytest configuration)

## Future Enhancements
- Generate reports in exact format needed for Indian Income Tax filing
- Add USD-INR conversion with historical exchange rates