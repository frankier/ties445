import re

evil = re.compile("öh|öö|uu|uh|äh|tä|oj|oo|oi|oh|ii|mmm|noo|huu|huh|hii|hh|hoo|ee|eh|he|ha|aha|aa", re.IGNORECASE)

def omor_unsafe(word):
    word_len = len(word)
    word_lower = word.lower()
    return (word_len > 100 or
            (word_len > 20 and evil.match(word)))
