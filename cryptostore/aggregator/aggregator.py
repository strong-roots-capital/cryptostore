'''
Copyright (C) 2018-2019  Bryant Moscon - bmoscon@gmail.com

Please see the LICENSE file for the terms and conditions
associated with this software.
'''
import asyncio
from multiprocessing import Process
import time
import logging

import redis

from cryptostore.aggregator.parquet import Parquet
from cryptostore.aggregator.arctic import Arctic
from cryptostore.config import Config


LOG = logging.getLogger('cryptostore')


class Aggregator(Process):
    def __init__(self, config_file=None):
        self.config_file = config_file
        super().__init__()

    def run(self):
        loop = asyncio.get_event_loop()
        self.config = Config()
        loop.create_task(self.loop())
        loop.run_forever()

    def __storage(self):
        if self.config.storage == 'parquet':
            return Parquet()
        elif self.config.storage == 'arctic':
            return Arctic(self.config.arctic)
        else:
            raise ValueError("Store type not supported")

    async def loop(self):
        while True:
            r = redis.Redis(self.config.redis['ip'], port=self.config.redis['port'], decode_responses=True)
            for exchange in self.config.exchanges:
                for dtype in self.config.exchanges[exchange]:
                    for pair in self.config.exchanges[exchange][dtype]:
                        store = self.__storage()
                        LOG.info(f'Reading {dtype}-{exchange}-{pair}')
                        data = r.xread({f'{dtype}-{exchange}-{pair}': '0-0'})

                        if len(data) == 0:
                            continue

                        agg = []
                        ids = []
                        for update_id, update in data[0][1]:
                            ids.append(update_id)
                            agg.append(update)

                        store.aggregate(agg)
                        store.write(exchange, dtype, pair, time.time())
                        r.xdel(f'{dtype}-{exchange}-{pair}', *ids)
            await asyncio.sleep(self.config.storage_interval)
