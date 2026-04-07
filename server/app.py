from env.environment import app
import uvicorn


def main():
    """Entry point for OpenEnv validator"""
    return app


if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=7860)