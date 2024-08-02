# app/routes.py

import signal
import unicodedata
import subprocess
import threading
import traceback
import base64
from werkzeug.utils import secure_filename
import pyotp
from pyotp import TOTP
import qrcode
from dateutil import parser as date_parser
from xml.etree import ElementTree as ET
from datetime import datetime
import re
from urllib.parse import urlparse
import os
import sys
import time
import requests
from flask import Blueprint, render_template, flash, redirect, url_for, request, jsonify, send_file, \
    send_from_directory, session, abort
from flask_login import login_user, current_user, logout_user, login_required
from app.models import User, Podcast, Episode, db, UnfinishedEpisode, UserPodcast, Discover
from app import bcrypt
from PIL import Image
from io import BytesIO
import feedparser
from random import choice

main = Blueprint('main', __name__)

sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../instance')))
from fetch import update_podcasts

def run_update_for_language(language_code):
    update_podcasts(language_code)

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
        except:
            continue
        time.sleep(24 * 60 * 60)  # Wait for 24 hours


# Start the scheduler in the background
scheduler_thread = threading.Thread(target=run_scheduler)
scheduler_thread.start()


@main.route('/')
def index():
    return render_template('index.html')


@main.route('/favicon.ico')
def favicon():
    return send_from_directory(('./static/assets'), 'favicon.ico', mimetype='image/vnd.microsoft.icon')


@main.route('/apple-touch-icon.png')
def apple_touch_icon():
    return send_from_directory(('./static/assets'), 'apple-touch-icon.png', mimetype='image/png')


@main.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('main.index'))

    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user:
            flash('Nom d\'utilisateur déjà existant. Veuillez choisir un nom d\'utilisateur différent.', 'danger')
        elif not is_password_strong(password):
            flash(
                'Le mot de passe doit comporter au moins 8 caractères et contenir au moins une lettre majuscule, une lettre minuscule et un chiffre.',
                'danger')
        else:
            hashed_password = bcrypt.generate_password_hash(password).decode('utf-8')
            new_user = User(username=username, password=hashed_password, is_2fa_enabled=False, otp_secret=False)
            db.session.add(new_user)
            db.session.commit()
            flash('Inscription réussie. Vous pouvez maintenant vous connecter.', 'success')
            return redirect(url_for('main.login'))

    return render_template('register.html')


def is_password_strong(password):
    if len(password) < 8:
        return False
    if not re.search(r'[A-Z]', password):
        return False
    if not re.search(r'[a-z]', password):
        return False
    if not re.search(r'\d', password):
        return False
    return True


@main.route('/verify_2fa', methods=['GET', 'POST'])
def verify_2fa():
    if 'user_id' not in session:
        return redirect(url_for('main.login'))

    if request.method == 'POST':
        totp_code = request.form.get('totp_code')

        user = User.query.get(session['user_id'])

        if user and user.is_2fa_enabled:
            totp = TOTP(user.otp_secret)

            if totp.verify(totp_code):
                login_user(user)
                session.pop('user_id')

                next_url = session.get('next_url')
                session.pop('next_url', None)

                if next_url:
                    return redirect(next_url)
                else:
                    return redirect(url_for('main.index'))
            else:
                flash('Code 2FA invalide. Veuillez réessayer.', 'danger')

    return render_template('verify_2fa.html')


@main.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        next_url = session.get('next_url')
        session.pop('next_url', None)
        if next_url:
            return redirect(next_url)
        else:
            return redirect(url_for('main.index'))
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        user = User.query.filter_by(username=username).first()

        if user and bcrypt.check_password_hash(user.password, password):
            if user.is_2fa_enabled:
                session['user_id'] = user.id
                return redirect(url_for('main.verify_2fa'))
            else:
                login_user(user)

                next_url = session.get('next_url')
                session.pop('next_url', None)

                if next_url:
                    return redirect(next_url)
                else:
                    return redirect(url_for('main.index'))

        else:
            flash('Connexion échouée. Veuillez vérifier votre nom d\'utilisateur et votre mot de passe.', 'danger')
    else:
        next_url = request.args.get('next')
        if next_url:
            session['next_url'] = next_url

    return render_template('login.html')


