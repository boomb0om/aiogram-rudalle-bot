import numpy as np
from PIL import Image
import os
import cv2
import re
import base64
from io import BytesIO
import time

import kfserving

import torch
import ruclip

from rudalle.pipelines import generate_images, show, super_resolution, cherry_pick_by_ruclip
from rudalle import get_rudalle_model, get_tokenizer, get_vae, get_realesrgan
from rudalle.utils import seed_everything
import requests
from PIL import Image, ImageDraw

from PIL import Image
import io

import sys
sys.path.insert(0, './rudalle-aspect-ratio')
from rudalle_aspect_ratio import RuDalleAspectRatio

from app.utils import *
from utils.logger import setup_logger
import config
    
    
class KFServingArgumentModel(kfserving.KFModel):

    def __init__(self, name: str, logger, gpu):
        super().__init__(name)
        self.name = name
        self.logger = logger
        
        self.gpu_id = gpu
        self.device = torch.device(f'cuda:{self.gpu_id}')
        self.cache_dir = './weights'
        self.ruclip_version = 'ruclip-vit-large-patch14-336'
        
        self.gpu = True
        self.ready = False

    def load(self):
        self.dalle = get_rudalle_model('Malevich', pretrained=True, fp16=True, device=self.device)
        self.tokenizer = get_tokenizer(cache_dir=self.cache_dir)
        self.vae = get_vae(dwt=False, cache_dir=self.cache_dir).to(self.device)
        self.clip, self.processor = ruclip.load(self.ruclip_version, device=self.device, cache_dir=self.cache_dir)
        self.clip_predictor = ruclip.Predictor(self.clip, self.processor, self.device, bs=8)
        self.realesrgan = get_realesrgan('x2', device=self.device, cache_dir=self.cache_dir)
        
        self.ready = True
        
        
    def task_generate(self, request):
        query = request["query"]
        images_num = int(request["images_num"])
        rerank_top = int(request["rerank_top"])
        aspect_ratio = float(request["aspect_ratio"])

        top_k, top_p = 2048, 0.99
        
        if aspect_ratio == 1:
            bs = config.rudalle_bs
            pil_images, scores = generate_images(query, self.tokenizer, self.dalle, self.vae, 
                                                 top_k=top_k, images_num=images_num, 
                                                 top_p=top_p, bs=bs)
        else:
            bs = config.rudalle_aspect_ratio_bs
            rudalle_ar = RuDalleAspectRatio(
                dalle=self.dalle, vae=self.vae, tokenizer=self.tokenizer,
                aspect_ratio=aspect_ratio, bs=bs, device=self.device
            )
            
            pil_images = []
            
            k, m = images_num//bs, images_num%bs
            for images_to_gen_part in [bs]*k+[m]:
                if images_to_gen_part == 0:
                    continue
                _, pil_images_part = rudalle_ar.generate_images(query, top_k=top_k, top_p=top_p, images_num=images_to_gen_part)
                pil_images.extend(pil_images_part)
        
        top_images, _ = cherry_pick_by_ruclip(pil_images, query, self.clip_predictor, rerank_top)
        
        # make grid image
        if aspect_ratio == 1:
            nrow = max(len(top_images)//8, 8) if len(top_images)>24 else max(len(top_images)//4, 4)
            if len(top_images) == 36:
                nrow = 6
                
            if len(top_images) == 1:
                grid_image = top_images[0].resize((512, 512))
                grid_image_numbers = put_text(top_images[0].resize((512,512)), str(1))
            else:
                grid_image = merge_pil_images(top_images, nrow=nrow, ratio=1)
                grid_image_numbers = merge_pil_images_with_numbers(top_images, nrow=nrow)
        
            grid_images = [grid_image, grid_image_numbers]
            grid_images = [encode_img(np.array(img), imgformat="JPEG") for img in grid_images]
            
            sr_images = super_resolution(super_resolution(top_images, self.realesrgan), self.realesrgan)
            sr_images = [encode_img(np.array(img), imgformat="JPEG") for img in sr_images]
                
            return {"ok": True, "grid_images": grid_images, "sr_images": sr_images}
        else:
            if 1 < aspect_ratio <= 2:
                nrow = min(len(top_images)//4, 4) if len(top_images)>=12 else min(len(top_images)//2, 2)
            elif 2 < aspect_ratio:
                nrow = 2 if len(top_images)>=4 else 1
            if 1/2 <= aspect_ratio < 1:
                nrow = max(len(top_images)//4, 4) if len(top_images)>=12 else max(len(top_images)//2, 2)
            elif aspect_ratio < 1/2:
                nrow = 4 if len(top_images)>=4 else len(top_images)
            grid_image = merge_pil_images(top_images, nrow=nrow, ratio=aspect_ratio)
            
            grid_images = [grid_image]
            grid_images = [encode_img(np.array(img), imgformat="JPEG") for img in grid_images]
            
            sr_images = super_resolution(super_resolution(top_images, self.realesrgan), self.realesrgan)
            sr_images = [encode_img(np.array(img), imgformat="JPEG") for img in sr_images]
        
            return {"ok": True, "grid_images": grid_images, "sr_images": sr_images}
        
    
    def predict(self, request):
        try:
            result_data = self.task_generate(request)
        except Exception as err:
            info_str = f"query={request['query']} | images_num={request['images_num']} | " +\
                       f"rerank_top={request['rerank_top']} | aspect_ratio={request['aspect_ratio']}"
            self.logger.exception(f'Error while generating images: {err}\n INFO: {info_str}')
            return {"ok": False, "error": str(err)}
            
        return result_data
    
    
if __name__ == "__main__":
    logger = setup_logger(f'app_{config.kfserving_name}_{config.kfserving_http_port}.log')
    logger.info(f'Using device cuda: {config.gpu_id}')
    
    model = KFServingArgumentModel(config.kfserving_name, logger, config.gpu_id)
    model.load()
    kfserving.KFServer(workers=1, http_port=config.kfserving_http_port).start([model])