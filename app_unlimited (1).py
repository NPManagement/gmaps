"""
Streamlit Web Interface - Google Maps Scraper
NO BS LIMITS - Scrape unlimited results!
"""

import asyncio
import platform

# FIX for Windows + Python 3.13 asyncio issue
if platform.system() == 'Windows':
    asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())

import streamlit as st
import pandas as pd
import sys
import os

# Add current directory to path
sys.path.insert(0, os.path.dirname(__file__))

# Import scraper functions
from gmaps_scraper import scrape_all, save_to_csv
import time
from datetime import datetime

# ============================================================================
# PAGE CONFIG
# ============================================================================

st.set_page_config(
    page_title="Google Maps Scraper - Unlimited",
    page_icon="🗺️",
    layout="wide",
    initial_sidebar_state="expanded"
)

# ============================================================================
# CUSTOM CSS
# ============================================================================

st.markdown("""
<style>
    .main {padding: 1rem;}
    .stButton>button {
        width: 100%;
        background: linear-gradient(90deg, #FF4B4B 0%, #FF6B6B 100%);
        color: white;
        border: none;
        padding: 0.75rem;
        font-size: 1.1rem;
        font-weight: bold;
        border-radius: 8px;
        cursor: pointer;
        transition: all 0.3s;
    }
    .stButton>button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 12px rgba(255,75,75,0.4);
    }
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .metric-value {
        font-size: 2.5rem;
        font-weight: bold;
        margin: 0.5rem 0;
    }
    .metric-label {
        font-size: 0.9rem;
        opacity: 0.9;
    }
    h1 {
        background: linear-gradient(90deg, #FF4B4B 0%, #FF6B6B 50%, #667eea 100%);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
        font-size: 3rem !important;
        font-weight: 900 !important;
    }
    .success-banner {
        background: linear-gradient(90deg, #56ab2f 0%, #a8e063 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 12px;
        text-align: center;
        font-size: 1.2rem;
        font-weight: bold;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.1);
    }
    .stTextArea textarea {
        font-family: 'Courier New', monospace;
        font-size: 1rem;
    }
</style>
""", unsafe_allow_html=True)

# ============================================================================
# SESSION STATE
# ============================================================================

if 'results' not in st.session_state:
    st.session_state.results = None
if 'scraping' not in st.session_state:
    st.session_state.scraping = False
if 'logs' not in st.session_state:
    st.session_state.logs = []

# ============================================================================
# HEADER
# ============================================================================

st.title("🗺️ Google Maps Scraper")
st.markdown("### **Unlimited Results | Full Contact Data | Zero Restrictions**")
st.markdown("---")

# ============================================================================
# SIDEBAR
# ============================================================================

with st.sidebar:
    st.header("⚙️ Settings")
    
    max_results = st.number_input(
        "Results per query",
        min_value=10,
        max_value=10000,
        value=500,
        step=50,
        help="NO LIMITS! Scrape as many as you want (100-10000 recommended)"
    )
    
    extract_contacts = st.checkbox(
        "Extract emails & social media",
        value=True,
        help="Visit websites to find contact information"
    )
    
    st.markdown("---")
    
    st.markdown("### 📊 What You'll Get")
    st.markdown("""
    **Per Query (~{}  results):**
    - ✅ Names & Addresses
    - ✅ Phone Numbers (~95%)
    - ✅ Websites (~60%)
    {}
    """.format(
        max_results,
        """- ✅ **Emails (~40%)**
    - ✅ **Instagram (~60%)**
    - ✅ **Facebook (~40%)**
    - ✅ **TikTok (~20%)**""" if extract_contacts else ""
    ))
    
    st.markdown("---")
    
    st.markdown("### ⏱️ Estimated Time")
    time_per_query = 3 if not extract_contacts else 8
    st.markdown(f"**~{time_per_query} min per query**")
    
    st.markdown("---")
    
    st.markdown("### 🎯 Tips")
    st.markdown("""
    - Start with 2-3 queries to test
    - Use format: `barbers in London`
    - Higher results = more time
    - Keep browser tab open
    """)

