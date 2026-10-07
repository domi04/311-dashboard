# Philadelphia 311 Dashboard

**Course:** Advanced Programming (CIS-3400-1)

A Streamlit dashboard for Philadelphia 311 requests from July 8 through December 31, 2025. It asks which ZIP codes have more located service requests than a typical ZIP, and what kinds of requests those busy ZIP codes report.

You can view a live demo here: [https://311-dashboard-lrvbanjdgodkfzsvbmd6yw.streamlit.app](https://311-dashboard-lrvbanjdgodkfzsvbmd6yw.streamlit.app)

## Run the dashboard

From this folder:

```bash
pip install -r requirements.txt
streamlit run app.py
```

Open the local URL Streamlit prints, usually [http://localhost:8501](http://localhost:8501).

Use **Start date** and **End date** in the sidebar. Those two controls replace `START_DATE` and `END_DATE` from Notebook 2. The map, the summary numbers, and both charts all use only requests inside that window.

## What the page shows

- **Summary numbers** for the selected dates: all requests, located service requests, the share sitting in the ten busiest ZIP codes, and the busiest ZIP.
- **Active ZIP codes:** a map of Philadelphia. A ZIP code turns blue when it has located service requests in the selected dates. Darker blue means more requests. A ZIP code with none stays gray. Hover a ZIP code to see its count.
- **Busiest ZIP codes:** a bar chart of the ten highest ZIP codes. The dashed line is the median among ZIP codes with at least 1,000 requests in the selected dates. If the window is too short for that, the line uses ZIP codes with at least 20 requests.
- **Request mix:** a stacked bar for those ten ZIP codes. The bands are maintenance, rubbish and recycling, abandoned vehicles, illegal dumping, graffiti, and everything else. Each bar is 100% of that ZIP code, so a wider band is a larger share of the local workload.

## How the ZIP views are built

Information Requests are left out of the map and the ZIP charts. Most of them have no ZIP code, so keeping them would hide the neighborhood pattern. They still count in "Requests in period."

A ZIP code is included only when it falls between 19102 and 19154. The map shapes are Philadelphia's own ZIP code outlines, stored in `philadelphia_zip_codes.geojson`.

These figures are counts of requests, not requests per resident. A larger ZIP code can rank high without having a higher rate.

## Project files

| File | Role |
| --- | --- |
| `app.py` | The Streamlit dashboard |
| `311_2025_dashboard.csv` | Reduced 2025 data the dashboard reads |
| `philadelphia_zip_codes.geojson` | ZIP code outlines for the map |
| `requirements.txt` | Python packages |
| `.streamlit/config.toml` | Light theme for the app |
| `Notebook_1_Prepare_2025_311_Dashboard_Data.ipynb` | Builds `311_2025_dashboard.csv` from the larger 311 file |
| `Notebook_2_Prototype_311_Dashboard (1).ipynb` | Prototypes the date filter and the two charts before Streamlit |
| `311_data_notebook_1.csv` | Larger source file used by Notebook 1 |

Notebook 1 keeps the file smaller by starting on July 8, 2025 and keeping only the columns the dashboard uses: request date, service name, ZIP code, status, month, day of week, and resolution time.
