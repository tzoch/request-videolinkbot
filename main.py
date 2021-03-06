#! /usr/bin/python
'''
Reddit Bot based off of VideoLinkBot by /u/shaggorama

This implementation seeks to complete this "dream" issue:
https://github.com/dmarx/VideoLinkBot/issues/37

This bot monitors the subreddit /r/RequestVideoLinkBot for user
requests. When the bot finds a new requestt, it finds the 
original submission, collects all the video links, and adds a 
comment to the request submission in (/r/RequestVLB).

As of right now, the bot does not post in the original 
submissions. Users requesting the bot are free to post the 
video list wherever they would like.

Currently, the bot only supports youtube, vimeo, and liveleak 
videos, but the plan is to add support for more hosts, and to 
possibly support NSFW hosts.

This version is by /u/OnceAndForever
'''
                                      
import time
import json
import re
import urlparse as up

import praw

from database import Database
from videohost import VideoHost


class RequestVLB(object):

    def __init__(self, subreddit, db_name, r):
        self.last_update = time.time()
        self.subreddit = subreddit

        self.r = r
        self.request_subreddit = self.r.get_subreddit(subreddit)
        self.submissions_to_crawl = []
        self.sleep_interval = 300 # 5 minutes
        self.db = Database(db_name)

    def processRequests(self, upd_interval=0):
        '''
        Reads the request subreddit and returns a list of submission_ids
        to scrape for videos
        
        :request_id refers to the submission id of the submission in 
            /r/RequestVideoLinkBot (where the request is made)
        :target_url refers to the full url of the reddit submission 
            that is the _target_ of the request
        :target_id refers to the submission id of the _target_ of the request
        '''
        if not self.submissions_to_crawl:
            print "No new requests to process! Fetching more..."
            print "Retrieving submissions from [{0}]".format(self.subreddit)
            print "Submissions last retrieved at [{0}]".format(
                                            time.strftime('%Y-%m-%d %H:%M:%S',
                                            time.localtime(self.last_update))
                                            )

            submissions = self.request_subreddit.get_new(limit=None)
            for request in submissions:
                # make sure the submission hasn't already been processed
                # and need to make sure the request links reddit thread
                if not self.db.isProcessed(request.id) and request.domain == 'reddit.com':
                    # for example
                    # exctract the 1jp6fc from the reddit url 
                    target_url = up.urlparse(request.url).path
                    target_id = target_url.split('/')[4]

                    self.submissions_to_crawl.append({
                                                    'request_id': request.id,
                                                    'target_url': request.url,
                                                    'target_id': target_id})

            self.last_update = time.time()
        else:
            # If there are requests to fulfil already, do those
            while self.submissions_to_crawl:
                request = self.submissions_to_crawl.pop()
                print 'Processing request: [{0}]'.format(
                                                        request['target_url']
                                                        )
                video_request = ProcessRequest(request['request_id'], 
                                               request['target_url'], 
                                               request['target_id'], 
                                               self.r)
                video_request.postComment()
            self.last_update = time.time()


