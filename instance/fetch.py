import re
import requests
import json
import sqlite3
import time
import multiprocessing
import logging

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Function to retrieve RSS feed and genres from iTunes API
def getrss(url):
    match = re.search(r'id(\d+)', url)
    if match:
        podID = match.group(1)
    else:
        match = re.search(r'\d+', url)
        if match:
            podID = match.group()
        else:
            logger.error("No podcast ID found")
            return ()

    params = {
        'id': int(podID),
        'entity': 'podcast'
    }

    response = requests.get('https://itunes.apple.com/lookup', params=params)
    try:
        data = response.json()
    except json.decoder.JSONDecodeError as e:
        logger.error("JSON decoding error: %s", e)
        return ()

    results = data.get('results', [])
    if results:
        for result in results:
            if 'feedUrl' in result and 'genres' in result:
                feed_url = result['feedUrl']
                genres = result.get('genres', [])
                genres = ', '.join(genres)
                return feed_url, genres, podID

    return ()

def update_podcasts(country_code):
    if country_code not in ['fr', 'ca', 'us', 'gb']:
        logger.error("Invalid country code. Please use one of the following: 'fr', 'ca', 'us', 'gb'.")
        return

    url = f"https://itunes.apple.com/{country_code}/rss/toppodcasts/limit=200/json"

    try:
        response = requests.get(url)
        data = response.json()
    except requests.RequestException as e:
        logger.error("Request error: %s", e)
        return
    except json.decoder.JSONDecodeError as e:
        logger.error("JSON decoding error: %s", e)
        data = {}

    if "feed" in data and "entry" in data["feed"]:
        podcasts = data["feed"]["entry"]

        url_language = re.search(r'itunes.apple.com/(\w+)/', url)
        language = url_language.group(1) if url_language else ''

        json_podcast_ids = [podcast.get("id", {}).get("label") for podcast in podcasts]

        with sqlite3.connect("instance/site.db") as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT apple_podcast_id FROM discover")
            db_podcast_ids = [row[0] for row in cursor.fetchall()]

            missing_podcast_ids = set(db_podcast_ids) - set(json_podcast_ids)

            for podcast in podcasts:
                name = podcast.get("im:name", {}).get("label")
                author = podcast.get("im:artist", {}).get("label")
                summary = podcast.get("summary", {}).get("label")
                href = podcast.get("id", {}).get("label")
                genres = ""

                if name and href:
                    result = getrss(href)
                    if result:
                        rss_feed, genres, podID = result
                        try:
                            image_url = ''
                            if 'im:image' in podcast:
                                images = podcast['im:image']
                                if images:
                                    image_url = images[-1]['label']

                            cursor.execute("SELECT * FROM discover WHERE rss_feed = ?", (rss_feed,))
                            existing_podcast = cursor.fetchone()

                            if existing_podcast:
                                cursor.execute(
                                    "UPDATE discover SET title = ?, keywords = ?, image = ?, description = ?, author = ?, apple_podcast_id = ?, language = ? WHERE rss_feed = ?",
                                    (name, genres, image_url, summary, author, podID, language, rss_feed))
                                conn.commit()
                                logger.info('Podcast %s updated successfully.', name)
                            else:
                                cursor.execute(
                                    "INSERT INTO discover (title, description, author, rss_feed, image, keywords, apple_podcast_id, language) VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                                    (name, summary, author, rss_feed, image_url, genres, podID, language))
                                conn.commit()
                                logger.info('Podcast %s added successfully.', name)

                            time.sleep(0.1)

                        except Exception as e:
                            logger.error("Error adding or updating podcast: %s", e)
                    else:
                        continue
                else:
                    continue

            for missing_podcast_id in missing_podcast_ids:
                cursor.execute("SELECT * FROM discover WHERE apple_podcast_id = ?", (missing_podcast_id,))
                podcast_details = cursor.fetchone()

                if podcast_details:
                    name = podcast_details[1]
                    genres = podcast_details[6]
                    rss_feed = podcast_details[4]
                    image_url = podcast_details[5]
                    summary = podcast_details[2]
                    author = podcast_details[3]

                    try:
                        cursor.execute(
                            "UPDATE discover SET title = ?, keywords = ?, image = ?, description = ?, author = ? WHERE apple_podcast_id = ?",
                            (name, genres, image_url, summary, author, missing_podcast_id))
                        conn.commit()
                        logger.info('Podcast %s updated successfully.', name)

                        time.sleep(0.1)

                    except Exception as e:
                        logger.error("Error updating podcast: %s", e)

    else:
        logger.info("No podcasts found.")

def run_update_for_language(language_code):
    try:
        update_podcasts(language_code)
    except Exception as e:
        logger.error("Error updating podcasts for language %s: %s", language_code, e)

def run_all_updates():
    languages = ['fr', 'gb', 'ca', 'us']
    processes = []

    for lang in languages:
        p = multiprocessing.Process(target=run_update_for_language, args=(lang,))
        processes.append(p)
        p.start()

    for p in processes:
        p.join()

def run_scheduler():
    while True:
        try:
            run_all_updates()
        except Exception as e:
            logger.error("Error in scheduler: %s", e)
        time.sleep(24 * 60 * 60)  # Wait for 24 hours
