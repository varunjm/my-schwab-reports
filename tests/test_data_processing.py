"""Tests for data processing functionality."""

import pandas as pd
import pytest
from datetime import date

from schwab_reports import SchwabReportsProcessor


class TestDataProcessing:
    """Test data processing methods."""

    def test_convert_amount_to_numeric_dollar_signs(self):
        """Test conversion of dollar amounts with $ signs."""
        df = pd.DataFrame({"Amount": ["$1,234.56", "$500.00", "($75.00)"]})

        SchwabReportsProcessor.convert_amount_to_numeric(df, "Amount")

        expected = [1234.56, 500.00, -75.00]
        pd.testing.assert_series_equal(df["Amount"], pd.Series(expected, name="Amount"))

    def test_convert_amount_to_numeric_commas(self):
        """Test conversion of amounts with commas."""
        df = pd.DataFrame({"Amount": ["1,234.56", "15,000.00", "500"]})

        SchwabReportsProcessor.convert_amount_to_numeric(df, "Amount")

        expected = [1234.56, 15000.00, 500.0]
        pd.testing.assert_series_equal(df["Amount"], pd.Series(expected, name="Amount"))

    def test_convert_amount_to_numeric_parentheses(self):
        """Test conversion of negative amounts in parentheses."""
        df = pd.DataFrame({"Amount": ["(123.45)", "(1,000.00)", "500.00"]})

        SchwabReportsProcessor.convert_amount_to_numeric(df, "Amount")

        expected = [-123.45, -1000.00, 500.00]
        pd.testing.assert_series_equal(df["Amount"], pd.Series(expected, name="Amount"))

    def test_fixup_stock_splits_before_split_date(self, processor_with_test_data):
        """Test stock split adjustment for transactions before split date."""
        # Create test data with dates before split
        df = pd.DataFrame(
            {
                "Date": [
                    "05/01/2024",
                    "06/15/2024",
                ],  # First is before split (06/07/2024)
                "Quantity": [10, 20],
            }
        )

        processor_with_test_data.fixup_stock_splits(df, "Date")

        # First quantity should be multiplied by 10, second should remain unchanged
        assert df.loc[0, "Quantity"] == 100  # 10 * 10
        assert df.loc[1, "Quantity"] == 20  # No change

    def test_fixup_stock_splits_after_split_date(self, processor_with_test_data):
        """Test stock split adjustment for transactions after split date."""
        df = pd.DataFrame(
            {
                "Date": ["07/01/2024", "08/15/2024"],  # Both after split (06/07/2024)
                "Quantity": [10, 20],
            }
        )

        processor_with_test_data.fixup_stock_splits(df, "Date")

        # No quantities should change
        assert df.loc[0, "Quantity"] == 10
        assert df.loc[1, "Quantity"] == 20

    def test_fixup_stock_splits_missing_quantity(self, processor_with_test_data):
        """Test stock split adjustment with missing quantity values."""
        df = pd.DataFrame(
            {"Date": ["05/01/2024", "06/15/2024"], "Quantity": [None, 20]}
        )

        processor_with_test_data.fixup_stock_splits(df, "Date")

        # None should remain None, valid quantity should be processed
        assert pd.isna(df.loc[0, "Quantity"])
        assert df.loc[1, "Quantity"] == 20


