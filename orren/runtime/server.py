from pathlib import Path
from fastapi import FastAPI, WebSocket
from fastapi.responses import HTMLResponse
from .runtime import OrrenRuntime
ROOT=Path(__file__).parent
def create_app():
    app=FastAPI(title="Orren — Living SIR Field")
    rt=OrrenRuntime()
    @app.get("/")
    async def index():
        return HTMLResponse((ROOT/"static"/"index.html").read_text())
    @app.get("/api/field")
    async def field():
        return rt.observer.snapshot()
    @app.post("/api/intent")
    async def intent(payload:dict):
        nodes=await rt.inject(str(payload.get("source","")))
        return {"created":[n.id for n in nodes],"field":rt.observer.snapshot()}
    @app.websocket("/ws")
    async def ws(socket:WebSocket):
        await socket.accept()
        await socket.send_json(rt.observer.snapshot())
        while True:
            msg=await socket.receive_json()
            kind=msg.get("type")
            if kind=="intent": await rt.inject(str(msg.get("source","")))
            elif kind=="create": await rt.visual.create_node(str(msg.get("name","Node")),msg.get("parent_id"))
            elif kind=="dimension": await rt.visual.set_dimension(msg["node_id"],msg["dimension"],msg.get("value"))
            elif kind=="move": await rt.visual.move(msg["node_id"],msg["parent_id"])
            await socket.send_json(rt.observer.snapshot())
    return app
def run():
    import uvicorn
    uvicorn.run(create_app(),host="127.0.0.1",port=8000)
