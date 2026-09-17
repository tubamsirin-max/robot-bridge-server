
import os
from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse

app = FastAPI()

# Bagli cihazlar
clients = {
    "pc": None,
    "android": None
}

# Gizli anahtar Render Environment Variable'dan gelecek
ROBOT_TOKEN = os.environ.get("ROBOT_TOKEN", "")


@app.get("/")
async def home():
    return JSONResponse(
        {
            "status": "online",
            "service": "Robot Bridge Server"
        }
    )


@app.get("/status")
async def status():
    return {
        "server": "online",
        "pc": clients["pc"] is not None,
        "android": clients["android"] is not None
    }


@app.websocket("/ws/{device}")
async def websocket_endpoint(
    websocket: WebSocket,
    device: str
):
    # Sadece PC ve Android kabul et
    if device not in ("pc", "android"):
        await websocket.close(code=1008)
        return

    # Token kontrolu
    token = websocket.query_params.get("token", "")

    if not ROBOT_TOKEN or token != ROBOT_TOKEN:
        await websocket.close(code=1008)
        return

    await websocket.accept()

    # Eski baglanti varsa kapat
    old_socket = clients.get(device)

    if old_socket is not None:
        try:
            await old_socket.close(
                code=1000,
                reason="Yeni baglanti acildi"
            )
        except Exception:
            pass

    clients[device] = websocket

    print(f"{device.upper()} BAGLANDI")

    try:
        await websocket.send_text(
            f"SERVER:CONNECTED:{device.upper()}"
        )

        while True:
            message = await websocket.receive_text()

            print(
                f"{device.upper()} -> {message}"
            )

            # PC'den gelirse Android'e
            if device == "pc":
                target = clients.get("android")

            # Android'den gelirse PC'ye
            else:
                target = clients.get("pc")

            if target is not None:
                try:
                    await target.send_text(message)

                except Exception:
                    pass

    except WebSocketDisconnect:
        print(f"{device.upper()} AYRILDI")

    except Exception as e:
        print(
            f"{device.upper()} HATA:",
            e
        )

    finally:
        if clients.get(device) is websocket:
            clients[device] = None
