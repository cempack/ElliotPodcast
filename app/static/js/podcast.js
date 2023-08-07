// Define the audio player component
class AudioPlayer {
    constructor() {
        this.audioPlayer = null;
        this.isPlaying = false;
        this.episodeList = [];
        this.currentEpisodeIndex = -1;
        this.progressBar = null;
        this.progressTime = null;
        this.autoStopDuration = 300; // Default duration set to 5 minutes (300 seconds)
        this.autoStopTimeout = null;
    }

    preloadAudio(audioUrl) {
        const audio = new Audio(audioUrl);
        audio.preload = 'auto';

        // Add an event listener to handle the loadedmetadata event
        audio.addEventListener('loadedmetadata', () => {
            // Update the timestamp with the duration of the audio
            this.progressTime.textContent = `0:00 / ${this.formatTime(audio.duration)}`;
        });

        // Add an event listener to handle the canplaythrough event
        audio.addEventListener('canplaythrough', () => {
            // Remove the loading animation and update the title
            const episodeTitle = document.getElementById('episodeTitle');
            episodeTitle.textContent = this.episodeList[this.currentEpisodeIndex].title;
        });

        this.mediaSessionUpdate();
    }

    createPlayer(audioUrl, episodeList, currentEpisodeIndex) {
        this.episodeList = episodeList;
        this.currentEpisodeIndex = currentEpisodeIndex;

        if (this.audioPlayer) {
            // Replace the audio source with the new URL
            this.audioPlayer.src = audioUrl;

            // Preload the new audio file
            this.preloadAudio(audioUrl);

            // Set the title to indicate loading
            const episodeTitle = document.getElementById('episodeTitle');
            episodeTitle.textContent = 'Chargement...';

            // Set the timestamp to 0/...
            this.progressTime.textContent = '0:00 / ...';
        } else {
            const playerContainer = document.createElement('div');
            playerContainer.id = 'audioPlayerContainer';
            playerContainer.innerHTML = `
      <div id="episodeTitle">Chargement...</div><button title="Arrêter la lecture" id="stopButton"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#161C20" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><line x1="18" y1="6" x2="6" y2="18"></line><line x1="6" y1="6" x2="18" y2="18"></line></svg></button>
      <div id="progressBarContainer">
      <div id="progressBar"></div>
      </div>
      <div id="utils">
      <div id="progressTime">00:00 / ...</div>
      <div title="Mise en veille automatique" id="autoStop"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#ffffff" stroke-width="2" stroke-linecap="butt" stroke-linejoin="bevel"><path d="M21 12.79A9 9 0 1 1 11.21 3 7 7 0 0 0 21 12.79z"></path></svg></div>
      </div>
      <div id="audioPlayer">
      <audio id="audio_element" title="${this.episodeList[this.currentEpisodeIndex].title}" src="${audioUrl}"></audio>
      </div>
      <div id="playerControls">
      <button title="Précédent" id="previousButton" class="playerButton"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="11 19 2 12 11 5 11 19"></polygon><polygon points="22 19 13 12 22 5 22 19"></polygon></svg></button>
      <button title="Reculer de 15s" id="backwardButton" class="playerButton"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M2.5 2v6h6M2.66 15.57a10 10 0 1 0 .57-8.38"/></svg></button>
      <button title="Reprendre la lecture" id="playButton" class="playerButton"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="5 3 19 12 5 21 5 3"></polygon></svg></button>
      <button title="Mettre la lecture en pause" id="pauseButton" class="playerButton"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><rect x="6" y="4" width="4" height="16"></rect><rect x="14" y="4" width="4" height="16"></rect></svg></button>
      <button title="Avancer de 15s" id="forwardButton" class="playerButton"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><path d="M21.5 2v6h-6M21.34 15.57a10 10 0 1 1-.57-8.38"/></svg></button>
      <button title="Suivant" id="nextButton" class="playerButton"><svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round"><polygon points="13 19 22 12 13 5 13 19"></polygon><polygon points="2 19 11 12 2 5 2 19"></polygon></svg></button>
      </div>
      `;
            document.body.appendChild(playerContainer);

            this.audioPlayer = document.querySelector('#audioPlayer audio');
            this.progressBar = document.querySelector('#progressBar');
            this.progressBarContainer = document.querySelector('#progressBarContainer');
            this.progressTime = document.querySelector('#progressTime');
            this.addEventListeners();

            // Preload the audio file
            this.preloadAudio(audioUrl);

            // Set the source of the audio player
            this.audioPlayer.src = audioUrl;
        }
    }

