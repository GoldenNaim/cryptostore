'''
Copyright (C) 2018-2019  Bryant Moscon - bmoscon@gmail.com

Please see the LICENSE file for the terms and conditions
associated with this software.
'''
from multiprocessing import Process, Queue
import asyncio
import logging
import json

from cryptostore.spawn import Spawn
from cryptostore.config import Config
from cryptostore.log import get_logger


LOG = get_logger('cryptostore', 'cryptostore.log', logging.INFO)


class Cryptostore:
    def __init__(self):
        self.queue = Queue()
        self.spawner = Spawn(self.queue)
        self.running_config = {}

    
    async def _load_config(self, start, stop):
        LOG.info("start: %s stop: %s", str(start), str(stop))
        for exchange in stop:
            self.queue.put(json.dumps({'op': 'stop', 'exchange': exchange}))
            
        for exchange in start:
            self.queue.put(json.dumps({'op': 'start', 'exchange': exchange, 'data': self.running_config['exchanges'][exchange]}))
    
    async def _reconfigure(self, config):
        stop = []
        start = []

        if self.running_config != config:
            if not config or 'exchanges' not in config or len(config['exchanges']) == 0:
                # shut it all down
                stop = list(self.running_config['exchanges'].keys()) if 'exchanges' in self.running_config else []
                self.running_config = config
            elif not self.running_config or 'exchanges' not in self.running_config or len(self.running_config['exchanges']) == 0:
                # nothing running currently, start it all
                self.running_config = config
                start = list(self.running_config['exchanges'].keys())
            else:
                for e in config['exchanges']:
                    if e in self.running_config['exchanges'] and config['exchanges'][e] == self.running_config['exchanges'][e]:
                        continue
                    elif e not in self.running_config['exchanges']:
                        start.append(e)
                    else:
                        stop.append(e)
                        start.append(e)
                
                for e in self.running_config['exchanges']:
                    if e in config['exchanges'] and config['exchanges'][e] == self.running_config['exchanges'][e]:
                        continue
                    elif e not in config['exchanges']:
                        stop.append(e)
                    else:
                        stop.append(e)
                        start.append(e)
            self.running_config = config
        await self._load_config(list(set(start)), list(set(stop)))

    def run(self):
        LOG.info("Starting cryptostore")
        self.spawner.start()
        LOG.info("Spawner started")
        
        loop = asyncio.get_event_loop()
        self.config = Config(callback=self._reconfigure)
        LOG.info("Cryptostore started")
        loop.run_forever()