@main.route('/settings', methods=['GET', 'POST'])
@login_required
def settings():
    session['2fa_enabled'] = current_user.is_2fa_enabled
    if request.method == 'POST':
        if 'new_username' in request.form:
            new_username = request.form['new_username']
            user = User.query.filter_by(username=new_username).first()
            if user:
                flash('Nom d\'utilisateur déjà existant. Veuillez choisir un nom d\'utilisateur différent.', 'danger')
                return redirect(url_for('main.settings'))
            current_user.username = new_username
            db.session.commit()
            flash('Nom d\'utilisateur modifié avec succès !', 'success')
            return redirect(url_for('main.settings'))

        if 'current_password' in request.form and 'new_password' in request.form and 'confirm_password' in request.form:
            current_password = request.form['current_password']
            new_password = request.form['new_password']
            confirm_password = request.form['confirm_password']

            if not bcrypt.check_password_hash(current_user.password, current_password):
                flash('Le mot de passe actuel est incorrect.', 'danger')
                return redirect(url_for('main.settings'))

            if new_password != confirm_password:
                flash('Le nouveau mot de passe et la confirmation ne correspondent pas.', 'danger')
                return redirect(url_for('main.settings'))

            if not is_password_strong(new_password):
                flash(
                    'Le mot de passe doit contenir au moins 8 caractères et inclure une combinaison de lettres, de chiffres et de caractères spéciaux.',
                    'danger')
                return redirect(url_for('main.settings'))

            current_user.password = bcrypt.generate_password_hash(new_password).decode('utf-8')
            db.session.commit()
            flash('Mot de passe modifié avec succès !', 'success')
            return redirect(url_for('main.settings'))

        if 'enable_2fa' in request.form:
            enable_2fa = request.form.get('enable_2fa')

            if enable_2fa == 'on':
                # Générer et afficher le code QR pour la configuration de l'authentification à deux facteurs (2FA)
                totp = pyotp.TOTP(pyotp.random_base32())
                qr_code_data = totp.provisioning_uri(name=current_user.username, issuer_name='Steraudio')
                img = qrcode.make(qr_code_data)
                buffer = BytesIO()
                img.save(buffer, format='PNG')
                qr_code_image = base64.b64encode(buffer.getvalue()).decode('utf-8')

                session['2fa_secret'] = totp.secret
                session['2fa_enabled'] = False

                return render_template('enable_2fa.html', qr_code_image=qr_code_image)

            else:
                # Désactiver l'authentification à deux facteurs (2FA)
                session.pop('2fa_secret', None)
                session['2fa_enabled'] = False

                current_user.otp_secret = None
                current_user.is_2fa_enabled = False
                db.session.commit()

                flash('L\'authentification à deux facteurs (2FA) a été désactivée !', 'success')
                return redirect(url_for('main.settings'))

        if 'totp_code' in request.form:
            if session['2fa_enabled']:
                # 2FA est déjà activé
                flash('L\'authentification à deux facteurs (2FA) est déjà activée !', 'info')

            totp_code = request.form.get('totp_code')

            if '2fa_secret' in session:
                totp = pyotp.TOTP(session['2fa_secret'])

                if totp.verify(totp_code):
                    # Activer l'authentification à deux facteurs (2FA)
                    current_user.otp_secret = str(session['2fa_secret'])
                    current_user.is_2fa_enabled = True
                    db.session.commit()
                    session['2fa_enabled'] = True
                    flash('L\'authentification à deux facteurs (2FA) a été activée !', 'success')
                else:
                    flash('Code TOTP invalide. Veuillez réessayer.', 'danger')

            if not session['2fa_enabled']:
                session['2fa_enabled'] = False
            return redirect(url_for('main.settings'))

        if 'delete_account' in request.form:
            # Delete podcasts linked to user (id)
            podcasts = UserPodcast.query.filter_by(user_id=current_user.id).all()
            for podcast in podcasts:
                # Delete the podcast itself
                db.session.delete(podcast)

            # Delete the user
            db.session.delete(current_user)
            db.session.commit()
            logout_user()
            flash('Votre compte a été supprimé !', 'success')
            return redirect(url_for('main.index'))

        if 'delete_podcasts' in request.form:
            # Delete podcasts linked to user (id)
            podcasts = UserPodcast.query.filter_by(user_id=current_user.id).all()
            for podcast in podcasts:
                # Delete the podcast itself
                db.session.delete(podcast)

            db.session.commit()
            flash('Vos podcasts ont été supprimé !', 'success')
            return redirect(url_for('main.settings'))

    return render_template('settings.html')


