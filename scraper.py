from urllib import request
from urllib import parse
import argparse
import time
import datetime
import locale

from bs4 import BeautifulSoup
from google.cloud import datastore


class Scraper(object):
    def __init__(self, client, stop_when_present, user_agent):
        """
        Args:
            client: a datastore.Client instance
            page_url: the url of the page to parse
            stop_when_present: whether to stop the crawl when the url has already been imported in the DB
        """
        self._client = client
        self._stop_when_present = stop_when_present
        self._user_agent = user_agent

    def Run(self, root_url):
        print("Starting collection of pages from root URL", root_url)
        for page in self._CollectPages(root_url):
            should_break, entity = self._ParsePage(page)
            if should_break:
                break
            print("Saved entity:", entity)

    def _ParsePage(self, page_url):
        """Parses a single page containing a lecture.

        Returns:
            A tuple (bool, entity) that contains whether the crawl should stop and the entity that was imported in the DB if any.
        """
        print("Parsing page", page_url)
        resp = request.urlopen(
            request.Request(
                page_url, headers={'User-Agent': self._user_agent}))
        s = BeautifulSoup(resp.read(), "html.parser")
        # Skip lessons without audio.
        audio_link = s.find("li", "audio")
        if not audio_link:
            print("No audio link @", page_url)
            return False, None
        audio_link = audio_link.find("a").get("href")
        key = self._client.key('Entry', audio_link)
        # If we already have it, skip.
        if self._client.get(key):
            print("Already saved", audio_link)
            return self._stop_when_present, None
        entity = datastore.Entity(
            key,
            exclude_from_indexes=["video_link", "audio_link", "source"])
        entity.update({
            "source": page_url,
            "scraped": datetime.datetime.utcnow(),
            "title": s.find(id="title").text.strip(),
            "lecturer": list(s.find("h3", "lecturer").children)[0],
            "function": list(s.find("h3", "lecturer").children)[1].text.strip(),
            # Day is like "29 Juin 2017"
            # The locale needs to be set to fr_FR for this to work.
            "date": time.strptime(
            s.find("span", "day").text.strip(), "%d %B %Y"),
            "lesson_type": s.find("span", "type").text.strip(),
            "audio_link": audio_link,
            # Audio links ends like "foo-bar-fr.mp3", language is at the end.
            "language": audio_link[audio_link.rfind("-")+1:-4],
            "chaire": s.find("div", "chair-baseline").text.strip(),
        })

        video_link = s.find("li", "video")
        if video_link:
            entity["video_link"] = video_link.find("a").get("href")
        self._client.put(entity)
        return False, entity

    def _CollectPages(self, url):
        """Collect pages with audio in them from the given root url.

        Args:
            url: url to start the crawl from
        Yields:
            pages urls to individual lessons
        """
        maybe_more_content = True
        num_pages = 0
        while maybe_more_content:
            resp = request.urlopen(
                request.Request(
                    url + "&index=" + str(num_pages),
                    headers={'User-Agent': self._user_agent}))
            s = BeautifulSoup(resp.read(), "html.parser")
            maybe_more_content = False
            for link in s.find_all("a"):
                href = link.get("href")
                if href.startswith("/site/"):
                    yield "http://www.college-de-france.fr" + href
                    num_pages += 1
                    maybe_more_content = True

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--project_id", help="Google Cloud Project ID.")
    parser.add_argument("--user_agent", help="user agent string to use, be nice and tell other people why they are being scraped.")
    parser.add_argument("--stop_when_present", help="Stop crawl when the first already imported item is found (useful after the first run).")
    parser.add_argument("--root_url", help="Root URL to start the crawl from.", default="http://www.college-de-france.fr/components/search-audiovideo.jsp?fulltext=&siteid=1156951719600&lang=FR&type=audio")
    args = parser.parse_args()

    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
    print("Creating client for project", args.project_id)
    client = datastore.Client(args.project_id)
    s = Scraper(client, args.stop_when_present, args.user_agent)
    s.Run(args.root_url)