# ============================================================================
# MAIN CONTENT
# ============================================================================

col1, col2 = st.columns([3, 1])

with col1:
    st.header("📝 Search Queries")
    
    default_queries = """barbers in Southend-on-Sea
barbers in Chelmsford
barbers in Colchester"""
    
    queries_text = st.text_area(
        "Enter your searches (one per line)",
        value=default_queries,
        height=250,
        help="Each line = one search. Example: 'barbers in London'"
    )
    
    # Parse queries
    queries = [q.strip() for q in queries_text.split('\n') if q.strip() and not q.strip().startswith('#')]
    
    if queries:
        st.success(f"✅ **{len(queries)} queries ready** | Will scrape up to **{len(queries) * max_results}** businesses!")
    else:
        st.warning("⚠️ Add at least one search query")

with col2:
    st.header("🚀 Control")
    
    # Start button
    start_disabled = len(queries) == 0 or st.session_state.scraping
    
    if st.button("▶️ START SCRAPING", disabled=start_disabled, type="primary"):
        st.session_state.scraping = True
        st.session_state.logs = []
        st.rerun()
    
    if st.session_state.results is not None:
        if st.button("🗑️ Clear Results"):
            st.session_state.results = None
            st.session_state.logs = []
            st.rerun()
    
    st.markdown("---")
    
    if st.session_state.scraping:
        st.markdown("### 🔄 Status")
        st.markdown("**SCRAPING...**")
        st.spinner("Processing...")

# ============================================================================
# SCRAPING LOGIC
# ============================================================================

if st.session_state.scraping:
    st.markdown("---")
    st.header("📋 Live Progress")
    
    progress_container = st.container()
    log_container = st.empty()
    
    with progress_container:
        progress_bar = st.progress(0)
        status_text = st.empty()
    
    try:
        # Run scraper
        status_text.markdown("🚀 **Initializing scraper...**")
        
        start_time = time.time()
        results = asyncio.run(scrape_all(queries, max_results, extract_contacts))
        
        # Store results
        st.session_state.results = results
        st.session_state.scraping = False
        
        elapsed = time.time() - start_time
        
        progress_bar.progress(100)
        status_text.markdown(f"✅ **Complete!** ({elapsed//60:.0f}m {elapsed%60:.0f}s)")
        
        st.success("🎉 Scraping finished successfully!")
        time.sleep(2)
        st.rerun()
        
    except Exception as e:
        st.error(f"❌ Error: {str(e)}")
        st.session_state.scraping = False
        st.button("Try Again")

# ============================================================================
# RESULTS DISPLAY
# ============================================================================

