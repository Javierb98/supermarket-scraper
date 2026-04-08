#!/bin/bash
cd /home/node-admin/scraper
source venv/bin/activate
python main.py
python pipeline/normalize.py
python pipeline/market_average.py
bash /home/node-admin/scraper/push_to_droplet.sh
