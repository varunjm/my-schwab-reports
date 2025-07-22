"""Shared test fixtures for Schwab reports tests."""

import os
import tempfile
from datetime import date
from typing import Dict, Any
import pandas as pd
import pytest
import yaml

from schwab_reports import SchwabReportsProcessor


@pytest.fixture
def sample_config() -> Dict[str, Any]:
    """Sample configuration for testing."""
    return {
        "year": 2024,
        "stock_splits": [{"date": "2024-06-07", "ratio": 10}],
        "directories": {"transactions": "test_transactions", "reports": "test_reports"},
        "file_patterns": {
            "eac_transactions": "EAC_transactions_{year}.csv",
            "individual_transactions": "Individual_transactions_{year}.csv",
            "individual_realized_gains": "Individual_realized_gains_{year}.csv",
        },
    }


@pytest.fixture
def config_file(sample_config, tmp_path):
    """Create a temporary config file for testing."""
    config_path = tmp_path / "test_config.yaml"
    with open(config_path, "w") as f:
        yaml.dump(sample_config, f)
    return str(config_path)


@pytest.fixture
def sample_eac_data() -> pd.DataFrame:
    """Sample EAC transaction data for testing."""
    return pd.DataFrame(
        {
            "Date": ["06/15/2024", "05/01/2024", "", ""],
            "Action": ["Sale", "Dividend", "Lot Sale", "Tax Withholding"],
            "Symbol": ["AAPL", "AAPL", "AAPL", "AAPL"],
            "Quantity": [100, None, 50, None],
            "Amount": ["$15,000.00", "$500.00", "$7,500.00", "($75.00)"],
            "Shares": [None, None, 50, None],
            "Type": [None, None, "RS", None],
            "VestFairMarketValue": [None, None, "$100.00", None],
            "PurchaseFairMarketValue": [None, None, "$80.00", None],
            "VestDate": [None, None, "01/01/2024", None],
            "PurchaseDate": [None, None, "01/01/2023", None],
        }
    )


@pytest.fixture
def sample_individual_data() -> pd.DataFrame:
    """Sample Individual account transaction data for testing."""
    return pd.DataFrame(
        {
            "Date": ["06/15/2024", "05/01/2024", "04/15/2024"],
            "Action": ["Reinvest Dividend", "Credit Interest", "NRA Tax Adj"],
            "Symbol": ["AAPL", "", "AAPL"],
            "Amount": ["$250.00", "$15.50", "($37.50)"],
            "Description": [
                "Dividend reinvestment",
                "Interest payment",
                "Tax adjustment",
            ],
        }
    )


@pytest.fixture
def sample_individual_sales_data() -> pd.DataFrame:
    """Sample Individual account sales data for testing."""
    return pd.DataFrame(
        {
            "Closed Date": ["06/20/2024", "05/15/2024"],
            "Symbol": ["AAPL", "MSFT"],
            "Quantity": [25, 50],
            "Proceeds": ["$4,250.00", "$18,750.00"],
            "Cost Basis (CB)": ["$3,750.00", "$15,000.00"],
            "Opened Date": ["01/15/2024", "02/01/2024"],
        }
    )


@pytest.fixture
def test_directories(tmp_path, sample_config):
    """Create temporary test directories with sample CSV files."""
    # Create directories
    transactions_dir = tmp_path / sample_config["directories"]["transactions"]
    reports_dir = tmp_path / sample_config["directories"]["reports"]
    transactions_dir.mkdir()
    reports_dir.mkdir()

    return {
        "transactions": str(transactions_dir),
        "reports": str(reports_dir),
        "tmp_path": str(tmp_path),
    }


@pytest.fixture
def sample_csv_files(
    test_directories,
    sample_eac_data,
    sample_individual_data,
    sample_individual_sales_data,
):
    """Create sample CSV files for testing."""
    transactions_dir = test_directories["transactions"]

    # Create EAC transactions file
    eac_file = os.path.join(transactions_dir, "EAC_transactions_2024.csv")
    sample_eac_data.to_csv(eac_file, index=False)

    # Create Individual transactions file
    individual_file = os.path.join(transactions_dir, "Individual_transactions_2024.csv")
    sample_individual_data.to_csv(individual_file, index=False)

    # Create Individual sales file
    sales_file = os.path.join(transactions_dir, "Individual_realized_gains_2024.csv")
    # Add header row and then data (mimicking the skiprows=1 behavior)
    with open(sales_file, "w") as f:
        f.write("Header row to skip\n")
        sample_individual_sales_data.to_csv(f, index=False)

    return {
        "eac_file": eac_file,
        "individual_file": individual_file,
        "sales_file": sales_file,
    }


@pytest.fixture
def processor_with_test_data(
    config_file, test_directories, sample_csv_files, monkeypatch
):
    """Create a SchwabReportsProcessor instance with test data."""
    # Update the config to use test directories
    with open(config_file, "r") as f:
        config = yaml.safe_load(f)

    config["directories"] = {
        "transactions": test_directories["transactions"],
        "reports": test_directories["reports"],
    }

    # Write updated config
    with open(config_file, "w") as f:
        yaml.dump(config, f)

    # Change to temp directory so file paths work correctly
    monkeypatch.chdir(test_directories["tmp_path"])

    # Create processor
    processor = SchwabReportsProcessor(config_file)
    return processor
