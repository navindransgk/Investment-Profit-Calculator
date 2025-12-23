import streamlit as st
import sqlite3
import pandas as pd
import yfinance as yf
from datetime import datetime
import math

# --- 1. SQLite Database Setup and Management ---
DB_NAME = "historical_data.db"

def get_monthly_prices():
    conn = sqlite3.connect(DB_NAME)
    mycursor = conn.cursor()

    #Selecting first trade everymonth for each ticker
    selectQuery = """
        SELECT hsd1.ticker, hsd1.date, open AS trading_price, company
        FROM historical_stock_data hsd1
        INNER JOIN (
            SELECT ticker, MIN(date) AS month_open_date
            FROM historical_stock_data
            GROUP BY ticker, STRFTIME('%Y-%m', date)
        ) hsd2 ON hsd1.ticker = hsd2.ticker AND hsd1.date = hsd2.month_open_date
        ORDER BY hsd1.ticker, hsd1.date
    """
    monthlyTradesDF = pd.read_sql_query(selectQuery, conn)

    # mycursor.execute('''
    #    DROP TABLE IF EXISTS monthly_tradings
    # ''')
    
    # Create table to store monthly transactions for each ticker
    createMonthlyPurchasesTable = """
        CREATE TABLE IF NOT EXISTS monthly_tradings(
            mtrade_id INTEGER PRIMARY KEY AUTOINCREMENT,
            ticker TEXT NOT NULL,
            trade_date TIMESTAMP NOT NULL,
            trading_price REAL,
            company TEXT NOT NULL
        );
    """
    mycursor.execute(createMonthlyPurchasesTable)
    
    # st.dataframe(monthlyTradesDF)

    #Insert the monthly trading records to the table
    insertMonthlyTrades = "INSERT INTO monthly_tradings(ticker, trade_date, trading_price, company) VALUES(?, ?, ?, ?)"
    for index, row in monthlyTradesDF.iterrows():
        mycursor.execute(insertMonthlyTrades, (row['Ticker'], row['Date'], row['trading_price'], row['Company']))

    conn.commit()
    conn.close()

    return monthlyTradesDF

def create_monthly_investment():
    """Create the investments table if it doesn't exist."""
    conn = sqlite3.connect(DB_NAME)
    
    # drop_cursor = conn.cursor()
    # drop_cursor.execute('''
    #    DROP TABLE IF EXISTS investments
    # ''') """
    
    create_cursor = conn.cursor()
    create_cursor.execute('''
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY,
            ticker TEXT,
            company TEXT,
            purchase_date TIMESTAMP,
            purchase_price REAL,
            investment_amount REAL,
            purchase_amount REAL,
            investment_balance REAL,
            total_shares INTEGER
        )
    ''')
    conn.commit()
    conn.close()

def add_investment(ticker, company, purchase_date, purchase_price, investment_amount, purchase_amount, investment_balance, total_shares):
    """Add a new monthly investment record to the database."""
    conn = sqlite3.connect(DB_NAME)
    c = conn.cursor()
    c.execute("INSERT INTO investments (ticker, company, purchase_date, purchase_price, investment_amount, purchase_amount, investment_balance, total_shares) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", 
              (ticker, company, purchase_date, purchase_price, investment_amount, purchase_amount, investment_balance, total_shares))
    conn.commit()
    conn.close()

def get_investments(selectedTickerValue):
    """Retrieve all investment records from the database."""
    conn = sqlite3.connect(DB_NAME)
    investmentSelectQuery = "SELECT * FROM investments WHERE ticker = ? ORDER BY purchase_date;"
    investmentSelectParams = (selectedTickerValue, )
    df = pd.read_sql_query(investmentSelectQuery, conn, params=investmentSelectParams)
    conn.close()
    return df

# --- 2. Stock Data Retrieval ---
def get_latest_prices():
    conn = sqlite3.connect(DB_NAME)
    mycursor = conn.cursor()

    #Selecting last trade price for each ticker
    selectQuery = """
        SELECT hsd1.ticker, date, close AS latest_trade_price
        FROM historical_stock_data hsd1
        INNER JOIN (
            SELECT ticker, MAX(date) AS latest_trade_date
            FROM historical_stock_data
            GROUP BY ticker
        ) hsd2 ON hsd1.ticker = hsd2.ticker AND hsd1.date = hsd2.latest_trade_date
        ORDER BY hsd1.ticker, hsd1.date
    """
    latestPricesDF = pd.read_sql_query(selectQuery, conn)
    return latestPricesDF

