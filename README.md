# College de France audio scraper

[![Build Status](https://travis-ci.org/attwad/cdf-scraper.svg?branch=master)](https://travis-ci.org/attwad/cdf-scraper)

This is a sraper for pages containing audio material from the College de France website.

## Purpose

It doesn't download any audio file but instead stores metadata about them (lesson title, lecturer, date, etc.)
in Google's Datastore to allow statistics and further extraction of data to be done.

## How to run

For devs, follow the [gist](https://gist.github.com/attwad/b8b180bd58eb130c9be73b3961183554).

For an actual prod run, a docker file is provided you can run it with:

```
docker build -t scraper .
docker run scraper
```

You'll have to create your own project in Google Compute Engine and pass in your project ID and proper
json service account credentials via environment variables.

# Output

Once you run it, you'll see a few thousands entities in your dashboard.
