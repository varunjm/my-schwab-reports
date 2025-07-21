import pandas as pd
import os

eac_df = None
individual_df = None
individual_sales_df = None

dividend_table = None
interest_table = None
tax_deducted_table = None
sale_table = None

stock_split_date = pd.to_datetime("2024-06-07", format="%Y-%m-%d").date()
stock_split_ratio = 10


def fixup_stock_splits(df, date_column):
    global stock_split_date, stock_split_ratio
    # if a sale date is before the stock split date, then multiply quantity by split ratio
    for index, row in df.iterrows():
        row_date = pd.to_datetime(row[date_column], format="%m/%d/%Y").date()
        if row_date < stock_split_date:
            # if row has 'Quantity' column, multiply it by split ratio
            if "Quantity" in row and row["Quantity"] is not None:
                df.at[index, "Quantity"] = df.at[index, "Quantity"] * stock_split_ratio


def normalize_eac_df():
    global eac_df

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


def init_data():
    global individual_df, eac_df, individual_sales_df

    if os.path.exists("transactions/Individual_transactions_2024.csv"):
        df = pd.read_csv("transactions/Individual_transactions_2024.csv")
        individual_df = df[df["Action"] != "Reinvest Shares"].copy()
        fixup_stock_splits(individual_df, "Date")

    if os.path.exists("transactions/Individual_realized_gains_2024.csv"):
        individual_sales_df = pd.read_csv(
            "transactions/Individual_realized_gains_2024.csv", skiprows=1
        )
        fixup_stock_splits(individual_sales_df, "Closed Date")

    if os.path.exists("transactions/EAC_transactions_2024.csv"):
        eac_df = pd.read_csv("transactions/EAC_transactions_2024.csv")
        normalize_eac_df()
        fixup_stock_splits(eac_df, "Date")


def populate_dividend_table():
    global dividend_table
    dividend_actions = ["Reinvest Dividend", "Qual Div Reinvest"]

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


def populate_interest_table():
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


def populate_tax_deducted_table():
    global tax_deducted_table
    tax_deducted_actions = ["NRA Tax Adj"]
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


def populate_eac_sale_table():
    global sale_table, eac_df
    global stock_split_date, stock_split_ratio

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


def populate_individual_sale_table():
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


def populate_sale_table():
    global sale_table, individual_sales_df
    populate_eac_sale_table()
    if individual_sales_df is not None:
        populate_individual_sale_table()
        # Only concatenate if individual_sales_df is not empty
        if not individual_sales_df.empty:
            sale_table = pd.concat([sale_table, individual_sales_df], ignore_index=True)
    sale_table["Date"] = pd.to_datetime(sale_table["Date"], format="%m/%d/%Y")
    sale_table = sale_table.sort_values(by="Date")


def convert_amount_to_numeric(table, field_name):
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


def save_reports_to_csv():
    global dividend_table, interest_table, tax_deducted_table, sale_table

    dividend_table.to_csv(
        "reports/dividend_transactions.csv", index=False, date_format="%Y/%m/%d"
    )
    interest_table.to_csv(
        "reports/interest_transactions.csv", index=False, date_format="%Y/%m/%d"
    )
    tax_deducted_table.to_csv(
        "reports/tax_deducted_transactions.csv", index=False, date_format="%Y/%m/%d"
    )
    sale_table.to_csv(
        "reports/sale_transactions.csv", index=False, date_format="%Y/%m/%d"
    )

    print("\nFiles saved:")
    print("- dividend_transactions.csv")
    print("- interest_transactions.csv")
    print("- tax_deducted_transactions.csv")
    print("- sale_transactions.csv")


def cleanup_all_tables():
    global dividend_table, interest_table, tax_deducted_table
    for table in [dividend_table, interest_table, tax_deducted_table, sale_table]:
        convert_amount_to_numeric(table, "Amount")
    convert_amount_to_numeric(sale_table, "Cost Basis")


def main():
    init_data()
    populate_dividend_table()
    populate_interest_table()
    populate_tax_deducted_table()
    populate_sale_table()
    cleanup_all_tables()
    save_reports_to_csv()


if __name__ == "__main__":
    main()
