import os
import traceback

from flask import Flask, Response

import billboard_to_spotify

app = Flask(__name__)


@app.route("/", methods=["POST", "GET"])
def run():
    try:
        billboard_to_spotify.updateBillboardForSAE()
        return Response("Billboard update complete", status=200)
    except Exception as e:
        traceback.print_exc()
        return Response(str(e), status=500)


if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port, debug=False)
