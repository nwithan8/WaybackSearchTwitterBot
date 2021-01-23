#!/usr/bin/python3

import logging
import tweepy
from tweepy import StreamListener, Stream

logging.basicConfig(format='%(asctime)s %(levelname)s:%(message)s',
                    level=logging.INFO)


def info(message: str):
    logging.info(msg=message)


def error(message: str):
    logging.error(msg=message)


def warning(message: str):
    logging.warning(msg=message)


class StdOutListener(StreamListener):

    def __init__(self, function_to_run):
        super().__init__()
        self._on_status_function = function_to_run

    def on_status(self, status):
        return self._on_status_function(status)

    def on_error(self, status_code):
        error(f"Error, code {status_code}")


class TwitterConnector:
    def __init__(self, consumer_key: str, consumer_secret: str, access_token: str, access_secret: str):
        self._auth = tweepy.OAuthHandler(consumer_key, consumer_secret)
        self._auth.set_access_token(access_token, access_secret)
        self._twit = tweepy.API(self._auth)
        self.stream = None
        info('Connected to Twitter.')

    def get_recent_tweets(self):
        return self._twit.user_timeline()

    def send_tweet(self, text: str):
        self._twit.update_status(text)

    def start_stream(self, username_to_track: str, function_to_run):
        listener = StdOutListener(function_to_run=function_to_run)
        self.stream = Stream(self._auth, listener)
        self.stream.filter(track=[username_to_track])


# Twitter API Credentials
"""
consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
access_secret = os.environ.get('TWITTER_ACCESS_SECRET')
"""
consumer_key = ''
consumer_secret = ''
access_token = ''
access_secret = ''


def print_hello(status):
    print("Hello!")


twitter = TwitterConnector(consumer_key=consumer_key,
                           consumer_secret=consumer_secret,
                           access_token=access_token,
                           access_secret=access_secret)

twitter.start_stream(username_to_track='nwithan8', function_to_run=print_hello)
