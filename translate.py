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
                if verbose:
                    print(f" reg", end="")
                if root != inf_fr: #it's listed
                    mode = feats['mode']
                    tense = feats['tense']
                    term = self.conj[mode][tense]
                    trans_word = root + term
                    if verbose:
                        print(f" {mode} {tense}", end="")
                else:
                    trans_word = word  
                
        else:
            trans_word = word

        if verbose:
            print(f") {word} -> {trans_word}")

        return trans_word
        

import spacy
from collections import OrderedDict

class TextSimplificator:
    def __init__(self, model="fr_dep_news_trf"):
        model = "fr_core_news_md"
        self.nlp = spacy.load(model)
    
    def simplify(self, text_file, verbose=False):
        # Read
        with open(text_file, 'r', encoding='utf‑8') as f:
            text = f.read()
        text = text.lower()
        lines = text.split("\n")
        
        lines_dict = []
        for line in lines:
            doc = self.nlp(line)
            od = OrderedDict()
            for token in doc:
                # Skip spaces if you want (or treat whitespace as you like)
                text = token.text
                lemma = token.lemma_
                pos = token.pos_  # Coarse POS
                
                morph = token.morph  # morphological features object
                # morph is not always present / might be empty
                
                simplified = self.simplify_feats(token, morph, verbose)
                
                od[text] = simplified
            lines_dict.append(od)
        
        return lines_dict
    
    def simplify_feats(self, token, morph, verbose = False):
        """
        Returns a dict like:
        {
            'lemma': ...,
            'pos': verb/noun/punc/misc,
            possibly mode, tense, number, etc.
        }
        """
        if verbose:
            print(f"{token}: {morph}")

        sfeats = {}
        sfeats['lemma'] = token.lemma_
        
        # default
        sfeats['pos'] = 'misc'
        
        # Verb / Aux handling
        if token.pos_ in ["VERB", "AUX"]:
            if verbose: print(" -> verb")
            # get the VerbForm feature
            verb_form = morph.get("VerbForm")[0]
            # Some tokens may not have VerbForm, handle missing
            if verb_form in ["Fin", "Inf"]: 
                if verbose: print(" -> known form") 
                sfeats['pos'] = 'verb'
                if verb_form == "Inf":
                    if verbose: print(" -> inf")
                    sfeats['mode'] = 'inf'
                else:
                    # finite verb: need mood, tense etc.
                    mood = morph.get("Mood")[0]
                    tense = morph.get("Tense")[0]
                    if verbose: print(f" -> {mood}, {tense}")
                    if mood:
                        sfeats['mode'] = mood.lower()
                    if tense:
                        if tense == "Pres":
                            tense = self.is_future(token.text)
                            if verbose and tense != "pres":
                                print(f" -> corrected as {tense}")
                        sfeats['tense'] = tense.lower()
            else:
                if verbose: print(" -> unknown form")
                # other forms (gerund, participle, etc.) → maybe misc or treat separately
                sfeats['pos'] = 'misc'
        
        # Noun handling
        elif token.pos_ == "NOUN":
            if verbose: print(" -> noun")
            sfeats['pos'] = 'noun'
            number = morph.get("Number")
            if number:
                sfeats['number'] = number[0].lower()
            else:
                sfeats['number'] = 'sing'  # default
        
        # Punctuation
        elif token.is_punct:
            if verbose: print(" -> punc")
            sfeats['pos'] = 'punc'
        
        
        # You might want pronouns, adjectives etc — you can expand similarly
        if verbose:
            print(f"extracted as: {sfeats}")
            print("")
        return sfeats

    def is_future(self, verb):
        term = {
            'rai': 1,
            'ras': 2,
            'ra': 3,
            'rons': 1,
            'rez': 2,
            'ront': 3
        }
        for t in term:
            if verb.endswith(t):
                return "fut"
        return "pres"
        
