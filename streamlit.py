# -*- coding: utf-8 -*-
"""streamlit.ipynb

Automatically generated by Colaboratory.

Original file is located at
    https://colab.research.google.com/drive/1zHu3gjaJEWCzcPZIazT0Ciq5xEChIpjD
"""

import streamlit as st
import pickle
import pandas as pd
import nltk
import spacy
from nltk.sentiment.vader import SentimentIntensityAnalyzer
import pkg_resources
from symspellpy import SymSpell, Verbosity
nltk.download('vader_lexicon')

def clean_data(df):

    pd.options.mode.chained_assignment = None

    print("******Cleaning Started*****")

    print(f'Shape of df before cleaning : {df.shape}')
    df = df[df['Review'].notna()]
    df['Review'] = df['Review'].str.replace("<br />", " ")
    df['Review'] = df['Review'].str.replace("\[?\[.+?\]?\]", " ")
    df['Review'] = df['Review'].str.replace("\/{3,}", " ")
    df['Review'] = df['Review'].str.replace("\&\#.+\&\#\d+?;", " ")
    df['Review'] = df['Review'].str.replace("\d+\&\#\d+?;", " ")
    df['Review'] = df['Review'].str.replace("\&\#\d+?;", " ")
    # df['Review'] = df['Review'].str.replace("\d+", "")
    # df['Review'] = df['Review'].str.replace("pros:", "")
    # df['Review'] = df['Review'].str.replace(".pros:", "")  
    # df['Review'] = df['Review'].str.replace(".pros", "")    
    df['Review'] = df['Review'].str.replace("sound quality", "soundquality")
    df['Review'] = df['Review'].str.replace("delivery quality", "deliveryquality")
    df['Review'] = df['Review'].str.replace("noise cancellation", "noisecancellation")
    df['Review'] = df['Review'].str.replace("battery life", "batterylife")
    df['Review'] = df['Review'].str.replace("product quality", "productquality")
    df['Review'] = df['Review'].str.replace("doesn't", "does not")
    df['Review'] = df['Review'].str.replace("don't", "do not")
    df['Review'] = df['Review'].str.replace("n't", "not")
    df['Review'] = df['Review'].str.replace("\n", " ")
    df['Review'] = df['Review'].str.replace(".", " ")
    #facial expressions
    df['Review'] = df['Review'].str.replace("\:\|", "")
    df['Review'] = df['Review'].str.replace("\:\)", "")
    df['Review'] = df['Review'].str.replace("\:\(", "")
    df['Review'] = df['Review'].str.replace("\:\/", "")
    #replace multiple spaces with single space
    df['Review'] = df['Review'].str.replace("\s{2,}", " ")

    df['Review'] = df['Review'].str.lower()
    print(f'Shape of df after cleaning : {df.shape}')
    print("******Cleaning Ended*****")


    return(df)

prod_pronouns = ['it','this','they','these']


