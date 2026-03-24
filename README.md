# Teams-Project-Management

Creating a virtual environment ensures project dependencies are isolated.

# Windows
python -m venv venv
venv\Scripts\activate

# macOS / Linux
python -m venv venv
source venv/bin/activate

Install all required Python packages listed in requirements.txt:
pip install -r requirements.txt

# Run the application
uvicorn main:app --reload