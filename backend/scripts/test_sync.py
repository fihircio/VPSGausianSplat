import asyncio
import websockets
import json
import argparse

async def test_sync(scene_id):
    uri = f"ws://localhost:8000/vps/ws/agents/{scene_id}"
    print(f"Connecting to {uri}...")
    
    try:
        async with websockets.connect(uri) as websocket:
            print("Connected! Sending pose update...")
            
            # Send a fake pose update
            pose = {
                "type": "pose_update",
                "agent_id": "test-ai-agent",
                "name": "Validation Bot",
                "position": [1.0, 2.0, 3.0],
                "rotation": [0, 0, 0, 1]
            }
            await websocket.send(json.dumps(pose))
            print("Pose sent. Waiting for broadcast echo...")
            
            # Should receive the broadcast back
            response = await asyncio.wait_for(websocket.recv(), timeout=5.0)
            data = json.loads(response)
            print(f"Received broadcast: {json.dumps(data, indent=2)}")
            
            if data.get("type") == "agent_update" and data.get("agent_id") == "test-ai-agent":
                print("\nSUCCESS: Sync broadcast verified!")
            else:
                print("\nFAILURE: Received unexpected message type.")
                
    except Exception as e:
        print(f"Error: {e}")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene_id", default="demo-scene")
    args = parser.parse_args()
    
    asyncio.run(test_sync(args.scene_id))
