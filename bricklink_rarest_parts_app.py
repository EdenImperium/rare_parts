
import streamlit as st
import pandas as pd
import time
import requests
from requests_oauthlib import OAuth1

st.set_page_config(page_title="BrickLink Rarest Parts Finder", layout="wide")

st.title("🔍 BrickLink Rarest Parts Finder")

st.markdown("Upload your BrickLink inventory CSV to find out which parts are the rarest (fewest sellers).")

# BrickLink API credentials
CONSUMER_KEY = st.secrets["CONSUMER_KEY"]
CONSUMER_SECRET = st.secrets["CONSUMER_SECRET"]
TOKEN_VALUE = st.secrets["TOKEN_VALUE"]
TOKEN_SECRET = st.secrets["TOKEN_SECRET"]

auth = OAuth1(CONSUMER_KEY, CONSUMER_SECRET, TOKEN_VALUE, TOKEN_SECRET)

@st.cache_data(show_spinner=False)
def search_part(part_name):
    search_url = f"https://www.bricklink.com/v1/search/data?query={part_name}"
    response = requests.get(search_url, auth=auth)
    if response.status_code == 200:
        results = response.json().get('data', [])
        if results:
            return results[0].get('no'), results[0].get('type')
    return None, None

@st.cache_data(show_spinner=False)
def get_seller_count(part_num, part_type, condition='U'):
    guide_url = f"https://api.bricklink.com/api/store/v1/items/{part_type}/{part_num}/price"
    params = {
        'guide_type': 'stock',
        'new_or_used': condition,
    }

    response = requests.get(guide_url, params=params, auth=auth)
    if response.status_code == 200:
        data = response.json().get('data', {})
        return data.get('total_quantity', 0), data.get('total_lots', 0)
    return None, None

uploaded_file = st.file_uploader("📄 Upload your BrickLink inventory CSV", type="csv")

if uploaded_file:
    df = pd.read_csv(uploaded_file)
    df.dropna(subset=['Description'], inplace=True)
    st.success(f"Loaded {len(df)} rows from your inventory.")

    progress = st.progress(0)
    results = []
    seen = set()

    for idx, row in enumerate(df.itertuples(), 1):
        desc = row.Description
        color = row.Color
        condition = row.Condition
        key = f"{desc} ({color}) [{condition}]"

        if key in seen:
            progress.progress(idx / len(df))
            continue
        seen.add(key)

        part_num, part_type = search_part(desc)
        time.sleep(1)

        if not part_num or not part_type:
            progress.progress(idx / len(df))
            continue

        qty, sellers = get_seller_count(part_num, part_type, condition='N' if condition == 'New' else 'U')
        time.sleep(1)

        results.append({
            'Description': desc,
            'Color': color,
            'Condition': condition,
            'Part Number': part_num,
            'Type': part_type,
            'Sellers': sellers if sellers is not None else 'N/A',
            'Quantity Available': qty if qty is not None else 'N/A'
        })
        progress.progress(idx / len(df))

    result_df = pd.DataFrame(results)
    st.markdown("### 📊 Rarest Parts")
    st.dataframe(result_df.sort_values(by="Sellers", na_position='last'))

    csv = result_df.to_csv(index=False).encode('utf-8')
    st.download_button("📥 Download Results as CSV", data=csv, file_name="rarest_parts.csv", mime='text/csv')
