import unicodedata
import csv
import sys
import scipy.io as io
import numpy as np
from subprocess import PIPE
import asyncio
import argparse
from asyncio.subprocess import create_subprocess_exec
from itertools import chain

from utils import omor_unsafe

from collections import deque
from collections import Counter
from nltk.tokenize import sent_tokenize
from nltk.tokenize import wordpunct_tokenize

MAX_WORD_LEN = 20
MAX_ENDING_LEN = 20
MAX_SENT_LEN = 40
POS_TAGS = ['UNKNOWN', 'PARTICLE', 'TRUNCATED', 'ADJECTIVE', 'ADPOSITION', 'ADVERB', 'NOUN', 'NUMERAL', 'PRONOUN', 'PUNCTUATION', 'VERB']
POS_TAGS_LEN = len(POS_TAGS)

loop = asyncio.get_event_loop()

class BlankEntry(Exception):
    pass

def omor_tags_to_dict(omor_tags):
    d = {}
    for bit in omor_tags.split('|'):
        k, v = bit[1:-1].split('=')
        d[k] = v
    return d

def normalise_counter(counter, slots, total_count):
    dist = [0] * slots
    for bin, count in counter.items():
        dist[bin] = float(count) / total_count
    return dist

def deforeignify(s):
    return unicodedata.normalize('NFKD', s).encode('ascii', 'ignore')

finnpos = None


async def process_finnpos_input(finnpos, sentences):
    sent_count = 0
    sent_len_counter = Counter()
    word_count = 0
    word_len_counter = Counter()
    for words in sentences:
        sent_len = len(words)
        if sent_len > MAX_SENT_LEN:
            sent_len = MAX_SENT_LEN
        sent_len_counter[sent_len - 1] += 1
        for word in words:
            finnpos.stdin.write(word.encode('utf-8'))
            finnpos.stdin.write(b'\n')
            word_len = len(word)
            if word_len > MAX_WORD_LEN:
                word_len = MAX_WORD_LEN
            word_len_counter[word_len - 1] += 1
            word_count += 1
        finnpos.stdin.write(b'\n')

        sent_count += 1
    word_dist = normalise_counter(word_len_counter, MAX_WORD_LEN, word_count)
    sent_dist = normalise_counter(sent_len_counter, MAX_SENT_LEN, sent_count)
    await finnpos.stdin.drain()

    return (sent_dist, word_dist)


async def process_finnpos_output(finnpos, sentences):
    ending_len_counter = Counter()
    unigrams = Counter()
    bigrams = Counter()
    trigrams = Counter()
    prev_prev_pos_idx = prev_pos_idx = POS_TAGS.index('PUNCTUATION')
    ending_word_count = 0
    gram_count = sum(len(s) for s in sentences)
    tags_left = gram_count
    async for tags in finnpos.stdout:
        tags = tags.decode('utf-8')
        if tags.strip() == '':
            prev_prev_pos_idx = prev_pos_idx = POS_TAGS.index('PUNCTUATION')
            if tags_left <= 0:
                break
            continue
        word, _, lemma, omor_tags, _ = tags.split('\t')
        first_omor_tag = omor_tags.split('||')[0]
        omor_tags_parsed = omor_tags_to_dict(first_omor_tag)
        cur_pos = omor_tags_parsed['POS']
        cur_pos_idx = POS_TAGS.index(cur_pos)
        if cur_pos != 'PUNCTUATION':
            ending_word_count += 1
            ending_len = len(word) - len(lemma) + 1
            if ending_len < 0:
                ending_len = 0
            elif ending_len > MAX_ENDING_LEN:
                ending_len = MAX_ENDING_LEN - 1
            ending_len_counter[ending_len] += 1
        unigrams[cur_pos_idx] += 1
        bigrams[prev_pos_idx * POS_TAGS_LEN + cur_pos_idx] += 1
        trigrams[prev_prev_pos_idx * POS_TAGS_LEN * POS_TAGS_LEN + prev_pos_idx * POS_TAGS_LEN + cur_pos_idx] += 1
        prev_prev_pos_idx = prev_pos_idx
        prev_pos_idx = cur_pos_idx
        tags_left -= 1

    ending_dist = normalise_counter(ending_len_counter, MAX_ENDING_LEN, ending_word_count)
    unigram_dist = normalise_counter(unigrams, POS_TAGS_LEN, gram_count)
    bigram_dist = normalise_counter(bigrams, POS_TAGS_LEN * POS_TAGS_LEN, gram_count)
    trigram_dist = normalise_counter(trigrams, POS_TAGS_LEN * POS_TAGS_LEN * POS_TAGS_LEN, gram_count)

    return (ending_dist, unigram_dist, bigram_dist, trigram_dist)


