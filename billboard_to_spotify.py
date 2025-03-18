import os
import requests
import base64
import datetime 
import concurrent.futures
import requests
import time
from bs4 import BeautifulSoup


class BillboardToSpotifyt:

    name = f"Billboard Hot 100"
    description = f"The unofficial Billboard Hot 100 playlist, updated in {datetime.datetime.now(datetime.timezone.utc).strftime('%Y-%m-%dT%H:%M%Z')} . Reference: https://www.billboard.com/charts/hot-100/"

    def __init__(self, user_id, client_id, client_secret, redirect_uri):

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
        auth = base64.b64encode(f'{self.client_id}:{self.client_secret}'.encode('ascii')).decode('ascii')
        headers = {
            'Authorization': f'Basic {auth}',
            'Content-Type':'application/x-www-form-urlencoded'
        }
        
        with open("refresh_token.txt", 'a+') as f:
            f.seek(0)
            token = f.read()
        if len(token) > 0:
            data = {
                'grant_type': 'refresh_token',
                'refresh_token': token,
            }

            r = requests.post(self.token_endpoint, headers=headers, data=data)
            print("Response: %d refresh" % r.status_code)
            if r.status_code == 200:
                j = r.json()
                self.access_token= f"{j['access_token']}"
                print(f"Token: {self.access_token}")
                with open("refresh_token.txt", 'w') as f:
                    f.write(f"{j['refresh_token'] if 'refresh_token' in j else token}")
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
        os.system(f"open {r.url}")
        code = input("paste code here: ")
        
        data = {
            'grant_type': 'authorization_code',
            'code' : code,
            'redirect_uri': self.redirect_uri
        }

        r = requests.post(self.token_endpoint, headers=headers, data=data)
        print("Response: %d new_token" % r.status_code)
        r = r.json()
        self.access_token= f"{r['access_token']}"
        with open("refresh_token.txt", 'w') as f:
            f.write(f"{r['refresh_token']}")

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
                          .replace('4x4xU', '4×4×U') 
                          for songs in song_names]
        return formatted_songs

    def creating_playlist(self):
        """creates a private Spotify playlist"""

        playlist_endpoint = f"https://api.spotify.com/v1/users/{self.user_id}/playlists"

        headers = { 
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        data ={
            "name": self.name,
            "description": self.description,
            "public": True
        }
        response = requests.post(playlist_endpoint, headers=headers, json=data)
        print("Response: %d creating_playlist" % response.status_code)
        r = response.json()
        if response.status_code > 201:
            print(r)
        return r['tracks']['href']
    
    def query_song_uri(self, song):
        print("Query: %s" % song)
        # limit 1 result in wired results
        headers = {"Content-Type": "application/json", "Authorization": f"Bearer {self.access_token}"}
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
                        query = song.replace('artist:', '')
                    elif retry == 2:
                        query = song[0:song.find('artist:')]
                    retry -= 1
                    print(f"Retry: {song}")
                    continue
                uris = tracks['items'][0]['uri']
                return uris
            except Exception as e:
                if retry > 0:
                    retry -= 1
                    time.sleep(2)
                    print(f"Retry: {song}")
                    continue
                raise e

# ########################################## Finding songs uris###########################################################
    def song_uris(self):
        """reachs uri parameters of songs and return a uris array ready for use in the next steps"""
        formatted_songs = self.billboard_top_100()

        with concurrent.futures.ThreadPoolExecutor(max_workers=10) as executor:
            uris_array = list(executor.map(self.query_song_uri, formatted_songs))
        return uris_array

# ############################GET PLAYLIST ID############################################################################
    def get_playlist_id(self):
        """returns an endpoint to use in the next function which is to add all songs to the playlist"""
        self.base_url = f'https://api.spotify.com/v1/users/{self.user_id}/playlists'
        params = {
            "limit": 30,
            "offset": 0,
        }

        headers_playlist = {"Content-Type": "application/json",
                            "Authorization": f"Bearer {self.access_token}"}
        response_playlist = requests.get(self.base_url, params=params, headers = headers_playlist)
        print("Response: %d get_playlist_id" % response_playlist.status_code)
        response_playlist = response_playlist.json()
        for item in response_playlist['items']:
            if item['name'] == self.name:
                return (item['tracks']['href'], item['snapshot_id'])
        return (None, None)


# ######################################## Adding songs to list ##########################################################
    def adding_playlist(self, end_point):
        """adds songs from Billboard website to Spotify playlist just created"""
        # filter
        uris = list(filter(lambda x: x != None, self.song_uris()))
        body = {
            "uris": uris,
            "position": 0,
        }
        headers = {
            "Content-Type": "application/json", 
            "Authorization": f"Bearer {self.access_token}"
        }
        response = requests.post(end_point, headers = headers, json=body)
        print(f"Response: {response.status_code} adding_playlist")
        if response.status_code >= 400:
            print(uris)
            print(response.json())

# ######################################## Remove songs from list ##########################################################
    def clear_playlist(self, end_point, snapshot_id):
        """get songs from Billboard website to Spotify playlist just created"""
        tracks = []
        offset = 0
        flag = True
        while(flag):
            headers = { 
                "Authorization": f"Bearer {self.access_token}",
                "Content-Type": "application/json",
            }
            params = {
                'fields': 'items(track(uri))',
                'limit': 50,
                'offset': len(tracks),
            }
            r = requests.get(end_point, headers=headers, params=params)
            print(f"Response: {r.status_code} tracks")
            j = r.json()
            tracks = tracks + [item['track'] for item in j['items']]

            flag = len(j['items']) > 0

        headers = { 
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        
        data = {
            'tracks': tracks
        }
        r = requests.delete(end_point, headers=headers, json=data)
        print(f"Response: {r.status_code} clear_playlist")

# ######################################## Update description ##########################################################
    def update_playlist_description(self, end_point):
        """update description of playlist"""
        playlist_endpoint = end_point.replace("/tracks", "")
        headers = { 
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "application/json",
        }
        data ={
            "name": self.name,
            "description": self.description,
            "public": True
        }
        response = requests.put(playlist_endpoint, headers=headers, json=data)
        print("Response: %d update_playlist_description" % response.status_code)

# ######################################## Add cover ##########################################################
    def add_cover(self, end_point):
        """add cover of playlist"""
        playlist_endpoint = end_point.replace("/tracks", "/images")
        headers = { 
            "Authorization": f"Bearer {self.access_token}",
            "Content-Type": "image/jpeg",
        }
        with open("billboard.png", "rb") as f:
            data = base64.b64encode(f.read())
        response = requests.put(playlist_endpoint, headers=headers, data=data)
        print("Response: %d add_cover" % response.status_code)
        