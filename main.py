from app.config import config
import uvicorn

def main():
    uvicorn.run(
        "app:api",
        host=config.HOST,
        port=config.PORT,
        reload=True,
        log_level="debug" if config.DEBUG else "info",
    )


if __name__ == "__main__":
    main()