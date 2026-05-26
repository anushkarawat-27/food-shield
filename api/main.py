from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from api.routes import events, recommend, regions, simulate, project, scenarios, export

app = FastAPI(title="FoodShield API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/health")
def health() -> dict:
    return {"status": "ok"}


app.include_router(regions.router)
app.include_router(simulate.router)
app.include_router(project.router)
app.include_router(recommend.router)
app.include_router(scenarios.router)
app.include_router(events.router)
app.include_router(export.router)