class TestDataInitialization:
    """Test data loading and initialization."""

    def test_init_data_loads_all_files(self, processor_with_test_data):
        """Test that init_data loads all available CSV files."""
        processor_with_test_data.init_data()

        # All DataFrames should be loaded
        assert processor_with_test_data.eac_df is not None
        assert processor_with_test_data.individual_df is not None
        assert processor_with_test_data.individual_sales_df is not None

        # Check data is loaded correctly
        assert len(processor_with_test_data.eac_df) > 0
        assert len(processor_with_test_data.individual_df) > 0
        assert len(processor_with_test_data.individual_sales_df) > 0

    def test_init_data_handles_missing_files(
        self, config_file, test_directories, monkeypatch
    ):
        """Test behavior when some CSV files are missing."""
        monkeypatch.chdir(test_directories["tmp_path"])
        processor = SchwabReportsProcessor(config_file)

        # No CSV files exist in this case
        processor.init_data()

        # All DataFrames should remain None
        assert processor.eac_df is None
        assert processor.individual_df is None
        assert processor.individual_sales_df is None

    def test_normalize_eac_df(self, processor_with_test_data):
        """Test EAC DataFrame normalization."""
        processor_with_test_data.init_data()

        # Check that numeric columns were processed
        eac_df = processor_with_test_data.eac_df

        # Amount column should be numeric
        assert pd.api.types.is_numeric_dtype(eac_df["Amount"])

        # Check that lot sale entries were created properly
        lot_sales = eac_df[eac_df["Action"] == "Lot Sale"]
        assert len(lot_sales) > 0


class TestTablePopulation:
    """Test individual table population methods."""

    def test_populate_dividend_table(self, processor_with_test_data):
        """Test dividend table population."""
        processor_with_test_data.init_data()
        processor_with_test_data.populate_dividend_table()

        assert processor_with_test_data.dividend_table is not None

        # Check expected columns
        expected_columns = ["Date", "Action", "Symbol", "Amount"]
        assert list(processor_with_test_data.dividend_table.columns) == expected_columns

        # Should have dividend transactions
        dividend_actions = ["Reinvest Dividend", "Qual Div Reinvest", "Dividend"]
        actions = processor_with_test_data.dividend_table["Action"].tolist()
        assert any(action in dividend_actions for action in actions)

    def test_populate_interest_table(self, processor_with_test_data):
        """Test interest table population."""
        processor_with_test_data.init_data()
        processor_with_test_data.populate_interest_table()

        assert processor_with_test_data.interest_table is not None

        # Check expected columns
        expected_columns = ["Date", "Action", "Amount"]
        assert list(processor_with_test_data.interest_table.columns) == expected_columns

        # Should have interest transactions
        actions = processor_with_test_data.interest_table["Action"].tolist()
        assert "Credit Interest" in actions

    def test_populate_tax_deducted_table(self, processor_with_test_data):
        """Test tax deducted table population."""
        processor_with_test_data.init_data()
        processor_with_test_data.populate_tax_deducted_table()

        assert processor_with_test_data.tax_deducted_table is not None

        # Check expected columns
        expected_columns = ["Date", "Symbol", "Amount"]
        assert (
            list(processor_with_test_data.tax_deducted_table.columns)
            == expected_columns
        )

    def test_populate_sale_table(self, processor_with_test_data):
        """Test sale table population."""
        processor_with_test_data.init_data()
        processor_with_test_data.populate_sale_table()

        assert processor_with_test_data.sale_table is not None

        # Check expected columns
        expected_columns = [
            "Date",
            "Symbol",
            "Quantity",
            "Amount",
            "Cost Basis",
            "PurchaseDate",
        ]
        assert list(processor_with_test_data.sale_table.columns) == expected_columns

    def test_cleanup_all_tables(self, processor_with_test_data):
        """Test table cleanup functionality."""
        processor_with_test_data.init_data()
        processor_with_test_data.populate_dividend_table()
        processor_with_test_data.populate_interest_table()
        processor_with_test_data.populate_tax_deducted_table()
        processor_with_test_data.populate_sale_table()

        processor_with_test_data.cleanup_all_tables()

        # All amount columns should be numeric
        assert pd.api.types.is_numeric_dtype(
            processor_with_test_data.dividend_table["Amount"]
        )
        assert pd.api.types.is_numeric_dtype(
            processor_with_test_data.interest_table["Amount"]
        )
        assert pd.api.types.is_numeric_dtype(
            processor_with_test_data.tax_deducted_table["Amount"]
        )
        assert pd.api.types.is_numeric_dtype(
            processor_with_test_data.sale_table["Amount"]
        )
        assert pd.api.types.is_numeric_dtype(
            processor_with_test_data.sale_table["Cost Basis"]
        )
