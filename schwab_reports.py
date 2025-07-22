import pandas as pd
import os
import yaml
from typing import Optional, List, Dict, Any
from datetime import date

# Configuration
config: Dict[str, Any] = {}

# Global DataFrames with type hints
eac_df: Optional[pd.DataFrame] = None
individual_df: Optional[pd.DataFrame] = None
individual_sales_df: Optional[pd.DataFrame] = None

dividend_table: Optional[pd.DataFrame] = None
interest_table: Optional[pd.DataFrame] = None
tax_deducted_table: Optional[pd.DataFrame] = None
sale_table: Optional[pd.DataFrame] = None


def load_config(config_path: str = "config.yaml") -> Dict[str, Any]:
    """
    Load configuration from YAML file.

    Args:
        config_path: Path to the configuration file

    Returns:
        Dictionary containing configuration values
    """
    try:
        with open(config_path, "r") as file:
            return yaml.safe_load(file)
    except FileNotFoundError:
        raise FileNotFoundError(f"Configuration file not found: {config_path}")
    except yaml.YAMLError as e:
        raise ValueError(f"Error parsing configuration file: {e}")


def get_stock_split_info() -> tuple[date, int]:
    """Get stock split date and ratio from configuration."""
    stock_split = config["stock_splits"][0]  # Use first stock split
    split_date = pd.to_datetime(stock_split["date"], format="%Y-%m-%d").date()
    split_ratio = stock_split["ratio"]
    return split_date, split_ratio


def get_file_path(file_type: str) -> str:
    """
    Generate file path based on configuration and current year.

    Args:
        file_type: Type of file (eac_transactions, individual_transactions, etc.)

    Returns:
        Full file path
    """
    pattern = config["file_patterns"][file_type]
    filename = pattern.format(year=config["year"])
    return os.path.join(config["directories"]["transactions"], filename)


def get_output_file_path(filename: str) -> str:
    """
    Generate output file path in the reports directory.

    Args:
        filename: Name of the output file

    Returns:
        Full file path in the reports directory
    """
    return os.path.join(config["directories"]["reports"], filename)


def fixup_stock_splits(df: pd.DataFrame, date_column: str) -> None:
    """
    Apply stock split adjustments to quantity data based on transaction dates.

    For transactions before the stock split date, multiply quantities by the split ratio.

    Args:
        df: DataFrame containing transaction data
        date_column: Name of the column containing transaction dates
    """
    stock_split_date, stock_split_ratio = get_stock_split_info()

    # if a sale date is before the stock split date, then multiply quantity by split ratio
    for index, row in df.iterrows():
        row_date = pd.to_datetime(row[date_column], format="%m/%d/%Y").date()
        if row_date < stock_split_date:
            # if row has 'Quantity' column, multiply it by split ratio
            if "Quantity" in row and row["Quantity"] is not None:
                df.at[index, "Quantity"] = df.at[index, "Quantity"] * stock_split_ratio


def normalize_eac_df() -> None:
    """
    Normalize and process EAC DataFrame with proper sale lot handling.

    Converts amount columns to numeric and processes sale transactions to create
    proper lot sale entries with calculated cost basis and purchase dates.
    """
    global eac_df

    stock_split_date, stock_split_ratio = get_stock_split_info()

    for column in [
        "Amount",
        "Shares",
        "Quantity",
        "PurchaseFairMarketValue",
        "VestFairMarketValue",
    ]:
        convert_amount_to_numeric(eac_df, column)

    # Gather the sale date and sale price for each sale and apply it to the lot sale rows
    # use only the lot sale rows in the final sale report from EAC
    for index, row in eac_df.iterrows():
        if row["Action"] == "Sale":
            row_date = pd.to_datetime(row["Date"], format="%m/%d/%Y").date()
            row_symbol = row["Symbol"]
            row_sale_fmv = row["Amount"] / row["Quantity"]
        elif pd.isna(row["Date"]) or row["Date"] == "":
            eac_df.at[index, "Action"] = "Lot Sale"
            eac_df.at[index, "Date"] = row_date
            eac_df.at[index, "Symbol"] = row_symbol
            eac_df.at[index, "Amount"] = row_sale_fmv * row["Shares"]
            eac_df.at[index, "Quantity"] = row["Shares"]

            fmv = (
                row["VestFairMarketValue"]
                if row["Type"] == "RS"
                else row["PurchaseFairMarketValue"]
            )
            cb = fmv * row["Shares"]
            eac_df.at[index, "Cost Basis"] = (
                cb * stock_split_ratio if row_date < stock_split_date else cb
            )
            eac_df.at[index, "PurchaseDate"] = (
                row["VestDate"] if row["Type"] == "RS" else row["PurchaseDate"]
            )


