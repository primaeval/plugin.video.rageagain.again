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

@plugin.route('/play_top_track/<artist>/<track>/<label>')
def play_top_track(artist,track,label):
    url = "http://rageagain.com/youtube/get_sources.json?track_artist={0}&track_name={1}&track_label={2}".format(urllib.quote(artist), urllib.quote(track),urllib.quote(label))
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
        'label' : "%s - %s" % (artist,track),
        'thumbnail' : "",
        'path' : "plugin://plugin.video.youtube/play/?video_id=%s" % yt,
        'is_playable' : True
    }
    return plugin.set_resolved_url(item)

@plugin.route('/playlister/<episode>')
def playlister(episode):
    path = 'special://profile/addon_data/plugin.video.rageagain.again/Music Videos/%s/' % episode
    xbmcvfs.mkdirs(path)
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
        strm = xbmcvfs.File(path+id+'.strm','wb')
        strm.write(plugin.url_for('play_track',id=id))
        strm.close()
        nfo = xbmcvfs.File(path+id+'.nfo','wb')
        s = '<musicvideo><title>%s</title><artist>%s</artist></musicvideo>' % (track["track"],track["artist"])
        nfo.write(s.encode("utf8"))
        nfo.close()
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
    path = 'special://profile/addon_data/plugin.video.rageagain.again/Music Videos/Top 200/'
    xbmcvfs.mkdirs(path)
    url = "http://rageagain.com/tracks/getTop200.json"
    r = requests.get(url)
    try:
        json = r.json()
        #log(json)
    except:
        return
    items = []
    tracks = json["tracks"]
    id = 1
    for track in tracks:
        strm = xbmcvfs.File(path+str(id)+'.strm','wb')
        s = plugin.url_for('play_top_track',artist=track["artist"],track=track["track"], label=(track["label"] or "None"))
        strm.write(s.encode("utf8"))
        strm.close()
        nfo = xbmcvfs.File(path+str(id)+'.nfo','wb')
        s = '<musicvideo><title>%s</title><artist>%s</artist></musicvideo>' % (track["track"],track["artist"])
        nfo.write(s.encode("utf8"))
        nfo.close()    
        items.append(
        {
            'label': "%s - %s" % (track["artist"], track["track"]),
            'path':  plugin.url_for('play_top_track',artist=track["artist"],track=track["track"], label=(track["label"] or "None")),
            'thumbnail':get_icon_path('tv'),
            'is_playable' : True
        })
        id = id + 1
    return items

@plugin.route('/')
def index():
    items = []
    if plugin.get_setting('scrape') == 'true':
        items.append(
        {
            'label': "Scape Whole Site to Library" ,
            'path': plugin.url_for('process_index',scrape=True),
            'thumbnail':get_icon_path('settings'),
        })    
    items = items + process_index(False)
    return items

@plugin.route('/process_index/<scrape>')
def process_index(scrape):
    items = []

    html = requests.get('http://rageagain.com').content

    match = re.compile('<a.*?</a>',flags=(re.DOTALL | re.MULTILINE)).findall(html)
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
        #log(a)
        text = re.compile('<span class="label.*?</span>',flags=(re.DOTALL | re.MULTILINE)).sub('',a)
        #log(text)
        text = re.compile('<.*?>',flags=(re.DOTALL | re.MULTILINE)).sub('',text)

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
    if scrape:
        top()
    for episode in sorted(playlists, reverse=True):
        if scrape:
            playlister(episode)
        label = "%s - %s %s" % (playlists[episode]["year"], playlists[episode]["date"], playlists[episode]["title"])
        if plugin.get_setting('episode') == "true":
            label = "[%s] %s" % (episode,label)
        items.append(
        {
            'label': label,
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