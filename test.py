"""
test.py
~~~~~~~~~~~~~~~

Test suite.
"""

from evaluation import *
from mini_qa import *

# Standard library
import json
import traceback

failed_tests = 0

def test(code, result=None):
    global failed_tests
    print "\nTesting: "+code
    if result: print "Expecting: "+result
    print "Output: %s" % eval(code)
    if result:
        print eval(result)
        if eval(code) == eval(result):
            print "Test passed"
        else:
            print "Test failed"
            failed_tests += 1

def finish_test():
    print "\n\nNUMBER OF FAILED TESTS: %s\n\n" % failed_tests

test("tokenize(\"Who is the world\'s    no. 1 tennis player?\")",
     "['who', 'is', 'the', 'worlds', 'no', '1', 'tennis', 'player']")

test("remove_spurious_words('This is a Cached version of something Similar to a regular sentence')", 
     "'This is a  version of something  to a regular sentence'")

test("candidate_answers('The quick brown fox jumped over the lazy grey dogs', ('brown', 'dogs'))", 
     "[('The',), ('quick',), ('fox',), ('jumped',), ('over',), ('the',), ('lazy',), ('grey',), ('The', 'quick'), ('quick', 'fox'), ('fox', 'jumped'), ('jumped', 'over'), ('over', 'the'), ('the', 'lazy'), ('lazy', 'grey'), ('The', 'quick', 'fox'), ('quick', 'fox', 'jumped'), ('fox', 'jumped', 'over'), ('jumped', 'over', 'the'), ('over', 'the', 'lazy'), ('the', 'lazy', 'grey')]")

test("ngrams(['the', 'quick', 'brown'], 2)", 
     "[('the', 'quick'), ('quick', 'brown')]")

# In the following, only evaluate to 1 decimal place.  Using floats
# the test may not pass, because of the ambiguities of floating point
# arithmetic
test("int(ngram_score(('Hello', 'there'), 7)*10)/10.0", 
     "%s" % (int(7 *CAPITALIZATION_FACTOR*10)/10.0))

test("is_capitalized('Hello')", "True")

test("is_capitalized('hello')", "False")

def test_qa_pairs():
    """
    Count the number of question-answer pairs in the qa_pairs.json
    file.
    """
    f = open("qa_pairs.json")
    qa_pairs = json.load(f)
    f.close()
    return len(qa_pairs)


try:
    print "\nTesting whether the qa_pairs.json file parses"
    print "Number of evaluation question-answer pairs is %s" % test_qa_pairs()
except:
    print "Test failed"
    traceback.print_exc()
    failed_tests += 1

finish_test()
