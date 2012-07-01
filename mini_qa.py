"""
mini_qa.py
~~~~~~~~~~

Toy question-answering program.
"""

#### Library imports

# standard library
from collections import defaultdict
import cPickle as pickle
import json
import re
import sys
from xml.etree import ElementTree

# third-party libraries
import boto
from boto.s3.connection import S3Connection
from boto.s3.key import Key
from google import search
import wolfram


#### Config

try:
    import config
except ImportError:
    print ("Failed to import config.  Enter configuration data into\n"
           "config.py.example, and rename it to config.py.")
    sys.exit()

wolfram_server = 'http://api.wolframalpha.com/v1/query.jsp'

#### Parameters used to score results returned from the Google-based
#### system
CAPITALIZATION_FACTOR = 2.2
QUOTED_QUERY_SCORE = 5
UNQUOTED_QUERY_SCORE = 2

#### Create or retrieve an S3 bucket for the cache of Google search
#### results
s3conn = S3Connection(config.AWS_ACCESS_KEY_ID, config.AWS_SECRET_ACCESS_KEY)
google_cache_bucket_name = (config.AWS_ACCESS_KEY_ID).lower()+"-google-cache"
try:
    GOOGLE_CACHE = Key(s3conn.create_bucket(google_cache_bucket_name))
except boto.exception.S3CreateError:
    print ("When creating an S3 bucket for Google cache results, a conflict\n"
           "occurred, and a bucket with the desired name already exists.")
    sys.exit()

#### Create or retrieve an S3 bucket for the cache of Wolfram Alpha
#### results
wolfram_cache_bucket_name = (config.AWS_ACCESS_KEY_ID).lower()+"-wolfram-cache"
try:
    WOLFRAM_CACHE = Key(s3conn.create_bucket(wolfram_cache_bucket_name))
except boto.exception.S3CreateError:
    print ("When creating an S3 bucket for Wolfram Alpha cache results, a\n"
           "conflict occurred, and a bucket with the desired name already\n"
           "exists.")
    sys.exit()


def pretty_qa(question, source="google", num=10):
    """
    Wrapper for the `qa` function.  `pretty_qa` uses `source` to
    answer `question`.  For allowed values for `source`, see `qa`.
    Some sources produce a ranked list of answers, in which case only
    the top `num` are printed (with scores in parentheses).
    """
    print "\nQ: "+question
    if source=="google":
        for (j, (answer, score)) in enumerate(qa(question, source)[:num]):
            print "%s. %s (%s)" % (j+1, answer, score)
    else: # assume source=="wolfram" or source=="hybrid"
        answer = qa(question, source)
        if answer:
            print answer
        else:
            print "No answer returned"

def qa(question, source="google"):
    """
    Return answers to `question` from `source`.  Allowed values for
    `source` are "google", "wolfram" and "hybrid".  Note that the
    format of the answers returned will depend on the value of
    `source`.  See `google_qa`, `wolfram_qa` and `hybrid_qa` for
    details.
    """
    if source=="google":
        return google_qa(question)
    elif source=="wolfram": 
        return wolfram_qa(question)
    else: # assume source=="hybrid"
        return hybrid_qa(question)

def google_qa(question):
    """
    Return a list of tuples whose first entry is a candidate answer to
    `question`, and whose second entry is the score for that answer.
    The tuples are ordered in decreasing order of score.  
    """
    answer_scores = defaultdict(int)
    for query in rewritten_queries(question):
        for summary in get_summaries(query.query):
            for sentence in sentences(summary):
                for ngram in candidate_answers(sentence, query.query):
                    answer_scores[ngram] += ngram_score(
                        ngram, query.score)
    ngrams_with_scores = sorted(answer_scores.iteritems(), 
                                key=lambda x: x[1], 
                                reverse=True)
    return [(" ".join(ngram), score) 
            for (ngram, score) in ngrams_with_scores]

def rewritten_queries(question):
    """
    Return a list of RewrittenQuery objects, containing the search
    queries (and corresponding weighting score) generated from
    `question`.  
    """
    rewrites = [] 
    tq = tokenize(question)
    verb = tq[1] # the simplest assumption, something to improve
    rewrites.append(
        RewrittenQuery("\"%s %s\"" % (verb, " ".join(tq[2:])), 
                       QUOTED_QUERY_SCORE))
    for j in range(2, len(tq)):
        rewrites.append(
            RewrittenQuery(
                "\"%s %s %s\"" % (
                    " ".join(tq[2:j+1]), verb, " ".join(tq[j+1:])),
                QUOTED_QUERY_SCORE))
    rewrites.append(RewrittenQuery(" ".join(tq[2:]), UNQUOTED_QUERY_SCORE))
    return rewrites

def tokenize(question):
    """
    Return a list containing a tokenized form of `question`.  Works by
    lowercasing, splitting around whitespace, and stripping all
    non-alphanumeric characters.  
    """
    return [re.sub(r"\W", "", x) for x in question.lower().split()]


class RewrittenQuery():
    """
    Given a question we rewrite it as a query to send to Google.
    Instances of the RewrittenQuery class are used to store these
    rewritten queries.  Instances have two attributes: the text of the
    rewritten query, which is sent to Google; and a score, indicating
    how much weight to give to the answers.  The score is used because
    some queries are much more likely to give highly relevant answers
    than others.
    """

    def __init__(self, query, score):
        self.query = query
        self.score = score