async def async_process_content(finnpos, content):
    sentences = []
    sentence_strs = sent_tokenize(content)
    for sent in sentence_strs:
        words = wordpunct_tokenize(sent)
        sentence = [word for word in words if not omor_unsafe(word)]
        if not len(sentence):
            raise BlankEntry()
        sentences.append(sentence)
    processed = await asyncio.gather(
        process_finnpos_input(finnpos, sentences),
        process_finnpos_output(finnpos, sentences))
    # word/sent, char/word, morph/word, unigram
    return tuple(chain.from_iterable(processed))


def process_content(finnpos, content):
    return loop.run_until_complete(async_process_content(finnpos, content))


async def process_finnpos_lemma_input(finnpos, sentences):
    for words in sentences:
        for word in words:
            if omor_unsafe(word):
                continue
            finnpos.stdin.write(word.encode('utf-8'))
            finnpos.stdin.write(b'\n')
        finnpos.stdin.write(b'\n')
    await finnpos.stdin.drain()


async def process_finnpos_lemma_output(finnpos, sentences):
    gram_count = sum(sum(1 for w in s if not omor_unsafe(w)) for s in sentences)
    tags_left = gram_count
    lemmas = []
    async for tags in finnpos.stdout:
        tags = tags.decode('utf-8')
        if tags.strip() == '':
            if tags_left <= 0:
                break
            continue
        word, _, lemma, omor_tags, _ = tags.split('\t')
        lemmas.append(lemma)
        tags_left -= 1

    return lemmas


async def async_process_lemma(finnpos, content):
    sentences = []
    sentence_strs = sent_tokenize(content)
    for sent in sentence_strs:
        words = wordpunct_tokenize(sent)
        sentences.append(words)
    processed = await asyncio.gather(
        process_finnpos_input(finnpos, sentences),
        process_finnpos_output(finnpos, sentences))
    return processed[1]


def parse_args():
    parser = argparse.ArgumentParser(description="Format csvs from content scraping into a matlab file .")
    parser.add_argument('output', help='Output (.mat) file')
    parser.add_argument('--gutenberg', help="Project Gutenberg CSV")
    parser.add_argument('--punkinfinland', help="Punkinfinland CSV")
    parser.add_argument('--yle', help="Yle selkouutiset CSV")
    parser.add_argument('--target-id', help="Just try and extract one, specified, target id")

    return parser.parse_args()


def force_ascii(x):
    return x.encode('ascii')


def main():
    args = parse_args()

    target_id = args.target_id

    mats = dict(
        meta = [],
        sentence_len_dist = [],
        word_len_dist = [],
        word_morph_len_dist = [],
        unigrams = [],
        bigrams = [],
        trigrams = []
    )

    finnpos = loop.run_until_complete(create_subprocess_exec(
        'ftb-label', stdin=PIPE, stdout=PIPE))

    def proc_cont(cont):
        sd, wd, wmd, u, b, t = process_content(finnpos, cont)
        mats['sentence_len_dist'].append(sd)
        mats['word_len_dist'].append(wd)
        mats['word_morph_len_dist'].append(wmd)
        mats['unigrams'].append(u)
        mats['bigrams'].append(b)
        mats['trigrams'].append(t)

    # Project gutenberg
    if args.gutenberg:
        with open(args.gutenberg) as csvfile:
            gutenberg = csv.DictReader(csvfile)
            for row in gutenberg:
                id = "{}:{}".format(row['id'], row['page'])
                if target_id is not None and id != target_id:
                    continue
                print(id)
                try:
                    proc_cont(row['content'])
                except BlankEntry:
                    continue
                else:
                    mats['meta'].append([id, 'gutenberg', row['id']])

    # Punk in Finland
    if args.punkinfinland:
        with open(args.punkinfinland) as csvfile:
            punk = csv.DictReader(csvfile)
            for row in punk:
                id = row['id']
                if target_id is not None and id != target_id:
                    continue
                print(id)
                try:
                    proc_cont(row['content'])
                except BlankEntry:
                    continue
                else:
                    mats['meta'].append([id, 'punkinfinland', deforeignify(row['author'])])

    # Yle
    if args.yle:
        with open(args.yle) as csvfile:
            yle = csv.DictReader(csvfile)
            for row in yle:
                id = row['id']
                if target_id is not None and id != target_id:
                    continue
                print(id)
                if row['is_very_easy'] == "[True]":
                    subclass_name = 'tosihelppo'
                else:
                    subclass_name = 'selkouutiset'
                try:
                    proc_cont(row['content'])
                except BlankEntry:
                    continue
                else:
                    mats['meta'].append([id, 'yle', subclass_name])

    # Everything must be ASCII clean or else Matlab with have a hissy fit
    mats['meta'] = np.array(mats['meta'])
    mats['meta'] = np.vectorize(force_ascii)(mats['meta'])

    for k in mats:
        if k != 'meta':
            mats[k] = np.array(mats[k])

    io.savemat(args.output, mats, appendmat=False)


if __name__ == '__main__':
    sys.exit(main())
