from billboard_to_spotify import updateBillboard
import os
USER_ID = os.environ["USER_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REDIRECT_URI= 'https://example.com'

updateBillboard(USER_ID, CLIENT_SECRET, CLIENT_ID, REDIRECT_URI)