@main.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('main.index'))


def is_url_and_rss_feed(string):
    result = urlparse(string)
    if not all([result.scheme, result.netloc]):
        return False

    try:
        feed = feedparser.parse(string)
        return bool(feed.version)
    except:
        return False


@main.route('/podcasts', methods=['GET', 'POST'])
@login_required
def podcasts():
    if request.method == 'POST':
        if request.form.get('title'):
            title = request.form.get('title')
        else:
            title = False
        rss_feed = request.form.get('rss_feed')

        if is_url_and_rss_feed(rss_feed):
            add_podcast_to_db(rss_feed)
        else:
            flash('URL du podcast invalide !', 'error')
            return redirect(url_for('main.podcasts'))

    podcasts = current_user.podcasts
    return render_template('podcasts.html', podcasts=podcasts)


def add_podcast_to_db(rss_feed):
    # Query the podcast URL to retrieve the keywords and image
    response = requests.get(rss_feed)
    if response.status_code != 200:
        flash('Erreur lors de la requête du podcast. Veuillez vérifier l\'URL.', 'error')
        return redirect(url_for('main.podcasts'))

    xml_data = response.text

    try:
        # Parse the XML data
        root = ET.fromstring(xml_data)

        # Check if the parsed feed is valid and contains podcast information
        itunes_ns = {'itunes': 'http://www.itunes.com/dtds/podcast-1.0.dtd'}
        subtitle_elem = root.find('.//itunes:summary', itunes_ns)
        author_elem = root.find('.//itunes:author', itunes_ns)
        image_elem = root.find('.//itunes:image', itunes_ns)
        title_elem = root.find('.//title')
        language_elem = root.find('.//language')
        explicit_elem = root.find('.//itunes:explicit', itunes_ns)

        if language_elem is not None:
            language = language_elem.text

        if explicit_elem is not None:
            explicit = explicit_elem.text
            if explicit == 'yes':
                explicit = True
            elif explicit == 'no':
                explicit = False
            else:
                explicit = False
        else:
            explicit = False

        owner_elem = root.find('.//itunes:owner', itunes_ns)

        if owner_elem is not None:
            name_elem = owner_elem.find('.//itunes:name', itunes_ns)
            if name_elem is not None and name_elem.text:
                owner_name = name_elem.text.strip()
            else:
                owner_name = ''

        # Check if the feed has at least one episode
        episode_elems = root.findall('.//item')

        required_elems = [author_elem, image_elem, title_elem, language_elem]
        if len(episode_elems) >= 1 and all(elem is not None for elem in required_elems):
            author = author_elem.text

            try:
                subtitle = subtitle_elem.text
            except:
                try:
                    subtitle = root.find('.//description').text
                except Exception as e:
                    subtitle = None
                    print(e)

            try:
                title = title_elem.text
            except:
                try:
                    title = root.find('.//title').text
                except Exception as e:
                    print(e)
                    flash('URL du podcast invalide !', 'error')
                    return redirect(url_for('main.podcasts'))

            existing_podcast_relationships = UserPodcast.query.filter_by(user_id=current_user.id).all()

            if existing_podcast_relationships:
                for relationship in existing_podcast_relationships:
                    existing_podcast = Podcast.query.filter_by(rss_feed=rss_feed, id=relationship.podcast_id).first()
                    if existing_podcast:
                        flash('Vous êtes déjà abonné au podcast : ' + str(existing_podcast.title) + '.', 'error')
                        return redirect(url_for('main.podcasts'))

            if subtitle:
                # Handle <![CDATA[...]]> section for subtitle
                cdata_regex = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)
                matches = cdata_regex.findall(subtitle)
                if matches:
                    description = matches[0]
                else:
                    description = re.sub('<[^<]+?>', '', subtitle)  # Strip HTML tags
            else:
                description = "Aucune description"

            image_elem = root.find('.//itunes:image', itunes_ns)
            image_url = image_elem.get('href') if image_elem is not None else ""

            try:
                categories = root.findall('.//itunes:category', itunes_ns)
                category_texts = [category.get('text') for category in categories]
                keywords = ', '.join(category_texts)
            except:
                keywords = None
        else:
            # It is not a valid podcast
            flash('URL du podcast invalide !', 'error')
            return redirect(url_for('main.podcasts'))
    except Exception as e:
        flash('Erreur lors de l\'analyse du podcast. Veuillez vérifier l\'URL.', 'error')
        traceback.print_exc()
        return redirect(url_for('main.podcasts'))

    existing_podcast = Podcast.query.filter_by(rss_feed=rss_feed).first()

    if existing_podcast:
        # Le podcast existe déjà, ajouter l'utilisateur à la liste des abonnés
        if current_user in existing_podcast.subscribers:
            flash('Vous êtes déjà abonné au podcast ' + str(existing_podcast.title), 'info')
        else:
            existing_podcast.subscribers.append(current_user)
            db.session.commit()
            flash('Le podcast ' + str(existing_podcast.title) + ' a été ajouté avec succès !', 'success')
    else:
        # Le podcast n'existe pas, créer un nouveau podcast
        new_podcast = Podcast(title=title, rss_feed=rss_feed, description=description, author=author)
        new_podcast.image = image_url
        new_podcast.keywords = keywords
        new_podcast.owner = owner_name
        new_podcast.explicit = explicit
        new_podcast.language = language
        new_podcast.subscribers.append(current_user)
        db.session.add(new_podcast)
        db.session.commit()
        flash('Le podcast ' + str(title) + ' a été ajouté avec succès !', 'success')


