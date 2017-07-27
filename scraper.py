from urllib import request
from urllib import parse
import argparse
import time
import datetime
import locale
import hashlib
import logging

from bs4 import BeautifulSoup
from google.cloud import datastore


class Scraper(object):
    def __init__(self, client, stop_when_present, user_agent, dry_run):
        """
        Args:
            client: a datastore.Client instance
            page_url: the url of the page to parse
            stop_when_present: whether to stop the crawl when the url has already been imported in the datastore
            dry_run: dry run will not import scraped pages into the datastore.
        """
        self._client = client
        self._stop_when_present = stop_when_present
        self._user_agent = user_agent
        self._dry_run = dry_run

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
            A tuple (bool, entity) that contains whether the crawl should stop and the entity that was imported in the datastore if any.
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
        # Find key parts.
        try:
            lecturer = list(s.find("h3", "lecturer").children)[0]
        except (IndexError, AttributeError):
            logging.info("No lecturer found, skipping")
            return False, None
        date = s.find("span", "day").text.strip()
        hour_start = s.find("span", "from").text.strip()
        if not hour_start:
            logging.info("No start hour found, skipping")
            # TODO: should we synthetize one instead then?
            return False, None
        # A single person cannot give two lessons starting at the same time
        # so hopefully this is a less brittle proxy than the audio link that
        # could change anytime.
        key = self._client.key('Entry', "|".join([lecturer, date, hour_start]))
        # If we already have it, skip.
        if self._client.get(key):
            print("Already saved", page_url)
            return self._stop_when_present, None
        entity = datastore.Entity(
            key,
            exclude_from_indexes=["VideoLink", "AudioLink", "source"])
        entity.update({
            "Source": page_url,
            # A random seed to be able to schedule random items.
            "Hash": hashlib.sha1(page_url.encode("utf-8")).digest(),
            "Scraped": datetime.datetime.utcnow(),
            "Title": s.find(id="title").text.strip(),
            "Lecturer": lecturer,
            "LessonType": s.find("h4").text.strip(),
            # Day is like "29 Juin 2017"
            # The locale needs to be set to fr_FR for this to work.
            "Date": time.strptime(date, "%d %B %Y"),
            "LessonType": s.find("span", "type").text.strip(),
            "AudioLink": audio_link,
            # Audio links ends like "foo-bar-fr.mp3", language is at the end.
            "Language": audio_link[audio_link.rfind("-")+1:-4],
            "Chaire": s.find("div", "chair-baseline").text.strip(),
        })

        try:
            entity["Function"] = list(
                s.find("h3", "lecturer").children)[1].text.strip()
        except (AttributeError, IndexError):
            # No function, okay.
            pass

        video_link = s.find("li", "video")
        if video_link:
            entity["VideoLink"] = video_link.find("a").get("href")
        if not self._dry_run:
            self._client.put(entity)
        else:
            print("[dry run]", entity)
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
    parser.add_argument("--dry_run", help="Dry runs will not import parsed pages in the datastore.", action="store_true")
    parser.add_argument("--user_agent", help="user agent string to use, be nice and tell other people why they are being scraped.")
    parser.add_argument("--stop_when_present", help="Stop crawl when the first already imported item is found (useful after the first run).")
    parser.add_argument("--root_url", help="Root URL to start the crawl from.", default="http://www.college-de-france.fr/components/search-audiovideo.jsp?fulltext=&siteid=1156951719600&lang=FR&type=audio")
    args = parser.parse_args()

    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
    print("Creating client for project", args.project_id)
    client = datastore.Client(args.project_id)
    s = Scraper(client, args.stop_when_present, args.user_agent, args.dry_run)
    s.Run(args.root_url)
