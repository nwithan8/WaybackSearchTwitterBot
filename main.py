#!/usr/bin/python3

import logging
import os
import re
import urllib
from typing import Union, Tuple

import tweepy
from tweepy import StreamListener, Stream
import waybackpy

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
        self.api = tweepy.API(self._auth)
        self.stream = None
        info('Connected to Twitter.')

    def get_recent_tweets(self):
        return self.api.user_timeline()

    def reply_to_tweet(self, tweet, text: str):
        self.api.update_status(f"@{str(tweet.user.screen_name)} {text}", in_reply_to_status_id=tweet.id)

    def send_tweet(self, text: str):
        self.api.update_status(text)

    def start_stream(self, username_to_track: str, function_to_run):
        listener = StdOutListener(function_to_run=function_to_run)
        self.stream = Stream(self._auth, listener)
        self.stream.filter(track=[username_to_track])


# Twitter API Credentials

consumer_key = os.environ.get('TWITTER_CONSUMER_KEY')
consumer_secret = os.environ.get('TWITTER_CONSUMER_SECRET')
access_token = os.environ.get('TWITTER_ACCESS_TOKEN')
access_secret = os.environ.get('TWITTER_ACCESS_SECRET')


twitter = TwitterConnector(consumer_key=consumer_key,
                           consumer_secret=consumer_secret,
                           access_token=access_token,
                           access_secret=access_secret)


def was_mentioned(status) -> bool:
    if hasattr(status, 'retweeted_status'):
        return False
    elif not status.entities['user_mentions']:
        return False
    else:
        for u in status.entities['user_mentions']:
            if u['screen_name'].lower() == 'searchwayback':
                return True
        return False


def get_base_tweet(status) -> tweepy.models.Status:
    if hasattr(status, 'in_reply_to_status_id') and status.in_reply_to_status_id:
        return twitter.api.get_status(status.in_reply_to_status_id)
    return status


def extract_link_from_tweet(status) -> str:
    url = re.findall('http[s]?://(?:[a-zA-Z]|[0-9]|[$-_@.&+]|[!*\(\),]|(?:%[0-9a-fA-F][0-9a-fA-F]))+', status.text)
    if not url:
        return ""
    url = url[0]  # only interact with the first link in a tweet
    try:
        return urllib.request.urlopen(url).geturl()  # not the way I would do it, but thanks SO
    except:
        return ""


def get_wayback_item(url) -> Union[waybackpy.Url, None]:
    try:
        user_agent = "Mozilla/5.0 (Macintosh; Intel Mac OS X 10.8; rv:40.0) Gecko/20100101 Firefox/40.0"
        return waybackpy.Url(url, user_agent)
    except:
        return None


def filter_wayback_with_instructions(status, wayback_item, url) -> str:
    try:
        date = re.search("([0-9]{2}\-[0-9]{2}\-[0-9]{4})", status.text)
        response = ""
        if "save" in status.text:
            try:
                wayback_item.save()
                return f"I saved that link to the Wayback Machine: https://web.archive.org/web/{url}"
            except:
                return f"Sorry, I couldn't save that link automatically. Click here to manually save it: " \
                       f"https://web.archive.org/save/{url} "
        elif date:
            date = date[0]  # only use first date
            month_day_year = date.split("-")
            wayback_item_entry = wayback_item.near(month=month_day_year[0], day=month_day_year[1],
                                                   year=month_day_year[2])
            return f"Here you go, the archive entry closest to {date}: {wayback_item_entry.archive_url}"
        elif "oldest" in status.text:
            wayback_item_entry = wayback_item.oldest()
            return f"Here you go, the oldest archive entry: {wayback_item_entry.archive_url}"
        else:
            wayback_item_entry = wayback_item.newest()
            return f"Here you go, the most recent archive entry: {wayback_item_entry.archive_url}"
    except:
        return "I had problems parsing the link and/or instructions from the tweet."


def process_tweet(status):
    info(f"Received tweet from f{status.user.screen_name}")
    if was_mentioned(status=status):
        tweet_to_reply_to = status
        tweet_with_link = get_base_tweet(status=status)
        link = extract_link_from_tweet(status=tweet_with_link)
        if link:
            wayback_item = get_wayback_item(url=link)
            if wayback_item is None:
                response = "I couldn't find that link on the Wayback Machine."
            else:
                response = filter_wayback_with_instructions(status=tweet_to_reply_to,
                                                            wayback_item=wayback_item,
                                                            url=link)
            twitter.reply_to_tweet(tweet=tweet_to_reply_to, text=response)
            info(f"Sent response to {tweet_to_reply_to.user.screen_name}: {response}")


twitter.start_stream(username_to_track='searchwayback', function_to_run=process_tweet)