def init_data() -> None:
    """
    Initialize and load data from CSV files into global DataFrames.

    Loads transaction data from CSV files based on configuration patterns.
    Applies necessary preprocessing including stock split adjustments.
    """
    global individual_df, eac_df, individual_sales_df

    # Load Individual transactions
    individual_transactions_path = get_file_path("individual_transactions")
    if os.path.exists(individual_transactions_path):
        df = pd.read_csv(individual_transactions_path)
        individual_df = df[df["Action"] != "Reinvest Shares"].copy()
        fixup_stock_splits(individual_df, "Date")

    # Load Individual realized gains
    individual_realized_gains_path = get_file_path("individual_realized_gains")
    if os.path.exists(individual_realized_gains_path):
        individual_sales_df = pd.read_csv(individual_realized_gains_path, skiprows=1)
        fixup_stock_splits(individual_sales_df, "Closed Date")

    # Load EAC transactions
    eac_transactions_path = get_file_path("eac_transactions")
    if os.path.exists(eac_transactions_path):
        eac_df = pd.read_csv(eac_transactions_path)
        normalize_eac_df()
        fixup_stock_splits(eac_df, "Date")


def populate_dividend_table() -> None:
    """
    Process and consolidate dividend transactions from all sources.

    Combines dividend data from both individual and EAC accounts,
    sorts by date, and stores in the global dividend_table.
    """
    global dividend_table
    dividend_actions: List[str] = ["Reinvest Dividend", "Qual Div Reinvest"]

    if individual_df is not None:
        dividend_table = individual_df[
            individual_df["Action"].isin(dividend_actions)
        ].copy()
    else:
        dividend_table = pd.DataFrame(columns=["Date", "Action", "Symbol", "Amount"])

    dividend_table = dividend_table[["Date", "Action", "Symbol", "Amount"]].copy()

    if eac_df is not None:
        eac_dividend_table = eac_df[eac_df["Action"] == "Dividend"].copy()
        eac_dividend_table = eac_dividend_table[
            ["Date", "Action", "Symbol", "Amount"]
        ].copy()
        # Only concatenate if eac_dividend_table is not empty
        if not eac_dividend_table.empty:
            dividend_table = pd.concat(
                [dividend_table, eac_dividend_table], ignore_index=True
            )

    # convert the data type of the "Date" column to datetime
    dividend_table["Date"] = pd.to_datetime(dividend_table["Date"], format="%m/%d/%Y")
    dividend_table = dividend_table.sort_values(by="Date")


def populate_interest_table() -> None:
    """
    Process interest transactions from individual account data.

    Extracts credit interest transactions, sorts by date, and stores
    in the global interest_table.
    """
    global interest_table
    if individual_df is not None:
        interest_table = individual_df[
            individual_df["Action"] == "Credit Interest"
        ].copy()
    else:
        interest_table = pd.DataFrame(columns=["Date", "Action", "Amount"])
    interest_table = interest_table[["Date", "Action", "Amount"]].copy()
    interest_table["Date"] = pd.to_datetime(interest_table["Date"], format="%m/%d/%Y")
    interest_table = interest_table.sort_values(by="Date")


def populate_tax_deducted_table() -> None:
    """
    Process tax deduction transactions from all sources.

    Combines tax withholding data from both individual and EAC accounts,
    sorts by date, and stores in the global tax_deducted_table.
    """
    global tax_deducted_table
    tax_deducted_actions: List[str] = ["NRA Tax Adj"]
    if individual_df is not None:
        tax_deducted_table = individual_df[
            individual_df["Action"].isin(tax_deducted_actions)
        ].copy()
        tax_deducted_table = tax_deducted_table[["Date", "Symbol", "Amount"]].copy()

    if eac_df is not None:
        eac_tax_table = eac_df[eac_df["Action"] == "Tax Withholding"].copy()
        # Keep only these columns in eac_tax_table: Date, Symbol, Amount
        eac_tax_table = eac_tax_table[["Date", "Symbol", "Amount"]].copy()
        # Only concatenate if eac_tax_table is not empty
        if not eac_tax_table.empty:
            tax_deducted_table = (
                eac_tax_table
                if tax_deducted_table is None
                else pd.concat([tax_deducted_table, eac_tax_table], ignore_index=True)
            )

    tax_deducted_table["Date"] = pd.to_datetime(
        tax_deducted_table["Date"], format="%m/%d/%Y"
    )
    tax_deducted_table = tax_deducted_table.sort_values(by="Date")