@main.route('/podcasts/delete/<int:podcast_id>', methods=['POST'])
@login_required
def delete_podcast(podcast_id):
    podcast = Podcast.query.get_or_404(podcast_id)

    if current_user in podcast.subscribers:
        podcast.subscribers.remove(current_user)
        db.session.commit()
        flash('Vous avez été désabonné du podcast ' + str(podcast.title), 'success')
    else:
        flash('Vous n\'êtes pas abonné à ce podcast.', 'info')

    return redirect(url_for('main.podcasts'))


@main.route('/podcasts/<int:podcast_id>')
@login_required
def view_podcast(podcast_id):
    podcast = Podcast.query.get_or_404(podcast_id)

    if current_user not in podcast.subscribers:
        flash('Vous n\'êtes pas abonné à ce podcast.', 'danger')
        return render_template('index.html')

    return render_template('podcast.html', podcast=podcast)


@main.route('/api/resize/<path:image_url>/<int:image_size>')
def resize_image(image_url, image_size):
    if image_size is not None and int(image_size) > 1000:
        abort(404)
    try:
        response = requests.get(image_url)
        image = Image.open(BytesIO(response.content))

        # Resize the image
        resized_image = image.resize((image_size, image_size))

        # Create a BytesIO object to store the resized image
        resized_image_data = BytesIO()
        resized_image.save(resized_image_data, format='png')
        resized_image_data.seek(0)

        # Return the resized image as a response
        return send_file(resized_image_data, mimetype='image/jpeg')
    except Exception as e:
        # Handle any errors that occur during image resizing or retrieval
        flash('Erreur lors du redimensionnement de l\'image.', 'error')
        return redirect(url_for('main.index'))


