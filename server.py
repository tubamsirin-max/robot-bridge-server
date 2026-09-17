import os

from fastapi import FastAPI, WebSocket, WebSocketDisconnect
from fastapi.responses import JSONResponse


# ============================================================
# ROBOT BRIDGE SERVER
# PC <-> RENDER <-> ANDROID
# ============================================================

app = FastAPI()


# ============================================================
# BAGLI CIHAZLAR
# ============================================================

clients = {
    "pc": None,
    "android": None
}


# ============================================================
# TOKEN
# ============================================================

# Token Render Environment Variables icinden okunur.
#
# Render:
#
# KEY:
# ROBOT_TOKEN
#
# VALUE:
# senin token degerin

ROBOT_TOKEN = os.environ.get(
    "ROBOT_TOKEN",
    ""
)


# ============================================================
# ANA SAYFA
# ============================================================

@app.get("/")
async def home():

    return JSONResponse(
        {
            "status": "online",
            "service": "Robot Bridge Server",
            "version": "2.0"
        }
    )


# ============================================================
# DURUM SAYFASI
# ============================================================

@app.get("/status")
async def status():

    return {
        "server": "online",
        "pc": clients["pc"] is not None,
        "android": clients["android"] is not None
    }


# ============================================================
# MESAJ GONDERME
# ============================================================

async def send_to(
    device: str,
    message: str
):

    socket = clients.get(device)

    if socket is None:
        return False

    try:

        await socket.send_text(message)

        return True

    except Exception as error:

        print(
            f"{device.upper()} GONDERME HATASI:",
            error
        )

        # Kopmus socket'i temizle
        if clients.get(device) is socket:
            clients[device] = None

        return False


# ============================================================
# WEBSOCKET
# ============================================================

@app.websocket("/ws/{device}")
async def websocket_endpoint(
    websocket: WebSocket,
    device: str
):

    # --------------------------------------------------------
    # CIHAZ KONTROLU
    # --------------------------------------------------------

    if device not in (
        "pc",
        "android"
    ):

        await websocket.close(
            code=1008
        )

        return


    # --------------------------------------------------------
    # TOKEN KONTROLU
    # --------------------------------------------------------

    token = websocket.query_params.get(
        "token",
        ""
    )


    if (
        not ROBOT_TOKEN
        or token != ROBOT_TOKEN
    ):

        await websocket.close(
            code=1008
        )

        return


    # --------------------------------------------------------
    # BAGLANTIYI KABUL ET
    # --------------------------------------------------------

    await websocket.accept()


    # --------------------------------------------------------
    # AYNI CIHAZIN ESKI BAGLANTISI VARSA KAPAT
    # --------------------------------------------------------

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


    print()
    print(
        f"{device.upper()} BAGLANDI"
    )


    # --------------------------------------------------------
    # BAGLANTI ONAYI
    # --------------------------------------------------------

    try:

        await websocket.send_text(
            f"SERVER:CONNECTED:{device.upper()}"
        )

    except Exception:

        pass


    # --------------------------------------------------------
    # DIGER CIHAZA ONLINE BILGISI
    # --------------------------------------------------------

    if device == "pc":

        await send_to(
            "android",
            "SERVER:PC_ONLINE"
        )

    else:

        await send_to(
            "pc",
            "SERVER:ANDROID_ONLINE"
        )


    # ========================================================
    # MESAJ DONGUSU
    # ========================================================

    try:

        while True:

            # Android veya PC'den mesaj al
            message = (
                await websocket.receive_text()
            )


            print(
                f"{device.upper()} -> {message}"
            )


            # ------------------------------------------------
            # PC'DEN GELDIYSE ANDROID'E
            # ------------------------------------------------

            if device == "pc":

                target_device = "android"


            # ------------------------------------------------
            # ANDROID'DEN GELDIYSE PC'YE
            # ------------------------------------------------

            else:

                target_device = "pc"


            # ------------------------------------------------
            # MESAJI DIGER CIHAZA AKTAR
            # ------------------------------------------------

            sent = await send_to(
                target_device,
                message
            )


            # ------------------------------------------------
            # DIGER CIHAZ BAGLI DEGILSE
            # ------------------------------------------------

            if not sent:

                try:

                    await websocket.send_text(
                        f"SERVER:{target_device.upper()}_OFFLINE"
                    )

                except Exception:

                    pass


    # ========================================================
    # BAGLANTI KOPTU
    # ========================================================

    except WebSocketDisconnect:

        print(
            f"{device.upper()} AYRILDI"
        )


    except Exception as error:

        print(
            f"{device.upper()} HATA:",
            error
        )


    # ========================================================
    # TEMIZLIK
    # ========================================================

    finally:

        if clients.get(device) is websocket:

            clients[device] = None


        # Diger cihaza offline bilgisini gonder

        if device == "pc":

            await send_to(
                "android",
                "SERVER:PC_OFFLINE"
            )

        else:

            await send_to(
                "pc",
                "SERVER:ANDROID_OFFLINE"
            )


        print(
            f"{device.upper()} BAGLANTISI TEMIZLENDI"
        )
