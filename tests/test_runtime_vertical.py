import asyncio
from orren.runtime import OrrenRuntime
from orren.runtime.field import ResolutionNode

def test_living_field_vertical(tmp_path):
    async def run():
        rt=OrrenRuntime(str(tmp_path/"orren.sqlite"))
        await rt.inject("MyApp { UI { Button } }")
        button=rt.field.find("Button")
        assert button is not None
        await rt.field.update_node(button.id,dimensions={"behavioral":"fetch weather"},confidence=.9)
        await rt.settle()
        art=await rt.realize(button.id,"python")
        assert art["status"]=="current"
        assert art["path"].endswith("button.py")
        assert rt.field.snapshot_id
    asyncio.run(run())

def test_non_destructive_resolution_and_visual_reparent(tmp_path):
    async def run():
        rt=OrrenRuntime(str(tmp_path/"orren.sqlite"))
        app=await rt.visual.create_node("MyApp")
        ui=await rt.visual.create_node("UI",app.id)
        button=await rt.visual.create_node("Button",ui.id)
        controls=await rt.visual.create_node("Controls",app.id)
        await rt.visual.move(button.id,controls.id)
        assert rt.field.parents(button.id)[0].id == controls.id
        resolution=await rt.conflicts.propose_conflict((button.id,controls.id),"reconcile placement")
        assert isinstance(resolution,ResolutionNode)
        assert rt.field.nodes[button.id].active
        assert rt.field.nodes[controls.id].active
        await rt.field.accept_resolution(resolution.id)
        assert not rt.field.nodes[button.id].active
        assert not rt.field.nodes[controls.id].active
    asyncio.run(run())
