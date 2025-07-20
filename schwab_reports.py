import pandas as pd
import numpy as np

#initialize individual_df and eac_df
individual_df = None
eac_df = None
individual_sales_df = None

dividend_table = None
interest_table = None
tax_deducted_table = None
sale_table = None

def fixup_stock_splits(df, filter_action, date_column):
    # if a sale date is before the stock split date, then multiply quantity by split ratio
    stock_split_date = pd.to_datetime('2024-06-07', format='%Y-%m-%d').date()
    stock_split_ratio = 10

    filtered_df = df[df['Action'] == 'Sale'] if filter_action else df
    for index, row in filtered_df.iterrows():
        row_date = pd.to_datetime(row[date_column], format='%m/%d/%Y').date()
        if row_date < stock_split_date:
            df.at[index, 'Quantity'] = df.at[index, 'Quantity']*stock_split_ratio

def init_data():
    global individual_df, eac_df, individual_sales_df

    df = pd.read_csv('transactions/Individual_transactions_2024.csv')
    individual_df = df[df['Action'] != 'Reinvest Shares'].copy()
    eac_df = pd.read_csv('transactions/EAC_transations_2024.csv')
    individual_sales_df = pd.read_csv('transactions/Individual_realized_gains_2024.csv')

    for table in [individual_df, eac_df]:
        fixup_stock_splits(table, True, 'Date')
    fixup_stock_splits(individual_sales_df, False, 'Closed Date')

def populate_dividend_table():
    global dividend_table
    dividend_actions = ['Reinvest Dividend', 'Qual Div Reinvest']
    dividend_table = individual_df[individual_df['Action'].isin(dividend_actions)].copy()
    dividend_table = dividend_table[['Date', 'Action', 'Symbol', 'Amount']].copy()

    if (eac_df is not None):
        eac_dividend_table = eac_df[eac_df['Action'] == 'Dividend'].copy()
        eac_dividend_table = eac_dividend_table[['Date', 'Action', 'Symbol', 'Amount']].copy()
        dividend_table = pd.concat([dividend_table, eac_dividend_table], ignore_index=True)

    dividend_table = dividend_table.sort_values(by='Date')

def populate_interest_table():
    global interest_table
    interest_table = individual_df[individual_df['Action'] == 'Credit Interest'].copy()
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

def populate_eac_sale_table():
    global sale_table, eac_df
    
    sale_rows = []
    current_sale_index = None
    lot_details = []
    
    for index, row in eac_df.iterrows():
        if row['Action'] == 'Sale':
            # If we have a previous sale with lot details, process it
            if current_sale_index is not None and lot_details:
                # Calculate average purchase price from PurchaseFairMarketValue
                purchase_prices = []
                purchase_dates = []
                for lot in lot_details:
                    if pd.notna(lot['PurchaseFairMarketValue']) and lot['PurchaseFairMarketValue'] != '':
                        price = float(lot['PurchaseFairMarketValue'].replace('$', ''))
                        purchase_prices.append(price)
                    
                    # Extract purchase date
                    if pd.notna(lot['PurchaseDate']) and lot['PurchaseDate'] != '':
                        purchase_dates.append(lot['PurchaseDate'])
                
                avg_purchase_price = sum(purchase_prices) / len(purchase_prices) if purchase_prices else 0
                sale_quantity = float(sale_rows[current_sale_index]['Quantity'])
                sale_rows[current_sale_index]['Cost Basis'] = avg_purchase_price * sale_quantity
                
                # Set earliest purchase date or comma-separated list of all dates
                if purchase_dates:
                    # Sort dates and take the earliest one
                    purchase_dates.sort()
                    sale_rows[current_sale_index]['PurchaseDate'] = purchase_dates[0]
                    # Alternative: show all dates - sale_rows[current_sale_index]['PurchaseDate'] = ', '.join(purchase_dates)
            
            # Start new sale
            current_sale_index = len(sale_rows)
            sale_rows.append({
                'Date': row['Date'],
                'Symbol': row['Symbol'],
                'Quantity': row['Quantity'],
                'Amount': row['Amount'],
                'Cost Basis': 0,  # Will be calculated from lot details
                'PurchaseDate': ''  # Will be populated from lot details
            })
            lot_details = []
            
        elif pd.isna(row['Date']) or row['Date'] == '':
            # This is a lot detail row
            if current_sale_index is not None:
                lot_details.append(row)
    
    # Process the last sale if exists
    if current_sale_index is not None and lot_details:
        purchase_prices = []
        purchase_dates = []
        for lot in lot_details:
            if pd.notna(lot['PurchaseFairMarketValue']) and lot['PurchaseFairMarketValue'] != '':
                price = float(lot['PurchaseFairMarketValue'].replace('$', ''))
                purchase_prices.append(price)
            
            # Extract purchase date
            if pd.notna(lot['PurchaseDate']) and lot['PurchaseDate'] != '':
                purchase_dates.append(lot['PurchaseDate'])
        
        avg_purchase_price = sum(purchase_prices) / len(purchase_prices) if purchase_prices else 0
        sale_quantity = float(sale_rows[current_sale_index]['Quantity'])
        sale_rows[current_sale_index]['Cost Basis'] = avg_purchase_price * sale_quantity

        # Set earliest purchase date or comma-separated list of all dates
        if purchase_dates:
            # Sort dates and take the earliest one
            purchase_dates.sort()
            sale_rows[current_sale_index]['PurchaseDate'] = purchase_dates[0]
            # Alternative: show all dates - sale_rows[current_sale_index]['PurchaseDate'] = ', '.join(purchase_dates)

    if sale_table is None:
        sale_table = pd.DataFrame(sale_rows)
    else:
        sale_table = pd.concat([sale_table, pd.DataFrame(sale_rows)], ignore_index=True)

