# -*- coding: utf-8 -*-
import os
import locale
import calendar
from datetime import date, datetime, timedelta
from functools import partial
import json

from w3lib.http import basic_auth_header
from scrapy import Spider, Request
from scrapy.loader import ItemLoader
from scrapy.utils.request import request_authenticate
from urllib.parse import quote
from w3lib.html import remove_tags
from py_bing_search import PyBingWebSearch

from scrapers.items import NewsItem


def mk_bing_request(search_term, api_key, callback):
    quoted_search = quote("'{}'".format(search_term))
    url = ("https://api.datamarket.azure.com/Bing/SearchWeb/v1/Web"
           "?Query={}&$format=json").format(quoted_search)
    request = Request(url, callback=callback)
    request_authenticate(request, "", api_key)
    return request


class YleSpider(Spider):
    name = "yle"
    allowed_domains = ["yle.fi", "api.datamarket.azure.com"]
    start_urls = (
        'http://yle.fi/uutiset/selkouutiset/selkouutisarkisto/',
    )
    date_fmt = "%d.%m.%Y"
    date_out_fmt = "%-d.%-m.%Y"

    def follow_link(self, response, link, callback):
        full_url = response.urljoin(link.css('::attr(href)').extract_first())
        return Request(full_url, callback=callback)

    def parse(self, response):
        if 'BING_API_KEY' not in os.environ:
            raise ValueError("You must set the BING_API_KEY environment variable")
        bing_api_key = os.environ['BING_API_KEY']
        for link in response.css('section.recents > article > a[href]'):
            title = link.css('h1::text').extract_first()
            yield self.follow_link(response, link, self.parse_news_post)

        yield Request('http://yle.fi/uutiset/selkouutiset/tosi_helppo/', callback=self.get_very_easy)

        oldest_str = title.strip().split(' ')[1]
        oldest = datetime.strptime(oldest_str, self.date_fmt).date()
        for r in self.get_older_from_search(oldest, bing_api_key):
            yield r

    def get_older_from_search(self, oldest, bing_api_key):
        locale.setlocale(locale.LC_TIME, 'fi_FI')
        while oldest > date(2015, 1, 1):
            date_str = datetime.strftime(oldest, self.date_out_fmt)
            dow = calendar.day_name[oldest.weekday()]

            search_term = 'site:http://yle.fi/uutiset/ intitle:"{} {}"'.format(dow, date_str)
            print(search_term)
            yield mk_bing_request(search_term, bing_api_key, self.process_bing_results)
            oldest -= timedelta(days=1)

    def process_bing_results(self, response):
        resp_dict = json.loads(response.text)
        print(resp_dict)
        for result in resp_dict['d']['results']:
            print(result['Title'], result['Url'])
            if '(tv)' in result['Title'] or '(radio)' in result['Title']:
                yield Request(result['Url'], callback=self.parse_news_post)

    def get_very_easy(self, response):
        links = response.xpath('//div[@class="text"]/h3/following-sibling::*//a')
        for link in links:
            yield self.follow_link(response, link, partial(self.parse_news_post, is_very_easy=True))

    def parse_news_post(self, response, is_very_easy=False):
        page_id = response.url.split('uutiset/')[1]
        date_title = response.css('h1[itemprop=name]::text').extract_first()
        content = response.css('#vasen_palsta > article > .text')
        if not is_very_easy:
            date_str = date_title.strip().split(' ')[1]
        if is_very_easy:
            l = ItemLoader(item=NewsItem())
            l.add_value('id', page_id)
            l.add_value('is_very_easy', True)
            title, date_str = date_title.split(' (')
            date_str = date_str.strip(')')
            l.add_value('post_date', date_str)
            l.add_value('content', title + '.')
            l.add_value('content', content.extract_first())
            yield l.load_item()
        elif content.css('h3').extract_first() is None:
            l = ItemLoader(item=NewsItem())
            l.add_value('id', page_id)
            l.add_value('is_very_easy', False)
            l.add_value('post_date', date_str)
            l.add_value('content', content.extract_first())
            yield l.load_item()
        else:
            cur = content.css('h3:first-of-type')
            gathered = []
            while cur:
                tag_name = cur.xpath('name()').extract_first()
                if tag_name == 'h3':
                    gathered.append([])
                gathered[-1].append(cur)
                cur = cur.xpath('following-sibling::*[1]')
            for i, item in enumerate(gathered):
                id = "{}#{}".format(page_id, i)
                content = ''.join([bit.extract_first() for bit in item])
                content = "<div>" + content + "</div>"
                l = ItemLoader(item=NewsItem())
                l.add_value('id', id)
                l.add_value('is_very_easy', False)
                l.add_value('post_date', date_str)
                l.add_value('content', content)
                yield l.load_item()
