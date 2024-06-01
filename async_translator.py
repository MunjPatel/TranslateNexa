import aiohttp
import random
import streamlit as st
import json
import time
import asyncio
import spacy
from bs4 import BeautifulSoup
from faker import Faker
from urllib.parse import quote

fake = Faker()

async def translate_text(session, user_text, target_language):
    url = "https://www.google.com/async/translate"
    quote_partial_payload = quote(f"{user_text}")
    payload = f'async=translate,sl:auto,tl:{target_language},st:' + quote_partial_payload + f",id:{random.randint(1,10000000)},qc:true,ac:false,_id:tw-async-translate,_pms:s,_fmt:pc"
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

    async with session.post(url, headers=headers, data=payload) as response:
        if response.status == 413:
            # Handle 413 error by reducing payload size
            half_length = len(user_text) // 2
            if half_length > 0:
                first_half = user_text[:half_length]
                second_half = user_text[half_length:]
                translated_first_half = await translate_text(session, first_half, target_language)
                translated_second_half = await translate_text(session, second_half, target_language)
                return translated_first_half + " " + translated_second_half
            else:
                return "Translation failed due to too large content."
        elif response.status == 200:
            response_text = await response.text()
            if response_text:
                response_soup = BeautifulSoup(response_text, 'html.parser')
                translated_text = response_soup.find('span', id='tw-answ-target-text').text
                return translated_text.replace("'", '').replace('"', '').strip()
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

st.set_page_config(page_title="TranslateNexa")

st.markdown("""
    <div style='text-align: center;'>
        <h3 style='color: grey;'>Google Translator Clone (with no limits)!</h3>
    </div>
    """, unsafe_allow_html=True)

hide_streamlit_style = """
<style>
#MainMenu { visibility: hidden; }
footer { visibility: hidden; }
</style>
"""
st.markdown(hide_streamlit_style, unsafe_allow_html=True)

async def translate_batch(session, batch, target_language):
    tasks = [translate_text(session, sentence, target_language) for sentence in batch]
    return await asyncio.gather(*tasks)

async def translate_sentences(sentences, target_language, progress_bar, progress_text, stats_text, batch_size):
    translated_sentences = []
    translation_output = ""
    start_time = time.time()
    total_tokens = 0
    total_requests = 0
    total_sentences_processed = 0

    async with aiohttp.ClientSession() as session:
        total = len(sentences)
        for i in range(0, total, batch_size):
            batch = sentences[i:i+batch_size]
            translated_batch = await translate_batch(session, batch, target_language)
            translated_sentences.extend(translated_batch)
            translation_output += " ".join(translated_batch) + " "
            
            # Update progress and stats
            elapsed_time = time.time() - start_time
            items_per_second = (i + len(batch)) / elapsed_time if elapsed_time > 0 else 0
            remaining_time = (total - (i + len(batch))) / items_per_second if items_per_second > 0 else 0
            progress = (i + len(batch)) / total
            progress_bar.progress(progress)
            progress_text.text(f"Translation Progress: {int(progress * 100)}%")

            total_tokens += sum(len(sentence.split()) for sentence in batch)
            total_requests += 1
            total_sentences_processed += len(batch)
            stats_text.markdown(f"**Speed:** {items_per_second:.2f} sentences/sec  \n**Total Number of Sentences Processed:** {total_sentences_processed}  \n**Batch Size Taken:** {batch_size} sentences/request  \n**Total Number of Requests Made:** {total_requests}")

    total_time = time.time() - start_time
    speed = len(sentences) / total_time if total_time > 0 else 0

    return translated_sentences, total_tokens, total_time, total_requests, speed, total_sentences_processed

with st.form('translator_form'):
    nlp = load_model("xx_sent_ud_sm")
    default_text = """AI-based text translation has revolutionized the way we communicate across languages. Leveraging advanced algorithms and machine learning techniques, AI translation systems can analyze and interpret text in one language and accurately translate it into another. These systems have significantly improved translation accuracy and efficiency, making cross-language communication more seamless and accessible than ever before. From translating business documents and technical manuals to facilitating multilingual conversations and global collaborations, AI-based text translation plays a crucial role in breaking down language barriers and promoting international understanding. Furthermore, AI-driven translation technologies continue to evolve rapidly, incorporating deep learning models, natural language processing (NLP), and neural networks to enhance translation quality and linguistic nuances. These advancements enable AI systems to handle complex sentences, idiomatic expressions, and cultural nuances with greater precision, resulting in more natural and contextually appropriate translations. As AI-based text translation continues to progress, it holds immense potential to bridge linguistic divides, facilitate global commerce, and foster cultural exchange on a global scale."""
    user_text = st.text_area("Input Text", height=150, value=default_text)
    with open("lang_codes.json", 'r') as codes:
        lang_codes = json.load(codes)
    shown_langs = tuple(lang for lang in lang_codes.keys())
    target_language = st.selectbox("Target Language", shown_langs)
    submit_button = st.form_submit_button("Translate")

    if submit_button:
        st.empty()  # Clear previous output

        if not user_text.strip():
            st.error("Please enter some input text!")
        else:
            doc = nlp(user_text)
            sentences = [sent.text for sent in doc.sents]

            # Dynamically determine batch size based on the length of the input text
            total_length = sum(len(sentence.split()) for sentence in sentences)
            batch_size = min(250, max(1, total_length // 50))  # Set upper limit for batch size to 250 sentences/request

            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            progress_bar = st.progress(0)
            progress_text = st.empty()
            stats_text = st.empty()
            translation_output = st.empty()

            try:
                translated_sentences, total_tokens, total_time, total_requests, speed, total_sentences_processed = loop.run_until_complete(
                    translate_sentences(sentences, lang_codes[target_language], progress_bar, progress_text, stats_text, batch_size=batch_size)
                )
                if translated_sentences:
                    translation_output.text_area("Translation Complete:", value=" ".join(translated_sentences), height=150)
            except Exception as e:
                st.error(f"Failed to translate! Error: {e}")
            finally:
                loop.close()