# --- 3. Profit Calculation and Streamlit UI ---
# This method is not being used currently
def calculate_profit(investments_df, latest_prices):
    """Calculate the total profit/loss."""
    total_invested = investments_df['amount'].sum()
    current_value = 150000.00
    
    for ticker in investments_df['ticker'].unique():
        stock_invested = investments_df[investments_df['ticker'] == ticker]['amount'].sum()
        Profit = current_value - stock_invested

    portfolio_value = 0
    for ticker in investments_df['ticker'].unique():
        ticker_data = investments_df[investments_df['ticker'] == ticker.split('.')[0]]
        total_spent = ticker_data['amount'].sum()
        
    st.warning("Accurate monthly profit calculation requires tracking the exact number of shares purchased at the time of investment, which this simple database schema does not support.")
    st.warning("Below is a simplified overall profit calculation based on total investment and current price (which is an oversimplification for DCA).")
    
    return total_invested # placeholder

def main():
    st.title("Stock Investment Profit Calculator")
    monthlyTradeDetailsDF = get_monthly_prices()
    create_monthly_investment()

    st.header("Latest Stock Prices")
    latestStockPricesDF = get_latest_prices()
    st.dataframe(latestStockPricesDF, hide_index=True)

    # Sidebar for adding investments
    with st.sidebar:
        st.header("Add Monthly Investment")
        # Example stocks from prompt
        ticker = st.selectbox("Select Stock Ticker", ["TCS.NS", "INFY.NS", "SBIN.NS", "HDFCBANK.NS", "HINDUNILVR.NS", "ICICIBANK.NS", "BHARTIARTL.NS", "LT.NS", "ITC.NS", "ASIANPAINT.NS", "WIPRO.NS", "RELIANCE.NS", "AXISBANK.NS"]) # Example tickers
        amount = 10000 # per stock
        investment_balance = 0
        st.write(f"Monthly amount per stock: ₹{amount:.2f}")
        
        selectedTickerValue = ticker.split('.')[0]
        stockwiseTradesDF = monthlyTradeDetailsDF[monthlyTradeDetailsDF['Ticker'] == selectedTickerValue]

        if st.button("Generate & Add Investments"):
            for index, row in stockwiseTradesDF.iterrows():
                if investment_balance == 0:
                    investment_amount = amount
                else:
                    investment_amount = amount + investment_balance

                units_purchased = int(investment_amount / row['trading_price'])
                purchase_amount = row['trading_price'] * units_purchased
                investment_balance = investment_amount - purchase_amount
                add_investment(row['Ticker'], row['Company'],row['Date'], row['trading_price'], investment_amount, purchase_amount, investment_balance, units_purchased)
                
            st.success(f"Added investments for {selectedTickerValue}")

    # Main area to display investments and calculate profit
    # st.header("Investment Records")
    investments_df = get_investments(selectedTickerValue)
    
    if not investments_df.empty:
        st.header(f"Investment History of {investments_df['company'].iloc[0]}")
        st.dataframe(investments_df, hide_index=True)
        
        total_invested = investments_df['investment_amount'].sum()
        # st.subheader(f"Total Amount Invested: ₹{total_invested:,.2f}")
        st.subheader(f"Consolidated Statement for {investments_df['company'].iloc[0]}")

        if st.button("Calculate Profit"):
            overallInvestmentDF = investments_df[investments_df['ticker'] == selectedTickerValue]
            overallInvestmentDF = overallInvestmentDF.sort_values('purchase_date', ascending=True)
            overallInvestmentDF['latest_price'] = overallInvestmentDF.iloc[-1]['purchase_price']
            overallInvestmentDF['current_returns'] = overallInvestmentDF['latest_price'] * overallInvestmentDF['total_shares']
            total_shares = overallInvestmentDF['total_shares'].sum()
            total_purchases = overallInvestmentDF['current_returns'].sum()
            
            profit_loss = total_purchases - total_invested
            # st.dataframe(overallInvestmentDF)
            
            st.write(f"Overall Returns: ₹{total_purchases:,.2f}")
            st.write(f"Overall Invested: ₹{total_invested:,.2f}")
            st.write(f"Shares Purchased: {total_shares}")
            
            if profit_loss >=0:
                st.markdown(f":green[Profit: ${profit_loss:,.2f}]")
            else:
                st.markdown(f":red[Loss: ${profit_loss:,.2f}]")
                
    else:
        st.write("No investments found. Use the sidebar to add some.")

if __name__ == "__main__":
    main()

