Request-VideoLinkBot
====================

RequestVideoLinkBot is a fork of the original VideoLinkBot by /u/shaggorama.
The original can be found here: https://github.com/dmarx/VideoLinkBot

This implementation seeks to complete this "dream" issue:
https://github.com/dmarx/VideoLinkBot/issues/37

This bot monitors the subreddit /r/RequestVideoLinkBot for user requests.

When the bot finds a new requestt, it finds the original submission,
collects all the video links, and adds a comment to the request
submission in (/r/RequestVLB). 

As of right now, the bot does not post in the original submissions. Users requesting
the bot are free to post the video list wherever they would like.

Currently, the bot only supports youtube, vimeo, and liveleak videos, but the
plan is to add support for more hosts, and to possible support NSFW hosts.

This version is by /u/OnceAndForever
