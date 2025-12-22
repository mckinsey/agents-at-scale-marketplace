import uvicorn
from .config import settings


def main():
    uvicorn.run(
        "file_api.app:app",
        host=settings.host,
        port=settings.port,
        reload=False,
    )


if __name__ == "__main__":
    main()
