# -*- coding: utf-8 -*-
"""
    Common utilities to be used in application
"""

import os

import datetime
import json
import google.generativeai as genai
import requests
from bs4 import BeautifulSoup
from youtube_transcript_api import YouTubeTranscriptApi

# Instance folder path, to keep stuff aware from flask app.
INSTANCE_FOLDER_PATH = 'C:/flaskstarter-instance-data'


# Form validation

NAME_LEN_MIN = 4
NAME_LEN_MAX = 25

PASSWORD_LEN_MIN = 6
PASSWORD_LEN_MAX = 16


# Model
STRING_LEN = 64


def get_current_time():
    return datetime.datetime.utcnow()


def pretty_date(dt, default=None):
    # Returns string representing "time since" eg 3 days ago, 5 hours ago etc.

    if default is None:
        default = 'just now'

    now = datetime.datetime.utcnow()
    diff = now - dt

    periods = (
        (diff.days / 365, 'year', 'years'),
        (diff.days / 30, 'month', 'months'),
        (diff.days / 7, 'week', 'weeks'),
        (diff.days, 'day', 'days'),
        (diff.seconds / 3600, 'hour', 'hours'),
        (diff.seconds / 60, 'minute', 'minutes'),
        (diff.seconds, 'second', 'seconds'),
    )

    for period, singular, plural in periods:

        if not period:
            continue

        if int(period) >= 1:
            if int(period) > 1:
                return u'%d %s ago' % (period, plural)
            return u'%d %s ago' % (period, singular)

    return default

def request_ai(prompt_text, file_object = None ):
    try:
        genai.configure(api_key=os.environ.get("GOOGLE_API_KEY"))
        model = genai.GenerativeModel('gemini-2.5-flash')
        content_to_send = [prompt_text]
        if file_object:
            content_to_send.append(file_object)
        generation_config = genai.types.GenerationConfig(
            response_mime_type="application/json"
        )
        response = model.generate_content(content_to_send, generation_config=generation_config)
        return json.loads(response.text)
    except Exception as e:
        print(f"An error occurred with the Gemini API: {e}")
        return None


def get_content(url):
    # --- YouTube Logic ---
    if "youtube.com/watch" in url or "youtu.be" in url:
        try:
            video_id = None
            if "v=" in url:
                video_id = url.split('v=')[1].split('&')[0]
            elif "youtu.be" in url:
                video_id = url.split('/')[-1]

            if not video_id:
                return False, "Could not find a valid YouTube video ID in the URL."

            transcript_list = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'de'])
            full_transcript = " ".join([item['text'] for item in transcript_list])
            return True, full_transcript
        except Exception as e:
            return False, f"Could not retrieve transcript: {e}"

    # --- Classic Article Logic ---
    else:
        try:
            headers = {
                'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
            }
            response = requests.get(url, headers=headers, timeout=10)
            response.raise_for_status()

            soup = BeautifulSoup(response.content, 'html.parser')

            selectors = ['article', 'main', 'div[role="main"]', 'div#main', 'div#content', 'div.post-content', 'div.article-body']
            content_area = None
            for selector in selectors:
                content_area = soup.select_one(selector)
                if content_area:
                    break
            
            if content_area:
                article_text = content_area.get_text(separator='\n', strip=True)
            else:
                article_text = soup.body.get_text(separator='\n', strip=True)
                
            return True, article_text
        except requests.RequestException as e:
            return False, f"Could not retrieve article: {e}"
        