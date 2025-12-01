import os
import shutil
import uuid
import json
import tempfile
import subprocess

from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse

app = FastAPI()

# Enable CORS for frontend http://localhost:5173
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/api/compare")
async def compare_repos(repoA: list[UploadFile] = File(...),
                        repoB: list[UploadFile] = File(...)):
    """
    Accepts two folder uploads (sent as multiple files),
    writes them to temp directories, then runs normalization.py.
    """
    try:
        # Create temp root
        temp_root = os.path.join(tempfile.gettempdir(), "temp_repos", str(uuid.uuid4()))
        repoA_dir = os.path.join(temp_root, "A")
        repoB_dir = os.path.join(temp_root, "B")
        os.makedirs(repoA_dir, exist_ok=True)
        os.makedirs(repoB_dir, exist_ok=True)

        # Save Repo A files
        for f in repoA:
            dest = os.path.join(repoA_dir, f.filename)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as out:
                out.write(await f.read())

        # Save Repo B files
        for f in repoB:
            dest = os.path.join(repoB_dir, f.filename)
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as out:
                out.write(await f.read())

        # Run your analyzer script
        backend_dir = os.path.dirname(__file__)
        script_path = os.path.join(backend_dir, "normalization.py")

        result = subprocess.run(
            ["python", script_path, repoA_dir, repoB_dir],
            capture_output=True,
            text=True
        )

        if result.returncode != 0:
            raise HTTPException(status_code=500, detail=f"Analyzer failed: {result.stderr}")

        # Read the JSON file produced by normalization.py
        out_json_path = os.path.join(backend_dir, "detailed_output_fixed.json")
        if not os.path.exists(out_json_path):
            raise HTTPException(status_code=500, detail="detailed_output_fixed.json not found")

        with open(out_json_path, "r", encoding="utf-8") as f:
            data = json.load(f)

        # Return parsed JSON to frontend
        return JSONResponse(content=data)

    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup temp folders
        try:
            shutil.rmtree(temp_root)
        except Exception:
            pass
