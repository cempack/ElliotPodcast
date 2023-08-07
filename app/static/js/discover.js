document.addEventListener("DOMContentLoaded", function() {
    var searchForm = document.querySelector("form");
    var searchInput = document.querySelector("input[type='text']");
    var xhr; // Declare the XMLHttpRequest object outside the event listener

    searchInput.addEventListener("input", function() {
        var searchTerm = searchInput.value.trim(); // Get the trimmed value of the search input

        // Abort any ongoing AJAX request
        if (xhr && xhr.readyState !== XMLHttpRequest.DONE) {
            xhr.abort();
        }

        // Clear the search results if the search bar is empty
        if (searchTerm === "") {
            clearSearchResults();
            return;
        }

        // Perform an AJAX request to the search endpoint
        xhr = new XMLHttpRequest();
        xhr.open("GET", "/api/discover?search=" + encodeURIComponent(searchTerm), true);
        xhr.onreadystatechange = function() {
            if (xhr.readyState === XMLHttpRequest.DONE && xhr.status === 200) {
                var response = JSON.parse(xhr.responseText);
                displaySearchResults(response);
            }
        };
        xhr.send();
    });

    function clearSearchResults() {
        var podcastList = document.getElementById("search-results");
        var searchTitle = document.getElementById("search-title");
        searchTitle.style.display = "none";
        podcastList.innerHTML = "";
    }

    function makeLinksClickable(description) {
        // Regular expression to match URLs
        var urlRegex = /(https?:\/\/[^\s]+)/g;

        // Replace the URLs with anchor tags
        var linkedDescription = description.replace(urlRegex, function(url) {
            return '<a href="' + url + '">' + url + '</a>';
        });

        return linkedDescription;
    }

    function displaySearchResults(results) {
        var podcastList = document.getElementById("search-results");
        var search = document.getElementById("search");
        var searchTitle = document.getElementById("search-title");
        search.style.display = "block";
        podcastList.innerHTML = ""; // Clear the existing search results
        searchTitle.style.display = "block";

        if (results.length === 0) {
            var noResultsMessage = document.createElement("p");
            noResultsMessage.textContent = "Aucun résultat.";
            podcastList.appendChild(noResultsMessage);
            return;
        }

        results.forEach(function(podcast) {
            podcast.description = makeLinksClickable(podcast.description);
            console.log(podcast.description);

            var podcastElement = document.createElement("div");
            podcastElement.classList.add("podcast");

            var titleElement = document.createElement("h3");
            titleElement.textContent = podcast.title;

            var infoElement = document.createElement("div");
            infoElement.classList.add("podcast-info");

            var authorElement = document.createElement("p");
            authorElement.innerHTML = "<strong>Auteur :</strong> " + podcast.author;

            var extendButton = document.createElement("button");
            extendButton.classList.add("extend-button");
            extendButton.textContent = "En savoir plus";

            var formElement = document.createElement("form");
            formElement.method = "POST";
            formElement.action = main_podcast;

            var rssFeedInput = document.createElement("input");
            rssFeedInput.value = podcast.rss_feed;
            rssFeedInput.type = "hidden";
            rssFeedInput.style.display = "none";
            rssFeedInput.id = "rss_feed";
            rssFeedInput.name = "rss_feed";
            rssFeedInput.required = true;

            var addButton = document.createElement("button");
            addButton.type = "submit";
            addButton.classList.add("add-button");
            addButton.textContent = "S'abonner au podcast";

            var extendedInfoElement = document.createElement("div");
            extendedInfoElement.classList.add("extended-info");
            extendedInfoElement.innerHTML = "<p><strong>Description :</strong> " + podcast.description + "</p>" +
                "<p><strong>Categories :</strong> " + podcast.keywords + "</p>";

            infoElement.appendChild(authorElement);
            formElement.appendChild(rssFeedInput);
            formElement.appendChild(addButton);
            infoElement.appendChild(formElement);
            infoElement.appendChild(extendedInfoElement);

            podcastElement.appendChild(titleElement);
            podcastElement.appendChild(infoElement);

            if (podcast.image) {
                var imageElement = document.createElement("img");
                imageElement.src = podcast.image;
                imageElement.alt = "Image du podcast " + podcast.title;
                podcastElement.appendChild(imageElement);
            }

            podcastList.appendChild(podcastElement);
        });
    }

    var extendButtons = document.getElementsByClassName("extend-button");
    for (var i = 0; i < extendButtons.length; i++) {
        extendButtons[i].addEventListener("click", togglePodcastInfo);
    }

    function togglePodcastInfo() {
        var extendedInfo = this.parentNode.querySelector(".extended-info");
        if (extendedInfo.classList.contains("show")) {
            hidePopup(extendedInfo);
        } else {
            showPopup(extendedInfo.innerHTML);
        }
    }

    function showPopup(content) {
        var popup = document.createElement("div");
        popup.classList.add("popup");
        var popupContent = document.createElement("div");
        popupContent.classList.add("popup-content");
        popupContent.innerHTML = content;
        var closeButton = document.createElement("span");
        closeButton.classList.add("close-button");
        closeButton.innerHTML = "&times;";
        closeButton.addEventListener("click", function() {
            hidePopup(popup);
        });
        popup.appendChild(popupContent);
        popup.appendChild(closeButton);
        document.body.appendChild(popup);
    }

    function hidePopup(popup) {
        if (popup) {
            popup.parentNode.removeChild(popup);
        }
    }
});