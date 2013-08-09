# usr/bin/python
'''
Class to deal with database connections and queries for
Request VideoLinkBot
'''

import sqlite3

class Database(object):

    def __init__(self, database=":memory:"):
        self.linksCache = []
        self._database = database
        c = self.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS request_submissions (processed_id INTEGER PRIMARY KEY ASC, request_id VARCHAR(10) UNIQUE)')
        self.conn.commit()

    @property
    def conn(self):
        if not hasattr(self, '_connection'):
            self._connection = sqlite3.connect(self._database)
        return self._connection

    def close(self):
        self.conn.close()

    def cursor(self):
        return self.conn.cursor()

    def getProcessed(self):
        c = self.cursor()
        c.execute('SELECT request_id FROM request_submissions')
        return c.fetchall() is not None

    def isProcessed(self, request_id):
        c = self.cursor()
        c.execute('SELECT request_id FROM request_submissions WHERE request_id = ?', (request_id,))
        if c.fetchone():
            return True
        return False

    def markAsProcessed(self, request_id):
        c = self.cursor()
        c.execute('INSERT INTO request_submissions (request_id) VALUES (?)', (request_id,))
        self.conn.commit()

    def cacheLinks(self, tuple_values):
        c = self.cursor()
        c.execute('CREATE TABLE IF NOT EXISTS link_cache (user_name VARCHAR, comment_permalink VARCHAR, karma_score INT, video_short_link VARCHAR, video_title VARCHAR)')
        self.conn.commit()
        # if list_values <= 1:
        c.execute('INSERT INTO link_cache (user_name, comment_permalink, karma_score, video_short_link, video_title) VALUES (?, ?, ?, ?, ?)', tuple_values) 
        # else:
        #     c.executemany('INSERT INTO link_cache (user_name, comment_permalink, karma_score, video_short_link, video_title) VALUES (?, ?, ?, ?, ?)', list_values)
        self.conn.commit()

    def returnLinksCache(self):
        c = self.cursor()
        c.execute('SELECT user_name, comment_permalink, karma_score, video_short_link, video_title FROM link_cache ORDER BY karma_score DESC')
        self.linksCache = c.fetchall()
        return self.linksCache
