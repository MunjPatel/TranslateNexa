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

# Initialize global variables
fake = Faker()
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

async def translate_text(session, user_text, target_language):
    url = "https://www.google.com/async/translate"
    quote_partial_payload = quote(f"{user_text}")
    payload = f'async=translate,sl:auto,tl:{target_language},st:' + quote_partial_payload + f",id:{random.randint(1,10000000)},qc:true,ac:false,_id:tw-async-translate,_pms:s,_fmt:pc"
    
    async with session.post(url, headers=headers, data=payload) as response:
        if response.status == 413:
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
                # Fix the extraction by correctly targeting the span element containing translation
                translated_span = response_soup.find('span', id='tw-answ-target-text')
                if translated_span:
                    translated_text = translated_span.text
                    return translated_text.replace("'", '').replace('"', '').strip()
                else:
                    return "An error occurred while extracting translation text."
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

st.set_page_config(page_title="TranslateNexa 🚀", page_icon="🌍")

# Header with emojis
st.markdown("""
    <div style='text-align: center;'>
        <h3 style='color: #6C757D;'>🌍✨ Google Translator Clone (with no limits)! ✨🌍</h3>
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
    start_time = time.time()

    async with aiohttp.ClientSession() as session:
        total = len(sentences)
        for i in range(0, total, batch_size):
            batch = sentences[i:i+batch_size]
            translated_batch = await translate_batch(session, batch, target_language)
            translated_sentences.extend(translated_batch)

            # Update UI
            elapsed_time = time.time() - start_time
            items_per_second = (i + len(batch)) / elapsed_time if elapsed_time > 0 else 0
            progress = (i + len(batch)) / total
            progress_bar.progress(progress)
            progress_text.text(f"⏳ Translation Progress: {int(progress * 100)}%")

            stats_text.markdown(f"🚀 **Speed:** {items_per_second:.2f} sentences/sec  \n"
                                f"💬 **Total Number of Sentences Processed:** {i + len(batch)}  \n"
                                f"📦 **Batch Size Taken:** {batch_size} sentences/request  \n"
                                f"📝 **Total Number of Requests Made:** {(i // batch_size) + 1}")

    total_time = time.time() - start_time
    speed = len(sentences) / total_time if total_time > 0 else 0
    return translated_sentences, total_time, speed

# Initialize session state if not already done
if 'user_text' not in st.session_state:
    st.session_state['user_text'] = ""
if 'target_languages' not in st.session_state:
    st.session_state['target_languages'] = []

# Function to clear input and output fields
def clear_text():
    st.session_state['user_text'] = ""
    st.session_state['target_languages'] = []

nlp = load_model("xx_sent_ud_sm")

with st.form('translator_form'):
    user_text = st.text_area("✍️ Input Text", height=150, value=st.session_state['user_text'], key="user_text")
    with open("lang_codes.json", 'r') as codes:
        lang_codes = json.load(codes)
    shown_langs = tuple(lang for lang in lang_codes.keys())
    target_languages = st.multiselect("🌐 Target Languages", shown_langs, max_selections=2, key="target_languages")
    
    col1, col2 = st.columns([1, 1])  # Two equal-width columns
    with col1:
        submit_button = st.form_submit_button("✨ Translate 🚀")
    with col2:
        clear_button = st.form_submit_button("🧹 Clear Text", on_click=clear_text, use_container_width=True)

    if submit_button:
        st.empty()  # Clear previous output

        if not user_text.strip():
            st.error("⚠️ Please enter some input text!")
        elif not target_languages:
            st.error("⚠️ Please select at least one target language!")
        else:
            doc = nlp(user_text)
            sentences = [sent.text for sent in doc.sents]

            total_length = sum(len(sentence.split()) for sentence in sentences)
            batch_size = min(250, max(1, total_length // 50))

            columns = st.columns(len(target_languages))
            progress_bars = {lang: columns[i].progress(0) for i, lang in enumerate(target_languages)}
            progress_texts = {lang: columns[i].empty() for i, lang in enumerate(target_languages)}
            stats_texts = {lang: columns[i].empty() for i, lang in enumerate(target_languages)}
            translation_outputs = {lang: columns[i].empty() for i, lang in enumerate(target_languages)}

            # Wrapper to run the async translation inside Streamlit
            async def translate_all_languages():
                tasks = []
                for lang in target_languages:
                    tasks.append(
                        translate_sentences(
                            sentences, lang_codes[lang], progress_bars[lang], progress_texts[lang], stats_texts[lang], batch_size=batch_size
                        )
                    )
                return await asyncio.gather(*tasks)

            # Run the async function using asyncio.run()
            try:
                all_results = asyncio.run(translate_all_languages())
                for i, lang in enumerate(target_languages):
                    translated_sentences, total_time, speed = all_results[i]
                    progress_texts[lang].text(f"✅ Translation Progress: 100%")
                    stats_texts[lang].markdown(
                        f"🚀 **Speed:** {speed:.2f} sentences/sec  \n"
                        f"💬 **Total Number of Sentences Processed:** {len(sentences)}  \n"
                        f"📦 **Batch Size Taken:** {batch_size} sentences/request  \n"
                        f"⏱ **Total Execution Time:** {total_time:.2f} seconds"
                    )
                    if translated_sentences:
                        translation_outputs[lang].text_area(f"🌍 Translation Complete ({lang}):", value=" ".join(translated_sentences), height=150)
            except Exception as e:
                st.error(f"❌ Failed to translate! Error: {e}")
