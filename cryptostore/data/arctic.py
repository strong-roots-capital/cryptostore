'''
Copyright (C) 2018-2019  Bryant Moscon - bmoscon@gmail.com

Please see the LICENSE file for the terms and conditions
associated with this software.
'''
import pandas as pd
from arctic import Arctic as ar
from arctic import CHUNK_STORE
from cryptofeed.defines import TRADES, L2_BOOK, L3_BOOK

from cryptostore.data.store import Store


class Arctic(Store):
    def __init__(self, connection: str):
        self.data = []
        self.con = ar(connection)

    def aggregate(self, data):
        self.data.extend(data)

    def write(self, exchange, data_type, pair, timestamp):
        chunk_size = None
        df = pd.DataFrame(self.data)
        self.data = []

        if data_type == TRADES:
            df['size'] = df.amount.astype('float64')
            df['price'] = df.price.astype('float64')
            df['date'] = pd.to_datetime(df['timestamp'], unit='s')
            df = df.drop(['pair', 'feed'], axis=1)
            chunk_size = 'H'
        elif data_type in { L2_BOOK, L3_BOOK }:
            df['size'] = df['size'].astype('float64')
            df['price'] = df.price.astype('float64')
            df['date'] = pd.to_datetime(df['timestamp'], unit='s')
            chunk_size = 'T'

        df.set_index('date', inplace=True)
        df = df.drop(['timestamp'], axis=1)
        # All timestamps are in UTC
        df.index = df.index.tz_localize(None)

        if exchange not in self.con.list_libraries():
            self.con.initialize_library(exchange, lib_type=CHUNK_STORE)
        self.con[exchange].append(f"{data_type}-{pair}", df, upsert=True, chunk_size=chunk_size)
