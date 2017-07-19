from urllib import request
from urllib import parse
import argparse
import time
import datetime
import locale

from bs4 import BeautifulSoup
from google.cloud import datastore

def ParsePage(client, page_url):
    """Parses a single page containing a lecture."""
    print("Parsing page", page_url)
    resp = request.urlopen(page_url)
    s = BeautifulSoup(resp.read(), "html.parser")
    # Skip lessons without audio.
    audio_link = s.find("li", "audio")
    if not audio_link:
        print("No audio link @", page_url)
        return
    audio_link = audio_link.find("a").get("href")
    key = client.key('Entry', audio_link)
    # If we already have it, skip.
    if client.get(key):
        print("Already saved", audio_link)
        return
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
    client.put(entity)
    return entity

def CollectPages(url):
    """Collect pages with audio in them from the given root url.

    Args:
        url: url to start the crawl from
    Yields:
        pages urls to individual lessons
    """
    maybe_more_content = True
    num_pages = 0
    while maybe_more_content:
        resp = request.urlopen(url + "&index=" + str(num_pages))
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
    parser.add_argument("--root_url", help="Root URL to start the crawl from.", default="http://www.college-de-france.fr/components/search-audiovideo.jsp?fulltext=&siteid=1156951719600&lang=FR&type=audio")
    args = parser.parse_args()

    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
    print("Creating client for project", args.project_id)
    client = datastore.Client(args.project_id)
    print("Starting collection of pages from root URL", args.root_url)
    for page in CollectPages(args.root_url):
        ParsePage(client, page)
