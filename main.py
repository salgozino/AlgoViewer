import dash
from dash.dependencies import Input, Output, State
import dash_table
import dash_auth
import dash_core_components as dcc
import dash_html_components as html
import plotly.graph_objs as go
from flask import Flask
import pandas as pd
from datetime import datetime

#Agrego al path la carpeta de AlgoTrading para sacar el DBtools
import sys
sys.path.append("../AlgoTrading")
import utils.DBtools as DBtools

def get_OR(db='rofex.db'):
    columns = ['date','transactTime','instrumentId_symbol','side','avgPx','cumQty','status','text']
    valid_status = ['FILLED','NEW','CANCELLED','REJECTED']
    df_OR = read_table("ORDERREPORT",db).reset_index()
    df_OR = df_OR[columns].loc[df_OR['status'].isin(valid_status)]
    df_OR.transactTime = pd.to_datetime(df_OR.transactTime,utc=False)
    df_OR.date = pd.to_datetime(df_OR.date)
    df_OR = df_OR.sort_index(ascending=0)
    # df_OR.set_index('transactTime', inplace=True)
    return df_OR
    
def get_tickers(db='rofex.db'):
    return DBtools.read_all_tickers(db)

def read_table(ticker,db='rofex.db',start_date=''):
    return DBtools.read_ticker(ticker,start_date,db)

def getOHLC(df,column_name_price = 'LA_price', column_name_size = 'LA_size', date_column='date',period='1Min'):

    try:
        df.drop_duplicates(subset=date_column, keep='first', inplace=True)
    except:
        pass
    
    if date_column in df.columns.names:
        df.set_index(date_column, inplace=True)
        df.index.name = 'date'
    
    df.index = pd.to_datetime(df.index)
    if column_name_price not in df.columns.values:
        cnames=['open','low','high','close','volume']
        ohlc = pd.DataFrame(columns=cnames)
    else:
        ohlc = df[column_name_price].resample(period).ohlc()
        
    try:
        vol  = df[column_name_size].resample(period).sum()

        ohlcv = pd.concat([ohlc, vol], axis=1, join_axes=[ohlc.index])
        ohlcv.rename(columns={column_name_size:'volumen'}, inplace=True)
        return ohlcv
    except:
        return ohlc
        
def get_ohlc(ticker='RFX20Mar19', period = '1T', db='rofex.db',start_date=''):
    current_df = read_table(ticker,db=db,start_date=start_date)
    current_df = current_df.copy()
    current_df.dropna(axis=1,how='all', inplace=True)
    
    if len(current_df.index)==1:
        ohlc = pd.DataFrame(columns=['date','open','high','low','close','volumen'])
    else:
        price_col = 'IV' if ticker == 'IRFX20' else 'LA_price'
        date_col = 'date' if ticker == 'IRFX20' else 'LA_date'
        try:
            ohlc = getOHLC(current_df,price_col,date_column=date_col, period=period)
        except:
            print("Error getting the OHLC")
            ohlc = pd.DataFrame(columns=['date','open','high','low','close','volumen'])
        ohlc.index = pd.to_datetime(ohlc.index)
    return ohlc

#Initialize variables
db = '../AlgoTrading/rofex.db'
list_of_df = []
tickers = get_tickers(db)
df_OR = get_OR(db)
get_ohlc('IRFX20',db=db)

## create our Flask Server application
def get_valid_usernames():
    valid_users = DBtools.read_table(table='users', db='usernames.db').values.tolist()
    return valid_users

app = dash.Dash(__name__)
auth = dash_auth.BasicAuth(
    app,
    get_valid_usernames()
)


## Set the title to the webpage
app.title = 'AlgoViewer v0.0.2'

markdown_text = '''
# AlgoViewer!  - v0.0.2 alfa
Desde esta app, estaremos visualizando todo lo que hacen los bots. Sus operaciones, ordenes abiertas, etc.
Se debe elegir el activo a graficar (máximo 3 tickers), junto con la fecha de inicio desde la que se quiere graficar.
En la tabla de OrderReport se pueden ver todas las ordenes FILLED CANCELLED or REJECTED de los tickers seleccionados.
'''

