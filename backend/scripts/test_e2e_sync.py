import asyncio
import websockets
import json
import urllib.request
import urllib.parse
from pathlib import Path
import os

async def test_localization_sync(scene_id):
    ws_uri = f"ws://localhost:8000/vps/ws/agents/{scene_id}"
    http_uri = "http://localhost:8000/vps/localize"
    
    img_path = Path("test_query.jpg")
    if not img_path.exists():
        from PIL import Image
        import numpy as np
        Image.fromarray(np.random.randint(0, 255, (224, 224, 3), dtype=np.uint8)).save(img_path)

    print(f"Connecting to WebSocket: {ws_uri}")
    async with websockets.connect(ws_uri) as websocket:
        print("Connected to WebSocket. Triggering localization via HTTP...")
        
        # Manually construct multipart form data for urllib or just use a helper
        boundary = "---------------------------boundary"
        data = []
        data.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"scene_id\"\r\n\r\n{scene_id}\r\n")
        data.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"agent_id\"\r\n\r\nhttp-agent-001\r\n")
        data.append(f"--{boundary}\r\nContent-Disposition: form-data; name=\"query_image\"; filename=\"test_query.jpg\"\r\nContent-Type: image/jpeg\r\n\r\n")
        
        with open(img_path, 'rb') as f:
            file_content = f.read()
        
        body = "".join(data).encode('utf-8') + file_content + f"\r\n--{boundary}--\r\n".encode('utf-8')
        
        req = urllib.request.Request(http_uri, data=body)
        req.add_header('Content-Type', f'multipart/form-data; boundary={boundary}')
        
        print("Sending HTTP request...")
        try:
            with urllib.request.urlopen(req) as response:
                print(f"HTTP Status: {response.getcode()}")
        except Exception as e:
            print(f"HTTP Error: {e}")
        
        print("Waiting for WebSocket broadcast...")
        try:
            broadcast = await asyncio.wait_for(websocket.recv(), timeout=10.0)
            msg = json.loads(broadcast)
            print(f"Received sync message: {json.dumps(msg, indent=2)}")
            if msg.get("agent_id") == "http-agent-001":
                print("\nSUCCESS: E2E HTTP-to-WebSocket sync verified!")
            else:
                print(f"\nFAILURE: Received wrong agent ID: {msg.get('agent_id')}")
        except asyncio.TimeoutError:
            print("\nFAILURE: Timed out waiting for sync message.")

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--scene_id", required=True)
    args = parser.parse_args()
    
    asyncio.run(test_localization_sync(args.scene_id))