class ProcessRequest(object):

    def __init__(self, request_id, target_url, 
                 target_id, r, db_name='processed.db'):
        self.request_id = request_id
        self.target_id = target_id
        self.target_url = target_url

        # need two instances of the praw submission object
        # target_submission, which is where the videos will be collected from.
        # request_submission, which is where the videos will be posted.
        self.r = r
        self.request_submission = self.r.get_submission(
                                            submission_id=self.request_id)
        self.target_submission = self.r.get_submission(
                                            submission_id=self.target_id,
                                            comment_limit=None)
        self.cache = Database()
        self.db = Database(db_name)

    def getVideoLinksFromHTML(self, comment_html):
        '''
        Takes the html str of a comment and returns a list of video links if
        the link is from a supported domain video host if there is one. 
        Otherwise, this returns an empty list.
        '''
        # thought i could use plaintext comments, but HTML is more reliable
        link_path = re.compile('href="(.*?)"')
        re_matches = link_path.findall(comment_html)
        links = []
        for match in re_matches:
            # Check to make sure whatever is in parenthesis is actually a link
            # the VideoHost class is responsible for validating video links
            link = up.urlparse(match).netloc
            if link:
                links.append(match)

        return links

    def getVideosInSubmission(self):
        '''
        Returns a nested list of all the comments with videos in them from
        a requested submission.

        This list contains all the information needed to make the comment.

        List format: [[commentor_username, comment_permalink, comment_score, 
                        video_link, video_title],...]
        '''

        flat_comments = praw.helpers.flatten_tree(self.target_submission.comments)
        for comment in flat_comments:
            comment_permalink = 'reddit.com/comments/' + self.target_id + '/_/' + comment.id
            # this was giving me a lot of problems
            if hasattr(comment, 'author'): # Apparently not everything is really a comment?
                if comment.author: # ignore deleted comments
                    if comment.author.name != 'VideoLinkBot': # ignore original VideoLinkBot
                        # find all links in comment text (comment could have multiple links)
                        links = self.getVideoLinksFromHTML(comment.body_html)
                        if links:
                            for video_link in links:
                                video = VideoHost(video_link)
                                if video.supported:
                                    self.cache.cacheLinks((comment.author.name, 
                                                           comment_permalink, 
                                                           comment.ups - comment.downs, 
                                                           video.title, 
                                                           video.shortLink))

        return self.cache.returnLinksCache()

    def comment(self, score_threshold=0):
        head = '''Here is a list of video links posted in [this requested submission]({0}):

|Source Comment|Score|Video Link|
|:-------|:-------:|:-------|\n'''.format(self.target_url)

        tail ="""\n[^[RequestVideoLinkBot&nbsp;FAQ]](http://www.reddit.com/r/RequestVideoLinkBot/wiki/faq) 
        [^[Feedback]](http://www.reddit.com/r/RequestVideoLinkBot/submit) 
        [^[Original&nbsp;VideoLinkBot]](http://www.reddit.com/u/VideoLinkBot) 
        [^[Source]](https://github.com/tzoch/request-videolinkbot)""" 
        
        text = u''
        if not self.cache.linksCache:
            video_data = self.getVideosInSubmission()
        else:
            video_data = self.cache.linksCache
        for data in video_data:
            if data[2] >= score_threshold: # help us trim comment
                # the list comes out as [author, comment_permalink, score, video_link, video_title]
                text += u'|[{0}]({1})|{2}|[{3}]({4})|\n'.format(data[0], 
                                                         addHTTP(data[1]), 
                                                         data[2], 
                                                         data[3], 
                                                         addHTTP(data[4]))

        return head+text+tail.encode('utf-8')

    def postComment(self):
        if len(self.comment()) < 10000:
            # currently only posts the comment to the request post, and not in the target post
            # but that functionality could be added
            try:
                self.request_submission.add_comment(self.comment())
                print 'Comment sucessfully posted!'
                self.db.markAsProcessed(self.request_id)
                return
            except:
                print 'Comment not posted!'
        else:
            print 'Comment is too long!\n[{0}] characters\nTrimming videos below threshold'.format(len(self.comment()))
            try:
                self.request_submission.add_comment(self.comment(5)) # don't post videos with a score of less than 5
                print 'Comment successfully posted!'
                self.db.markAsProcessed(self.request_id)
                return
            except:
                print 'Comment not posted!'

def addHTTP(url):
    if url[:7] == 'http://' or url[:8] == 'https://':
        return url
    else:
        return 'http://' + url

def main():
    config = json.load(open('config.json'))

    r = praw.Reddit(config['user-agent'])
    r.login(config['username'], config['password'])

    vlb = RequestVLB('RequestVideoLinkBot', config['database'], r)

    while True:
        print 'Top of loop'
        try:
            vlb.processRequests()
        except KeyboardInterrupt:
            import sys
            sys.exit(0)
        finally:
            if not vlb.submissions_to_crawl: # We have processed everything. Sleep and wait for new requests
                print 'Finished Processing...taking a nap for {0} seconds'.format(vlb.sleep_interval)
                time.sleep(vlb.sleep_interval)

if __name__ == '__main__':
    main()
