from urllib import request
from urllib import robotparser
import argparse
import time
import datetime
import locale
import hashlib
import logging
import collections

from bs4 import BeautifulSoup
from google.cloud import datastore

def _trimmed_text(node):
    """Returns the trimmed text contained in the given DOM node or None if
    empty or if node is None.
    """
    try:
        return node.text.strip() or None
    except AttributeError:
        return None


class Scraper(object):
    def __init__(
        self, client, stop_when_present, user_agent, dry_run, overwrite,
        robot_parser):
        """
        Args:
            client: a datastore.Client instance
            page_url: the url of the page to parse
            stop_when_present: whether to stop the crawl when the url has
                already been imported in the datastore
            dry_run: dry run will not import scraped pages into the datastore.
            overwrite: whether to overwrite already scraped entries
            robot_parser: a robotparser.RobotFileParser to use and respect
                robots.txt directives.
        """
        self._client = client
        self._stop_when_present = stop_when_present
        self._user_agent = user_agent
        self._dry_run = dry_run
        self._overwrite = overwrite
        self._status = collections.Counter()
        self._robot = robot_parser

    def Run(self, root_url):
        logging.info("Parsing robots.txt")
        self._robot.set_url("http://www.college-de-france.fr/robots.txt")
        self._robot.read()
        logging.info("Starting collection of pages from root URL %s", root_url)
        for page in self._CollectPages(root_url):
            should_break_early, entity = self._ParsePage(page)
            if should_break_early:
                logging.info("Early exit as already scraped page has been found")
                break
            logging.debug("Saved entity: %s", entity)
            logging.info(self._status)

    def _ParsePage(self, page_url):
        """Parses a single page containing a lecture.

        Returns:
            A tuple (bool, entity) that contains whether the crawl should stop and the entity that was imported in the datastore if any.
        """
        logging.info("Parsing page %s", page_url)
        if not self._robot.can_fetch(self._user_agent, page_url):
            logging.info("Fetch of url disallowed by robots.txt")
            self._status["disallowed"] += 1
            return False, None
        resp = request.urlopen(
            request.Request(
                page_url, headers={'User-Agent': self._user_agent}))
        s = BeautifulSoup(resp.read(), "html.parser")
        # Skip lessons without audio.
        audio_link = s.find("li", "audio")
        if not audio_link:
            logging.warning("No audio link @ %s", page_url)
            self._status["no_audio"] += 1
            return False, None
        audio_link = audio_link.find("a").get("href")
        # Find key parts.
        try:
            lecturer = str(list(s.find("h3", "lecturer").children)[0]).strip()
        except (IndexError, AttributeError):
            logging.warning("No lecturer found, skipping")
            self._status["no_key"] += 1
            return False, None
        try:
            date = s.find("span", "day").text.strip()
        except AttributeError:
            logging.warning("No date found, skipping")
            self._status["no_key"] += 1
            return False, None
        try:
            hour_start = s.find("span", "from").text.strip()
        except AttributeError:
            logging.warning("No start hour found, skipping")
            self._status["no_key"] += 1
            return False, None
        # A single person cannot give two lessons starting at the same time
        # so hopefully this is a less brittle primary key than the audio link
        # or source url that could change anytime.
        key = self._client.key('Entry', "|".join([lecturer, date, hour_start]))
        # If we already have it, skip.
        previous_entity = self._client.get(key)
        if previous_entity:
            logging.info("Already saved %s", page_url)
            self._status["present"] += 1
            # Only overwrite entities which are not converted yet.
            if self._overwrite and previous_entity.get("Converted"):
                return False, None
            # Bail if we do not want to overwrite existing entities.
            if not self._overwrite:
                return self._stop_when_present, None
        entity = datastore.Entity(
            key,
            exclude_from_indexes=["VideoLink", "AudioLink", "source"])
        entity.update({
            "Source": page_url,
            # We need those two here to index them and efficiently schedule
            # random lessons for transcription.
            "Scheduled": False,
            "Converted": False,
            # A random seed to be able to schedule random items.
            "Hash": hashlib.sha1(page_url.encode("utf-8")).digest(),
            "Scraped": datetime.datetime.utcnow(),
            "Title": _trimmed_text(s.find(id="title")),
            "TypeTitle": _trimmed_text(s.find("h4")),
            "LessonType": _trimmed_text(s.find("span", "type")),
            "Lecturer": lecturer,
            # Day is like "29 Juin 2017"
            # The locale needs to be set to fr_FR for this to work.
            "Date": datetime.datetime.fromtimestamp(
                time.mktime(time.strptime(date, "%d %B %Y"))),
            "AudioLink": audio_link,
            "Chaire": _trimmed_text(s.find("div", "chair-baseline"))
        })

        # Audio links ends like "foo-bar-fr.mp3", language is at the end.
        # Sometimes it is not specified though... so use a whitelisted length.
        language = audio_link[audio_link.rfind("-")+1:-4]
        if len(language) == 2:
            entity["Language"] = language
        else:
            entity["Language"] = "fr"

        try:
            entity["Function"] = list(
                s.find("h3", "lecturer").children)[1].text.strip()
        except (AttributeError, IndexError):
            # No function, okay.
            self._status["no_function"] += 1
            pass

        # Parse duration of the audio.
        try:
            hour_end = s.find("span", "to").text.strip()
            time_from = time.strptime(hour_start, "%H:%M")
            time_end = time.strptime(hour_end, "%H:%M")
            # There are no lessons that ends the next day so this works.
            entity["DurationSec"] = int(
                (
                    datetime.timedelta(
                        hours=time_end.tm_hour, minutes=time_end.tm_min)
                    - datetime.timedelta(
                        hours=time_from.tm_hour, minutes=time_from.tm_min)
                ).total_seconds())
        except (AttributeError, ValueError):
            logging.info("No end or wrong hour found, skipping")
            # TODO: Fix to 1H ? there are 2k source urls without end time...
            self._status["no_duration"] += 1
            return False, None

        video_link = s.find("li", "video")
        if video_link:
            entity["VideoLink"] = video_link.find("a").get("href")
            self._status["has_video"] += 1

        # Save entity finally.
        if not self._dry_run:
            self._client.put(entity)
        else:
            logging.debug("[dry run] %s", entity)
        self._status["OK"] += 1
        return False, entity

    def _CollectPages(self, url):
        """Collect pages with audio in them from the given root url.

        Args:
            url: url to start the crawl from
        Yields:
            pages urls to individual lessons
        """
        if not self._robot.can_fetch(self._user_agent, url):
            logging.warning("Fetch of root url disallowed by robots.txt")
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
    parser.add_argument("--stop_when_present", help="Stop crawl when the first already imported item is found (useful after the first run).", action="store_true")
    parser.add_argument("--overwrite", help="Overwrite already imported entries if they are not converted already.", action="store_true")
    parser.add_argument("--root_url", help="Root URL to start the crawl from.", default="http://www.college-de-france.fr/components/search-audiovideo.jsp?fulltext=&siteid=1156951719600&lang=FR&type=audio")
    args = parser.parse_args()
    logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', level=logging.DEBUG)

    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
    logging.info("Creating client for project %s", args.project_id)
    client = datastore.Client(args.project_id)
    s = Scraper(
        client,
        args.stop_when_present,
        args.user_agent,
        args.dry_run,
        args.overwrite,
        robotparser.RobotFileParser())
    s.Run(args.root_url)
