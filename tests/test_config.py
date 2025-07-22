"""Tests for configuration loading and basic functionality."""

import os
import pytest
import yaml
from datetime import date

from schwab_reports import SchwabReportsProcessor


class TestConfiguration:
    """Test configuration loading and validation."""

    def test_load_config_success(self, config_file):
        """Test successful configuration loading."""
        processor = SchwabReportsProcessor(config_file)

        assert processor.config["year"] == 2024
        assert len(processor.config["stock_splits"]) == 1
        assert processor.config["stock_splits"][0]["ratio"] == 10

    def test_load_config_file_not_found(self, tmp_path):
        """Test behavior when config file doesn't exist."""
        non_existent_file = str(tmp_path / "non_existent.yaml")

        with pytest.raises(FileNotFoundError):
            SchwabReportsProcessor(non_existent_file)

    def test_load_config_invalid_yaml(self, tmp_path):
        """Test behavior with invalid YAML file."""
        invalid_config = tmp_path / "invalid.yaml"
        with open(invalid_config, "w") as f:
            f.write("invalid: yaml: content: [")

        with pytest.raises(ValueError):
            SchwabReportsProcessor(str(invalid_config))

    def test_get_stock_split_info(self, config_file):
        """Test stock split information extraction."""
        processor = SchwabReportsProcessor(config_file)
        split_date, split_ratio = processor.get_stock_split_info()

        assert isinstance(split_date, date)
        assert split_date == date(2024, 6, 7)
        assert split_ratio == 10

    def test_get_file_path(self, config_file):
        """Test file path generation."""
        processor = SchwabReportsProcessor(config_file)

        eac_path = processor.get_file_path("eac_transactions")
        expected = os.path.join("test_transactions", "EAC_transactions_2024.csv")
        assert eac_path == expected

        individual_path = processor.get_file_path("individual_transactions")
        expected = os.path.join("test_transactions", "Individual_transactions_2024.csv")
        assert individual_path == expected

    def test_get_output_file_path(self, config_file):
        """Test output file path generation."""
        processor = SchwabReportsProcessor(config_file)

        output_path = processor.get_output_file_path("dividend_transactions.csv")
        expected = os.path.join("test_reports", "dividend_transactions.csv")
        assert output_path == expected


class TestInitialization:
    """Test processor initialization."""

    def test_initialization_with_default_config(
        self, monkeypatch, sample_config, tmp_path
    ):
        """Test initialization with default config file."""
        # Create default config file in current directory
        monkeypatch.chdir(tmp_path)
        with open("config.yaml", "w") as f:
            yaml.dump(sample_config, f)

        processor = SchwabReportsProcessor()
        assert processor.config["year"] == 2024

    def test_initialization_sets_dataframes_to_none(self, config_file):
        """Test that all DataFrames are initialized to None."""
        processor = SchwabReportsProcessor(config_file)

        assert processor.eac_df is None
        assert processor.individual_df is None
        assert processor.individual_sales_df is None
        assert processor.dividend_table is None
        assert processor.interest_table is None
        assert processor.tax_deducted_table is None
        assert processor.sale_table is None
