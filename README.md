# podcast-episode-script-generator
## Quick Start

### Backend
```bash
python3 -m venv .venv  

# For Mac
source .venv/bin/activate

# For Window
.venv\Scripts\Activate.ps1

pip install -r requirements.txt

# .env
echo "GOOGLE_API_KEY=YOUR_KEY" > .env

# run API
uvicorn src.main:app --reload

# frontend
cd frontend
python -m http.server 5500
