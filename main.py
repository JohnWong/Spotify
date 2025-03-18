from billboard_to_spotify import BillboardToSpotifyt
import os
USER_ID = os.environ["USER_ID"]
CLIENT_ID = os.environ["CLIENT_ID"]
CLIENT_SECRET = os.environ["CLIENT_SECRET"]
REDIRECT_URI= 'https://example.com'

## enter a date for reaching top 100 song of this date
billboard_playlist = BillboardToSpotifyt(user_id=USER_ID,client_secret=CLIENT_SECRET,client_id=CLIENT_ID,redirect_uri=REDIRECT_URI)

## To reach token you should call the function of request_user_authorization. This process has two step. 1. Go to link
#and confirm authorization. 2. Paste the code in the url code= part.As a result of this two-step process,
# the authorization process will be completed and the token will be accessed.
billboard_playlist.request_user_authorization()

# billboard_playlist.query_song_uri("4x4xU artist:Lainey Wilson")
end_point, snapshot_id = billboard_playlist.get_playlist_id()
if end_point != None:
    billboard_playlist.clear_playlist(end_point, snapshot_id)
    billboard_playlist.update_playlist_description(end_point)
else:
    ## create a private spotify playlist named by the entered date by calling the function creation_playlist
    end_point = billboard_playlist.creating_playlist()
    billboard_playlist.add_cover(end_point)    
## add songs to playlist
billboard_playlist.adding_playlist(end_point)
