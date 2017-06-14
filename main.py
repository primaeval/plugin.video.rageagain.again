from xbmcswift2 import Plugin, ListItem
from xbmcswift2 import actions
import xbmc,xbmcaddon,xbmcvfs,xbmcgui,xbmcplugin
import re
import requests,urllib
import os,sys
import xml.etree.ElementTree as ET
import base64
import datetime

from requests.packages.urllib3.exceptions import InsecureRequestWarning
requests.packages.urllib3.disable_warnings(InsecureRequestWarning)

plugin = Plugin()
big_list_view = False

def log(v):
    xbmc.log(repr(v))

def get_icon_path(icon_name):
    addon_path = xbmcaddon.Addon().getAddonInfo("path")
    return os.path.join(addon_path, 'resources', 'img', icon_name+".png")

def remove_formatting(label):
    label = re.sub(r"\[/?[BI]\]",'',label)
    label = re.sub(r"\[/?COLOR.*?\]",'',label)
    return label

def escape( str ):
    str = str.replace("'","&#39;")
    str = str.replace("&", "&amp;")
    str = str.replace("<", "&lt;")
    str = str.replace(">", "&gt;")
    str = str.replace("\"", "&quot;")
    return str

def unescape( str ):
    str = str.replace("&lt;","<")
    str = str.replace("&gt;",">")
    str = str.replace("&quot;","\"")
    str = str.replace("&amp;","&")
    str = str.replace("&#39;","'")
    return str


    
@plugin.route('/play_track/<id>')
def play_track(id):
    url = "http://rageagain.com/youtube/get_sources.json?track_id=%s" % id
    r = requests.get(url)
    try:
        json = r.json()
    except:
        return
    sources = json["sources"]
    try:
        yt = sources[0]["id"]
    except:
        return
    item = {
        'label' : id,
        'thumbnail' : "",
        'path' : "plugin://plugin.video.youtube/play/?video_id=%s" % yt,
        'is_playable' : True
    }
    return plugin.set_resolved_url(item)    
    
@plugin.route('/playlister/<episode>')
def playlister(episode):
    url = "http://rageagain.com/tracks/getByPlaylistId/%s.json" % episode
    r = requests.get(url)
    try:
        json = r.json()
    except:
        return
    items = []
    tracks = json["tracks"]
    for id in sorted(tracks, reverse=True):
        track = tracks[id]
        items.append(
        {
            'label': "%s - %s" % (track["artist"], track["track"]),
            'path': plugin.url_for('play_track',id=id),
            'thumbnail':get_icon_path('tv'),
            'is_playable' : True
        })
    return items
    
@plugin.route('/top')
def top():
    url = "http://rageagain.com/tracks/getTop200.json"
    r = requests.get(url)
    try:
        json = r.json()
        #log(json)
    except:
        return
    items = []
    tracks = json["tracks"]
    for track in tracks:
        #track = tracks[id]
        items.append(
        {
            'label': "%s - %s" % (track["artist"], track["track"]),
            'path': '', # plugin.url_for('play_track',id='none'),
            'thumbnail':get_icon_path('tv'),
            'is_playable' : True
        })
    return items    

@plugin.route('/')
def index():
    items = []
    
    html = requests.get('http://rageagain.com').content
    
    match = re.findall('<a.*?</a>',html,flags=(re.DOTALL | re.MULTILINE))
    year = ''
    playlists = {}
    dates = True
    for a in match:
        year_match = re.search('name="episode-([0-9]{4})"',a)
        if year_match:
            year = year_match.group(1)
            #log(year)
        if not year:
            continue
        url = ''
        href_match = re.search('href="#/episode/([0-9]+)/1"',a)
        episode = ''
        if href_match:
            href = href_match.group(1)
            episode = int(href)
            url = "http://rageagain.com/#/episode/%s/1" % href
            #log(url)
        text = re.sub('<span class="label.*?</span>','',a,flags=(re.DOTALL | re.MULTILINE))            
        text = re.sub('<.*?>','',text,flags=(re.DOTALL | re.MULTILINE))

        #log(text)
        text = re.sub('\r\n','',text)
        text = re.sub('\s+',' ',text)
        text = text.strip()
        #log(text)
        if url:
            if not text:
                text = "UNKNOWN"
            if not episode in playlists:
                playlists[episode] = {}
                playlists[episode]["date"] = ''
                playlists[episode]["title"] = ""
                playlists[episode]["year"] = ""
                
            playlists[episode]["url"] = url
            
            if dates == True:
                playlists[episode]["date"] = text
                playlists[episode]["year"] = year
            else:
                playlists[episode]["title"] = " - " + text
            #log((episode,playlists[episode]))
        if episode == 1:
            dates = False
        #log(a)
    items.append(
    {
        'label': "Top 200" ,
        'path': plugin.url_for('top'),
        'thumbnail':get_icon_path('tv'),
    })        
    for episode in sorted(playlists, reverse=True):
        items.append(
        {
            'label': "[%d] %s %s %s" % (episode, playlists[episode]["year"], playlists[episode]["date"], playlists[episode]["title"]),
            'path': plugin.url_for('playlister',episode=episode),
            'thumbnail':get_icon_path('tv'),
        })

    return items


if __name__ == '__main__':
    plugin.run()
    if big_list_view == True:
        view_mode = int(plugin.get_setting('view_mode'))
        if view_mode:
            plugin.set_view_mode(view_mode)