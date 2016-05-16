# -*- coding: utf-8 -*-
import re
from scrapy import Spider, Request
from w3lib.html import remove_tags

from scrapers.items import BookPage

YEAR_REXEX = re.compile(r'\b\d\d\d\d\b')
PUNCT_END = re.compile(r'[.!?]\s*$')
EBOOK_END = re.compile(r'\*\*\*.*END OF .* PROJECT GUTENBERG EBOOK')

class ProjectGutenbergPipeline(Spider):
    name = "projectgutenberg"
    allowed_domains = ["www.gutenberg.org", "www.gutenberg.lib.md.us"]
    start_urls = (
        'http://www.gutenberg.org/robot/harvest?filetypes[]=txt&l&langs[]=fi',
    )
    user_agent = ("Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Ubuntu Chromium/49.0.2623.108 "
                  "Chrome/49.0.2623.108 Safari/537.36")

    def maybe_follow_next(self, response):
        next_link = response.css('a:contains(Next)::attr(href)').extract_first()
        if next_link:
            full_url = response.urljoin(next_link)
            return Request(full_url, callback=self.parse)

    def parse(self, response):
        downloads = response.css('a:not(:contains(Next))::attr(href)')
        for download in downloads.extract():
            req = Request(download, callback=self.download)
            req.meta['id'] = download.split('/')[-2]
            yield req
        yield self.maybe_follow_next(response)

    def download(self, response):
        print("download")
        lines = response.body_as_unicode().split("\n")
        front = lines[:100]
        years = []
        taking_title = False
        title = ""
        taking_author = False
        author = ""
        blanklines = 0
        startline = 0
        for i, line in enumerate(front):
            if not line.strip():
                taking_title = False
                taking_author = False
                blanklines += 1
                continue
            if blanklines > 3 or line.startswith('*** START OF THIS PROJECT GUTENBERG EBOOK'):
                startline = i + 1
            blanklines = 0
            if line.startswith('Title: ') or taking_title:
                title += line.replace('Title: ', '').strip()
            if line.startswith('Author: ') or taking_author:
                author += line.replace('Author: ', '').strip()
            for year in YEAR_REXEX.findall(line):
                years.append(int(year))
        book = front[startline:] + lines[100:]
        year = sorted(years)[0]
        bookinfo = dict(
            id=response.meta['id'],
            year=year,
            title=title,
            author=author,
        )
        endi = None
        page = 1
        while endi is None and book:
            lines = book[:100]
            last_para_break = 0
            last_sentence_end = 0
            for i, line in enumerate(lines):
                if not line.split():
                    last_para_break = i
                if EBOOK_END.match(line):
                    endi = i
                if PUNCT_END.search(line):
                    last_sentence_end = i + 1

            if endi is not None:
                spliti = endi
            elif last_para_break > 50:
                spliti = last_para_break
            elif last_sentence_end > 50:
                spliti = last_sentence_end
            else:
                spliti = 100

            content = "\n".join(lines[:spliti]).replace("\r", "")
            content = re.sub("[^\n]\n[^\n]", " ", content, flags=re.MULTILINE).strip()
            if content:
                yield BookPage(
                    content=content,
                    page=page,
                    **bookinfo
                )

            book = book[spliti:]
            page += 1
