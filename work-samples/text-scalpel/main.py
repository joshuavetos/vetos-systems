import uvicorn
from src.text_scalpel.api import app

if __name__ == "__main__":
    # Launch the server
    uvicorn.run(app, host="0.0.0.0", port=8000)
