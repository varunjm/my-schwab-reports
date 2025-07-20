import pandas as pd
import numpy as np

# Read the CSV files
df = pd.read_csv('transactions/Individual_transactions_2024.csv')
eac_df = pd.read_csv('transactions/EAC_transations_2024.csv')

# Filter out "Reinvest Shares" actions from Individual transactions
filtered_df = df[df['Action'] != 'Reinvest Shares'].copy()

# print(f"\nAfter filtering out 'Reinvest Shares': {filtered_df.shape[0]} rows remaining")

# Define categories - split dividends and interest
dividend_actions = ['Reinvest Dividend', 'Qual Div Reinvest']
interest_actions = ['Credit Interest']
tax_deducted_actions = ['NRA Tax Adj']

# Separate Individual transactions into tables
dividend_table = filtered_df[filtered_df['Action'].isin(dividend_actions)].copy()
# Keep only these columns in dividend_table: Date, Action, Symbol, Amount
dividend_table = dividend_table[['Date', 'Action', 'Symbol', 'Amount']].copy()

interest_table = filtered_df[filtered_df['Action'].isin(interest_actions)].copy()
# Keep only these columns in interest_table: Date, Action, Amount
interest_table = interest_table[['Date', 'Action', 'Amount']].copy()

tax_deducted_table = filtered_df[filtered_df['Action'].isin(tax_deducted_actions)].copy()
# Keep only these columns in tax_deducted_table: Date, Symbol, Amount
tax_deducted_table = tax_deducted_table[['Date', 'Symbol', 'Amount']].copy()

# Extract and add EAC transactions
eac_dividend_table = eac_df[eac_df['Action'] == 'Dividend'].copy()
# Keep only these columns in dividend_table: Date, Action, Symbol, Amount
eac_dividend_table = eac_dividend_table[['Date', 'Action', 'Symbol', 'Amount']].copy()

eac_tax_table = eac_df[eac_df['Action'] == 'Tax Withholding'].copy()
# Keep only these columns in eac_tax_table: Date, Symbol, Amount
eac_tax_table = eac_tax_table[['Date', 'Symbol', 'Amount']].copy()

# Combine the tables
if not eac_dividend_table.empty:
    dividend_table = pd.concat([dividend_table, eac_dividend_table], ignore_index=True)
    dividend_table = dividend_table.sort_values(by='Date')

if not eac_tax_table.empty:
    tax_deducted_table = pd.concat([tax_deducted_table, eac_tax_table], ignore_index=True)
    tax_deducted_table = tax_deducted_table.sort_values(by='Date')

# Convert Amount column to numeric for calculations (removing $ and converting to float)
dividend_table['Amount_Numeric'] = dividend_table['Amount'].str.replace('$', '').str.replace(',', '').astype(float)
interest_table['Amount_Numeric'] = interest_table['Amount'].str.replace('$', '').str.replace(',', '').astype(float)
tax_deducted_table['Amount_Numeric'] = tax_deducted_table['Amount'].str.replace('$', '').str.replace(',', '').astype(float)

# Save to separate CSV files
dividend_table.to_csv('reports/dividend_transactions.csv', index=False)
interest_table.to_csv('reports/interest_transactions.csv', index=False)
tax_deducted_table.to_csv('reports/tax_deducted_transactions.csv', index=False)

print(f"\nFiles saved:")
print("- dividend_transactions.csv")
print("- interest_transactions.csv")
print("- tax_deducted_transactions.csv")
