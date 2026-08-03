# -*- coding: utf-8 -*-
import os
import base64
import datetime 
import time
import json
from bs4 import BeautifulSoup
import requests
import threading
import sae_patch

read_refresh_token = sae_patch.read_refresh_token
write_refresh_token = sae_patch.write_refresh_token

PLAYLIST_ID = "6M13zytAhM5hCLn4YZ5znR"

try:
    from queue import Queue
except:
    from Queue import Queue


def _request_with_retry(method, url, max_retries=5, **kwargs):
    """HTTP request that honors Spotify's 429 rate-limit Retry-After header."""
    response = None
    for attempt in range(max_retries):
        response = requests.request(method, url, **kwargs)
        if response.status_code != 429:
            return response
        retry_after = int(response.headers.get("Retry-After", "2"))
        print("Rate limited (429), retry after %ds (attempt %d/%d)"
              % (retry_after, attempt + 1, max_retries))
        time.sleep(retry_after + 1)
    return response


class BillboardToSpotify:

    name = "Billboard Hot 100"

    def __init__(self, user_id, client_id, client_secret, redirect_uri):

        updated_at = datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M%Z')
        self.description = "The unofficial Billboard Hot 100 playlist, updated in %s. Reference: https://www.billboard.com/charts/hot-100/" % updated_at
        self.url ="https://www.billboard.com/charts/hot-100/"
        self.user_id = user_id
        self.client_id = client_id
        self.client_secret = client_secret
        self.redirect_uri = redirect_uri
        self.endpoint = 'https://accounts.spotify.com/authorize'
        self.scope = 'playlist-modify-private playlist-read-private playlist-modify-public ugc-image-upload'
        self.token_endpoint  ='https://accounts.spotify.com/api/token'
        self.access_token = ""

    def request_user_authorization(self):
        """ Two-step function returns access_code to use in the next steps.Go to link in the terminal, accept authorization
        and copy the code (you should find in the "code=" part) in url.Then paste the code in terminal"""
        concat = self.client_id+':'+self.client_secret
        auth = base64.b64encode(concat.encode('ascii')).decode('ascii')
        headers = {
            'Authorization': "Basic " + auth,
            'Content-Type': "application/x-www-form-urlencoded"
        }
        
        token = read_refresh_token("refresh_token.txt")
        if len(token) > 0:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': token,
            }

            r = requests.post(self.token_endpoint, headers=headers, data=data)
            print("Response: %d refresh" % r.status_code)
            if r.status_code == 200:
                j = r.json()
                self.access_token= j['access_token']
                write_refresh_token(j['refresh_token'] if 'refresh_token' in j else token, "refresh_token.txt")
                return
        
        params = {
            'response_type': 'code',
            'client_id': self.client_id,
            'scope': self.scope,
            'redirect_uri': self.redirect_uri,
        }

        r = requests.get(self.endpoint, params=params)
        print("Response: %d account" % r.status_code)
        print(r.url)
        code = raw_input("paste code here: ")
        
        data = {
            'grant_type': 'authorization_code',
            'code' : code,
            'redirect_uri': self.redirect_uri
        }

        r = requests.post(self.token_endpoint, headers=headers, data=data)
        print("Response: %d new_token" % r.status_code)
        r = r.json()
        self.access_token= r['access_token']
        write_refresh_token(r['refresh_token'], "refresh_token.txt")

########################## Picking hot 100 song for a certain date from Billboard#######################################
    def billboard_top_100(self):
        """ takes top 100 songs for a certain date from the Billboard website and format songs list for using spotify api. Returns formatted song list """
        url = self.url
        respond  =requests.get(url)
        print("Response: %d billboard" % respond.status_code)
        website_html = respond.text
        soup = BeautifulSoup(website_html, "html.parser")
        song_names_spans = soup.find_all("div" , class_="o-chart-results-list-row-container")
        song_itmes = [row.find("h3", id="title-of-a-story") for row in song_names_spans]
        song_names = [song.getText() + "  artist:" + song.find_next_sibling("span").getText() for song in song_itmes]
        formatted_songs= [songs
                          .replace('\t','')
                          .replace('\n','')
                          .replace('Featuring', ' ')
                          .replace('  ', ' ') 
                          .replace('4x4xU', u'4×4×U')
                          for songs in song_names]
        return formatted_songs

    def query_song_uri(self, song):
        print("Query: %s" % song)
        # limit 1 result in wired results
        headers = {"Content-Type": "application/json", "Authorization": "Bearer " + self.access_token}
        songuris_endpoint = 'https://api.spotify.com/v1/search?'
        retry = 3
        query = song
        while retry > 0:
            try:
                params = {
                    "q": query,
                    "type": "track",
                    "limit": 10
                }
                response = requests.get(songuris_endpoint, params=params, headers = headers)
                
                # print(response.json()["tracks"])
                tracks = response.json()["tracks"]
                if tracks["total"] < 1:
                    # no result, retry without artist
                    if retry == 3:
                        query = song[0:song.find('artist:')]
                    retry -= 1
                    print("Retry: " + query)
                    continue
                uris = tracks['items'][0]['uri']
                print("Found: " + tracks['items'][0]['name'])
                return uris
            except Exception as e:
                if retry > 0:
                    retry -= 1
                    time.sleep(2)
                    print("Retry: " + query)
                    continue
                raise e

