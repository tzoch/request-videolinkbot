#! usr/bin/python
'''
Class to handle video host addresses. Inteded functionality:

video = VideoHost('https://www.youtube.com/watch?v=9nWjNgV_6yc')

video.title returns: Breaking Bad: The Middle School Musical - Geek Week
video.shortLink returns: http://youtu.be/9nWjNgV_6yc

Should return the same information for all supported hosts.
'''

import re
import urlparse as up
from HTMLParser import HTMLParser

from urllib2 import urlopen

import requests
from BeautifulSoup import BeautifulSoup

# TO DO: add youtube api intergration so that I can avoid limits to calling for youtube video title
# vimeo request: http://vimeo.com/api/v2/video/[VIDEO_ID].[json]
# ex: http://vimeo.com/api/v2/video/20592566.json 

class VideoHost(object):

    def __init__(self, video_url):
        self.video_url = video_url
        self._re_patterns = {'youtube' : 'v=([A-Za-z0-9_-]+)',
        }

        # would like to support twitch.tv and nsfw video hosts
        self._supported_domains = ['youtube', 'youtu.be', 'vimeo', 'liveleak']

    @property
    def supported(self):
        if self.host in self._supported_domains:
            return True
        return False

    @property
    def host(self):
        self._parsed = up.urlparse(self.video_url)
        domain = self._parsed.netloc
        stripped = domain.lstrip('w.')
        # will work for youtube.com, vimeo.com, liveleak.com
        if stripped[-4:] == '.com':
            domain = stripped[:-4]
        # also catch youtube short links
        if stripped[-3:] == '.be' and stripped[:-3] == 'youtu':
            domain = 'youtu.be'
        return domain

    @property
    def video_id(self):
        if not self.supported:
            return None
        # get youtube id
        if self.host == 'youtube':
            regex = re.compile(self._re_patterns[self.host])
            match = re.search(regex, self.video_url)
            if match:
                # return everything but the first two items in the list
                # because those are the 'v=' characters in the youtube url
                return match.group()[2:]
            # it does link to youtube, but it is not a video (user channel, user profile, etc)
            else:
                return -1
        elif self.host == 'youtu.be':
            return self._parsed.path[1:]
        elif self.host == 'vimeo':
            return self._parsed.path[1:]
        elif self.host == 'liveleak':
            return self._parsed.query
            
    @property
    def title(self):
        if not self.supported:
            return None
        
        try:    
            site_str = urlopen(self.video_url).read()
        except:
            print 'Some error getting title of {0} video at {1}\nUsing default title!'.format(self.host, self.video_url)
            return self.video_url

        if self.host == 'youtube' or self.host == 'youtu.be':
            try:
                title = self.getYoutubeTitle(self.video_id)
                return title
            except:
                title = self.getTitleFromSoup(self.video_url)
                return title[:-10]
        elif self.host == 'liveleak':
            title = self.getTitleFromSoup(self.video_url)
            return title[15:]
        elif self.host == 'vimeo':
            try:
                title = self.getVimeoTitle(self.video_id)
                return title
            except:
                title = self.getTitleFromSoup(self.video_url)
                # remove the 'on Vimeo' at the end of every video
                return title[:-9]

    def getYoutubeTitle(self, video_id):
        api_key = 'secret'

        params = {'key': api_key, 'part': 'snippet,statistics', 'id': video_id}
        req = requests.get('https://www.googleapis.com/youtube/v3/videos', params=params)
        data = json.loads(req.text)
        return data['items'][0]['snippet']['title']

    def getVimeoTitle(self, video_id):
        url = 'http://vimeo.com/api/v2/video/'+ video_id +'.json' 
        req = requests.get(url)
        data = json.loads(req.text)
        return data[0]['title']

    def getTitleFromSoup(self, video_url):
        req = requests.get(video_url)
        soup = BeautifulSoup(req.text)
        html = soup.title.string
        clean_title = HTMLParser().unescape(html)
        return clean_title.replace('|', '-') # | (pipe characters) screw with reddit's table foramtting

    @property
    def shortLink(self):
        # this might be redundant, because at this point, the only url
        # that really gets shorter is youtube. But with this, i still strip
        # the http:// that isn't necessary
        if not self.supported:
            return None
        # get youtube id
        if self.host == 'youtube' or self.host == 'youtu.be':
            # can't shorten the link if the youtube link isn't actually a video
            if self.video_id != -1:
                return 'youtu.be/' + self.video_id
            else:
                return self.video_url
        elif self.host == 'vimeo':
            return 'vimeo.com/' + self.video_id
        elif self.host == 'liveleak':
            return 'liveleak.com/view?' + self.video_id
