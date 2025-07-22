"""Integration tests for complete processing pipeline."""

import os
import pandas as pd
import pytest

from schwab_reports import SchwabReportsProcessor


class TestIntegration:
    """Test complete processing pipeline."""

    def test_process_all_pipeline(self, processor_with_test_data):
        """Test the complete processing pipeline."""
        # Run the complete pipeline
        processor_with_test_data.process_all()

        # Check that all tables were created
        assert processor_with_test_data.dividend_table is not None
        assert processor_with_test_data.interest_table is not None
        assert processor_with_test_data.tax_deducted_table is not None
        assert processor_with_test_data.sale_table is not None

        # Check that all tables have data
        assert len(processor_with_test_data.dividend_table) > 0
        assert len(processor_with_test_data.interest_table) > 0
        assert len(processor_with_test_data.tax_deducted_table) > 0
        assert len(processor_with_test_data.sale_table) > 0

    def test_save_reports_to_csv(self, processor_with_test_data):
        """Test saving reports to CSV files."""
        # Process data first
        processor_with_test_data.init_data()
        processor_with_test_data.populate_dividend_table()
        processor_with_test_data.populate_interest_table()
        processor_with_test_data.populate_tax_deducted_table()
        processor_with_test_data.populate_sale_table()
        processor_with_test_data.cleanup_all_tables()

        # Save reports
        processor_with_test_data.save_reports_to_csv()

        # Check that files were created
        reports_dir = processor_with_test_data.config["directories"]["reports"]

        expected_files = [
            "dividend_transactions.csv",
            "interest_transactions.csv",
            "tax_deducted_transactions.csv",
            "sale_transactions.csv",
        ]

        for filename in expected_files:
            filepath = os.path.join(reports_dir, filename)
            assert os.path.exists(filepath), f"File {filename} was not created"

            # Check that files are not empty
            df = pd.read_csv(filepath)
            assert len(df) > 0, f"File {filename} is empty"

    def test_output_file_structure(self, processor_with_test_data):
        """Test that output files have the correct structure."""
        processor_with_test_data.process_all()

        reports_dir = processor_with_test_data.config["directories"]["reports"]

        # Test dividend transactions CSV
        dividend_df = pd.read_csv(
            os.path.join(reports_dir, "dividend_transactions.csv")
        )
        expected_dividend_columns = ["Date", "Action", "Symbol", "Amount"]
        assert list(dividend_df.columns) == expected_dividend_columns

        # Test interest transactions CSV
        interest_df = pd.read_csv(
            os.path.join(reports_dir, "interest_transactions.csv")
        )
        expected_interest_columns = ["Date", "Action", "Amount"]
        assert list(interest_df.columns) == expected_interest_columns

        # Test tax deducted transactions CSV
        tax_df = pd.read_csv(os.path.join(reports_dir, "tax_deducted_transactions.csv"))
        expected_tax_columns = ["Date", "Symbol", "Amount"]
        assert list(tax_df.columns) == expected_tax_columns

        # Test sale transactions CSV
        sale_df = pd.read_csv(os.path.join(reports_dir, "sale_transactions.csv"))
        expected_sale_columns = [
            "Date",
            "Symbol",
            "Quantity",
            "Amount",
            "Cost Basis",
            "PurchaseDate",
        ]
        assert list(sale_df.columns) == expected_sale_columns

    def test_date_formatting_in_output(self, processor_with_test_data):
        """Test that dates are properly formatted in output files."""
        processor_with_test_data.process_all()

        reports_dir = processor_with_test_data.config["directories"]["reports"]

        # Check dividend transactions for proper date format
        dividend_df = pd.read_csv(
            os.path.join(reports_dir, "dividend_transactions.csv")
        )

        # Dates should be in YYYY/MM/DD format
        for date_str in dividend_df["Date"]:
            # Should be able to parse as datetime
            pd.to_datetime(date_str, format="%Y/%m/%d")

    def test_amount_values_are_numeric(self, processor_with_test_data):
        """Test that amount values in output files are properly numeric."""
        processor_with_test_data.process_all()

        reports_dir = processor_with_test_data.config["directories"]["reports"]

        # Check all files have numeric amounts
        files_and_columns = [
            ("dividend_transactions.csv", "Amount"),
            ("interest_transactions.csv", "Amount"),
            ("tax_deducted_transactions.csv", "Amount"),
            ("sale_transactions.csv", "Amount"),
            ("sale_transactions.csv", "Cost Basis"),
        ]

        for filename, column in files_and_columns:
            df = pd.read_csv(os.path.join(reports_dir, filename))

            # All values should be numeric (can be parsed as float)
            for value in df[column]:
                assert isinstance(float(value), float), (
                    f"Non-numeric value in {filename}[{column}]: {value}"
                )


class TestEdgeCases:
    """Test edge cases and error conditions."""

    def test_process_with_no_data_files(
        self, config_file, test_directories, monkeypatch
    ):
        """Test processing when no data files are available."""
        monkeypatch.chdir(test_directories["tmp_path"])
        processor = SchwabReportsProcessor(config_file)

        # Should not raise errors, but tables should be empty or None
        processor.process_all()

        # Check that empty DataFrames were created where needed
        assert processor.dividend_table is not None
        assert processor.interest_table is not None

    def test_stock_split_edge_cases(self, processor_with_test_data):
        """Test stock split functionality with edge cases."""
        # Test with dates exactly on split date
        df = pd.DataFrame(
            {
                "Date": ["06/07/2024"],  # Exactly on split date
                "Quantity": [10],
            }
        )

        processor_with_test_data.fixup_stock_splits(df, "Date")

        # Date exactly on split should not be adjusted (< comparison)
        assert df.loc[0, "Quantity"] == 10

    def test_empty_dataframe_processing(self, processor_with_test_data):
        """Test processing of empty DataFrames."""
        empty_df = pd.DataFrame()

        # Should not raise errors
        processor_with_test_data.fixup_stock_splits(empty_df, "Date")

        # DataFrame should remain empty
        assert len(empty_df) == 0


class TestMainFunction:
    """Test the main entry point."""

    def test_main_function(
        self, monkeypatch, processor_with_test_data, test_directories
    ):
        """Test the main function execution."""
        # Import main function
        from schwab_reports import main

        # Change to test directory and ensure config exists
        monkeypatch.chdir(test_directories["tmp_path"])

        # Create a config.yaml in the working directory
        config_data = processor_with_test_data.config
        import yaml

        with open("config.yaml", "w") as f:
            yaml.dump(config_data, f)

        # Should run without errors
        main()

        # Check that output files were created
        reports_dir = config_data["directories"]["reports"]
        assert os.path.exists(os.path.join(reports_dir, "dividend_transactions.csv"))
        assert os.path.exists(os.path.join(reports_dir, "interest_transactions.csv"))
        assert os.path.exists(
            os.path.join(reports_dir, "tax_deducted_transactions.csv")
        )
        assert os.path.exists(os.path.join(reports_dir, "sale_transactions.csv"))
