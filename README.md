# 🏏 Rajasthan Royals Scouting Engine — SupeRR Selector

An enterprise-grade cricket decision support system and situational pressure analytics engine built for **Rajasthan Royals Scouting & Talent Acquisition** for **SupeRR Selector Season 2**.

The system ingests delivery-level records across **IPL (2022–2026)** and **T20 Internationals (T20I)** to quantify clutch situational performance and discover high-value **Uncapped Prospects** who deliver when the game is on the line.

---

## ⚡ Quick Start (VS Code / Cursor / Terminal)

### Prerequisites
- Python 3.9+ (tested on Python 3.10, 3.11, 3.12)
- pip

### 1. Open the project in VS Code / Cursor
Open the root project folder in VS Code or Cursor:
```bash
code .
```

### 2. (Optional) Create a virtual environment
```bash
python -m venv .venv

# Windows (PowerShell):
.venv\Scripts\Activate.ps1

# Windows (Command Prompt):
.venv\Scripts\activate.bat

# macOS / Linux:
source .venv/bin/activate
```

### 3. Install dependencies
```bash
pip install -r requirements.txt
```

### 4. Run the Scouting Engine
The SQLite database (`db.sqlite3`) is **already pre-migrated, loaded with 200,999 deliveries, and pre-computed with all pressure indices**. You can run immediately:

**Windows:**
Double-click `start_server.bat` or run:
```powershell
python manage.py runserver 127.0.0.1:8000
```

**macOS / Linux:**
```bash
chmod +x run.sh
./run.sh
```