if st.session_state.results is not None and not st.session_state.scraping:
    st.markdown("---")
    
    # Success banner
    st.markdown(f"""
    <div class='success-banner'>
        🎉 SUCCESS! Scraped {len(st.session_state.results)} businesses with full contact data!
    </div>
    """, unsafe_allow_html=True)
    
    # Convert to DataFrame
    df = pd.DataFrame(st.session_state.results)
    
    # Statistics Cards
    st.header("📊 Results Overview")
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    total = len(df)
    
    with col1:
        st.markdown(f"""
        <div class='metric-card'>
            <div class='metric-label'>TOTAL</div>
            <div class='metric-value'>{total}</div>
            <div class='metric-label'>Businesses</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        phone_count = df['phone'].astype(str).str.strip().ne('').sum()
        phone_pct = int(phone_count * 100 / total) if total > 0 else 0
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #f093fb 0%, #f5576c 100%);'>
            <div class='metric-label'>PHONE</div>
            <div class='metric-value'>{phone_count}</div>
            <div class='metric-label'>{phone_pct}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col3:
        email_count = df['email'].astype(str).str.strip().ne('').sum()
        email_pct = int(email_count * 100 / total) if total > 0 else 0
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #4facfe 0%, #00f2fe 100%);'>
            <div class='metric-label'>EMAIL</div>
            <div class='metric-value'>{email_count}</div>
            <div class='metric-label'>{email_pct}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col4:
        instagram_count = df['instagram'].astype(str).str.strip().ne('').sum()
        instagram_pct = int(instagram_count * 100 / total) if total > 0 else 0
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #fa709a 0%, #fee140 100%);'>
            <div class='metric-label'>INSTAGRAM</div>
            <div class='metric-value'>{instagram_count}</div>
            <div class='metric-label'>{instagram_pct}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    with col5:
        facebook_count = df['facebook'].astype(str).str.strip().ne('').sum()
        facebook_pct = int(facebook_count * 100 / total) if total > 0 else 0
        st.markdown(f"""
        <div class='metric-card' style='background: linear-gradient(135deg, #30cfd0 0%, #330867 100%);'>
            <div class='metric-label'>FACEBOOK</div>
            <div class='metric-value'>{facebook_count}</div>
            <div class='metric-label'>{facebook_pct}%</div>
        </div>
        """, unsafe_allow_html=True)
    
    st.markdown("<br>", unsafe_allow_html=True)
    
    # Download Section
    st.header("💾 Download Your Data")
    
    col1, col2 = st.columns([2, 1])
    
    with col1:
        # Generate CSV
        csv = df.to_csv(index=False).encode('utf-8')
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"gmaps_results_{timestamp}.csv"
        
        st.download_button(
            label="⬇️ DOWNLOAD CSV",
            data=csv,
            file_name=filename,
            mime='text/csv',
            use_container_width=True
        )
    
    with col2:
        st.metric("File Size", f"{len(csv) / 1024:.1f} KB")
    
    # Data Table
    st.markdown("---")
    st.header("📋 Browse Results")
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        filter_email = st.checkbox("📧 Only with email")
    with col2:
        filter_instagram = st.checkbox("📷 Only with Instagram")
    with col3:
        filter_facebook = st.checkbox("👥 Only with Facebook")
    with col4:
        search_term = st.text_input("🔍 Search", "")
    
    # Apply filters
    filtered_df = df.copy()
    
    if filter_email:
        filtered_df = filtered_df[filtered_df['email'].astype(str).str.strip().ne('')]
    
    if filter_instagram:
        filtered_df = filtered_df[filtered_df['instagram'].astype(str).str.strip().ne('')]
    
    if filter_facebook:
        filtered_df = filtered_df[filtered_df['facebook'].astype(str).str.strip().ne('')]
    
    if search_term:
        mask = filtered_df.astype(str).apply(lambda x: x.str.contains(search_term, case=False, na=False)).any(axis=1)
        filtered_df = filtered_df[mask]
    
    # Display table
    st.dataframe(
        filtered_df,
        use_container_width=True,
        height=500,
        column_config={
            "title": st.column_config.TextColumn("Business Name", width="medium"),
            "phone": st.column_config.TextColumn("Phone", width="small"),
            "email": st.column_config.TextColumn("Email", width="medium"),
            "instagram": st.column_config.LinkColumn("Instagram", width="small"),
            "facebook": st.column_config.LinkColumn("Facebook", width="small"),
            "rating": st.column_config.NumberColumn("Rating", format="⭐ %.1f"),
        }
    )
    
    st.info(f"📊 Showing **{len(filtered_df)}** of **{len(df)}** results")

# ============================================================================
# FOOTER
# ============================================================================

st.markdown("---")
st.markdown("""
<div style='text-align: center; padding: 2rem; color: #666;'>
    <h3>🚀 Google Maps Scraper - Unlimited Edition</h3>
    <p>No limits. No restrictions. Just results.</p>
    <p style='font-size: 0.9rem; opacity: 0.7;'>
        Built with ❤️ for data enthusiasts | 100% Free & Open Source
    </p>
</div>
""", unsafe_allow_html=True)