    addEventListeners() {
        const playButton = document.querySelector('#playButton');
        const pauseButton = document.querySelector('#pauseButton');
        const previousButton = document.querySelector('#previousButton');
        const backwardButton = document.querySelector('#backwardButton');
        const forwardButton = document.querySelector('#forwardButton');
        const nextButton = document.querySelector('#nextButton');
        const stopButton = document.querySelector('#stopButton');
        const autoStopButton = document.querySelector('#autoStop');

        autoStopButton.addEventListener('click', this.promptAutoStopDuration.bind(this));
        playButton.addEventListener('click', this.play.bind(this));
        pauseButton.addEventListener('click', this.pause.bind(this));
        previousButton.addEventListener('click', this.previous.bind(this));
        backwardButton.addEventListener('click', this.backward.bind(this));
        forwardButton.addEventListener('click', this.forward.bind(this));
        nextButton.addEventListener('click', this.next.bind(this));
        stopButton.addEventListener('click', this.stop.bind(this));
        this.audioPlayer.addEventListener('ended', this.handleAudioEnd.bind(this));
        this.progressBarContainer.addEventListener('click', this.changeTime.bind(this));

        // Add event listener for space key
        window.addEventListener('keydown', (event) => {
            if (event.code === 'Space') {
                event.preventDefault();
                this.togglePlay();
            } else if (event.code === 'ArrowLeft') {
                event.preventDefault();
                this.backward();
            } else if (event.code === 'ArrowRight') {
                event.preventDefault();
                this.forward();
            }
        });
    }

    togglePlay() {
        if (this.isPlaying) {
            this.pause();
        } else {
            this.play();
        }
    }

    play() {
        if (!this.isPlaying) {
            // Show the player
            const audioPlayerContainer = document.querySelector('#audioPlayerContainer');
            if (audioPlayerContainer) {
                audioPlayerContainer.style.display = "flex";
            }
            this.audioPlayer.play();
            this.isPlaying = true;
            this.updateButtons();
            this.updateProgressBar();
            const episode = this.episodeList[this.currentEpisodeIndex];
            this.audioPlayer.setAttribute('title', episode.title);
            this.mediaSessionUpdate();
        }
    }

    pause() {
        if (this.isPlaying) {
            this.audioPlayer.pause();
            this.isPlaying = false;
            this.updateButtons();
            this.mediaSessionUpdate();
        }
    }

    promptAutoStopDuration() {
        const options = [300, 900, 1800, 3600]; // Durations in seconds
        const optionLabels = ['5m', '15m', '30m', '60m'];

        const dialogContainer = document.createElement('div');
        dialogContainer.id = 'autoStopDialog';
        dialogContainer.style.position = 'fixed';
        dialogContainer.style.top = '35%';
        dialogContainer.style.left = '50%';
        dialogContainer.style.transform = 'translate(-50%, -50%)';
        dialogContainer.style.backgroundColor = '#202529';
        dialogContainer.style.border = '1px solid #cccccc';
        dialogContainer.style.borderRadius = '10px';
        dialogContainer.style.padding = '16px';
        dialogContainer.style.boxShadow = '0px 2px 4px rgba(0, 0, 0, 0.1)';
        dialogContainer.style.zIndex = '9999';
        dialogContainer.style.display = 'flex';
        dialogContainer.style.flexDirection = 'column';
        dialogContainer.style.gap = '10px';
        dialogContainer.style.width = '50%';
        dialogContainer.style.textAlign = 'center';
        dialogContainer.style.alignItems = 'center';

        const titleElement = document.createElement('h2');
        titleElement.textContent = 'Mise en veille automatique';
        titleElement.style.marginTop = '0';
        titleElement.style.marginBottom = '16px';

        dialogContainer.appendChild(titleElement);

        options.forEach((duration, index) => {
            const button = document.createElement('button');
            button.textContent = optionLabels[index];
            button.style.marginRight = '8px';
            button.style.background = '#18B777';
            button.style.outline = 'none';
            button.style.border = 'none';
            button.style.borderRadius = '8px';
            button.style.width = '60%';
            button.addEventListener('click', () => {
                this.startAutoStopTimer(duration);
                dialogContainer.remove();
            });
            dialogContainer.appendChild(button);
        });

        document.body.appendChild(dialogContainer);
    }

    startAutoStopTimer(duration) {
        if (this.autoStopTimeout) {
            clearTimeout(this.autoStopTimeout);
        }

        this.autoStopDuration = duration;

        this.autoStopTimeout = setTimeout(() => {
            this.stop();
        }, this.autoStopDuration * 1000); // Convert seconds to milliseconds

        console.log(`Auto-stop enabled. The audio will stop after ${this.formatTime(this.autoStopDuration)}.`);
    }

