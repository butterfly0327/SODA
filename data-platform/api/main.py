from fastapi import FastAPI


app = FastAPI(title="SODA Data Platform API")


@app.get("/")
def root() -> dict[str, str]:
    return {"status": "ok", "service": "fastapi"}


@app.get("/health")
def health() -> dict[str, str]:
    return {"status": "ok", "service": "fastapi"}
