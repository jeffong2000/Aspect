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
import matplotlib.pyplot as plt
import numpy as np
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
    ## Adjectival Complement - A is a child of something with relationship of nsubj, while
    ## M is a child of the same something with relationship of acomp

    rule2_pairs = []

    for token in doc:

        children = token.children
        A = "999999"
        M = "999999"
        add_neg_pfx = False
        for child in children :
            if(child.dep_ == "nsubj" and not child.is_stop):
                A = child.text


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


        if(A != "999999" and M != "999999"):
            rule2_pairs.append((A, M, sid.polarity_scores(M)['compound'],3))

    ## THIRD RULE OF DEPENDANCY PARSE -
    ## M - Sentiment modifier || A - Aspect

    #Adverbial modifier to a passive verb - A is a child of something with relationship of nsubjpass, while
    # M is a child of the same something with relationship of advmod
    #Assumption - A verb will have only one NSUBJ and DOBJ

    rule3_pairs = []
    for token in doc:


        children = token.children
        A = "999999"
        M = "999999"
        add_neg_pfx = False
        for child in children :
            if((child.dep_ == "nsubjpass" or child.dep_ == "nsubj") and not child.is_stop):
                A = child.text


            if(child.dep_ == "advmod" and not child.is_stop):
                M = child.text
                M_children = child.children
                for child_m in M_children:
                    if(child_m.dep_ == "advmod"):
                        M_hash = child_m.text
                        M = M_hash + " " + child.text
                        break
  

            if(child.dep_ == "neg"):
                neg_prefix = child.text
                add_neg_pfx = True

        if (add_neg_pfx and M != "999999"):
            M = neg_prefix + " " + M

        if(A != "999999" and M != "999999"):
            rule3_pairs.append((A, M,sid.polarity_scores(M)['compound'],4)) # )
    aspects = []

    aspects = rule1_pairs + rule2_pairs + rule3_pairs 

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
model = pickle.load(open('ABSAModel.pkl','rb'))
st.set_page_config(layout="centered")
st.title("Web Based Aspect-based sentiment analysis for earphone and headset")
st.subheader("Aspect-based sentiment analysis by review")
input = st.text_input("Enter the review you want")
result = model.predict([input])
btn = st.button("Predict")

if btn:
  st.subheader("Aspect extracted:")
  dic = (apply_extraction(input,nlp,sid)) #Dependency parsing
  for i in dic['aspect_pairs']:
    if(i[0] in ["item","items","quality","sound","soundquality","design","product","connection","looking","call","headphone","headphones","earphone","earphones",
                  "overall","earpiece","looks","battery","soundclarity","features","feature(s","feature","performance","paired","headset","headsets"
                "pairing","something","volume","version","earbuds","earbud","soundeffect","effect","playing","control","cast","voice","material","piece",
                "batterydrain","mic","color","colour","colors","colours","job","jbl","love","casing","use","usage","cover","bluetooth","clarity","range",
                "soundrange","batch","recommend","texture","portability","case","audio","system","device","volume","earbuds","bass","pitch","tone","noisecancellation","microphone","grade","experience",
                "delivery","deliveryquality","time","deliverytime","condition","receive","received","packed","packing","package","shipping","value","price","buy","purchase","order","deal",
                "service","staff","seller","reply","follow","followup","gift",'coordinating']):
      
          st.subheader(i[0]+"\t|\t"+i[1])
  st.markdown("###")
  col1, col2, col3,col4 = st.columns(4)
  for res in result:
    col1.metric("Product quality", res[0])
    col2.metric("Price", res[1])
    col3.metric("Service quality", res[2])
    col4.metric("Delivery quality", res[3])
  st.success("Aspect and sentiment is found")
st.write("")
st.markdown("***")
st.write("")
st.write("")
st.subheader("Ecommerce performance analysis in every aspect")
uploaded_file = st.file_uploader("Upload the review dataset")
click = st.button("Extract")
if uploaded_file is not None:
  if click:
    test = pd.read_csv(uploaded_file,on_bad_lines='skip', encoding= 'unicode_escape',delimiter=';')
    pred = model.predict(test.iloc[:,0].to_numpy())
    pred = pd.DataFrame(pred, columns = ['Product quality','Price','Service Quality','Delivery quality'])
    pred.insert(0,"Review",test.iloc[:,0].to_numpy())
    col1,col2,col3,col4 = st.columns(4)
    with col1:
        count= pred['Product quality'].value_counts().drop("-")
        colours = {'Positive': 'green', 'Negative': 'red','Neutral': 'grey'}
        labels = count.index.tolist()
        count.plot(kind='pie',autopct='%1.2f%%',colors=[colours[key] for key in labels])
        plt.title("Polarity of Product quality Aspect")
        plt.legend()
        st.set_option('deprecation.showPyplotGlobalUse', False)
        st.pyplot()
    with col2:
        count= pred['Price'].value_counts().drop("-")
        colours = {'Positive': 'green', 'Negative': 'red','Neutral': 'grey'}
        labels = count.index.tolist()
        count.plot(kind='pie',autopct='%1.2f%%',colors=[colours[key] for key in labels])
        plt.title("Polarity of Price Aspect")
        plt.legend()
        st.set_option('deprecation.showPyplotGlobalUse', False)
        st.pyplot()
    with col3: 
        count= pred['Service Quality'].value_counts().drop("-")
        colours = {'Positive': 'green', 'Negative': 'red','Neutral': 'grey'}
        labels = count.index.tolist()
        count.plot(kind='pie',autopct='%1.2f%%',colors=[colours[key] for key in labels])
        plt.title("Polarity of Service Quality Aspect")
        plt.legend()
        st.set_option('deprecation.showPyplotGlobalUse', False)
        st.pyplot()
    with col4:
        count= pred['Delivery quality'].value_counts().drop("-")
        colours = {'Positive': 'green', 'Negative': 'red','Neutral': 'grey'}
        labels = count.index.tolist()
        count.plot(kind='pie',autopct='%1.2f%%',colors=[colours[key] for key in labels])
        plt.title("Polarity of Delivery Aspect")
        plt.legend()
        st.set_option('deprecation.showPyplotGlobalUse', False)
        st.pyplot()
    st.success("Analysis successful")
    st.dataframe(pred,width=1024, height=768)


