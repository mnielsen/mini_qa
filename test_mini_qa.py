#### test_mini_qa.py
#
# By Michael Nielsen, 2012
#
# Test suite for mini_qa.py

from mini_qa import *

failed_tests = 0

def test(code, result=None):
    print
    print "Testing: "+code
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

test("ngram_score(('Hello', 'there'), 7)", "21")

test("is_capitalized('Hello')", "True")

test("is_capitalized('hello')", "False")

finish_test()
