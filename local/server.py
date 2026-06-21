#!/usr/bin/env python3
"""FastAPI server for the Workflow Editor. Reads Snowflake config from env."""
import json
import os
import tomllib
from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.staticfiles import StaticFiles
from snowflake.snowpark import Session

app = FastAPI(title="Workflow Editor")

# --- Snowflake session ---
def create_session():
    conn_name = os.environ.get("SNOWFLAKE_CONNECTION", "U2C")
    paths = [
        os.path.expanduser("~/.snowflake/config.toml"),
        os.path.expanduser("~/Library/Application Support/snowflake/config.toml"),
    ]
    config_path = None
    for p in paths:
        if os.path.exists(p):
            config_path = p
            break
    if not config_path:
        raise FileNotFoundError(f"Config not found at {paths}")
    with open(config_path, "rb") as f:
        cfg = tomllib.load(f)
    conn = cfg["connections"][conn_name]
    return Session.builder.configs({
        "account": conn["account"], "user": conn["user"], "password": conn["password"],
        "host": conn.get("host"), "port": conn.get("port", 443),
        "protocol": conn.get("protocol", "https"), "database": conn.get("database"),
        "schema": conn.get("schema"), "warehouse": conn.get("warehouse"), "role": conn.get("role"),
    }).create()


session = create_session()

# Get the directory containing this file
BASE_DIR = os.path.dirname(os.path.abspath(__file__))


# --- API routes ---

@app.get("/api/workflows")
def list_workflows():
    rows = session.sql("""
        SELECT CF_NAM_Configuration_Name AS name,
               CF_TYP_CFT_ConfigurationType AS type
        FROM metadata.lCF_Configuration
        ORDER BY CF_NAM_Configuration_Name
    """).collect()
    return [{"name": r["NAME"], "type": r["TYPE"]} for r in rows]


@app.get("/api/workflows/{name}")
def get_workflow(name: str):
    result = session.call("metadata._ConfigurationGet", name)
    if not result:
        raise HTTPException(status_code=404, detail="Workflow not found")
    return {"name": name, "content": result}


@app.put("/api/workflows/{name}")
def save_workflow(name: str, body: dict):
    content = json.dumps(body) if isinstance(body, dict) else body
    cf_id = session.call("metadata._ConfigurationUpsert", name, content, "Workflow")
    return {"name": name, "cf_id": cf_id}


@app.delete("/api/workflows/{name}")
def delete_workflow(name: str):
    result = session.call("metadata._ConfigurationDelete", name)
    return {"status": result}


# --- Static files ---

@app.get("/", response_class=HTMLResponse)
def index():
    with open(os.path.join(BASE_DIR, "index.html"), "r") as f:
        return f.read()


@app.get("/LayoutEngine.js")
def layout_engine():
    return FileResponse(os.path.join(BASE_DIR, "LayoutEngine.js"))


# --- Run ---

if __name__ == "__main__":
    import uvicorn
    port = int(os.environ.get("PORT", 8000))
    print(f"Starting server on http://localhost:{port}")
    uvicorn.run(app, host="0.0.0.0", port=port)
