"""Apply the requested punctuation and citation cleanup to report prose."""
import re

DASHES=str.maketrans({'\u2013':'-','\u2014':'-'})
BRACKETED=re.compile(r'\[[^\[\]]*\]')

def clean_text(value):
    text=str(value).translate(DASHES)
    # Repeated removal also handles nested square brackets.
    while True:
        cleaned=BRACKETED.sub('',text)
        if cleaned==text:break
        text=cleaned
    text=text.replace('[','').replace(']','')
    text=re.sub(r'[ \t]+(?=[.,;:!?])','',text)
    return re.sub(r' {2,}',' ',text)
