import uvicorn
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles

from config import PORT
from db.database import init_db
from dashboard.routes import router

app = FastAPI(title="Whoop Dashboard")
app.include_router(router)


@app.on_event("startup")
async def startup():
    init_db()


if __name__ == "__main__":
    uvicorn.run("main:app", host="127.0.0.1", port=PORT, reload=True)
