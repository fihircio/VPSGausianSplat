import asyncio
import websockets
import json

async def simulate_agent(scene_id, agent_id, name):
    uri = f"ws://localhost:8000/vps/ws/agents/{scene_id}"
    async with websockets.connect(uri) as websocket:
        print(f"Agent {name} ({agent_id}) connected to scene {scene_id}")
        
        # 1. Listen for initial state or broadcasts
        async def listen():
            try:
                async for message in websocket:
                    data = json.loads(message)
                    print(f"Agent {name} received: {data.get('type')} from {data.get('agent_id') or 'system'}")
            except Exception as e:
                print(f"Agent {name} listener error: {e}")

        listener_task = asyncio.create_task(listen())

        # 2. Send some pose updates
        for i in range(3):
            pose_msg = {
                "type": "pose_update",
                "agent_id": agent_id,
                "name": name,
                "position": [float(i), 0.0, 0.0],
                "rotation": [0.0, 0.0, 0.0, 1.0]
            }
            await websocket.send(json.dumps(pose_msg))
            print(f"Agent {name} sent pose update {i}")
            await asyncio.sleep(1)

        await asyncio.sleep(2)
        listener_task.cancel()

async def main():
    scene_id = "test-scene"
    await asyncio.gather(
        simulate_agent(scene_id, "agent_1", "Doctor Alice"),
        simulate_agent(scene_id, "agent_2", "Nurse Bob")
    )

if __name__ == "__main__":
    try:
        asyncio.run(main())
    except ConnectionRefusedError:
        print("Error: Backend server is not running on localhost:8000")
    except Exception as e:
        print(f"Test error: {e}")