#Dependency parser
def apply_extraction(row,nlp,sid):

    

    doc=nlp(row)


    ## FIRST RULE OF DEPENDANCY PARSE -
    ## M - Sentiment modifier || A - Aspect
    ## RULE = M is child of A with a relationshio of amod
    rule1_pairs = []
    for token in doc:
        A = "999999"
        M = "999999"
        if token.dep_ == "amod" and not token.is_stop:
            M = token.text
            A = token.head.text

            # add adverbial modifier of adjective (e.g. 'most comfortable headphones')
            M_children = token.children
            for child_m in M_children:
                if(child_m.dep_ == "advmod"):
                    M_hash = child_m.text
                    M = M_hash + " " + M
                    break

            # negation in adjective, the "no" keyword is a 'det' of the noun (e.g. no interesting characters)
            A_children = token.head.children
            for child_a in A_children:
                if(child_a.dep_ == "det" and child_a.text == 'no'):
                    neg_prefix = 'not'
                    M = neg_prefix + " " + M
                    break

        if(A != "999999" and M != "999999"):
            rule1_pairs.append((A, M,sid.polarity_scores(token.text)['compound'],1))

    ## SECOND RULE OF DEPENDANCY PARSE -
    ## M - Sentiment modifier || A - Aspect
    #Direct Object - A is a child of something with relationship of nsubj, while
    # M is a child of the same something with relationship of dobj
    #Assumption - A verb will have only one NSUBJ and DOBJ

    rule2_pairs = []
    for token in doc:
        children = token.children
        A = "999999"
        M = "999999"
        add_neg_pfx = False
        for child in children :
            if(child.dep_ == "nsubj" and not child.is_stop):
                A = child.text
                # check_spelling(child.text)

            if((child.dep_ == "dobj" and child.pos_ == "ADJ") and not child.is_stop):
                M = child.text
                #check_spelling(child.text)

            if(child.dep_ == "neg"):
                neg_prefix = child.text
                add_neg_pfx = True

    if (add_neg_pfx and M != "999999"):
        M = neg_prefix + " " + M

        if(A != "999999" and M != "999999"):
            rule2_pairs.append((A, M,sid.polarity_scores(M)['compound'],2))


    ## THIRD RULE OF DEPENDANCY PARSE -
    ## M - Sentiment modifier || A - Aspect
    ## Adjectival Complement - A is a child of something with relationship of nsubj, while
    ## M is a child of the same something with relationship of acomp
    ## Assumption - A verb will have only one NSUBJ and DOBJ
    ## "The sound of the speakers would be better. The sound of the speakers could be better" - handled using AUX dependency



    rule3_pairs = []

    for token in doc:

        children = token.children
        A = "999999"
        M = "999999"
        add_neg_pfx = False
        for child in children :
            if(child.dep_ == "nsubj" and not child.is_stop):
                A = child.text
                # check_spelling(child.text)

            if(child.dep_ == "acomp" and not child.is_stop):
                M = child.text

            # example - 'this could have been better' -> (this, not better)
            if(child.dep_ == "aux" and child.tag_ == "MD"):
                neg_prefix = "not"
                add_neg_pfx = True

            if(child.dep_ == "neg"):
                neg_prefix = child.text
                add_neg_pfx = True

        if (add_neg_pfx and M != "999999"):
            M = neg_prefix + " " + M
                #check_spelling(child.text)

        if(A != "999999" and M != "999999"):
            rule3_pairs.append((A, M, sid.polarity_scores(M)['compound'],3))

    ## FOURTH RULE OF DEPENDANCY PARSE -
    ## M - Sentiment modifier || A - Aspect

    #Adverbial modifier to a passive verb - A is a child of something with relationship of nsubjpass, while
    # M is a child of the same something with relationship of advmod

    #Assumption - A verb will have only one NSUBJ and DOBJ

    rule4_pairs = []
    for token in doc:


        children = token.children
        A = "999999"
        M = "999999"
        add_neg_pfx = False
        for child in children :
            if((child.dep_ == "nsubjpass" or child.dep_ == "nsubj") and not child.is_stop):
                A = child.text
                # check_spelling(child.text)

            if(child.dep_ == "advmod" and not child.is_stop):
                M = child.text
                M_children = child.children
                for child_m in M_children:
                    if(child_m.dep_ == "advmod"):
                        M_hash = child_m.text
                        M = M_hash + " " + child.text
                        break
                #check_spelling(child.text)

            if(child.dep_ == "neg"):
                neg_prefix = child.text
                add_neg_pfx = True

        if (add_neg_pfx and M != "999999"):
            M = neg_prefix + " " + M

        if(A != "999999" and M != "999999"):
            rule4_pairs.append((A, M,sid.polarity_scores(M)['compound'],4)) # )


    ## FIFTH RULE OF DEPENDANCY PARSE -
    ## M - Sentiment modifier || A - Aspect

    #Complement of a copular verb - A is a child of M with relationship of nsubj, while
    # M has a child with relationship of cop

    #Assumption - A verb will have only one NSUBJ and DOBJ

    rule5_pairs = []
    for token in doc:
        children = token.children
        A = "999999"
        buf_var = "999999"
        for child in children :
            if(child.dep_ == "nsubj" and not child.is_stop):
                A = child.text
                # check_spelling(child.text)

            if(child.dep_ == "cop" and not child.is_stop):
                buf_var = child.text
                #check_spelling(child.text)

        if(A != "999999" and buf_var != "999999"):
            rule5_pairs.append((A, token.text,sid.polarity_scores(token.text)['compound'],5))


    ## SIXTH RULE OF DEPENDANCY PARSE -
    ## M - Sentiment modifier || A - Aspect
    ## Example - "It ok", "ok" is INTJ (interjections like bravo, great etc)


    rule6_pairs = []
    for token in doc:
        children = token.children
        A = "999999"
        M = "999999"
        if(token.pos_ == "INTJ" and not token.is_stop):
            for child in children :
                if(child.dep_ == "nsubj" and not child.is_stop):
                    A = child.text
                    M = token.text
                    # check_spelling(child.text)

        if(A != "999999" and M != "999999"):
            rule6_pairs.append((A, M,sid.polarity_scores(M)['compound'],6))


    ## SEVENTH RULE OF DEPENDANCY PARSE -
    ## M - Sentiment modifier || A - Aspect
    ## ATTR - link between a verb like 'be/seem/appear' and its complement
    ## Example: 'this is garbage' -> (this, garbage)

    rule7_pairs = []
    for token in doc:
        children = token.children
        A = "999999"
        M = "999999"
        add_neg_pfx = False
        for child in children :
            if(child.dep_ == "nsubj" and not child.is_stop):
                A = child.text
                # check_spelling(child.text)

            if((child.dep_ == "attr") and not child.is_stop):
                M = child.text
                #check_spelling(child.text)

            if(child.dep_ == "neg"):
                neg_prefix = child.text
                add_neg_pfx = True

        if (add_neg_pfx and M != "999999"):
            M = neg_prefix + " " + M

        if(A != "999999" and M != "999999"):
            rule7_pairs.append((A, token.text,sid.polarity_scores(token.text)['compound'],7))



    aspects = []

    aspects = rule1_pairs + rule2_pairs + rule3_pairs +rule4_pairs +rule5_pairs + rule6_pairs + rule7_pairs

    # replace all instances of "it", "this" and "they" with "product"
    aspects = [(A,M,P,r) if A not in prod_pronouns else ("product",M,P,r) for A,M,P,r in aspects ]

    dic = { "aspect_pairs" : aspects}

    return dic

