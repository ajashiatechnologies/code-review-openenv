# server/app.py - Official wrapper for Hugging Face + OpenEnv
from env.environment import app

# Expose 'app' directly - this is what HF Space and OpenEnv expect
__all__ = ["app"]

def main():
    """Entry point used by pyproject.toml"""
    import uvicorn
    uvicorn.run("server.app:app", host="0.0.0.0", port=7860, log_level="info")

if __name__ == "__main__":
    main()