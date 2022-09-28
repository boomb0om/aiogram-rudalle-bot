import numpy as np
from PIL import Image
import os
import cv2
import re
import base64
from io import BytesIO
import time
from datetime import datetime
from rudalle.utils import pil_list_to_torch_tensors
import requests
from PIL import Image, ImageDraw
import torch
import torchvision
from datetime import datetime


def chunks(lst, n):
    """Yield successive n-sized chunks from lst."""
    for i in range(0, len(lst), n):
        yield lst[i:i + n]

def decode_img(img_b64):
    bin_img = base64.b64decode(img_b64)
    buff = BytesIO(bin_img)
    return Image.open(buff)

def encode_img(img: np.ndarray, imgformat="PNG") -> str:
    buff = BytesIO()
    Image.fromarray(img).save(buff, format=imgformat)
    img_b64 = base64.b64encode(buff.getvalue()).decode('utf-8')
    return img_b64

def merge_pil_images(pil_images, nrow=16, ratio=1):
    if ratio >= 1:
        resize_shape = (int(192*ratio), 192)
    else:
        ratio = 1/ratio
        resize_shape = (192, int(192*ratio))
    merged_images = [pil_image.resize(resize_shape) for pil_image in pil_images]
    merged_images = pil_list_to_torch_tensors(merged_images)
    merged_images = torchvision.utils.make_grid(merged_images, nrow=nrow)
    merged_images = torchvision.transforms.functional.to_pil_image(merged_images.detach())
    return merged_images

def put_text(pil_image, text):
    image = np.array(pil_image)
    overlay = image.copy()
    output = image.copy()
    font = cv2.FONT_HERSHEY_SIMPLEX
    origin = (int(pil_image.size[0]/16),int(pil_image.size[0]/6))
    fontScale = 1.65
    color = (0, 0, 0) 
    thickness = 3
    image = cv2.putText(overlay, text, origin, font, fontScale, color, thickness, cv2.LINE_AA) 
    alpha = 0.75
    cv2.addWeighted(overlay, alpha, output, 1 - alpha, 0, output)
    return Image.fromarray(output)

def merge_pil_images_with_numbers(pil_images, nrow=6):
    merged_images = [put_text(pil_image.resize((512,512)), str(i+1)).resize((192, 192)) for i, pil_image in enumerate(pil_images)]
    merged_images = pil_list_to_torch_tensors(merged_images)
    merged_images = torchvision.utils.make_grid(merged_images, nrow=nrow)
    merged_images = torchvision.transforms.functional.to_pil_image(merged_images.detach())
    return merged_images