    stop() {
        if (this.isPlaying || !this.isPlaying) {
            this.pause();
            this.audioPlayer.currentTime = "0000";
            // Remove the player
            const audioPlayerContainer = document.querySelector('#audioPlayerContainer');
            if (audioPlayerContainer) {
                audioPlayerContainer.style.display = "none";
            }
        }

        if (this.autoStopTimeout) {
            clearTimeout(this.autoStopTimeout);
            this.autoStopTimeout = null;
            console.log('Auto-stop canceled.');
        }
    }

    previous() {
        if (this.currentEpisodeIndex > 0) {
            this.currentEpisodeIndex--;
            const episode = this.episodeList[this.currentEpisodeIndex];
            const audioUrl = episode.audio_url;
            this.audioPlayer.setAttribute('title', episode.title);
            this.audioPlayer.src = audioUrl;
            this.isPlaying = false;
            this.play();
            const episodeTitle = document.getElementById('episodeTitle');
            episodeTitle.textContent = this.episodeList[this.currentEpisodeIndex].title;
        }
    }

    backward() {
        this.audioPlayer.currentTime -= 15;
    }

    forward() {
        this.audioPlayer.currentTime += 15;
    }

    next() {
        if (this.currentEpisodeIndex < this.episodeList.length - 1) {
            this.currentEpisodeIndex++;
            const episode = this.episodeList[this.currentEpisodeIndex];
            const audioUrl = episode.audio_url;
            this.audioPlayer.setAttribute('title', episode.title);
            this.audioPlayer.src = audioUrl;
            this.isPlaying = false;
            this.play();
            const episodeTitle = document.getElementById('episodeTitle');
            episodeTitle.textContent = this.episodeList[this.currentEpisodeIndex].title;
        }
    }

    handleAudioEnd() {
        this.isPlaying = false;
        this.updateButtons();
        this.next();
        this.mediaSessionUpdate();
    }

    updateButtons() {
        const playButton = document.querySelector('#playButton');
        const pauseButton = document.querySelector('#pauseButton');

        if (this.isPlaying) {
            playButton.style.display = 'none';
            pauseButton.style.display = 'block';
        } else {
            playButton.style.display = 'block';
            pauseButton.style.display = 'none';
        }
    }

    updateProgressBar() {
        this.audioPlayer.addEventListener('timeupdate', () => {
            const currentTime = this.audioPlayer.currentTime;
            const duration = this.audioPlayer.duration;

            // Check if duration is a finite number
            if (duration && Number.isFinite(duration)) {
                const progress = (currentTime / duration) * 100;
                // console.log(currentTime + " / " + duration);
                this.progressBar.style.width = `${progress}%`;
                this.progressTime.textContent = this.formatTime(currentTime) + " / " + this.formatTime(duration);
            } else {
                console.error('Invalid duration value:', duration);
            }
        });
    }

    setPositionState() {
        if ('setPositionState' in navigator.mediaSession) {
            console.log(this.audioPlayer.duration);

            // Check if duration is a finite number
            if (Number.isFinite(this.audioPlayer.duration)) {
                const currentTime = this.audioPlayer.currentTime;
                const duration = this.audioPlayer.duration;
                navigator.mediaSession.setPositionState({
                    duration: duration,
                    position: currentTime,
                });
            } else {
                console.error('Invalid duration value:', this.audioPlayer.duration);
            }
        }
    }

    changeTime(event) {
        const progressBarContainer = document.querySelector('#progressBarContainer');
        const progressBarRect = progressBarContainer.getBoundingClientRect();
        const clickPosition = event.clientX - progressBarRect.left;
        const progressBarWidth = progressBarRect.width;
        const percentage = clickPosition / progressBarWidth;
        this.audioPlayer.currentTime = this.audioPlayer.duration * percentage;
        updateProgressBar();
    }

    formatTime(time) {
        const minutes = Math.floor(time / 60);
        const seconds = Math.floor(time % 60);
        return `${this.padZero(minutes)}:${this.padZero(seconds)}`;
    }

    padZero(num) {
        return num.toString().padStart(2, '0');
    }

    mediaSessionUpdate() {
        if ("mediaSession" in navigator) {
            const artworkUrl = image_url;
            const currentEpisode = this.episodeList[this.currentEpisodeIndex];
            const { title, artist } = currentEpisode;
            const podcast_title = document.getElementById('title');

            const mediaMetadataOptions = {
                title: 'Steraudio - ' + podcast_title.textContent + ' : ' + title,
                artist: artist,
            };

            if (artworkUrl) {
                mediaMetadataOptions.artwork = [
                    { src: '/api/resize/' + artworkUrl + '/96', sizes: "96x96", type: "image/png" },
                    { src: '/api/resize/' + artworkUrl + '/128', sizes: '128x128', type: 'image/png' },
                    { src: '/api/resize/' + artworkUrl + '/192', sizes: '192x192', type: 'image/png' },
                    { src: '/api/resize/' + artworkUrl + '/256', sizes: '256x256', type: 'image/png' },
                    { src: '/api/resize/' + artworkUrl + '/384', sizes: '384x384', type: 'image/png' },
                    { src: '/api/resize/' + artworkUrl + '/512', sizes: '512x512', type: 'image/png' }
                ];
            }

            navigator.mediaSession.metadata = new MediaMetadata(mediaMetadataOptions);
        }
    }
}

