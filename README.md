# taletei_translator
A little automatic translator from french to my conlang, taletei.

## Usage

```
python -m translate.py <step nb> <source file>
```

The script executes in 2 steps, indicated by the <steb nb> argument. <source file> is the file containing the text you want to translate or transcribe.

## Step 1
Step 1 is the translation. It assumes the text is written in french using taletei grammar. It's able to detect conjugated verbs, plurals etc. and will accurately transcribed those in taletei (I mean it should... normally). Unknown words are just not translated and appear as their original version in the translation. 
It uses Spacy to infer information.

This step will automatically save the output to save.txt.

We assume users will want to fix and tweak the translation, replacing unknowm words etc. before continuing.

## Step 2
Step 2 is transcription, it takes a text written in taletei and reverses the syllables order, so that it ends up correct when using the taletei font.
Words with unknown letters/impossible combinations are skipped.
