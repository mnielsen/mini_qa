#### mini_qa.py
#
# By Michael Nielsen, 2012
#
# A toy question-answering system, which uses Google to attempt to
# answer questions of the form "Who... ?"  An example is: "Who
# discovered relativity?"
#
# The design is a toy version of the AskMSR system developed by
# researchers at Microsoft Research.  The original paper is:
#
# Brill, Lin, Banko, Dumais and Ng, "Data-Intensive Question
# Answering" (2001).
#
# I've described background to this program here:
#
# http://michaelnielsen.org/ddi/how-to-answer-a-question-v1/


#### Library imports

# standard library
from collections import defaultdict
import json
import operator
import re
import string
import urllib
import urllib2

# third party libraries
from google import search

def pretty_qa(question, num=10):
    """
    Wrapper for the `qa` function.  `pretty_qa` prints the top `num`
    ranking answers to `question`, with the scores in parentheses.
    """
    print "Q: "+question
    for (j, (answer, score)) in enumerate(qa(question)[:num]):
        print "%s. %s (%s)" % (j+1, " ".join(answer), score)
    print

def qa(question):
    """
    Return a list of tuples whose first entry is the answer to
    `question`, and whose second entry is the score for that answer.
    The tuples are in decreasing order of score.  Note that the
    answers themseles are tuples, with each entry being a word.
    """
    answer_scores = defaultdict(int)
    for query in rewritten_queries(question):
        for summary in get_google_summaries(query.query):
            for sentence in sentences(summary):
                for ngram in candidate_answers(sentence, query.query):
                    answer_scores[ngram] += ngram_score(ngram, query.score)
    return sorted(
            answer_scores.iteritems(), key=operator.itemgetter(1), reverse=True)

def rewritten_queries(question):
    """
    Return a list of RewrittenQuery objects, containing the search
    queries (and corresponding weighting score) generated from
    `question`."""
    rewrites = [] # where we'll store our list of RewrittenQuery objects
    tq = tokenize(question)
    verb = tq[1] # the simplest assumption, something to improve
    rewrites.append(RewrittenQuery(verb+" "+" ".join(tq[2:]), 5))
    for j in range(2, len(tq)):
        rewrites.append(
            RewrittenQuery(
                " ".join(tq[2:j+1])+" "+verb+" "+string.join(tq[j+1:]),
                5))
    rewrites.append(RewrittenQuery(" ".join(tq[2:]), 2))
    return rewrites

def tokenize(question):
    """
    Return a list containing a tokenized form of `question`.  Works
    by stripping all non-alphanumeric characters, lowercasing,
    and splitting around whitespace.
    """
    return [re.sub(r"\W", "", x) for x in question.lower().split()]

class RewrittenQuery():
    """
    Given a question we rewrite it as a query to send to Google.
    RewrittenQuery is used to store these rewritten queries.
    Instances have two attributes: the text of the rewritten query,
    which is sent to Google; and a score, indicating how much weight
    to give to the answers.  The score is used because some queries
    are much more likely to give highly relevant answers than others.
    """

    def __init__(self, query, score):
        self.query = query
        self.score = score

def get_google_summaries(query):
    """
    Return a list of the top 10 summaries associated to the Google
    results for `query`.  Note that these are
    BeautifulSoup.BeautifulSoup objects, and may need to be
    manipulated further to extract text, links, etc.
    """
    return search(query)

def sentences(summary):
    """
    Return a list whose entries are the sentences in the
    BeautifulSoup.BeautifulSoup object `summary` returned from Google.
    Note that the sentences contain alphabetical and space characters
    only, no punctuation.
    """
    text = remove_spurious_words(text_of(summary))
    sentences = remove_all("", text.split("."))
    return [re.sub(r"[^a-zA-Z ]", "", sentence) for sentence in sentences]

def text_of(soup):
    """
    Return the text associated to the BeautifulSoup.BeautifulSoup
    object `soup`.
    """
    text_soup = soup.findAll(text=True)
    if text_soup:
        return ''.join(soup.findAll(text=True))
    else:
        return ''

def remove_spurious_words(text):
    """
    Return `text` with words stripped which we should ignore in
    generating answers.  For example, Google includes the word
    "Cached" in many search summaries, and this word should therefore
    mostly be ignored.
    """
    spurious_words = ["Cached", "Similar"]
    for word in spurious_words:
        text = text.replace(word, "")
    return text

def remove_all(elt, l):
    """
    Returns the list `l` with all entries `elt` deleted.
    """
    return filter(lambda x: x != elt, l)

def candidate_answers(sentence, query):
    """
    Return all the 1-, 2-, and 3-grams in `sentence`.  Terms appearing
    in `query` are filtered out.
    """
    filtered_sentence = filter(lambda x: x.lower() not in query, sentence.split())
    return [(x,) for x in filtered_sentence]+\
        [(filtered_sentence[j], filtered_sentence[j+1]) \
         for j in range(len(filtered_sentence)-1)]+ \
        [(filtered_sentence[j], filtered_sentence[j+1], filtered_sentence[j+2]) \
         for j in range(len(filtered_sentence)-2)]

def ngram_score(ngram, score):
    """
    Return the score associated to `ngram`.  The base score is
    `score`, but it's modified by a factor which is 3 to the power of
    the number of capitalized words.  This is a way of biasing answers
    toward proper nouns.
    """
    capitalized_words = [word for word in ngram if is_capitalized(word)]    
    return score * (3**len(capitalized_words))

def is_capitalized(word):
    """
    Return True or False according to whether `word` is capitalized.
    """
    return word == word.capitalize()

if __name__ == "__main__":
    pretty_qa("Who ran the first four-minute mile?")
    pretty_qa("Who killed Abraham Lincoln?")
    pretty_qa("Who invented the C programming language?")
    pretty_qa("Who invented relativity?")
    pretty_qa("Who caused the financial crash of 2008?")
    pretty_qa("Who caused the Great Depression?")
    pretty_qa("Who is the most evil person in the world?")
    pretty_qa("Who wrote the poems of Wiliam Shakespeare?")
    pretty_qa("Who shot Kennedy?")
    pretty_qa("Who is the world's best tennis player?")