@main.route('/api/episodes/<int:podcast_id>', methods=['GET'])
@login_required
def api_episodes(podcast_id):
    podcast = Podcast.query.get_or_404(podcast_id)

    # Query the podcast URL to retrieve the episodes and podcast details
    response = requests.get(podcast.rss_feed)
    xml_data = response.text

    # Parse the XML data
    root = ET.fromstring(xml_data)
    episodes_data = root.findall('.//item')[:50]  # Limit to a maximum of 50 episodes

    # Track the episodes to be deleted
    episodes_to_delete = list(podcast.episodes)

    # Add or update the episodes in the database
    for episode_data in episodes_data:
        title = episode_data.find('title').text
        audio_url = episode_data.find('.//enclosure').get('url')
        pubdate_str = episode_data.find('.//pubDate').text
        subtitle_elem = episode_data.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}summary')
        description_elem = episode_data.find('.//description')
        duration_elem = episode_data.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}duration')
        episode_elem = episode_data.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}episode')
        season_elem = episode_data.find('.//{http://www.itunes.com/dtds/podcast-1.0.dtd}season')

        # Check if subtitle element exists
        if subtitle_elem is not None:
            # Handle <![CDATA[...]]> section for subtitle
            subtitle = subtitle_elem.text
            cdata_regex = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)
            matches = cdata_regex.findall(subtitle)
            if matches:
                subtitle = matches[0]
            else:
                subtitle = re.sub('<[^<]+?>', '', subtitle)  # Strip HTML tags
        elif description_elem is not None:
            # Handle <![CDATA[...]]> section for description
            description = description_elem.text
            cdata_regex = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)
            matches = cdata_regex.findall(description)
            if matches:
                subtitle = matches[0]
            else:
                subtitle = re.sub('<[^<]+?>', '', description)  # Strip HTML tags
        else:
            subtitle = ""

        # Check if duration element exists
        if duration_elem is not None:
            try:
                duration = time.strftime('%H:%M:%S', time.gmtime(int(duration_elem.text)))
            except:
                duration = duration_elem.text
        else:
            duration = ""

        # Convert pubdate string to datetime object
        pubdate = date_parser.parse(pubdate_str)

        if episode_elem is not None:
            episode_number = episode_elem.text
        else:
            episode_number = ''

        if season_elem is not None:
            season_number = season_elem.text
        else:
            season_number = ''

        # Check if the episode already exists in the database
        existing_episode = Episode.query.filter_by(
            title=title,
            pubdate=pubdate,
            podcast_id=podcast.id
        ).first()

        # If the episode doesn't exist, add it to the database
        if not existing_episode:
            episode = Episode(
                title=title,
                subtitle=subtitle,
                audio_url=audio_url,
                pubdate=pubdate,
                duration=duration,
                episode=episode_number,
                season=season_number,
                podcast_id=podcast.id
            )
            db.session.add(episode)
        else:
            # If the episode exists, update it if any of its elements don't match
            if (
                    existing_episode.subtitle != subtitle or
                    existing_episode.audio_url != audio_url or
                    existing_episode.duration != duration or
                    existing_episode.pubdate != pubdate or
                    existing_episode.episode != episode_number or
                    existing_episode.season != season_number
            ):
                existing_episode.subtitle = subtitle
                existing_episode.audio_url = audio_url
                existing_episode.duration = duration
                existing_episode.pubdate = pubdate
                existing_episode.episode = episode_number
                existing_episode.season = season_number

        # Remove the episode from the list of episodes to be deleted
        try:
            episodes_to_delete.remove(existing_episode)
        except ValueError:
            pass

    error = ""
    # Delete any episodes that were not present in the latest API response
    for episode in episodes_to_delete:
        db.session.delete(episode)

    # Update the keywords, description, and image for the podcast if they have changed in the feed
    try:
        itunes_namespace = "{http://www.itunes.com/dtds/podcast-1.0.dtd}"
        keywords_element = root.find(f'.//{itunes_namespace}keywords')

        if keywords_element is not None:
            keywords = keywords_element.text
        else:
            categories = root.findall(f'.//{itunes_namespace}category')
            category_texts = [category.get('text') for category in categories]
            keywords = ', '.join(category_texts[:4])

        # Split the keywords by comma
        keywords_list = keywords.split(',')

        # Trim leading and trailing spaces for each keyword
        keywords_list = [keyword.strip() for keyword in keywords_list]

        # Ensure a maximum of 4 keywords
        keywords_list = keywords_list[:4]

        try:
            # Join the truncated keywords with commas
            keywords = ', '.join(keywords_list)
        except:
            error = "Single keyword"

        if len(keywords) > 50:
            keywords = keywords[:50].rsplit(', ', 1)[0]

        description_itunes = root.find(f'.//{itunes_namespace}summary')
        description_element = root.find('.//description')

        if description_itunes is not None:
            description = description_element.text
        elif description_element is not None:
            description = description_element.text
        else:
            description = podcast.description

        # Check if subtitle element exists
        if description is not None:
            # Handle <![CDATA[...]]> section for subtitle
            cdata_regex = re.compile(r"<!\[CDATA\[(.*?)\]\]>", re.DOTALL)
            matches = cdata_regex.findall(description)
            if matches:
                description = matches[0]
            else:
                description = re.sub('<[^<]+?>', '', description)  # Strip HTML tags

        author_element = root.find(f'.//{itunes_namespace}author')
        if author_element is not None:
            author = author_element.text
        else:
            author = podcast.author

        image_element = root.find(f'.//{itunes_namespace}image')
        image_href = image_element.get('href') if image_element is not None else ""

        owner_element = root.find(f'.//{itunes_namespace}owner')
        if owner_element is not None:
            name_elem = owner_element.find(f'.//{itunes_namespace}name')
            if name_elem is not None and name_elem.text:
                owner = name_elem.text.strip()
            else:
                owner = ''

        language_element = root.find(f'.//language')
        if language_element is not None:
            language = language_element.text
        else:
            language = podcast.language

        explicit_elem = root.find(f'.//{itunes_namespace}explicit')

        if explicit_elem is not None:
            explicit = explicit_elem.text
            if explicit == 'yes':
                explicit = True
            elif explicit == 'no':
                explicit = False
            else:
                explicit = False
        else:
            explicit = False

        if (
                podcast.keywords != keywords or
                podcast.description != description or
                podcast.author != author or
                podcast.image != image_href or
                podcast.owner != owner or
                podcast.explicit != explicit or
                podcast.language != language
        ):
            podcast.keywords = keywords
            podcast.description = description
            podcast.author = author
            podcast.image = image_href
            podcast.owner = owner
            podcast.explicit = explicit
            podcast.language = language
    except Exception as e:
        # podcast.keywords = "Aucun mot clé"
        error = e

    if not error:
        error = None

    # Update the last updated timestamp for the podcast
    podcast.last_updated = datetime.utcnow()
    db.session.commit()

    # Prepare the JSON response
    episodes = podcast.episodes

    response_data = {
        'error': str(error),
        'title': podcast.title,
        'description': podcast.description,
        'author': podcast.author,
        'rss_feed': podcast.rss_feed,
        'image': podcast.image,
        'keywords': podcast.keywords,
        'owner': podcast.owner,
        'explicit': podcast.explicit,
        'language': podcast.language,
        'episodes': [
            {
                'id': episode.id,
                'title': episode.title,
                'subtitle': episode.subtitle,
                'audio_url': episode.audio_url,
                'pubdate': episode.pubdate.isoformat(),
                'duration': episode.duration
            }
            for episode in episodes
        ]
    }

    try:
        return jsonify(response_data)
    except:
        return "error"


