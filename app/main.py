from fastapi import FastAPI

app = FastAPI(
    title="Open Timetable Generator",
    description="API for institutional timetable generation and optimisation.",
    version="0.1.0",
)


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok"}