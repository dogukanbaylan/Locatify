# Locatify

Web app that searches Google Maps with Playwright, previews business listings, and downloads them as an Excel file.

## Setup (Windows)

```powershell
python -m venv venv
venv\Scripts\activate
python -m pip install -r requirements.txt
python -m playwright install chromium
python main.py
```

Open http://127.0.0.1:8000

## Setup (Mac / Linux)

```bash
python3 -m venv venv
source venv/bin/activate
python -m pip install -r requirements.txt
python -m playwright install chromium
python main.py
```

The app launches Chromium only, so `python -m playwright install chromium` is enough. `python -m playwright install` installs every Playwright browser.

## Use

1. Enter a search that includes the place, for example `Konya restoran`.
2. Choose how many results to read (1–40).
3. Leave **Show browser window** off to run headless, or turn it on to watch Chromium.
4. Press **Start scraping**. Rows fill in as each listing is opened.
5. Press **Download Excel** when the run finishes.

Direct file download, without the page:

```powershell
curl "http://127.0.0.1:8000/api/search?query=konya+restoran&max_results=10" -o results.xlsx
```

Phone numbers that Google Maps does not publish are left blank. Review counts are saved when Maps shows them. A logged-out limited view often hides that number. A consent dialog or bot check can block a run; turn on **Show browser window** and try again.

Automated collection can conflict with Google’s terms. Use it for data you are allowed to collect.