@main.route('/export')
@login_required
def export_opml():
    # Create the root element of the OPML document
    opml = ET.Element('opml', version='1.0')
    head = ET.SubElement(opml, 'head')
    body = ET.SubElement(opml, 'body')

    # Add the title element to the head
    title = ET.SubElement(head, 'title')
    title.text = 'Podcast Subscriptions'

    # Iterate over the user's podcasts and add outline elements to the body
    for podcast in current_user.podcasts:
        outline = ET.SubElement(body, 'outline', text=podcast.title, type='rss', xmlUrl=podcast.rss_feed)

    # Create an ElementTree object from the root element
    tree = ET.ElementTree(opml)

    # Create a BytesIO object to store the OPML data
    opml_data = BytesIO()
    tree.write(opml_data, encoding='utf-8', xml_declaration=True)

    # Set the file pointer to the beginning of the BytesIO object
    opml_data.seek(0)

    # Set the desired filename for the attachment
    attachment_filename = 'Steraudio.opml'

    # Send the file as an attachment
    return send_file(opml_data, mimetype='text/xml', as_attachment=True, download_name=attachment_filename)


ALLOWED_EXTENSIONS = {'xml', 'opml'}


@main.route('/import', methods=['POST'])
def import_opml():
    file = request.files['file']

    if file and allowed_file(file.filename):
        try:
            filename = secure_filename(file.filename)
            extension = filename.rsplit('.', 1)[1].lower()

            if extension == 'opml' or extension == 'xml':
                tree = ET.parse(file)
                root = tree.getroot()
                outlines = root.findall('.//outline')

                podcast_count = 0

                if outlines:
                    for outline in outlines:
                        podcast_name = outline.get('text')
                        podcast_url = outline.get('xmlUrl')
                        podcast_count += 1

                        if podcast_count > 30:
                            print('Skipping podcast', podcast_name, 'due to more than 30 podcasts.')
                        else:
                            add_podcast_to_db(podcast_url)
                    else:
                        print('Warning: Missing xmlUrl attribute for podcast:', podcast_name)

                    return {'message': 'Podcasts imported correctly.'}, 200
                else:
                    return {'error': 'No podcast outlines found in the OPML/XML file.'}, 400

            else:
                return {'error': 'Invalid file format. Only XML or OPML files are allowed.'}, 400

        except ET.ParseError:
            return {'error': 'Error parsing OPML/XML file.'}, 400
    else:
        return {'error': 'No file provided or invalid file format.'}, 400


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


