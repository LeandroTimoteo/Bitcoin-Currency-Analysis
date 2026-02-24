# Bitcoin Currency Analysis

![Python](https://img.shields.io/badge/Python-3.x-3776AB?logo=python&logoColor=white)
![Streamlit](https://img.shields.io/badge/Streamlit-app-FF4B4B?logo=streamlit&logoColor=white)
![Plotly](https://img.shields.io/badge/Plotly-charts-3F4F75?logo=plotly&logoColor=white)
![Last commit](https://img.shields.io/github/last-commit/LeandroTimoteo/Bitcoin-Currency-Analysis)
![Stars](https://img.shields.io/github/stars/LeandroTimoteo/Bitcoin-Currency-Analysis?style=social)

An exchange-style **crypto dashboard** built with **Streamlit**. It shows real-time market snapshots, fiat conversions, and candlestick charts.

## Features

- Market cards for major cryptocurrencies (price + % change)
- Fiat conversion (USD/BRL/EUR/GBP)
- Quick converter (amount → fiat)
- Binance-style dark UI
- Candlestick chart (Plotly)
- Auto-refresh toggle

## Screenshots

Add screenshots to `assets/screenshots/` and keep the filenames below (or update the paths):

![Dashboard](assets/screenshots/dashboard.png)
![Candlestick chart](assets/screenshots/chart.png)

## Tech Stack

- Python
- Streamlit
- Plotly
- yfinance
- pandas / numpy

## Run locally (Windows / PowerShell)

1. Create and activate a virtual environment (optional if you already have one):

   ```powershell
   python -m venv .venv
   .\.venv\Scripts\Activate.ps1
   ```

2. Install dependencies:

   ```powershell
   pip install -r requirements.txt
   ```

3. Start the app:

   ```powershell
   .\run_app.ps1 -Port 8502
   ```

Open: `http://127.0.0.1:8502`

## Run without the launcher

```powershell
streamlit run .\Scripts\app.py --server.address 127.0.0.1 --server.port 8502
```

## Deploy (Streamlit Community Cloud)

1. Push this repository to GitHub.
2. In Streamlit Community Cloud, select this repo and set:
   - **Main file path**: `Scripts/app.py`
3. Deploy.

## Project Structure

- `Scripts/app.py` — Streamlit app
- `run_app.ps1` — Starts Streamlit and opens the browser
- `requirements.txt` — Python dependencies

## Notes

- Market data and FX rates come from **yfinance**.
- If yfinance is temporarily unavailable, some values may show as `—`.

## 👨‍💻 Author

Leandro Timóteo Silva — Systems Analyst

- 📧 E-mail: leandrinhots6@gmail.com  
- 💼 LinkedIn: linkedin.com/in/leandro-timóteo-ads  
- 📱 WhatsApp: 83987830223
