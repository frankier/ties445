# -*- coding: utf-8 -*-

from scrapy.item import Item, Field
from scrapy.loader.processors import MapCompose, Compose
from scrapylib.processors import default_input_processor as clean_html_processor
from scrapylib.processors.date import parse_datetime
from lxml import html as lhtml

def fix_tree(html):
    lh = lhtml.fromstring(html)

    comments = lh.xpath('//comment()')
    for c in comments:
        p = c.getparent()
        p.remove(c)

    for div in lh.cssselect('.quotetitle, .quotecontent'):
        div.drop_tree()

    for img in lh.cssselect('img'):
        parent = img.getparent()
        assert parent is not None
        previous = img.getprevious()
        new_tail = img.get('alt', "") + (img.tail or "")
        if previous is None:
            parent.text = (parent.text or '') + new_tail
        else:
            previous.tail = (previous.tail or '') + new_tail
        parent.remove(img)

    return lhtml.tostring(lh, encoding='unicode')

clean_post_processor = Compose(
    MapCompose(fix_tree),
    clean_html_processor
)

class ForumPost(Item):
    id = Field()
    author = Field()
    post_date = Field(input_processor=MapCompose(parse_datetime))
    breadcrumbs = Field()
    content = Field(input_processor=clean_post_processor)

class BookPage(Item):
    id = Field()
    author = Field()
    year = Field()
    title = Field()
    page = Field()
    content = Field()

class NewsItem(Item):
    id = Field()
    title = Field()
    post_date = Field()
    content = Field()
