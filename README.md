# About `mini_qa`

`mini_qa` is a toy question-answering program.  It uses Google to
attempt to answer questions of the form "Who... ?"

An example question is: "Who discovered relativity?"

The design is a toy version of the AskMSR system developed by
researchers at Microsoft Research.  The original paper is:

Brill, Lin, Banko, Dumais and Ng, "Data-Intensive Question
Answering" (2001).

I've described background to this program
[here](http://michaelnielsen.org/ddi/how-to-answer-a-question-v1/).

# Note on contributions and pull requests

Bug fixes are welcome.

This program is a toy, and I don't intend to add features, so won't
accept pull requests that add features.  But feel free to fork and add
features if you like --- the beauty of AskMSR is that it's an easy
system to extend.

If you have comments or suggestions about the style of the main
program (`mini_qa.py`), I'd like to hear them.  Leave them on the
issue tracker, or email me (mn@michaelnielsen.org).  By contast,
`test_mini_qa.py` is more of a quick-and-dirty kludge, so I'm not
looking for feedback on that code.
