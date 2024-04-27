import random
import streamlit as st
import requests as re
import json

from bs4 import BeautifulSoup
from faker import Faker
from urllib.parse import quote

fake = Faker()

def translate_text(user_text, target_language):
    try:
        url = "https://www.google.com/async/translate"

        quote_partial_payload = quote(f"{user_text}")
        payload = f'async=translate,sl:auto,tl:{target_language},st:'+quote_partial_payload+f",id:{random.randint(1,10000000)},qc:true,ac:false,_id:tw-async-translate,_pms:s,_fmt:pc"
        headers = {
        'accept': '*/*',
        'accept-language': 'en-US,en;q=0.9',
        'content-type': 'application/x-www-form-urlencoded;charset=UTF-8',
        'origin': 'https://www.google.com',
        'priority': 'u=1, i',
        'referer': 'https://www.google.com/',
        'sec-fetch-dest': 'empty',
        'sec-fetch-mode': 'cors',
        'sec-fetch-site': 'same-origin',
        'user-agent': f"{fake.user_agent()}",
        'x-dos-behavior': 'Embed',
        }

        response = re.request("POST", url, headers=headers, data=payload)
        response_text = response.text
        response_soup = BeautifulSoup(response_text, 'html.parser')
        translated_text = response_soup.find('span', id = 'tw-answ-target-text').text
        return translated_text
    except Exception as e:
        return ""

st.markdown("""
    <div style='text-align: center;'>
        <img src='https://www.edgemiddleeast.com/cloud/2023/08/08/9dCrm2UL-Gen-AI-1200x800.jpg' 
             style='width: 300px; height: 300px; object-fit: cover; border-radius: 50%; margin-top: 20px;'>
        <h3 style='color: grey;'>AI Translator</h3>
    </div>
    """, unsafe_allow_html=True)

# Add CSS to hide Streamlit elements
hide_streamlit_style = """
<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)
  
with st.form('translator_form'):
    default_text = """AI-based text translation has revolutionized the way we communicate across languages. Leveraging advanced algorithms and machine learning techniques, AI translation systems can analyze and interpret text in one language and accurately translate it into another. These systems have significantly improved translation accuracy and efficiency, making cross-language communication more seamless and accessible than ever before. From translating business documents and technical manuals to facilitating multilingual conversations and global collaborations, AI-based text translation plays a crucial role in breaking down language barriers and promoting international understanding. Furthermore, AI-driven translation technologies continue to evolve rapidly, incorporating deep learning models, natural language processing (NLP), and neural networks to enhance translation quality and linguistic nuances. These advancements enable AI systems to handle complex sentences, idiomatic expressions, and cultural nuances with greater precision, resulting in more natural and contextually appropriate translations. As AI-based text translation continues to progress, it holds immense potential to bridge linguistic divides, facilitate global commerce, and foster cultural exchange on a global scale.
    """
    user_text = st.text_area("Input Text", height = 100, value = default_text)
    with open("lang_codes.json",'r') as codes:
        lang_codes = json.load(codes)
    shown_langs = tuple([lang for lang in lang_codes.keys()])
    target_language = st.selectbox("Target Language",shown_langs)
    submit_button = st.form_submit_button("Translate")
    if not user_text:
        st.error("Please enter some input text!")
    if user_text and target_language:
        if submit_button:
            with st.spinner("Translating..."):
                translated_text = translate_text(user_text, lang_codes[target_language])
                if translated_text == "":
                    st.error('Failed to translate text!')
                else:
                    st.write(translated_text)