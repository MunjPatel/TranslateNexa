import aiohttp
import random
import streamlit as st
import requests as re
import json
import asyncio
import spacy
import subprocess

from bs4 import BeautifulSoup
from tqdm import tqdm
from faker import Faker
from urllib.parse import quote
# from asyncio import WindowsSelectorEventLoopPolicy

fake = Faker()
# if asyncio.get_event_loop_policy() is not WindowsSelectorEventLoopPolicy:
#     asyncio.set_event_loop_policy(WindowsSelectorEventLoopPolicy())

async def translate_text(user_text, target_language):
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

    async with aiohttp.ClientSession() as session:
        async with session.post(url, headers=headers, data=payload) as response:
            if response.status == 200:
                response_text = await response.text()
                if response_text != "":
                    response_soup = BeautifulSoup(response_text, 'html.parser')
                    translated_text = response_soup.find('span', id = 'tw-answ-target-text').text
                    return translated_text.replace("'",'').replace('"','').strip()  # Clean translated text
                else:
                    return "An error occurred while parsing the response."
            else:
                return f"Translation failed with status code: {response.status}"
            

@st.cache_resource
def load_model(model_name):
    try:
        nlp = spacy.load(model_name)
        nlp.add_pipe('sentencizer')
        return nlp
    except OSError:
        raise 

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

# async def translate_sentences(sentences, target_language):
#     translated_sentences = []
#     async with aiohttp.ClientSession() as session:
#         for sentence in tqdm(sentences):
#             translated_text = await translate_text(sentence, target_language)
#             translated_sentences.append(translated_text)
#     return translated_sentences

async def translate_sentences(sentences, target_language, progress_bar, progress_text):
    translated_sentences = []
    async with aiohttp.ClientSession() as session:
        total = len(sentences)
        for i, sentence in enumerate(sentences):
            translated_text = await translate_text(sentence, target_language)
            translated_sentences.append(translated_text)
            progress = (i + 1) / total
            progress_bar.progress(progress)
            progress_text.text(f"Translation Progress: {int(progress * 100)}%")
    return translated_sentences

with st.form('translator_form'):
    nlp = load_model("xx_ent_wiki_sm")
    default_text = """AI-based text translation has revolutionized the way we communicate across languages. Leveraging advanced algorithms and machine learning techniques, AI translation systems can analyze and interpret text in one language and accurately translate it into another. These systems have significantly improved translation accuracy and efficiency, making cross-language communication more seamless and accessible than ever before. From translating business documents and technical manuals to facilitating multilingual conversations and global collaborations, AI-based text translation plays a crucial role in breaking down language barriers and promoting international understanding. Furthermore, AI-driven translation technologies continue to evolve rapidly, incorporating deep learning models, natural language processing (NLP), and neural networks to enhance translation quality and linguistic nuances. These advancements enable AI systems to handle complex sentences, idiomatic expressions, and cultural nuances with greater precision, resulting in more natural and contextually appropriate translations. As AI-based text translation continues to progress, it holds immense potential to bridge linguistic divides, facilitate global commerce, and foster cultural exchange on a global scale."""
    user_text = st.text_area("Input Text", height=100, value=default_text)
    with open("lang_codes.json", 'r') as codes:
        lang_codes = json.load(codes)
    shown_langs = tuple(lang for lang in lang_codes.keys())
    target_language = st.selectbox("Target Language", shown_langs)
    submit_button = st.form_submit_button("Translate")

    # Clear previous translation results when a new translation starts
    translation_output = st.empty()  # Create an empty widget for displaying translation results

    if submit_button:
        if not user_text:
            st.error("Please enter some input text!")
        else:
            doc = nlp(user_text)
            sentences = [sent.text for sent in doc.sents]
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            progress_bar = st.progress(0)
            progress_text = st.empty()  # Create an empty widget for displaying progress text
            translated_sentences_task = loop.create_task(translate_sentences(sentences.copy(), lang_codes[target_language], progress_bar, progress_text))
            translation_output.text("Translating... Please wait.")  # Set a placeholder text while translating

            try:
                translated_sentences = loop.run_until_complete(translated_sentences_task)
                if translated_sentences:
                    translated_text = " ".join(translated_sentences)
                    translation_output.success("Translation Complete:")
                    translation_output.write(translated_text)
                else:
                    translation_output.error("Failed to translate!")
            finally:
                loop.close()
                progress_text.empty()  # Clean up the text widget