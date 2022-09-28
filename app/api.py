from PIL import Image
from io import BytesIO
import numpy as np
import os
import logging

import asyncio
import aiohttp


class KFServingAPI:
    def __init__(self, url):
        self.url = url
        self.timeout = aiohttp.ClientTimeout(total=None)
        self.session = aiohttp.ClientSession(timeout=self.timeout)
        
        self.queue = []
        self.wait_delay = 2
        
    async def task_generate(self, user_id, query, images_to_gen, aspect_ratio):
        data = {   
            "task": "generate",
            "query": query,
            "images_num": images_to_gen,
            "aspect_ratio": aspect_ratio,
            "rerank_top": images_to_gen 
        }
        return await self.push_infer(user_id, data)
    
    async def push_infer(self, user_id, data):
        self.queue.append(user_id)
        
        while self.queue[0] != user_id: # ждем очередь
            await asyncio.sleep(self.wait_delay)
        
        r = await self.session.post(self.url, json=data)
        self.queue.pop(0)
        
        if r.status != 200:
            return {'ok': False, 'error': f'Response status code == {r.status}'}
        
        data = await r.json()
        return data