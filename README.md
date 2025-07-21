# my-schwab-reports

A Python script to process Charles Schwab CSV exports and generate consolidated tax reports for Indian residents with US investments.

## What does this do?

This script processes CSV exports from Charles Schwab accounts (Employee Stock Award Center/EAC and Individual trading accounts) and generates consolidated reports required for Indian tax filing:

- **Dividend report** - All dividend earnings with TDS details
- **Interest earned report** - Interest from cash holdings and savings
- **Sale report** - Stock sales with cost basis and gains/losses
- **TDS report** - Tax Deducted at Source from dividends and interest

The generated reports help streamline the process of filing taxes in India for income earned from US investments.

## Prerequisites

- Python 3.12+ (tested on Python 3.12)
- Access to Charles Schwab online account
- Basic familiarity with command line

**Tested on:**
- Ubuntu 24.04
- Python 3.12
- Pip 24.0

## Setup

### 1. Clone and prepare environment
```bash
git clone https://github.com/varunjm/my-schwab-reports.git
cd my-schwab-reports
mkdir -p transactions reports
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 2. Download Schwab reports

**Important:** File names must match exactly as specified below.

#### For Employee Stock Award Center (EAC) account:
1. Go to **Transaction History (EAC)**
2. Select your desired date range (typically full financial year)
3. Filter by transaction types: **Share sales, Cash transactions**
4. Click **Export**
5. Save as: `EAC_transactions_YYYY.csv` (e.g., `EAC_transactions_2024.csv`)

#### For Individual trading account (skip if you don't have one):
1. Go to **Transaction History (Individual)**
2. Select the same date range
3. Filter by transaction types: **Dividends, Interest, Misc, Taxes**
4. Click **Export**
5. Save as: `Individual_transactions_YYYY.csv`

1. Go to **Realized Gain/Loss (Individual)**
2. Select the same date range
3. Click **Export** → **Export Details Only**
4. Save as: `Individual_realized_gains_YYYY.csv`

### 3. Place files in transactions directory

## Future features
- Generate each of those tables in the exact format needed for Income tax filing.
- Add USD-INR conversion infromation and generate tables with INR values.
- Add a config file where we can specify the various inputs:
    - File names of schwab exports.
    - Stock split date and ratio for the given FY.