Open your browser and navigate to:
👉 **[http://127.0.0.1:8000](http://127.0.0.1:8000)**

---

## 🎯 SupeRR Selector Official Submission: Top 10 Picks

### 🏏 Top 10 Batters Under Pressure (Uncapped Prospects)
| Rank | Player Name | Pressure Score | Pressure SR | Normal SR | Runs (Balls) | Matches |
|:----:|:------------|:--------------:|:-----------:|:---------:|:------------:|:-------:|
| **1** | **Prabhsimran Singh** | **80.3** | 193.62 | 148.87 | 273 (141) | 63 |
| **2** | **Sai Sudharsan** | **79.8** | 170.13 | 137.93 | 541 (318) | 57 |
| **3** | **Shashank Singh** | **79.5** | 187.68 | 158.42 | 655 (349) | 42 |
| **4** | **Lalit Yadav** | **78.4** | 129.66 | 114.75 | 153 (118) | 16 |
| **5** | **Anuj Rawat** | **78.0** | 144.34 | 124.69 | 153 (106) | 21 |
| **6** | **M Shahrukh Khan** | **76.1** | 169.31 | 147.20 | 320 (189) | 43 |
| **7** | **Nehal Wadhera** | **75.8** | 147.73 | 139.12 | 325 (220) | 45 |
| **8** | **Sameer Rizvi** | **75.7** | 181.11 | 152.00 | 163 (90) | 18 |
| **9** | **Ayush Badoni** | **74.4** | 156.56 | 134.19 | 573 (366) | 60 |
| **10** | **Rahul Tewatia** | **73.7** | 157.10 | 137.89 | 564 (359) | 57 |

---

### 🎳 Top 10 Bowlers Under Pressure (Uncapped Prospects)
| Rank | Player Name | Pressure Score | Pressure Econ | Normal Econ | Wickets | Pressure Overs | Matches |
|:----:|:------------|:--------------:|:-------------:|:-----------:|:-------:|:--------------:|:-------:|
| **1** | **Gurjapneet Singh** | **89.6** | 7.21 | 8.12 | 8 | 15.4 | 12 |
| **2** | **Rasikh Salam** | **81.6** | 9.04 | 9.75 | 23 | 39.1 | 28 |
| **3** | **Anshul Kamboj** | **81.2** | 9.64 | 9.88 | 15 | 25.0 | 28 |
| **4** | **Sai Kishore** | **78.4** | 7.87 | 7.92 | 11 | 18.1 | 28 |
| **5** | **Vaibhav Arora** | **78.2** | 10.08 | 9.65 | 19 | 42.4 | 44 |
| **6** | **Akash Madhwal** | **76.4** | 9.07 | 9.42 | 11 | 20.5 | 17 |
| **7** | **Sakib Hussain** | **75.6** | 7.49 | 8.20 | 8 | 19.3 | 11 |
| **8** | **Suyash Sharma** | **73.5** | 9.06 | 8.52 | 11 | 42.5 | 43 |
| **9** | **Vyshak Kumar** | **73.0** | 9.80 | 10.15 | 9 | 19.2 | 27 |
| **10** | **Harsh Dubey** | **72.3** | 9.56 | 8.92 | 9 | 14.0 | 15 |

---

## 📐 Pressure Modeling Methodology

### 1. Delivery Pressure Signal (SSPE)
Each ball delivery receives a situational pressure weight $\ge 1.5$ based on match context:
- **Death Overs:** Overs 17 to 20 (`overid >= 16`) $\rightarrow +1.0$
- **Powerplay Closure:** Overs 5 to 6 (`overid 4-5`) $\rightarrow +0.5$
- **High Required Run Rate:** Innings 2, $RRR > 14$ $\rightarrow +2.0$ | $RRR \in [12, 14]$ $\rightarrow +1.5$ | $RRR \in [10, 12]$ $\rightarrow +1.0$
- **Clutch Finish:** Runs needed $\le 15$ with $\le 24$ balls remaining $\rightarrow +0.5$
- **Collapse Resistance:** Wickets fallen $\ge 7$ $\rightarrow +1.0$ | $5-6$ wickets $\rightarrow +0.5$
- **Knockout Fixture Multiplier:** Qualifier, Eliminator, Semi-Final, Final $\rightarrow \times 1.5$ multiplier

### 2. Batting Pressure Index (0–100)
$$\text{Score} = \left[ 0.40 \cdot \left(\frac{\text{Pressure SR}}{\text{Normal SR}}\right) + 0.30 \cdot \left(\frac{\text{Pressure Boundary Rate}}{\text{Normal Boundary Rate}}\right) + 0.30 \cdot \min\left(1.0, \frac{\text{Pressure Balls}}{150}\right) \right] \times 70.0$$

### 3. Bowling Pressure Index (0–100)
$$\text{Score} = \left[ 0.45 \cdot \left(\frac{\text{Normal Econ}}{\text{Pressure Econ}}\right) + 0.35 \cdot \left(\frac{\text{Pressure Wicket Rate}}{\text{Overall Wicket Rate}}\right) + 0.20 \cdot \min\left(1.0, \frac{\text{Pressure Balls}}{200}\right) \right] \times 70.0$$

---

## 📁 Project Structure

```
RR_Player_Intelligence/
├── manage.py                          # Django entry point
├── requirements.txt                   # Minimal production dependencies
├── start_server.bat                   # 1-click launch for Windows
├── run.sh                             # 1-click launch for macOS / Linux
├── db.sqlite3                         # Fully pre-populated SQLite database (200k+ rows)
├── README.md                          # Documentation & methodology guide
├── data/                              # CSV datasets (competitions, matches, balls, etc.)
├── rr_intel/                          # Django project configuration
│   ├── __init__.py
│   ├── settings.py                    # ALLOWED_HOSTS=['*'], REST_FRAMEWORK
│   ├── urls.py                        # Root URL routing
│   └── wsgi.py
└── core/                              # Main intelligence engine
    ├── models.py                      # Data models with is_uncapped flag
    ├── pressure.py                    # Situational delivery pressure engine
    ├── metrics.py                     # Batting & bowling pressure algorithms
    ├── views.py                       # REST API endpoints
    ├── urls.py                        # Core API routes
    ├── management/commands/
    │   └── load_data.py               # Data ingestion & calculation command
    └── templates/core/
        └── index.html                 # Enterprise single-page scouting application
```

---

## 🚀 Pushing to GitHub

```bash
git init
git add .
git commit -m "feat: Rajasthan Royals Scouting Engine - SupeRR Selector Season 2"
git branch -M main
git remote add origin <your-github-repo-url>
git push -u origin main
```