def populate_individual_sale_table():
    global individual_sales_df
    individual_sales_df = individual_sales_df[['Closed Date', 'Symbol', 'Quantity', 'Proceeds', 'Cost Basis (CB)', 'Opened Date']].copy()
    # Rename columns to match sale_table format
    individual_sales_df = individual_sales_df.rename(columns={
        'Closed Date': 'Date',
        'Quantity': 'Quantity',
        'Proceeds': 'Amount',
        'Cost Basis (CB)': 'Cost Basis',
        'Opened Date': 'PurchaseDate'
    })

def populate_sale_table():
    global sale_table, individual_sales_df
    populate_eac_sale_table()
    populate_individual_sale_table()
    sale_table = pd.concat([sale_table, individual_sales_df], ignore_index=True)

    # Convert Date column to datetime before sorting
    sale_table['Date'] = pd.to_datetime(sale_table['Date'], format='%m/%d/%Y')
    sale_table = sale_table.sort_values(by='Date')

def convert_amount_to_numeric(table, field_name):
    # skip index
    table[field_name] = table[field_name].astype(str)
    if table[field_name].str.contains('$').any():
        table[field_name] = table[field_name].str.replace('$', '')
    if table[field_name].str.contains(',').any():
        table[field_name] = table[field_name].str.replace(',', '')
    table[field_name] = table[field_name].str.strip().astype(float)

def save_reports_to_csv():
    global dividend_table, interest_table, tax_deducted_table, sale_table
    dividend_table.to_csv('reports/dividend_transactions.csv', index=False)
    interest_table.to_csv('reports/interest_transactions.csv', index=False)
    tax_deducted_table.to_csv('reports/tax_deducted_transactions.csv', index=False)
    sale_table.to_csv('reports/sale_transactions.csv', index=False)

    print(f"\nFiles saved:")
    print("- dividend_transactions.csv")
    print("- interest_transactions.csv")
    print("- tax_deducted_transactions.csv")
    print("- sale_transactions.csv")

def main():
    global dividend_table, interest_table, tax_deducted_table
    init_data()
    populate_dividend_table()
    populate_interest_table()
    populate_tax_deducted_table()
    populate_sale_table()
    print(sale_table)

    for table in [dividend_table, interest_table, tax_deducted_table, sale_table]:
        convert_amount_to_numeric(table, 'Amount')
    convert_amount_to_numeric(sale_table, 'Cost Basis')

    save_reports_to_csv()

if __name__ == "__main__":
    main()
