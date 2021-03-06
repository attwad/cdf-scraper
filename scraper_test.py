from urllib import request
from urllib import robotparser
import unittest
from unittest.mock import patch
from unittest.mock import create_autospec
from unittest.mock import call
from unittest.mock import MagicMock
import io
import locale
import logging
import time
import datetime

import scraper
from google.cloud import datastore

@patch.object(request, "urlopen")
class TestScraper(unittest.TestCase):
    def setUp(self):
        self._mock_client = create_autospec(datastore.Client)
        self._mock_robot = create_autospec(robotparser.RobotFileParser)
        self._mock_robot.can_fetch.return_value = True
        self._scraper = scraper.Scraper(
            self._mock_client,
            True, # stop_when_present
            'Morzina',
            False, # dry_run
            False, # overwrite
            self._mock_robot)
        self._headers = {'User-Agent': 'Morzina'}
        # HTML copy pasted almost verbatim (minus noisy head tags).
        self._page_io = io.StringIO("""
        <!doctype html>
        <body>
        <header id="head">
        <!--[noindex-->
        	<div id="root" class="section">
        		<h1 id="logo" class="dgt-nav">
        			<a href="/site/college/index.htm">Coll&egrave;ge de France</a>
        		</h1>

        		<nav id="menu">
        			<ul class="menu dgt-nav dgt-menu" data-url="/site/jscript/menu_college.htm">
        				<li>
        					<a href="/site/jscript/menu_college.htm">menu</a>
        				</li>
        			</ul>
        		</nav>
        		<div id="tools">
        <ul id="langs">
        <!--[digital.langs-->
        	<li><span>fr</span></li>
        <li><a href="/site/en-alain-wijffels/index.htm">en</a></li>
        <li><a href="/site/cn-college/index.htm">cn</a></li>
        <!--digital.langs]-->
        </ul></div>
        	</div><!--root-->
        <!--noindex]-->
        </header><!-- #header -->
        <main id="main">
        <!--[digital.page-->
        	<div class="page" data-id="/site/alain-wijffels/index.htm" data-url="/site/alain-wijffels/index.htm"></div>
        	<!--digital.page]-->
        <!--[digital.page-->
        	<div class="page" data-id="/site/alain-wijffels/_closing-lecture.htm" data-url="/site/alain-wijffels/_closing-lecture.htm"></div>
        	<!--digital.page]-->
        <!--[digital.page-->
        	<div class="page" data-id="/site/alain-wijffels/closing-lecture-2016-2017.htm" data-url="/site/alain-wijffels/closing-lecture-2016-2017.htm"></div>
        	<!--digital.page]-->
        <!--[digital.page-->
        			<div class="page page6" data-id="/site/alain-wijffels/closing-lecture-2017-06-29-17h00.htm" data-url="/site/alain-wijffels/closing-lecture-2017-06-29-17h00.htm" data-site="college" data-channel="enseignement" data-subject="alain-wijffels" data-chapter="agenda" data-alias="closing-lecture-2017-06-29-17h00">
        				<div class="section">
           					<div class="dgt-fat video">
        	   					<div class="dgt-section-body">
        <div class="block headerpage">
        <h4><a href="/site/alain-wijffels/closing-lecture-2016-2017.htm">Pour une culture juridique européenne</a></h4>
        <h1 id="title">
        			Pour une culture juridique européenne</h1>
        <ul class="context-buttons">
        			<li class="twitter" id="share_twitter">
        				<a href="javascript:sharePage('twitter','/site/alain-wijffels/closing-lecture-2017-06-29-17h00.htm', 'Pour une culture juridique européenne')" title="twitter">
        					<span class="icon"></span>
        				</a>
        			</li>
        			<li class="facebook" id="share_facebook">
        				<a href="javascript:sharePage('facebook','/site/alain-wijffels/closing-lecture-2017-06-29-17h00.htm', 'Pour une culture juridique européenne')" title="facebook">
        					<span class="icon"></span>
        				</a>
        			</li>
        			<li class="linkedin" id="share_linkedin">
        				<a href="javascript:sharePage('linkedin','/site/alain-wijffels/closing-lecture-2017-06-29-17h00.htm', 'Pour une culture juridique européenne')" title="linkedin">
        					<span class="icon"></span>
        				</a>
        			</li>
        		</ul>
        <div class="switchlang">
        <ul id="langs">
        <!--[digital.langs-->
        	<li><span>fr</span></li>
        <li><a href="/site/en-alain-wijffels/index.htm">en</a></li>
        <li><a href="/site/cn-college/index.htm">cn</a></li>
        <!--digital.langs]-->
        </ul></div>
        	</div>
        <div class="block metadata">
        		<h3 class="lecturer"> Alain Wijffels<span class="function">Historien du droit, Professeur aux universités de Leyde, Louvain et Louvain-la-Neuve, directeur de recherche CNRS</span>
        		</h3>
        <div class="date-place event-past">
        <span class="date">
        <span class="day">29 juin 2017</span>
        <span class="from">17:00</span>
        <span class="to">18:00</span>
        </span>
        <span class="type">Leçon de clôture</span>
        <span class="place">Amphithéâtre Maurice Halbwachs&nbsp;-&nbsp;Marcelin Berthelot</span>
        </div><!--date-place-->
        </div><!--block--><div itemscope itemtype="http://schema.org/VideoObject" class="block video">
        						<meta itemprop="name" content="Pour une culture juridique européenne - Video - Chaire Européenne (2016-2017) - 29 juin 2017 17:00 - Alain Wijffels - Coll&#232;ge de France" />
        						<meta itemprop="description" content="Ce document est la  captation vidéo d'un enseignement par Alain Wijffels. Elle a été enregistrée par le Collège de France le 29 juin 2017 17:00 dans le cadre de la diffusion des savoirs. Elle fait partie de l'enseignement Chaire Européenne (2016-2017). D'autres vidéos sont accessible sur http://www.college-de-france.fr. © Collège de France" />
        						<meta itemprop="thumbnailUrl" content="http://www.college-de-france.fr/video/alain-wijffels/2017/lc-wijffels-20170629_thumb.jpg" />
        						<meta itemprop="contentURL" content="http://www.college-de-france.fr/video/alain-wijffels/2017/lc-wijffels-20170629.mp4" />
        						<meta itemprop="uploadDate" content="2017-06-29T17:00:00+01:00" />
        						<video id="mainvideo" class="video-js vjs-default-skin" controls preload="none"
        							poster="http://www.college-de-france.fr/video/alain-wijffels/2017/lc-wijffels-20170629_thumb.jpg"
        							data-width="480"
        							data-height="360"
        							data-setup="{}">
        							<source src="http://www.college-de-france.fr/video/alain-wijffels/2017/lc-wijffels-20170629.mp4" type='video/mp4' />
        						</video>
        					</div>
        					<!--block-->
        <div class="block multiplelink side">
        							<ul class="picto">
        								<li class=video>
        									<a href="http://www.college-de-france.fr/video/alain-wijffels/2017/lc-wijffels-20170629.mp4" target="_blank"><span class="icon"></span>Télécharger la vidéo</a>
        								</li>
        <li class="audio "><a href="http://www.college-de-france.fr/audio/alain-wijffels/2017/alain-wijffels.2017-06-29-17-00-00-a-fr.mp3" target="_blank" ><span class="icon"></span>Télécharger l'audio</a></li>
        </ul>
        						</div>
        <div class="chair-baseline">
        									<a href="/site/alain-wijffels/index.htm">
        										<span class="icon"></span>
        										Chaire Européenne (2016-2017)</a>
        								</div>
        </div>
        					</div>
        				</div>
        			</div>
        			<!--digital.page]-->
        </main>
        	</body>
        </html>
                            """)

    def test_two_links_on_first_page(self, mock_url_open):
        mock_url_open.side_effect = (
            io.StringIO("""
            <body>
            <a href="/site/url1"></a>
            <a href="/not/a/good/url"></a>
            <a href="/site/url2"></a>
            </body>
            """),
            io.StringIO("empty second page"))
        root = "http:///root/?foo=bar"
        pages = list(self._scraper._CollectPages(root))
        self.assertSequenceEqual(
            ("http://www.college-de-france.fr/site/url1",
             "http://www.college-de-france.fr/site/url2"),
            pages)
        self.assertEqual(2, mock_url_open.call_count)

    def test_already_scraped(self, mock_url_open):
        mock_url_open.return_value = self._page_io
        self._mock_client.get.return_value = {
            "Converted": False, "Title": "A lesson"}
        stop_when_present, _ = self._scraper._ParsePage("http:///page/url")
        self.assertTrue(stop_when_present)
        self._mock_client.put.assert_not_called()

    def test_robot_txt_disallowed(self, mock_url_open):
        self._mock_robot.can_fetch.return_value = False
        stop_when_present, entity = self._scraper._ParsePage("http:///page/url")
        self.assertFalse(stop_when_present)
        self.assertFalse(entity)
        self._mock_client.put.assert_not_called()

    def test_already_scraped_overwrite(self, mock_url_open):
        self._scraper = scraper.Scraper(
            self._mock_client,
            True, # stop_when_present
            'Morzina',
            False, # dry_run
            True, # overwrite
            self._mock_robot)
        mock_url_open.return_value = self._page_io
        self._mock_client.get.return_value = {
            "Converted": False, "Title": "A lesson"}
        stop_when_present, ent = self._scraper._ParsePage("http:///page/url")
        self.assertFalse(stop_when_present)
        self._mock_client.put.assert_called_once_with(ent)

    def test_already_scraped_overwrite_converted(self, mock_url_open):
        self._scraper = scraper.Scraper(
            self._mock_client,
            True, # stop_when_present
            'Morzina',
            False, # dry_run
            True, # overwrite
            self._mock_robot)
        mock_url_open.return_value = self._page_io
        self._mock_client.get.return_value = {
            "Converted": True, "Title": "A lesson"}
        stop_when_present, ent = self._scraper._ParsePage("http:///page/url")
        self.assertFalse(stop_when_present)
        self._mock_client.put.assert_not_called()

    def testNoAudioLink(self, mock_url_open):
        mock_url_open.return_value = io.StringIO("an empty page")
        self._mock_client.get.return_value = {
            "Converted": False, "Title": "A lesson"}
        stop_when_present, _ = self._scraper._ParsePage("http:///page/url")
        self.assertFalse(stop_when_present)
        self._mock_client.put.assert_not_called()

    def testSavesEntity(self, mock_url_open):
        mock_url_open.return_value = self._page_io
        self._mock_client.get.return_value = None
        stop_when_present, ent = self._scraper._ParsePage("http:///page/url")
        self._mock_client.put.assert_called_once_with(ent)
        self.assertEqual("http:///page/url", ent["Source"])
        self.assertTrue(ent["Scraped"])
        self.assertEqual("Pour une culture juridique européenne", ent["Title"])
        self.assertEqual(3600, ent["DurationSec"])
        self.assertEqual("Pour une culture juridique européenne", ent["TypeTitle"])
        self.assertEqual('Alain Wijffels', ent["Lecturer"])
        self.assertEqual(
            "Historien du droit, Professeur aux universités de Leyde, Louvain "
            "et Louvain-la-Neuve, directeur de recherche CNRS", ent["Function"])
        self.assertEqual(datetime.datetime(2017, 6, 29, 0, 0),
                         ent["Date"])
        self.assertEqual("Leçon de clôture", ent["LessonType"])
        self.assertEqual("http://www.college-de-france.fr/audio/alain-wijffels/2017/alain-wijffels.2017-06-29-17-00-00-a-fr.mp3", ent["AudioLink"])
        self.assertEqual("fr", ent["Language"])
        self.assertEqual("Chaire Européenne (2016-2017)", ent["Chaire"])


if __name__ == '__main__':
    logging.basicConfig(format='%(levelname)s %(asctime)s %(message)s', level=logging.DEBUG)
    locale.setlocale(locale.LC_ALL, 'fr_FR.UTF-8')
    unittest.main()