def get_summaries(query, source="google"):
    """
    Return a list of the top 10 summaries associated to the results
    for `query` returned by `source`.  Returns all available summaries
    if there are fewer than 10 summaries available.  Note that these
    summaries are returned as BeautifulSoup.BeautifulSoup objects, and
    may need to be manipulated further to extract text, links, etc.
    Note also that we use GOOGLE_CACHE to cache old results, and will
    preferentially retrieve from the cache, whenever possible.
    """
    GOOGLE_CACHE.key = query
    if GOOGLE_CACHE.exists():
        return pickle.loads(GOOGLE_CACHE.get_contents_as_string())
    else:
        results = search(query)
        GOOGLE_CACHE.set_contents_from_string(pickle.dumps(results))
        return results

def sentences(summary):
    """
    Return a list whose entries are the sentences in the
    BeautifulSoup.BeautifulSoup object `summary` returned from Google.
    Note that the sentences contain alphabetical and space characters
    only, and all punctuation, numbers and other special characters
    have been removed.
    """
    text = remove_spurious_words(text_of(summary))
    sentences = [sentence for sentence in text.split(".") if sentence]
    return [re.sub(r"[^a-zA-Z ]", "", sentence) for sentence in sentences]

def text_of(soup):
    """
    Return the text associated to the BeautifulSoup.BeautifulSoup
    object `soup`.
    """
    return ''.join([str(x) for x in soup.findAll(text=True)])

def remove_spurious_words(text):
    """
    Return `text` with spurious words stripped.  For example, Google
    includes the word "Cached" in many search summaries, and this word
    should therefore mostly be ignored.
    """
    spurious_words = ["Cached", "Similar"]
    for word in spurious_words:
        text = text.replace(word, "")
    return text

def candidate_answers(sentence, query):
    """
    Return all the 1-, 2-, and 3-grams in `sentence`.  Terms appearing
    in `query` are filtered out.  Note that the n-grams are returned
    as a list of tuples.  So a 1-gram is a tuple with 1 element, a
    2-gram is a tuple with 2 elements, and so on.
    """
    filtered_sentence = [word for word in sentence.split() 
                         if word.lower() not in query]
    return sum([ngrams(filtered_sentence, j) for j in range(1,4)], [])

def ngrams(words, n=1):
    """
    Return all the `n`-grams in the list `words`.  The n-grams are
    returned as a list of tuples, each tuple containing an n-gram, as
    per the description in `candidate_answers`.
    """
    return [tuple(words[j:j+n]) for j in xrange(len(words)-n+1)]

def ngram_score(ngram, score):
    """
    Return the score associated to `ngram`.  The base score is
    `score`, but it's modified by a factor which is
    `CAPITALIZATION_FACTOR` to the power of the number of capitalized
    words.  This biases answers toward proper nouns.
    """
    num_capitalized_words = sum(
        1 for word in ngram if is_capitalized(word)) 
    return score * (CAPITALIZATION_FACTOR**num_capitalized_words)

def is_capitalized(word):
    """
    Return True or False according to whether `word` is capitalized.
    """
    return word == word.capitalize()

def wolfram_qa(question):
    """
    Return Wolfram Alpha's answer to `question`.  Caches results to
    not overuse the Wolfram API.  Note that this is mainly a wrapper
    around `wolfram_qa_uncached`, and more information may be found in
    that docstring.
    """
    WOLFRAM_CACHE.key = question
    if WOLFRAM_CACHE.exists():
        return pickle.loads(WOLFRAM_CACHE.get_contents_as_string())
    else:
        result = wolfram_qa_uncached(question)
        WOLFRAM_CACHE.set_contents_from_string(pickle.dumps(result))
        return result

def wolfram_qa_uncached(question):
    """
    Return Wolfram Alpha's answer to `question`.  The answer is
    returned in plain text.  If there is no answer it returns None.
    """
    waeo = wolfram.WolframAlphaEngine(
        config.WOLFRAM_APPID, wolfram_server)
    query = waeo.CreateQuery(question)
    result = waeo.PerformQuery(query)
    waeqr = wolfram.WolframAlphaQueryResult(result)
    try:
        xml_pods = [ElementTree.fromstring(x) for x in waeqr.XMLPods()] 
    except UnicodeEncodeError:
        xml_pods = []
    try:
        primary_pods = [xml for xml in xml_pods 
                        if ("primary" in xml.attrib)
                        and (xml.attrib["primary"] == "true")]
        primary_pod = primary_pods[0]
        subpod = primary_pod.getchildren()[0]
        answer = subpod.getchildren()[0].text
        principle_line_of_answer = answer.split("\n")[0]
        rewritten_answer = re.sub("\|", "and", principle_line_of_answer)
        return " ".join(rewritten_answer.split())
    except IndexError:
        return None

def hybrid_qa(question):
    """
    Return an answer to `question` using a combination of Google
    search results and Wolfram Alpha.  The procedure is to query Alpha
    and use its answer, falling back to the highest-ranked result
    returned by `google_qa` if Alpha produces no results.  The answer
    is returned in plain text.
    """
    wolfram_answer = wolfram_qa(question)
    if wolfram_answer:
        return wolfram_answer
    else:
        return google_qa(question)[0][0]

if __name__ == "__main__":
    pretty_qa("Who ran the first four-minute mile?")
    pretty_qa("Who makes the best pizza in New York?")
    pretty_qa("Who invented the C programming language?")
    pretty_qa("Who wrote the Iliad?")
    pretty_qa("Who caused the financial crash of 2008?")
    pretty_qa("Who caused the Great Depression?")
    pretty_qa("Who is the most evil person in the world?")
    pretty_qa("Who wrote the plays of Wiliam Shakespeare?")
    pretty_qa("Who is the world's best tennis player?")
    pretty_qa("Who is the richest person in the world?")