@main.route('/add_unfinished_episode', methods=['POST'])
@login_required
def add_unfinished_episode():
    data = request.json
    episode_id = data.get('episodeId')
    playback_time = data.get('playbackTime')

    # Create a new unfinished episode entry in the database
    unfinished_episode = UnfinishedEpisode(episode_id=episode_id, playback_time=playback_time)
    db.session.add(unfinished_episode)
    db.session.commit()

    # Return a success response
    response = jsonify({'message': 'Unfinished episode added'})
    return response


@main.route('/remove_unfinished_episode', methods=['POST'])
@login_required
def remove_unfinished_episode():
    data = request.json
    episode_id = data.get('episodeId')

    # Remove the unfinished episode from the database
    unfinished_episode = UnfinishedEpisode.query.filter_by(episode_id=episode_id).first()
    if unfinished_episode:
        db.session.delete(unfinished_episode)
        db.session.commit()

    # Return a success response
    response = jsonify({'message': 'Unfinished episode removed'})
    return response


@main.route('/discover', methods=['GET'])
@login_required
def discover():
    browser_language = request.headers.get('Accept-Language')
    primary_language = browser_language.split(',')[0].split(';')[0].split('-')[0]

    languages = ['fr', 'us', 'gb', 'ca', 'en']

    if primary_language.lower() in languages:
        podcasts = Discover.query.filter_by(language=primary_language).all()
    else:
        podcasts = Discover.query.all()

    # Count the number of podcasts in each category
    category_counts = {}
    for podcast in podcasts:
        keywords = podcast.keywords.split(', ')
        for keyword in keywords:
            if keyword == "Podcasts":
                continue  # Skip if category is "Podcasts"
            if keyword not in category_counts:
                category_counts[keyword] = 0
            category_counts[keyword] += 1

    # Sort categories based on the number of podcasts they contain
    sorted_categories = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)

    # Limit the number of categories to 10
    sorted_categories = sorted_categories[:10]

    # Sort categories alphabetically
    sorted_categories = sorted(sorted_categories, key=lambda x: x[0])

    # Define the translations for category names
    category_translations = {
        'Arts': 'Arts',
        'Books': 'Livres',
        'Design': 'Design',
        'Fashion & Beauty': 'Mode et beauté',
        'Food': 'Cuisine',
        'Performing Arts': 'Arts du spectacle',
        'Visual Arts': 'Arts visuels',
        'Business': 'Affaires',
        'Careers': 'Carrières',
        'Entrepreneurship': 'Entrepreneuriat',
        'Investing': 'Investissement',
        'Management': 'Gestion',
        'Marketing': 'Marketing',
        'Non-Profit': 'Organisme sans but lucratif',
        'Comedy': 'Comédie',
        'Comedy Interviews': 'Entretiens comiques',
        'Improv': 'Improvisation',
        'Stand-Up': 'Stand-Up',
        'Education': 'Éducation',
        'Courses': 'Cours',
        'How To': 'Comment faire',
        'Language Learning': 'Apprentissage des langues',
        'Self-Improvement': 'Développement personnel',
        'Fiction': 'Fiction',
        'Comedy Fiction': 'Fiction comique',
        'Drama': 'Drame',
        'Science Fiction': 'Science-fiction',
        'Government': 'Gouvernement',
        'History': 'Histoire',
        'Health & Fitness': 'Santé et forme physique',
        'Alternative Health': 'Santé alternative',
        'Fitness': 'Forme physique',
        'Medicine': 'Médecine',
        'Mental Health': 'Santé mentale',
        'Nutrition': 'Nutrition',
        'Sexuality': 'Sexualité',
        'Kids & Family': 'Enfants et famille',
        'Education for Kids': "Éducation pour les enfants",
        'Parenting': 'Parentalité',
        'Pets & Animals': 'Animaux de compagnie',
        'Stories for Kids': 'Histoires pour enfants',
        'Leisure': 'Loisirs',
        'Animation & Manga': 'Animation et manga',
        'Automotive': 'Automobile',
        'Aviation': 'Aviation',
        'Crafts': 'Artisanat',
        'Games': 'Jeux',
        'Hobbies': 'Passions',
        'Home & Garden': 'Maison et jardin',
        'Video Games': 'Jeux vidéo',
        'Music': 'Musique',
        'Music Commentary': 'Commentaires musicaux',
        'Music History': 'Histoire de la musique',
        'Music Interviews': 'Entretiens musicaux',
        'News': 'Actualités',
        'Business News': 'Actualités économiques',
        'Daily News': 'Actualités quotidiennes',
        'Entertainment News': 'Actualités du divertissement',
        'News Commentary': 'Commentaires sur l\'actualité',
        'Politics': 'Politique',
        'Sports News': 'Actualités sportives',
        'Tech News': 'Actualités technologiques',
        'Religion & Spirituality': 'Religion et spiritualité',
        'Buddhism': 'Bouddhisme',
        'Christianity': 'Christianisme',
        'Hinduism': 'Hindouisme',
        'Islam': 'Islam',
        'Judaism': 'Judaïsme',
        'Religion': 'Religion',
        'Spirituality': 'Spiritualité',
        'Science': 'Science',
        'Astronomy': 'Astronomie',
        'Chemistry': 'Chimie',
        'Earth Sciences': 'Sciences de la Terre',
        'Life Sciences': 'Sciences de la vie',
        'Mathematics': 'Mathématiques',
        'Natural Sciences': 'Sciences naturelles',
        'Nature': 'Nature',
        'Physics': 'Physique',
        'Social Sciences': 'Sciences sociales',
        'Society & Culture': 'Société et culture',
        'Documentary': 'Documentaire',
        'Personal Journals': 'Journaux personnels',
        'Philosophy': 'Philosophie',
        'Places & Travel': 'Lieux et voyages',
        'Relationships': 'Relations',
        'Sports': 'Sports',
        'Baseball': 'Baseball',
        'Basketball': 'Basketball',
        'Cricket': 'Cricket',
        'Fantasy Sports': 'Sports de fantasy',
        'Football': 'Football',
        'Golf': 'Golf',
        'Hockey': 'Hockey',
        'Rugby': 'Rugby',
        'Soccer': 'Football (Soccer)',
        'Swimming': 'Natation',
        'Tennis': 'Tennis',
        'Volleyball': 'Volleyball',
        'Wilderness': 'Nature sauvage',
        'Wrestling': 'Lutte',
        'Technology': 'Technologie',
        'True Crime': 'Crime réel',
        'TV & Film': 'Télévision et cinéma',
        'After Shows': 'Après les émissions',
        'Film History': 'Histoire du cinéma',
        'Film Interviews': 'Entretiens de films',
        'Film Reviews': 'Critiques de films',
        'TV Reviews': 'Critiques de séries télévisées',
    }

    # Limit each category to 10 podcasts
    categories = {}
    category_limit = 10
    for category, count in sorted_categories:
        translated_category = category_translations.get(category, category)
        categories[translated_category] = []
        for podcast in podcasts:
            keywords = podcast.keywords.split(', ')
            if category in keywords:
                categories[translated_category].append(podcast)
                if len(categories[translated_category]) == category_limit:
                    break

    return render_template('discover.html', podcasts=podcasts, categories=categories)


