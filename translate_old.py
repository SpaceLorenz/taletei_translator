import pandas as pd
import re

# TODO
# - expressions (en plusieurs mots)
# - pluriels

def get(dict, key):
    if key in dict.keys():
        if isinstance(dict[key], list):
            return dict[key][0]
        return dict[key]
    return key

class TaleteiTranslator:

    plural = "se"

    def __init__(self, from_fr = True):
        words = "mots.csv"
        verbs = "verbes-reg.csv"
        verbs_irr = "verbes-irr.csv"
        conj = "conj.csv"

        words = pd.read_csv(words, sep = ";", encoding='utf-8')
        words = words.fillna("")
        verbs = pd.read_csv(verbs, sep = ";", encoding='utf-8')
        verbs_irr = pd.read_csv(verbs_irr, sep = ";", encoding='utf-8')
        conj = pd.read_csv('conj.csv', sep = ";", encoding='utf-8')

        self.words_to_dict(words, from_fr)
        self.verbs_to_dict(verbs, conj, from_fr)
        self.verbs_irr_to_dict(verbs_irr)

        self.ts = TextSimplificator()


    def words_to_dict(self, words, from_fr):
        self.words_dict = {}
        for row in words.itertuples():
            if isinstance(row.fr, str) and " " in row.fr: # TODO: integrate support for expressions with multiple words
                continue
            inw = row.fr
            outw = row.tlt
            if not from_fr:
                inw = row.tlt
                outw = row.fr
            
            if inw in self.words_dict.keys():
                self.words_dict[inw] = self.words_dict[inw] + [outw]
            else:
                self.words_dict[inw] = [outw]
    
    def verbs_to_dict(self, verbs, conj, from_fr):
        conj.index = conj['temps']
        del conj['temps']
        self.conj = conj.to_dict(orient='dict')

        self.verbs_dict = {}
        for row in verbs.itertuples():
            if not isinstance(row.tlt, str): # nan or empty
                continue
            tlt_root = row.tlt[:-2]
            inv = row.fr
            outv = tlt_root
            if not from_fr:
                inv = tlt_root
                outv = row.fr

            self.verbs_dict[inv] = outv    
    
    def verbs_irr_to_dict(self, df):
        df.index = df['fr']
        del df['fr']
        self.verbs_irr = df.to_dict(orient='index')

    def clean_text(self, text):
        chars_to_remove = "\n,;:'"
        for c in chars_to_remove:
            text = [t.replace(c, "") for t in text]
        text = [t.lower() for t in text]
        return text        

    def translate_file(self, in_file, verbose = False):
        text = self.ts.simplify(in_file, verbose)
        if verbose:
            print("----------------------------------")
        recomp_txt = [list(d.keys()) for d in text]

        if verbose:
            print(f"Text to translate (cleaned:)\n{recomp_txt}")

        self.tlt_text = ""
        for line in text:
            for word in line.keys():
                tword = self.translate_word(word, line[word], verbose)
                self.tlt_text+= " " + tword
            self.tlt_text += "\n"
        self.tlt_text = self.post_clean(self.tlt_text)
        return self.tlt_text
    
    def post_clean(self, txt):
        rep = {
            "  ": " ",
            "\n ": "\n",
            " .": "."
        }
        for k, v in rep.items():
            txt = txt.replace(k, v)

        txt = re.sub(r"c(?!h)", "k", txt)
        return txt
    
    def translate_word(self, word, feats, verbose = False):
        """
        sfeats{
            lemma: lemma
            pos: verb, noun, punc or misc
            if verb:
                mode: inf, ind, imp, sub, cnd
                tense: pres, past, imp, fut, pqp (past-past)
            idf noun:
                number: plur or sing
        }
        """
        pos = feats['pos']
        if verbose:
            print(f"({pos}", end="")
        if pos == "misc" or pos == "punc":
            trans_word = get(self.words_dict, word)
            if trans_word == word and pos=="misc": # try the lemma
                trans_word = get(self.words_dict, feats['lemma'])

        elif pos == "noun":
            trans_word = get(self.words_dict, feats['lemma'])
            if feats['number'] == "plur" and trans_word != word:
                trans_word += TaleteiTranslator.plural

        elif pos == "verb":
            inf_fr = feats['lemma']
            #print(f"------ \n{inf_fr}\n{self.verbs_irr.keys()}\n ------")
            trans_dict = get(self.verbs_irr, inf_fr)
            if trans_dict != inf_fr: #it's in there
                mode = feats['mode']
                tense = feats['tense']
                key = mode + "-" + tense
                trans_word = trans_dict[key]
                if verbose:
                    print(f" irr, {mode} {tense} ", end="")
            else: #it's a regular verb
                root = get(self.verbs_dict, inf_fr)
                if root != inf_fr: #it's listed
                    mode = feats['mode']
                    tense = feats['tense']
                    term = self.conj[mode][tense]
                    trans_word = root + term
                else:
                    trans_word = word  
                if verbose:
                    print(f" reg, {mode} {tense}", end="")
        else:
            trans_word = word

        if verbose:
            print(f") {word} -> {trans_word}")

        return trans_word
        

import stanza
from collections import OrderedDict

class TextSimplificator:

    def __init__(self):
        #stanza.download("fr")  # only first time
        self.nlp = stanza.Pipeline("fr", processors="tokenize, mwt, pos, lemma")

    def simplify(self, text_file, verbose = False):
        text = ""
        with open(text_file, 'r') as f:
            text = f.read()
        text = text.lower()
        lines = text.split("\n")
        docs = [self.nlp(s) for s in lines]
        lines_dict = []
        for doc in docs:
            lines_dict.append(OrderedDict())
            for word in doc.iter_words():
                feats_str = word.feats  # e.g. "Mood=Ind|Number=Sing|Person=1|Tense=Imp|VerbForm=Fin"
                feats = {}
                if feats_str:
                    feats = dict(item.split("=") for item in feats_str.split("|"))
                    lines_dict[-1][word.text] = self.simplify_feats(word, feats)
                else:
                    lines_dict[-1][word.text] = {'pos':'punc'}
                if verbose:
                    print(f"{word.text}: {word.lemma} {word.feats}")
        return lines_dict

    def simplify_feats(self, word, feats):
        """
        sfeats{
            lemma: lemma
            pos: verb, noun, punc or misc
            if verb:
                mode: inf, ind, imp, sub, cnd
                tense: pres, past, imp, fut, pqp (past-past)
            idf noun:
                number: plur or sing
        }
        """
        sfeats = {}
        sfeats['lemma'] = word.lemma
        sfeats['pos'] = 'misc'
        if word.pos == "VERB":
            print(feats['VerbForm'])
        if word.upos == "VERB" or word.upos == "AUX" and (feats['VerbForm'] == "Fin" or feats['VerbForm'] == "Inf"): 
            sfeats['pos'] = 'verb'
            form = feats['VerbForm'] # garder si Fin ou Inf, transformer en mot misc si autre (parlé, parlant -> adjectifs en tlt)
            if form != "Inf":
                sfeats['mode'] = feats['Mood'].lower() # Ind, Imp, Sub, Cnd
                sfeats['tense'] = feats['Tense'].lower() # Pres, Past (passé simple), Imp (imparfait), Fut, Pqp (j'avais parlé)
            else:
                sfeats['mode'] = "inf"
        else:
            sfeats['pos'] = 'misc'
            if word.pos == "NOUN":
                sfeats['pos'] = "noun" #important bc they have a plural form
                sfeats['number'] = 'sing'
                if "Number" in feats.keys():
                    sfeats['number'] = feats['Number'].lower() # plur or sing
        return sfeats
