"""Bootstrap public source caches; no personal credentials required."""
import json
from pathlib import Path
import requests

ROOT = Path(__file__).resolve().parents[1]
RAW = ROOT/'data/raw'
PUBLIC_DEMO = 'aqi_demo_wbf92Qx21zX-Wa_Tg8Dx1nXe'

def download(url,path,**kwargs):
    path.parent.mkdir(parents=True,exist_ok=True)
    if path.exists():
        print('Cached',path.name)
        return
    response = requests.get(url,timeout=180,**kwargs)
    response.raise_for_status()
    if path.suffix == '.zip' and not response.content.startswith(b'PK'):
        raise ValueError('Expected ZIP response; download may require authentication')
    path.write_bytes(response.content)
    print('Downloaded',path.name,len(response.content))

download('https://airquality.xkdr.org/v1/stations',RAW/'xkdr_stations.csv',
         headers={'Authorization':f'Bearer {PUBLIC_DEMO}'},params={'city':'Delhi','format':'csv'})
download('https://www.kaggle.com/api/v1/datasets/download/rohanrao/air-quality-data-in-india',
         RAW/'kaggle/air-quality-data-in-india.zip')
download('https://www.kaggle.com/api/v1/datasets/list',RAW/'kaggle/catalog.json',
         params={'search':'air-quality-data-in-india','user':'rohanrao'})