def normalize_text(text):
    """
    Normalize the text by removing accents and converting it to lowercase.
    """
    normalized_text = unicodedata.normalize('NFD', text).encode('ascii', 'ignore').decode('utf-8')
    return normalized_text.lower()


@main.route('/api/discover', methods=['GET'])
@login_required
def discover_api():
    search_query = request.args.get('search')  # Get the search query from the request arguments
    podcasts = Discover.query.all()

    # Normalize the search query
    normalized_query = normalize_text(search_query) if search_query else ""

    # Filter podcasts based on the search query
    if normalized_query:
        podcasts = [
            podcast for podcast in podcasts if
            normalized_query in normalize_text(podcast.title) or
            normalized_query in normalize_text(podcast.author) or
            normalized_query in normalize_text(podcast.description)
        ]

        # Sort the filtered podcasts based on priority (title > author > description)
        podcasts.sort(key=lambda podcast: (
            normalized_query in normalize_text(podcast.title),
            normalized_query in normalize_text(podcast.author),
            normalized_query in normalize_text(podcast.description)
        ), reverse=True)

    response_data = []
    for podcast in podcasts:
        data = {
            'title': podcast.title,
            'description': podcast.description,
            'author': podcast.author,
            'rss_feed': podcast.rss_feed,
            'image': podcast.image,
            'keywords': podcast.keywords
        }
        response_data.append(data)

    try:
        return jsonify(response_data)
    except Exception as e:
        print(e)
        return "error"