window.addEventListener('DOMContentLoaded', function() {
    let audioPlayer = null;

    fetch(fetch_url)
        .then((response) => response.json())
        .then((data) => {
            const podcast_title = data.title;
            const episodesDiv = document.getElementById('episodes');
            const episodes = data.episodes;
            episodes.forEach((episode) => {
                let subtitle = episode.subtitle;
                if (subtitle.length > 100) {
                    subtitle = subtitle.slice(0, 100);
                    const lastSpaceIndex = subtitle.lastIndexOf(' ');
                    subtitle = subtitle.slice(0, lastSpaceIndex).trim() + '...';
                }
                const episodeDiv = document.createElement('div');

                const pubdate = new Date(episode.pubdate);
                const today = new Date();
                const yesterday = new Date();
                yesterday.setDate(yesterday.getDate() - 1);

                const options = { hour: 'numeric', minute: 'numeric' };

                let readableDate;

                if (pubdate >= yesterday && pubdate <= today) {
                    const currentTime = pubdate.toLocaleTimeString('fr-FR', options);
                    readableDate = `Aujourd'hui à ${currentTime}`;
                } else if (pubdate >= new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate(), 0, 0, 0) && pubdate <= yesterday) {
                    const currentTime = pubdate.toLocaleTimeString('fr-FR', options);
                    readableDate = `Hier à ${currentTime}`;
                } else if (pubdate >= new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate() - 1, 0, 0, 0) && pubdate <= new Date(yesterday.getFullYear(), yesterday.getMonth(), yesterday.getDate(), 0, 0, 0)) {
                    const currentTime = pubdate.toLocaleTimeString('fr-FR', options);
                    readableDate = `Avant-hier à ${currentTime}`;
                } else {
                    readableDate = pubdate.toLocaleDateString('fr-FR', options);
                }

                episodeDiv.innerHTML = `
      <img src="${image_url}">
      <p id="episode_id" style="display: none;">${episode.id}</p>
      <div>
      <h4>${episode.title}</h4>
      <p id="description">Description: ${subtitle}</p>
      <p>Date de publication: ${readableDate}</p>
      <p>Durée: ${episode.duration}</p>
      </div>
      <button class="episode" data-audio-url="${episode.audio_url}">
      <svg xmlns="http://www.w3.org/2000/svg" width="24" height="24" viewBox="0 0 24 24" fill="none" stroke="#000000" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
      <polygon points="5 3 19 12 5 21 5 3"></polygon>
      </svg>
      </button>
      `;
                episodesDiv.appendChild(episodeDiv);
            });

            const playButtons = document.querySelectorAll('.episode');
            playButtons.forEach((button) => {
                button.addEventListener('click', function() {
                    const audioUrl = this.getAttribute('data-audio-url');
                    const currentEpisodeIndex = Array.from(playButtons).indexOf(this);

                    if (!audioPlayer) {
                        audioPlayer = new AudioPlayer();
                    } else {
                        audioPlayer.pause();
                    }

                    audioPlayer.createPlayer(audioUrl, episodes, currentEpisodeIndex);
                    audioPlayer.play();

                    const episodeTitle = document.getElementById('episodeTitle');
                    episodeTitle.textContent = episodes[currentEpisodeIndex].title;
                });
            });

            const actionHandlers = [
                ['play', () => audioPlayer.play()],
                ['pause', () => audioPlayer.pause()],
                ['previoustrack', () => audioPlayer.previous()],
                ['nexttrack', () => audioPlayer.next()],
                ['seekbackward', () => audioPlayer.backward()],
                ['seekforward', () => audioPlayer.forward()],
                ['stop', () => audioPlayer.stop()],
            ];

            for (const [action, handler] of actionHandlers) {
                try {
                    navigator.mediaSession.setActionHandler(action, handler);
                } catch (error) {
                    console.log(`The media session action "${action}" is not supported yet.`);
                }
            }
        })
        .catch((error) => console.log(error));
});

// Change page name
const podcast_title = document.getElementById('title');
document.title = "Steraudio - " + podcast_title.textContent;