#Layout!
app.layout = html.Div(
        id='wrapper',
        className='wrapper',
        children=[
                dcc.Markdown(children=markdown_text),
                html.Div(className='row',children=[
                    html.Div(className='three columns',children=[
                        dcc.Dropdown(
                            id='ticker',
                            options=[{'label': ticker, 'value': ticker} for ticker in tickers if ticker != 'ORDERREPORT'],
                            value="IRFX20",
                            multi=True,
                            )
                        ]),
                    html.Div(className='one column',children=[        
                        dcc.DatePickerSingle(
                            id='date-picker-single',
                            date=datetime.today()
                            )
                        ]),
                ]
                ),
                
                html.Div(className='row', children=[
                    dcc.Graph(id='graph', animate=True)
                    ]),
                
                html.H1("Order Report"),
                html.Div(className="row",children=[
                    dash_table.DataTable(
                        id='OrderReport-table',
                        columns=[{"name": i, "id": i} for i in df_OR.columns],
                        data=df_OR.to_dict("rows"),
                        filtering=True,
                        sorting=True,
                        sorting_type="multi",
                        pagination_mode="fe",
                        pagination_settings={
                            "displayed_pages": 1,
                            "current_page": 0,
                            "page_size": 12,
                        },
                        navigation="page",
                                ),
                ]
                ),
    
                dcc.Interval(
                    id='interval-component',
                    interval=30*1000, # in milliseconds
                    n_intervals=0
                )
        ]
)
    
@app.callback(Output('graph', 'figure'),
    [Input('ticker', 'value'),
    Input('date-picker-single','date'),
    Input('interval-component', 'n_intervals')])
def update_graph(tickers,date,n_intervals):
    if len(tickers) != 0:
        if (len(tickers)> 3) & (type(tickers) is list):
            tickers = tickers[:3]
        data = []
        tickers = tickers if isinstance(tickers,list) else [tickers]
        for i,ticker in enumerate(tickers,1):
            ohlc_graph = get_ohlc(ticker,'1T',db=db,start_date=date)
            data.append(go.Scatter(
                x=ohlc_graph.index,
                y=ohlc_graph.close,
                name=ticker,
                yaxis= 'y' if i==1 else 'y{}'.format(str(i)),
                ))
            
            orders = DBtools.read_orders(ticker,date,db)
            #print(orders)
            # ohlc_graph.dropna(inplace=True)
            if not orders.empty:
                buys = orders[orders['side']=='BUY']
                sells = orders[orders['side']=='SELL']
                if not buys.empty:
                    data.append(go.Scatter(
                        x=buys.date,
                        y=buys.avgPx,
                        name=ticker + ' Buys',
                        yaxis= 'y' if i==1 else 'y{}'.format(str(i)),
                        mode = 'markers',   
                        marker = {'size':12, 'symbol':'triangle-up'}
                        ))   
                if not sells.empty:
                    data.append(go.Scatter(
                        x=sells.date,
                        y=sells.avgPx,
                        yaxis= 'y' if i==1 else 'y{}'.format(str(i)),
                        name = ticker + ' Sells',
                        mode = 'markers',   
                        marker = {'size':12, 'symbol':'triangle-down'}
                        ))   
            
        
        if len(tickers) == 1:
            domain=[0., 1]
        elif len(tickers) == 2:
            domain=[0.15, 1]
        elif len(tickers) == 3:
            domain=[0.275, 1]
        elif len(tickers) == 3:
            domain=[0.4, 1]
        return {
            'data': data,
            'layout': go.Layout(
                        xaxis=dict(
                                    rangeselector=dict(
                                        buttons=list([
                                            dict(count=1,
                                                 label='1h',
                                                 step='hour',
                                                 stepmode='backward'),
                                             dict(count=4,
                                                 label='4h',
                                                 step='hour',
                                                 stepmode='backward'),
                                            dict(count=1,
                                                 label='1d',
                                                 step='day',
                                                 stepmode='backward'),
                                            dict(step='all')
                                        ])
                                    ),
                                    type='date',
                                    domain=domain,
                                ),
                        yaxis={
                            'title':tickers[0],
                            'type':'linear',
                            'position':0.,
                            'visible':True},
                        yaxis2={
                            'overlaying':'y',
                            'type':'linear',
                            'visible':True if len(tickers)>1 else False,
                            'position':0.125,
                            'title':tickers[1] if len(tickers)>1 else '',
                            },
                        yaxis3={
                            'overlaying':'y',
                            'type':'linear',
                            'visible':True if len(tickers)>2 else False,
                            'position':0.25,
                            'title':tickers[2] if len(tickers)>2 else '',
                            },
                        yaxis4={
                            'overlaying':'y',
                            'type':'linear',
                            'visible':True if len(tickers)>3 else False,
                            'position':0.375,
                            'title':tickers[3] if len(tickers)>3 else '',
                            },
            )
        }




@app.callback(Output('OrderReport-table', 'data'),
              [Input('ticker', 'value'),
               Input('interval-component', 'n_intervals')
               ])
def update_table(tickers, n, maxrows=12):
    if type(tickers) != list:
        tickers = [tickers]
    OR = get_OR(db)
    OR = OR[OR['instrumentId_symbol'].str.upper().isin(tickers)]
    return OR.to_dict("rows")


if __name__ == '__main__':
#    app.run_server(debug=False,
#                   host='0.0.0.0',
#                   port=80)
    app.run_server(debug=True,
                   host='127.0.0.1',
                   port=80)
