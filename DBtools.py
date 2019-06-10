"""
Conections to the database.
The database has an table for the ORDERREPORT and one table for one ticker that
was monitored, en each table of each ticker, different market data could be 
found. Y have to perform a normalization of the columns.
"""
import sqlite3
import pandas as pd
from datetime import datetime
import logging

def rename_table(table):
    return table.replace(".","").replace("-","").replace('/','').replace(" ","").upper()

def make_connection(db_file='rofex.db'):
    """
    Create the connection with the file
    """
    try:
        con = sqlite3.connect(db_file)
        # con.execute("PRAGMA journal_mode=WAL")
        #journal_mode=Wal prevent the writers lock the database for the readeers
        return con
    except sqlite3.Error as e:
        logging.error(e)
        create_db(db_file)
        print(e)
    return None

def create_db(db_file='rofex.db',schema='schema.sql'):
    with open(schema) as fp:
        con = make_connection(db_file)
        cur = con.cursor()
        cur.executescript(fp.read())

def read_table(table='RFX20Mar19', db = 'rofex.db',conn = None):
    """
    Read all the data in the table specified.
    The table name is equivalent to the ticker of the asset.
    """
    table = rename_table(table)
    if conn == None:
        conn = make_connection(db)
    query = "SELECT * FROM {}".format(table)
    df = pd.read_sql(query, conn)
    return df

def read_table_old(table='RFX20Mar19', db = 'rofex.db',conn = None):
    """
    Read all the data in the table specified.
    The table name is equivalent to the ticker of the asset.
    """
    table = rename_table(table)
    if conn == None:
        conn = make_connection(db)
    query = "SELECT * FROM {}".format(table)
    df = pd.read_sql(query, conn)
    return df
    
def export_entire_table(df, table, db='rofex.db', conn = None):
    """
    Export the entire DF to a table, replacing all the data if the table already axist
    """
    table = rename_table(table)
    if conn == None:
        conn = make_connection(db)
    if isinstance(df,dict):
        df = pd.DataFrame([df])
        try:
            df.set_index('date',inplace=True)
        except:
            logging.debug("No date column for set index in new table")
    df.to_sql(table, conn, if_exists='replace')
    conn.commit()
    print("New Table generated")
    
def append_rows(df,table, db='rofex.db', conn = None):
    """
    Append information to the table in the database.
    The code will look the last value in the table, and append the new values from the dataFrame
    """
    table = rename_table(table)
    if conn == None:
        conn = make_connection(db)
        # c = conn.cursor()
    try:
        df.to_sql(table, conn, if_exists='append')
    except:
        logging.error("Problems exporting the new data to de database. a new table is created.")
        export_entire_table(df,table,db,conn)
    
def read_ticker(table,start_date='',db='rofex.db',conn=None):
    """
    Read the information of a ticker, from the specified start date.
    The start date must be a string with the format '%Y-%m-%d'
    """
    table = rename_table(table)
    # print(ticker)
    if conn == None:
        # print('Opening Connection with the DB')
        conn = make_connection(db)
    if start_date == '':
        query = "SELECT * FROM {}".format('"'+table+'"')
    else:
        query = 'SELECT * FROM "{}" WHERE date>date("{}")'.format(table, start_date)
    df = pd.read_sql(query, conn)
    df.set_index('date',inplace=True)
    # print(df.tail()) 
    return df
    
def read_last_price(table,db='rofex.db',conn=None):
    """
    Read the last price of a ticker, from the DB
    """
    table = rename_table(table)
    if conn == None:
        conn = make_connection(db)
    query = "SELECT LA_price FROM {} ORDER BY date DESC LIMIT 1".format('"'+table+'"')
    c = conn.cursor()
    value = c.execute(query).fetchone()
    return value[0]

def read_last_row(table,db='rofex.db',conn=None):
    """
    Read the last price of a ticker, from the DB
    """
    table = rename_table(table)
    if conn == None:
        conn = make_connection(db)
        conn.row_factory = sqlite3.Row
    query = "SELECT * FROM {} ORDER BY date DESC LIMIT 1".format('"'+table+'"')
    c = conn.cursor()
    row = c.execute(query).fetchone()
    return dict(row)

def read_last_row_df(table,db='rofex.db',conn=None):
    """
    Read the last price of a ticker, from the DB
    """
    table = rename_table(table)
    if conn == None:
        conn = make_connection(db)
    query = "SELECT * FROM {} ORDER BY date DESC LIMIT 1".format('"'+table+'"')
    c = conn.cursor()
    df = pd.read_sql(query, conn)
    return df

def sql_append(data,table,db='rofex.db',conn = None):
    """
    En vez de hacer un append desde pandas, lo hago directamente desde sqlite, con la lista de data, antes de pasarlo por dataframe.
    """
    table = rename_table(table)
    if conn == None:
        conn = make_connection(db)
    cur = conn.cursor()
    query = "SELECT name FROM sqlite_master WHERE type='table' AND name='{}'".format(table);
    table_sql = cur.execute(query).fetchone()
    if isinstance(table_sql,tuple):
        table_sql = table_sql[0]
        
    try:
        if table_sql != None:
            if table_sql.upper() == table.upper():
                columns = ', '.join(data.keys())
                placeholders = ':'+', :'.join(data.keys())
                query = 'INSERT INTO %s (%s) VALUES (%s)' % (table,columns, placeholders)
                cur.execute(query, data)
                conn.commit()
            else:
                export_entire_table(data,table,db,conn)
        else:
            export_entire_table(data,table,db,conn)
    except:
        logging.exception("Missing the value due to error in sql_append: Table:{}; data:{}".format(table,data))

def read_all_tickers(db='rofex.db',conn=None):
    if conn == None:
        conn = make_connection(db)
    cur = conn.cursor()
    query = "SELECT name FROM sqlite_master WHERE type='table'";
    tickers = cur.execute(query).fetchall()
    ticks = []
    for t in tickers:
        ticks.append(t[0])
    return ticks
    
    
if __name__ == '__main__':
    # print(read_last_price("RFX20Mar19"))
    start = datetime.now()
    # df = read_ticker('RFX20Mar19')
    # print('Read ticker information takes:', (datetime.now()-start).total_seconds(), 'seconds')
    # print(df.tail())
    row = read_last_row("I.RFX20")
    print(row['LA_price'])
    print('Read ticker information takes:', (datetime.now()-start).total_seconds(), 'seconds')