def populate_eac_sale_table() -> None:
    """
    Process EAC sale transactions and add to sale table.

    Extracts lot sale data from EAC transactions with proper date conversion
    and adds to the global sale_table.
    """
    global sale_table, eac_df

    eac_df = eac_df[eac_df["Action"] == "Lot Sale"].copy()
    eac_df = eac_df[
        ["Date", "Symbol", "Quantity", "Amount", "Cost Basis", "PurchaseDate"]
    ].copy()
    eac_df["Date"] = pd.to_datetime(eac_df["Date"], format="%m/%d/%Y")
    sale_table = (
        eac_df
        if sale_table is None
        else pd.concat([sale_table, eac_df], ignore_index=True)
    )


def populate_individual_sale_table() -> None:
    """
    Process individual account sale transactions.

    Normalizes column names to match the standard sale table format
    and prepares data for consolidation.
    """
    global individual_sales_df
    individual_sales_df = individual_sales_df[
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
    individual_sales_df = individual_sales_df.rename(
        columns={
            "Closed Date": "Date",
            "Quantity": "Quantity",
            "Proceeds": "Amount",
            "Cost Basis (CB)": "Cost Basis",
            "Opened Date": "PurchaseDate",
        }
    )


def populate_sale_table() -> None:
    """
    Consolidate all sale transactions from EAC and individual accounts.

    Combines sale data from all sources, sorts by date, and stores
    in the global sale_table.
    """
    global sale_table, individual_sales_df
    populate_eac_sale_table()
    if individual_sales_df is not None:
        populate_individual_sale_table()
        # Only concatenate if individual_sales_df is not empty
        if not individual_sales_df.empty:
            sale_table = pd.concat([sale_table, individual_sales_df], ignore_index=True)
    sale_table["Date"] = pd.to_datetime(sale_table["Date"], format="%m/%d/%Y")
    sale_table = sale_table.sort_values(by="Date")


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
        table[field_name] = table[field_name].str.replace("(", "-").str.replace(")", "")
    table[field_name] = table[field_name].str.strip().astype(float)


def save_reports_to_csv() -> None:
    global dividend_table, interest_table, tax_deducted_table, sale_table

    dividend_table.to_csv(
        get_output_file_path("dividend_transactions.csv"),
        index=False,
        date_format="%Y/%m/%d",
    )
    interest_table.to_csv(
        get_output_file_path("interest_transactions.csv"),
        index=False,
        date_format="%Y/%m/%d",
    )
    tax_deducted_table.to_csv(
        get_output_file_path("tax_deducted_transactions.csv"),
        index=False,
        date_format="%Y/%m/%d",
    )
    sale_table.to_csv(
        get_output_file_path("sale_transactions.csv"),
        index=False,
        date_format="%Y/%m/%d",
    )

    print(f"\nFiles saved to {config['directories']['reports']}:")
    print("- dividend_transactions.csv")
    print("- interest_transactions.csv")
    print("- tax_deducted_transactions.csv")
    print("- sale_transactions.csv")


def cleanup_all_tables() -> None:
    global dividend_table, interest_table, tax_deducted_table
    for table in [dividend_table, interest_table, tax_deducted_table, sale_table]:
        convert_amount_to_numeric(table, "Amount")
    convert_amount_to_numeric(sale_table, "Cost Basis")


def main():
    global config
    config = load_config()
    print(f"Processing transactions for year: {config['year']}")

    init_data()
    populate_dividend_table()
    populate_interest_table()
    populate_tax_deducted_table()
    populate_sale_table()
    cleanup_all_tables()
    save_reports_to_csv()


if __name__ == "__main__":
    main()