# ########################################## Finding songs uris###########################################################
    def song_uris(self):
        """reachs uri parameters of songs and return a uris array ready for use in the next steps"""
        formatted_songs = self.billboard_top_100()

        result = {}
        jobs = Queue()

        def do_stuff(q):
            while not q.empty():
                value = q.get()
                uri = self.query_song_uri(value)
                result[value] = uri
                q.task_done()

        for i in formatted_songs:
            jobs.put(i)

        for i in range(10):
            worker = threading.Thread(target=do_stuff, args=(jobs,))
            worker.start()

        jobs.join()
        return [result[song] for song in formatted_songs]

# ######################################## Adding songs to list ##########################################################
    def adding_playlist(self, end_point, song_uris):
        """adds songs from Billboard website to Spotify playlist just created"""
        # filter
        uris = list(filter(lambda x: x != None, song_uris))
        body = {
            "uris": uris,
            "position": 0,
        }
        print(len(uris))
        headers = {
            "Content-Type": "application/json", 
            "Authorization": "Bearer " + self.access_token
        }
        response = _request_with_retry("POST", end_point, headers=headers, json=body)
        print("Response: %s adding_playlist" % response.status_code)
        if response.status_code >= 400:
            print(uris)
            print(response.json())
            raise Exception("adding_playlist failed: %d" % response.status_code)

# ######################################## Remove songs from list ##########################################################
    def clear_playlist(self, end_point, snapshot_id):
        """get songs from Billboard website to Spotify playlist just created"""
        tracks = []
        offset = 0
        flag = True
        while(flag):
            headers = { 
                "Authorization": "Bearer " + self.access_token,
                "Content-Type": "application/json",
            }
            params = {
                'fields': 'items(track(uri))',
                'limit': 50,
                'offset': len(tracks),
            }
            r = requests.get(end_point, headers=headers, params=params)
            print("Response: %d tracks" % r.status_code)
            j = r.json()
            tracks = tracks + [item['track'] for item in j['items']]

            flag = len(j['items']) > 0

        if len(tracks) == 0:
            return
        
        headers = { 
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json",
        }
      

        n = 100
        # Iterate and slice the list
        for i in range(0, len(tracks), n):
            data = {
                'tracks': tracks[i:i + n]
            }
            r = _request_with_retry("DELETE", end_point, headers=headers, json=data)
            print("Response: %d clear_playlist" % r.status_code)

# ######################################## Update description ##########################################################
    def update_playlist_description(self, end_point):
        """update description of playlist"""
        playlist_endpoint = end_point.replace("/tracks", "")
        headers = { 
            "Authorization": "Bearer " + self.access_token,
            "Content-Type": "application/json",
        }
        data ={
            "name": self.name,
            "description": self.description,
            "public": True
        }
        response = requests.put(playlist_endpoint, headers=headers, json=data)
        print("Response: %d update_playlist_description" % response.status_code)

def updateBillboard(USER_ID, CLIENT_SECRET, CLIENT_ID, REDIRECT_URI):
    ## enter a date for reaching top 100 song of this date
    billboard_playlist = BillboardToSpotify(user_id=USER_ID,client_secret=CLIENT_SECRET,client_id=CLIENT_ID,redirect_uri=REDIRECT_URI)

    ## To reach token you should call the function of request_user_authorization. This process has two step. 1. Go to link
    #and confirm authorization. 2. Paste the code in the url code= part.As a result of this two-step process,
    # the authorization process will be completed and the token will be accessed.
    billboard_playlist.request_user_authorization()

    end_point = "https://api.spotify.com/v1/playlists/%s/tracks" % PLAYLIST_ID
    snapshot_id = None
    print("end_point: %s" % end_point)

    # Resolve all songs FIRST. Only touch the playlist once we have a
    # non-empty result, so a failed Billboard/search step never leaves the
    # playlist cleared-but-empty.
    songs = [uri for uri in billboard_playlist.song_uris() if uri is not None]
    if len(songs) == 0:
        raise Exception("no songs resolved from Billboard, aborting without clearing playlist")

    billboard_playlist.update_playlist_description(end_point)
    billboard_playlist.clear_playlist(end_point, snapshot_id)
    billboard_playlist.adding_playlist(end_point, songs)

def updateBillboardForSAE():
    content = json.loads(read_refresh_token("api.json"))    
    
    USER_ID = content['USER_ID']
    CLIENT_ID = content["CLIENT_ID"]
    CLIENT_SECRET = content["CLIENT_SECRET"]
    REDIRECT_URI= 'https://example.com'

    updateBillboard(USER_ID, CLIENT_SECRET, CLIENT_ID, REDIRECT_URI)

if __name__ == "__main__":
    updateBillboardForSAE()
