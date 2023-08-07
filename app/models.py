# app/models.py

from flask_login import UserMixin
from app import db, login_manager
import re

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(20), unique=True, nullable=False)
    password = db.Column(db.String(60), nullable=False)
    otp_secret = db.Column(db.String(16), nullable=True)
    is_2fa_enabled = db.Column(db.Boolean, default=False)
    subscriptions = db.relationship('Podcast', secondary='user_podcast', backref=db.backref('subscribers', lazy=True), lazy=True)
    podcasts = db.relationship('Podcast', secondary='user_podcast', back_populates='owners', lazy=True, overlaps="subscribers,subscriptions")


class UserPodcast(db.Model):
    __tablename__ = 'user_podcast'
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), primary_key=True)
    podcast_id = db.Column(db.Integer, db.ForeignKey('podcast.id'), primary_key=True)


class Podcast(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    rss_feed = db.Column(db.String(200), nullable=False, unique=True)
    episodes_list = db.relationship('Episode', backref='podcast', lazy=True)
    image = db.Column(db.String(200), nullable=True)
    keywords = db.Column(db.String(200), nullable=True)
    owner = db.Column(db.String(100), nullable=True)
    explicit = db.Column(db.Boolean, nullable=False)
    language = db.Column(db.String(50), nullable=True)
    owners = db.relationship('User', secondary='user_podcast', back_populates='podcasts', lazy=True, overlaps="subscribers,subscriptions")

    @property
    def episodes(self):
        return sorted(self.episodes_list, key=lambda e: e.pubdate, reverse=True)


class Episode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    audio_url = db.Column(db.String(200), nullable=False)
    video_url = db.Column(db.String(200), nullable=True)
    pubdate = db.Column(db.DateTime, nullable=False)
    duration = db.Column(db.String(50), nullable=True)
    subtitle = db.Column(db.Text, nullable=True)
    episode = db.Column(db.Integer, nullable=True)
    season = db.Column(db.Integer, nullable=True)
    podcast_id = db.Column(db.Integer, db.ForeignKey('podcast.id'), nullable=False)


class UnfinishedEpisode(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    episode_id = db.Column(db.Integer, db.ForeignKey('episode.id'), nullable=False)
    playback_time = db.Column(db.Integer, nullable=False)


class Discover(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    description = db.Column(db.String(300), nullable=False)
    author = db.Column(db.String(100), nullable=False)
    rss_feed = db.Column(db.String(200), nullable=False, unique=True)
    image = db.Column(db.String(200), nullable=True)
    keywords = db.Column(db.String(200), nullable=True)
    apple_podcast_id = db.Column(db.String(100), nullable=False)
    language = db.Column(db.String(50), nullable=False)