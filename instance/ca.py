import re
import requests
import json
import sqlite3
import time

# Function to retrieve RSS feed and genres from iTunes API
def getrss(url):
    feed_url = ''
    genres = ''

    match = re.search(r'id(\d+)', url)
    if match:
        podID = match.group(1)
    else:
        match = re.search(r'\d+', url)
        if match:
            podID = match.group()
        else:
            print("Aucun identifiant de podcast trouvé")
            return

    params = {
        'id': int(podID),
        'entity': 'podcast'
    }

    response = requests.get('https://itunes.apple.com/lookup', params=params)
    try:
        data = response.json()
    except json.decoder.JSONDecodeError as e:
        print("Erreur de décodage JSON :", e)
        return None, None

    results = data.get('results', [])
    if results:
        for result in results:
            if 'feedUrl' in result and 'genres' in result:
                feed_url = result['feedUrl']
                genres = result.get('genres', [])
                genres = ', '.join(genres)
                break

    rss_feed = feed_url
    return rss_feed, genres, podID

# Connect to the SQLite database
conn = sqlite3.connect("instance/site.db")
cursor = conn.cursor()

url = "https://itunes.apple.com/ca/rss/toppodcasts/limit=200/json"

response = requests.get(url)
try:
    data = response.json()
except json.decoder.JSONDecodeError as e:
    print("Erreur de décodage JSON :", e)
    data = {}

if "feed" in data and "entry" in data["feed"]:
    podcasts = data["feed"]["entry"]

    url_language = re.search(r'itunes.apple.com/(\w+)/', url)
    language = url_language.group(1) if url_language else ''

    # Get the list of podcast IDs from the JSON response
    json_podcast_ids = [podcast.get("id", {}).get("label") for podcast in podcasts]

    # Get the list of podcast IDs from the database
    cursor.execute("SELECT apple_podcast_id FROM discover")
    db_podcast_ids = [row[0] for row in cursor.fetchall()]

    # Find the podcast IDs that are in the database but not in the JSON response
    missing_podcast_ids = set(db_podcast_ids) - set(json_podcast_ids)

    for podcast in podcasts:
        name = podcast.get("im:name", {}).get("label")
        author = podcast.get("im:artist", {}).get("label")
        summary = podcast.get("summary", {}).get("label")
        href = podcast.get("id", {}).get("label")
        genres = ""

        if name and href:
            rss_feed, genres, podID = getrss(href)
            if rss_feed:
                try:
                    image_url = ''

                    if 'im:image' in podcast:
                        images = podcast['im:image']
                        if images:
                            image_url = images[-1]['label']  # Get the largest image size

                    # Check if the podcast with the same RSS feed already exists
                    cursor.execute("SELECT * FROM discover WHERE rss_feed = ?", (rss_feed,))
                    existing_podcast = cursor.fetchone()

                    if existing_podcast:
                        # Update the existing podcast details
                        cursor.execute("UPDATE discover SET title = ?, keywords = ?, image = ?, description = ?, author = ?, apple_podcast_id = ?, language = ? WHERE rss_feed = ?", (name, genres, image_url, summary, rss_feed, author, podID, language))
                        conn.commit()
                        # print('Podcast', name, 'mis à jour avec succès.')
                    else:
                        # Insert the new podcast into the database
                        cursor.execute("INSERT INTO discover (title, description, author, rss_feed, image, keywords, apple_podcast_id, language) VALUES (?, ?, ?, ?, ?, ?, ?, ?)", (name, summary, author, rss_feed, image_url, genres, podID, language))
                        conn.commit()
                        # print('Podcast', name, 'ajouté avec succès.')


                    # Sleep for a short duration to avoid overwhelming the server
                    time.sleep(0.1)

                except Exception as e:
                    print("Erreur lors de l'ajout ou de la mise à jour du podcast :", e)
            else:
                # print("Ignorer l'entrée en raison d'un flux RSS caché :", name, "-", genres)
                continue
        else:
            # print("Ignorer l'entrée en raison de champs manquants :", podcast)
            continue
else:
    print("Aucun podcast trouvé.")

# Update the podcasts that are in the database but not present in the JSON response
for missing_podcast_id in missing_podcast_ids:
    # Retrieve the podcast details from the database
    cursor.execute("SELECT * FROM discover WHERE apple_podcast_id = ?", (missing_podcast_id,))
    podcast_details = cursor.fetchone()

    if podcast_details:
        # Extract the relevant information from the database
        name = podcast_details[1]
        genres = podcast_details[6]
        rss_feed = podcast_details[4]
        image_url = podcast_details[5]
        summary = podcast_details[2]
        author = podcast_details[3]

        try:
            # Make the necessary updates to the podcast details
            # Here, you can perform the desired updates based on your requirements
            # For example, you can update the podcast details using an API request or other data sources

            # Update the podcast details in the database
            cursor.execute("UPDATE discover SET title = ?, keywords = ?, image = ?, description = ?, author = ? WHERE apple_podcast_id = ?", (name, genres, image_url, summary, author, missing_podcast_id))
            conn.commit()
            # print('Podcast', name, 'updated successfully.')

            # Sleep for a short duration to avoid overwhelming the server
            time.sleep(0.1)

        except Exception as e:
            print("Error updating podcast:", e)

# Close the database connection
conn.close()
