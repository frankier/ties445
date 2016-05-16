# -*- coding: utf-8 -*-
from scrapy import Spider, Request
from scrapy.loader import ItemLoader
from w3lib.html import remove_tags

from scrapers.items import ForumPost

class PunkInFinlandSpider(Spider):
    name = "punkinfinland"
    allowed_domains = ["www.punkinfinland.net"]
    start_urls = (
        'http://www.punkinfinland.net/forum/',
    )

    # Utils
    def maybe_follow_next(self, response, callback):
        next_link = response.css('#pagecontent > table:first-child a:contains(Next)::attr(href)').extract_first()
        if next_link:
            full_url = response.urljoin(next_link)
            return Request(full_url, callback=callback)

    def follow_link(self, response, link, callback):
        full_url = response.urljoin(link.css('::attr(href)').extract_first())
        return Request(full_url, callback=callback)

    # Impl
    def parse(self, response):
        for link in response.css('a.forumlink'):
            if link.css('::text').extract_first().lower() == "in english":
                continue
            yield self.follow_link(response, link, self.parse)
        for link in response.css('a.topictitle'):
            yield self.follow_link(response, link, self.parse_topic_page)
        yield self.maybe_follow_next(response, self.parse)

    def parse_topic_page(self, response):
        breadcrumbs = "{} » {}".format(
            remove_tags(response.css('.breadcrumbs').extract_first()),
            response.css('.titles::text').extract_first())
        # Tables containing a postbody are posts
        for post in response.xpath("//div[@id='pagecontent']/table[.//div[@class='postbody']]"):
            yield self.parse_post(breadcrumbs, post)
        yield self.maybe_follow_next(response, self.parse_topic_page)

    def parse_post(self, breadcrumbs, post):
        l = ItemLoader(item=ForumPost(), selector=post)
        posted_info = "tr[contains(@class, 'row')][1]//table//td[@class='gensmall']/div[last()]"
        l.add_css('author', '.postauthor::text')
        l.add_xpath('post_date', posted_info + "/text()[last()]")
        l.add_value('id', post.xpath(posted_info + "/a/@href").extract_first().split('#p')[-1])
        l.add_css('content', '.postbody:first-child')
        l.add_value('breadcrumbs', breadcrumbs)
        post = l.load_item()
        if len(post['content'][0]) > 5:
            return post