#SymSpell
sym_spell = SymSpell(max_dictionary_edit_distance=3)
dictionary_path = pkg_resources.resource_filename(
    "symspellpy", "frequency_dictionary_en_82_765.txt")
sym_spell.load_dictionary(dictionary_path, term_index=0, count_index=1)
def spell_check(aspect):
  suggestions = sym_spell.lookup(aspect, Verbosity.CLOSEST)
  for suggestion in suggestions:
      aspect = suggestion.term
      break;
  return aspect

#Main function
nlp = spacy.load('en_core_web_sm')
sid = SentimentIntensityAnalyzer()
model = pickle.load(open('aspectModel1.pkl','rb'))
st.title("Web Based Aspect-based sentiment analysis for earphone and headset")
input = st.text_input("Enter the review you want")
result = model.predict([input])
btn = st.button("Predict")
if btn:
  dic = (apply_extraction(input,nlp,sid)) #Dependency parsing
  # for x in dic['aspect_pairs']:
  #   corrected_aspect = spell_check(x[0])
  #   y = list(x)
  #   y[0]=corrected_aspect
  #   dic['aspect_pairs'][dic['aspect_pairs'].index(x)] = tuple(y)
  for i in dic['aspect_pairs']:
    if(i[0] in ["item","items","quality","sound","soundquality","design","product","connection","looking","call","headphone","headphones","earphone","earphones",
                  "overall","earpiece","looks","battery","soundclarity","features","feature(s","feature","performance","paired","headset","headsets"
                "pairing","something","volume","version","earbuds","earbud","soundeffect","effect","playing","control","cast","voice","material","piece",
                "batterydrain","mic","color","colour","colors","colours","job","jbl","love","casing","use","usage","cover","bluetooth","clarity","range",
                "soundrange","batch","recommend","texture","portability","case","audio","system","device","volume","earbuds","bass","pitch","tone","noisecancellation","microphone","grade","experience",
                "delivery","deliveryquality","time","deliverytime","condition","receive","received","packed","packing","package","shipping","value","price","buy","purchase","order","deal",
                "service","staff","seller","reply","follow","followup","gift",'coordinating']):
      
          st.subheader(i[0]+"\t|\t"+i[1])
  st.text(result)
col1, col2, col3,col4 = st.columns(4)
for res in result:
    col1.metric("Product quality", res[0])
    col2.metric("Price", res[1])
    col3.metric("Service quality", res[2])
    col4.metric("Delivery quality", res[3])
  st.success("Aspect and sentiment is found")
