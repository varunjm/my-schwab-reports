import pandas as pd
import os
import yaml
from typing import Optional, List, Dict, Any
from datetime import date


class SchwabReportsProcessor:
    """
    A class to process Schwab transaction reports and generate consolidated CSV files.

    This class handles loading transaction data from various Schwab report formats,
    applies stock split adjustments, and generates consolidated reports for
    dividends, interest, tax deductions, and sales.
    """

    def __init__(self, config_path: str = "config.yaml"):
        """
        Initialize the processor with configuration.

        Args:
            config_path: Path to the configuration YAML file
        """
        # Configuration
        self.config: Dict[str, Any] = {}

        # DataFrames for storing transaction data
        self.eac_df: Optional[pd.DataFrame] = None
        self.individual_df: Optional[pd.DataFrame] = None
        self.individual_sales_df: Optional[pd.DataFrame] = None

        # Processed tables for reports
        self.dividend_table: Optional[pd.DataFrame] = None
        self.interest_table: Optional[pd.DataFrame] = None
        self.tax_deducted_table: Optional[pd.DataFrame] = None
        self.sale_table: Optional[pd.DataFrame] = None

        # Load configuration on initialization
        self.load_config(config_path)

    def load_config(self, config_path: str) -> None:
        """
        Load configuration from YAML file.

        Args:
            config_path: Path to the configuration file

        Raises:
            FileNotFoundError: If configuration file is not found
            ValueError: If configuration file cannot be parsed
        """
        try:
            with open(config_path, "r") as file:
                self.config = yaml.safe_load(file)
        except FileNotFoundError:
            raise FileNotFoundError(f"Configuration file not found: {config_path}")
        except yaml.YAMLError as e:
            raise ValueError(f"Error parsing configuration file: {e}")

    def get_stock_split_info(self) -> tuple[date, int]:
        """Get stock split date and ratio from configuration."""
        stock_split = self.config["stock_splits"][0]  # Use first stock split
        split_date = pd.to_datetime(stock_split["date"], format="%Y-%m-%d").date()
        split_ratio = stock_split["ratio"]
        return split_date, split_ratio

    def get_file_path(self, file_type: str) -> str:
        """
        Generate file path based on configuration and current year.

        Args:
            file_type: Type of file (eac_transactions, individual_transactions, etc.)

        Returns:
            Full file path
        """
        pattern = self.config["file_patterns"][file_type]
        filename = pattern.format(year=self.config["year"])
        return os.path.join(self.config["directories"]["transactions"], filename)

    def get_output_file_path(self, filename: str) -> str:
        """
        Generate output file path in the reports directory.

        Args:
            filename: Name of the output file

        Returns:
            Full file path in the reports directory
        """
        return os.path.join(self.config["directories"]["reports"], filename)

    def fixup_stock_splits(self, df: pd.DataFrame, date_column: str) -> None:
        """
        Apply stock split adjustments to quantity data based on transaction dates.

        For transactions before the stock split date, multiply quantities by the split ratio.

        Args:
            df: DataFrame containing transaction data
            date_column: Name of the column containing transaction dates
        """
        stock_split_date, stock_split_ratio = self.get_stock_split_info()

        # if a sale date is before the stock split date, then multiply quantity by split ratio
        for index, row in df.iterrows():
            row_date = pd.to_datetime(row[date_column], format="%m/%d/%Y").date()
            if row_date < stock_split_date:
                # if row has 'Quantity' column, multiply it by split ratio
                if "Quantity" in row and row["Quantity"] is not None:
                    df.at[index, "Quantity"] = (
                        df.at[index, "Quantity"] * stock_split_ratio
                    )

    def normalize_eac_df(self) -> None:
        """
        Normalize and process EAC DataFrame with proper sale lot handling.

        Converts amount columns to numeric and processes sale transactions to create
        proper lot sale entries with calculated cost basis and purchase dates.
        """
        stock_split_date, stock_split_ratio = self.get_stock_split_info()

        for column in [
            "Amount",
            "Shares",
            "Quantity",
            "PurchaseFairMarketValue",
            "VestFairMarketValue",
        ]:
            self.convert_amount_to_numeric(self.eac_df, column)

        # Gather the sale date and sale price for each sale and apply it to the lot sale rows
        # use only the lot sale rows in the final sale report from EAC
        for index, row in self.eac_df.iterrows():
            if row["Action"] == "Sale":
                row_date = pd.to_datetime(row["Date"], format="%m/%d/%Y").date()
                row_symbol = row["Symbol"]
                row_sale_fmv = row["Amount"] / row["Quantity"]
            elif pd.isna(row["Date"]) or row["Date"] == "":
                self.eac_df.at[index, "Action"] = "Lot Sale"
                self.eac_df.at[index, "Date"] = row_date
                self.eac_df.at[index, "Symbol"] = row_symbol
                self.eac_df.at[index, "Amount"] = row_sale_fmv * row["Shares"]
                self.eac_df.at[index, "Quantity"] = row["Shares"]

                fmv = (
                    row["VestFairMarketValue"]
                    if row["Type"] == "RS"
                    else row["PurchaseFairMarketValue"]
                )
                cb = fmv * row["Shares"]
                self.eac_df.at[index, "Cost Basis"] = (
                    cb * stock_split_ratio if row_date < stock_split_date else cb
                )
                self.eac_df.at[index, "PurchaseDate"] = (
                    row["VestDate"] if row["Type"] == "RS" else row["PurchaseDate"]
                )

    def init_data(self) -> None:
        """
        Initialize and load data from CSV files into DataFrames.

        Loads transaction data from CSV files based on configuration patterns.
        Applies necessary preprocessing including stock split adjustments.
        """
        # Load Individual transactions
        individual_transactions_path = self.get_file_path("individual_transactions")
        if os.path.exists(individual_transactions_path):
            df = pd.read_csv(individual_transactions_path)
            self.individual_df = df[df["Action"] != "Reinvest Shares"].copy()
            self.fixup_stock_splits(self.individual_df, "Date")

        # Load Individual realized gains
        individual_realized_gains_path = self.get_file_path("individual_realized_gains")
        if os.path.exists(individual_realized_gains_path):
            self.individual_sales_df = pd.read_csv(
                individual_realized_gains_path, skiprows=1
            )
            self.fixup_stock_splits(self.individual_sales_df, "Closed Date")

        # Load EAC transactions
        eac_transactions_path = self.get_file_path("eac_transactions")
        if os.path.exists(eac_transactions_path):
            self.eac_df = pd.read_csv(eac_transactions_path)
            self.normalize_eac_df()
            self.fixup_stock_splits(self.eac_df, "Date")

    def populate_dividend_table(self) -> None:
        """
        Process and consolidate dividend transactions from all sources.

        Combines dividend data from both individual and EAC accounts,
        sorts by date, and stores in the dividend_table.
        """
        dividend_actions: List[str] = ["Reinvest Dividend", "Qual Div Reinvest"]

        if self.individual_df is not None:
            self.dividend_table = self.individual_df[
                self.individual_df["Action"].isin(dividend_actions)
            ].copy()
        else:
            self.dividend_table = pd.DataFrame(
                columns=["Date", "Action", "Symbol", "Amount"]
            )

        self.dividend_table = self.dividend_table[
            ["Date", "Action", "Symbol", "Amount"]
        ].copy()

        if self.eac_df is not None:
            eac_dividend_table = self.eac_df[self.eac_df["Action"] == "Dividend"].copy()
            eac_dividend_table = eac_dividend_table[
                ["Date", "Action", "Symbol", "Amount"]
            ].copy()
            # Only concatenate if eac_dividend_table is not empty
            if not eac_dividend_table.empty:
                self.dividend_table = pd.concat(
                    [self.dividend_table, eac_dividend_table], ignore_index=True
                )

        # convert the data type of the "Date" column to datetime
        self.dividend_table["Date"] = pd.to_datetime(
            self.dividend_table["Date"], format="%m/%d/%Y"
        )
        self.dividend_table = self.dividend_table.sort_values(by="Date")

    def populate_interest_table(self) -> None:
        """
        Process interest transactions from individual account data.

        Extracts credit interest transactions, sorts by date, and stores
        in the interest_table.
        """
        if self.individual_df is not None:
            self.interest_table = self.individual_df[
                self.individual_df["Action"] == "Credit Interest"
            ].copy()
        else:
            self.interest_table = pd.DataFrame(columns=["Date", "Action", "Amount"])
        self.interest_table = self.interest_table[["Date", "Action", "Amount"]].copy()
        self.interest_table["Date"] = pd.to_datetime(
            self.interest_table["Date"], format="%m/%d/%Y"
        )
        self.interest_table = self.interest_table.sort_values(by="Date")

    def populate_tax_deducted_table(self) -> None:
        """
        Process tax deduction transactions from all sources.

        Combines tax withholding data from both individual and EAC accounts,
        sorts by date, and stores in the tax_deducted_table.
        """
        tax_deducted_actions: List[str] = ["NRA Tax Adj"]

        # Initialize empty table first
        self.tax_deducted_table = None

        if self.individual_df is not None:
            self.tax_deducted_table = self.individual_df[
                self.individual_df["Action"].isin(tax_deducted_actions)
            ].copy()
            self.tax_deducted_table = self.tax_deducted_table[
                ["Date", "Symbol", "Amount"]
            ].copy()

        if self.eac_df is not None:
            eac_tax_table = self.eac_df[
                self.eac_df["Action"] == "Tax Withholding"
            ].copy()
            # Keep only these columns in eac_tax_table: Date, Symbol, Amount
            eac_tax_table = eac_tax_table[["Date", "Symbol", "Amount"]].copy()
            # Only concatenate if eac_tax_table is not empty
            if not eac_tax_table.empty:
                self.tax_deducted_table = (
                    eac_tax_table
                    if self.tax_deducted_table is None
                    else pd.concat(
                        [self.tax_deducted_table, eac_tax_table], ignore_index=True
                    )
                )

        # If still None, create empty DataFrame
        if self.tax_deducted_table is None:
            self.tax_deducted_table = pd.DataFrame(columns=["Date", "Symbol", "Amount"])

        # Only process if not empty
        if not self.tax_deducted_table.empty:
            self.tax_deducted_table["Date"] = pd.to_datetime(
                self.tax_deducted_table["Date"], format="%m/%d/%Y"
            )
            self.tax_deducted_table = self.tax_deducted_table.sort_values(by="Date")

    def populate_eac_sale_table(self) -> None:
        """
        Process EAC sale transactions and add to sale table.

        Extracts lot sale data from EAC transactions with proper date conversion
        and adds to the sale_table.
        """
        if self.eac_df is not None:
            eac_sales = self.eac_df[self.eac_df["Action"] == "Lot Sale"].copy()
            eac_sales = eac_sales[
                ["Date", "Symbol", "Quantity", "Amount", "Cost Basis", "PurchaseDate"]
            ].copy()
            if not eac_sales.empty:
                eac_sales["Date"] = pd.to_datetime(eac_sales["Date"], format="%m/%d/%Y")
                self.sale_table = (
                    eac_sales
                    if self.sale_table is None
                    else pd.concat([self.sale_table, eac_sales], ignore_index=True)
                )

    def populate_individual_sale_table(self) -> None:
        """
        Process individual account sale transactions.

        Normalizes column names to match the standard sale table format
        and prepares data for consolidation.
        """
        individual_sales = self.individual_sales_df[
            [
                "Closed Date",
                "Symbol",
                "Quantity",
                "Proceeds",
                "Cost Basis (CB)",
                "Opened Date",
            ]
        ].copy()
        # Rename columns to match sale_table format
        individual_sales = individual_sales.rename(
            columns={
                "Closed Date": "Date",
                "Quantity": "Quantity",
                "Proceeds": "Amount",
                "Cost Basis (CB)": "Cost Basis",
                "Opened Date": "PurchaseDate",
            }
        )
        return individual_sales

    def populate_sale_table(self) -> None:
        """
        Consolidate all sale transactions from EAC and individual accounts.

        Combines sale data from all sources, sorts by date, and stores
        in the sale_table.
        """
        self.populate_eac_sale_table()
        if self.individual_sales_df is not None:
            individual_sales = self.populate_individual_sale_table()
            # Only concatenate if individual_sales is not empty
            if not individual_sales.empty:
                self.sale_table = pd.concat(
                    [self.sale_table, individual_sales], ignore_index=True
                )

        # If still None, create empty DataFrame
        if self.sale_table is None:
            self.sale_table = pd.DataFrame(
                columns=[
                    "Date",
                    "Symbol",
                    "Quantity",
                    "Amount",
                    "Cost Basis",
                    "PurchaseDate",
                ]
            )

        # Only process if not empty
        if not self.sale_table.empty:
            self.sale_table["Date"] = pd.to_datetime(
                self.sale_table["Date"], format="%m/%d/%Y"
            )
            self.sale_table = self.sale_table.sort_values(by="Date")

    @staticmethod
    def convert_amount_to_numeric(table: pd.DataFrame, field_name: str) -> None:
        """
        Convert currency strings to numeric values, handling various formats.

        Handles the following formats:
        - Dollar signs ($): $1,234.56 -> 1234.56
        - Commas: 1,234.56 -> 1234.56
        - Parentheses for negatives: (123.45) -> -123.45

        Args:
            table: The pandas DataFrame to modify
            field_name: The column name to convert to numeric

        Note:
            Modifies the DataFrame in-place
        """
        # skip index
        table[field_name] = table[field_name].astype(str)
        if table[field_name].str.contains("\\$").any():
            table[field_name] = table[field_name].str.replace("$", "")
        if table[field_name].str.contains(",").any():
            table[field_name] = table[field_name].str.replace(",", "")
        # if a negative number is written as (x), replace it with -x
        if table[field_name].str.contains("\\(").any():
            table[field_name] = (
                table[field_name].str.replace("(", "-").str.replace(")", "")
            )
        table[field_name] = table[field_name].str.strip().astype(float)

    def save_reports_to_csv(self) -> None:
        """
        Save all processed tables to CSV files in the reports directory.
        """
        self.dividend_table.to_csv(
            self.get_output_file_path("dividend_transactions.csv"),
            index=False,
            date_format="%Y/%m/%d",
        )
        self.interest_table.to_csv(
            self.get_output_file_path("interest_transactions.csv"),
            index=False,
            date_format="%Y/%m/%d",
        )
        self.tax_deducted_table.to_csv(
            self.get_output_file_path("tax_deducted_transactions.csv"),
            index=False,
            date_format="%Y/%m/%d",
        )
        self.sale_table.to_csv(
            self.get_output_file_path("sale_transactions.csv"),
            index=False,
            date_format="%Y/%m/%d",
        )

        print(f"\nFiles saved to {self.config['directories']['reports']}:")
        print("- dividend_transactions.csv")
        print("- interest_transactions.csv")
        print("- tax_deducted_transactions.csv")
        print("- sale_transactions.csv")

    def cleanup_all_tables(self) -> None:
        """
        Clean up and normalize amount columns in all tables.
        """
        for table in [
            self.dividend_table,
            self.interest_table,
            self.tax_deducted_table,
            self.sale_table,
        ]:
            if table is not None and not table.empty:
                self.convert_amount_to_numeric(table, "Amount")

        if self.sale_table is not None and not self.sale_table.empty:
            self.convert_amount_to_numeric(self.sale_table, "Cost Basis")

    def process_all(self) -> None:
        """
        Execute the complete processing pipeline.

        This method runs all the steps required to process Schwab reports:
        1. Initialize and load data from CSV files
        2. Populate all transaction tables
        3. Clean up data formats
        4. Save reports to CSV files
        """
        print(f"Processing transactions for year: {self.config['year']}")

        self.init_data()
        self.populate_dividend_table()
        self.populate_interest_table()
        self.populate_tax_deducted_table()
        self.populate_sale_table()
        self.cleanup_all_tables()
        self.save_reports_to_csv()


def main():
    """
    Main entry point for the script.

    Creates a SchwabReportsProcessor instance and runs the complete processing pipeline.
    """
    processor = SchwabReportsProcessor()
    processor.process_all()


if __name__ == "__main__":
    main()
