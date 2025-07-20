import pandas as pd
import numpy as np

#initialize individual_df and eac_df
individual_df = None
eac_df = None

dividend_table = None
interest_table = None
tax_deducted_table = None

def init_data():
    global individual_df, eac_df
    df = pd.read_csv('transactions/Individual_transactions_2024.csv')
    # Filter out "Reinvest Shares" actions from Individual transactions
    individual_df = df[df['Action'] != 'Reinvest Shares'].copy()
    eac_df = pd.read_csv('transactions/EAC_transations_2024.csv')

def populate_dividend_table():
    global dividend_table
    dividend_actions = ['Reinvest Dividend', 'Qual Div Reinvest']
    # Separate Individual transactions into tables
    dividend_table = individual_df[individual_df['Action'].isin(dividend_actions)].copy()
    # Keep only these columns in dividend_table: Date, Action, Symbol, Amount
    dividend_table = dividend_table[['Date', 'Action', 'Symbol', 'Amount']].copy()

    if (eac_df is not None):
        # Extract and add EAC transactions
        eac_dividend_table = eac_df[eac_df['Action'] == 'Dividend'].copy()
        # Keep only these columns in dividend_table: Date, Action, Symbol, Amount
        eac_dividend_table = eac_dividend_table[['Date', 'Action', 'Symbol', 'Amount']].copy()
        dividend_table = pd.concat([dividend_table, eac_dividend_table], ignore_index=True)

    dividend_table = dividend_table.sort_values(by='Date')

def populate_interest_table():
    global interest_table
    interest_actions = ['Credit Interest']
    interest_table = individual_df[individual_df['Action'].isin(interest_actions)].copy()
    # Keep only these columns in interest_table: Date, Action, Amount
    interest_table = interest_table[['Date', 'Action', 'Amount']].copy()

def populate_tax_deducted_table():
    global tax_deducted_table
    tax_deducted_actions = ['NRA Tax Adj']
    tax_deducted_table = individual_df[individual_df['Action'].isin(tax_deducted_actions)].copy()
    # Keep only these columns in tax_deducted_table: Date, Symbol, Amount
    tax_deducted_table = tax_deducted_table[['Date', 'Symbol', 'Amount']].copy()

    if (eac_df is not None):
        eac_tax_table = eac_df[eac_df['Action'] == 'Tax Withholding'].copy()
        # Keep only these columns in eac_tax_table: Date, Symbol, Amount
        eac_tax_table = eac_tax_table[['Date', 'Symbol', 'Amount']].copy()
        tax_deducted_table = pd.concat([tax_deducted_table, eac_tax_table], ignore_index=True)

    tax_deducted_table = tax_deducted_table.sort_values(by='Date')

def convert_amount_to_numeric(table):
    # Convert Amount column to numeric for calculations (removing $ and converting to float)
    table['Amount_Numeric'] = table['Amount'].str.replace('$', '').str.replace(',', '').astype(float)

def save_reports_to_csv():
    global dividend_table, interest_table, tax_deducted_table
    dividend_table.to_csv('reports/dividend_transactions.csv', index=False)
    interest_table.to_csv('reports/interest_transactions.csv', index=False)
    tax_deducted_table.to_csv('reports/tax_deducted_transactions.csv', index=False)

    print(f"\nFiles saved:")
    print("- dividend_transactions.csv")
    print("- interest_transactions.csv")
    print("- tax_deducted_transactions.csv")

def main():
    global dividend_table, interest_table, tax_deducted_table
    init_data()
    populate_dividend_table()
    populate_interest_table()
    populate_tax_deducted_table()
    for table in [dividend_table, interest_table, tax_deducted_table]:
        convert_amount_to_numeric(table)
    save_reports_to_csv()

if __name__ == "__main__":
    main()
