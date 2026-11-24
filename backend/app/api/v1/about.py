"""Which version is running, and what changed in each."""
from fastapi import APIRouter
from app import version as v

router = APIRouter(tags=["about"])


@router.get("/version", summary="The running version and the changelog (public)")
def version():
    log = v.changelog()
    cur = next((e for e in log if e["version"] == v.__version__), None)
    return {"version": v.__version__, "released": (cur or {}).get("date", ""), "changelog": log}
