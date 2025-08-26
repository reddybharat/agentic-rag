from fastapi import FastAPI
from src.routers.graph import router as graph_router

app = FastAPI()

# Register graph-related APIs
app.include_router(graph_router, prefix="/graph")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("app:app", host="0.0.0.0", port=8000, reload=True)
