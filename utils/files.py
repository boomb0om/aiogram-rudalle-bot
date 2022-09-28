from PIL import Image
import numpy as np
import cv2
from io import BytesIO
import io
import aiohttp
import base64
import re
import zipfile
import tarfile


def filter_symbols_ruen(s):
    r = re.compile("[а-яА-Яa-zA-Z0-9ё_ ]+")
    return ''.join([symbol for symbol in filter(r.match, s)])

def filter_symbols_filename(s):
    r = re.compile("[a-zA-Z0-9_]+")
    return ''.join([symbol for symbol in filter(r.match, s)])
                
async def download_image(image_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(image_url) as resp:
            if resp.status == 200:
                img = Image.open(BytesIO(await resp.read()))
                return img
            else:
                raise ValueError(f'Status code: {resp.status}')
                
async def download_to_bytes(file_url):
    async with aiohttp.ClientSession() as session:
        async with session.get(file_url) as resp:
            if resp.status == 200:
                file_bytes = BytesIO(await resp.read())
                return file_bytes
            else:
                raise ValueError(f'Status code: {resp.status}')
                
def prepare_archive(zip_bytes, query):
    filename = filter_symbols_ruen(query)+'.zip'
    if filename.strip() == '.zip':
        filename = 'images.zip'
    zip_bytes.seek(0)
    zip_bytes.name = filename
    return zip_bytes, filename

def images_to_archive(pil_images, sharedname):
    buff = BytesIO()
    zf = zipfile.ZipFile(buff, 'w')
    for c, img in enumerate(pil_images):
        img_buff = BytesIO()
        img.save(img_buff, format="PNG")
        zf.write(img_buff, f"{sharedname} {c+1}.png")
    zf.close()
    buff.seek(0)
    buff.name = sharedname+'.zip'
    return buff, sharedname+'.zip'

def pil_image_to_bytes(image, filename, format="JPEG"):
    buff = BytesIO()
    image.save(buff, format=format)
    buff.seek(0)
    buff.name = filename
    return buff
    
def base64_to_bytes(base64string):
    bin_img = base64.b64decode(base64string)
    buff = BytesIO(bin_img)
    return buff