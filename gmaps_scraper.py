"""
Google Maps Scraper - Python Version
Based on working scraping methods + Social Media Enhancement
No BS limits - scrape as much as you want!
"""

import asyncio
import csv
import re
import time
from playwright.async_api import async_playwright
from datetime import datetime

# ============================================================================
# PATTERNS
# ============================================================================

EMAIL_PATTERN = re.compile(r'\b[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Z|a-z]{2,}\b')

SOCIAL_PATTERNS = {
    'instagram': re.compile(r'(?:https?://)?(?:www\.)?instagram\.com/([a-zA-Z0-9._]+)/?'),
    'facebook': re.compile(r'(?:https?://)?(?:www\.)?facebook\.com/([a-zA-Z0-9.]+)/?'),
    'twitter': re.compile(r'(?:https?://)?(?:www\.)?(?:twitter|x)\.com/([a-zA-Z0-9_]+)/?'),
    'tiktok': re.compile(r'(?:https?://)?(?:www\.)?tiktok\.com/@([a-zA-Z0-9._]+)/?'),
    'linkedin': re.compile(r'(?:https?://)?(?:www\.)?linkedin\.com/(?:company|in)/([a-zA-Z0-9-]+)/?'),
    'youtube': re.compile(r'(?:https?://)?(?:www\.)?youtube\.com/(?:c|channel|user|@)([a-zA-Z0-9_-]+)/?'),
}

PHONE_PATTERN = re.compile(r'[\+\(]?[0-9][0-9 \.\-\(\)]{8,}[0-9]')

# ============================================================================
# EXTRACTION FUNCTIONS
# ============================================================================

def extract_emails(text):
    """Extract emails from text"""
    emails = EMAIL_PATTERN.findall(text)
    # Filter out common false positives
    filtered = [e for e in emails if not any(x in e.lower() for x in ['wixpress', 'sentry', 'gstatic', 'schema.org'])]
    return list(set(filtered))

def extract_socials(text):
    """Extract social media from text"""
    socials = {}
    for platform, pattern in SOCIAL_PATTERNS.items():
        matches = pattern.findall(text)
        if matches:
            handle = matches[0]
            if platform == 'twitter':
                socials[platform] = f"https://x.com/{handle}"
            else:
                socials[platform] = f"https://{platform}.com/{handle}"
    return socials

def extract_phone(text):
    """Extract phone number"""
    matches = PHONE_PATTERN.findall(text)
    return matches[0] if matches else ""

# ============================================================================
# GOOGLE MAPS SCRAPER
# ============================================================================

async def scrape_google_maps_search(page, query, max_results=1000):
    """
    Scrape Google Maps search results
    NO LIMIT - scrape as many as you want!
    """
    
    print(f"\n{'='*60}")
    print(f"🔍 Query: {query}")
    print(f"📊 Target: {max_results} results")
    print(f"{'='*60}")
    
    # Go to Google Maps
    await page.goto(f"https://www.google.com/maps/search/{query.replace(' ', '+')}")
    await page.wait_for_timeout(3000)
    
    # Handle consent if it appears
    try:
        consent = page.locator('button:has-text("Accept all"), button:has-text("Reject all")').first
        if await consent.count() > 0:
            await consent.click()
            await page.wait_for_timeout(2000)
    except:
        pass
    
    # Wait for results
    try:
        await page.wait_for_selector('[role="feed"]', timeout=10000)
    except:
        print("❌ No results found!")
        return []
    
    # Scroll to load ALL results
    print("📜 Scrolling to load results...")
    
    last_height = 0
    no_change_count = 0
    results_found = 0
    
    while results_found < max_results and no_change_count < 5:
        # Scroll
        await page.evaluate("""
            const feed = document.querySelector('[role="feed"]');
            if (feed) {
                feed.scrollTo(0, feed.scrollHeight);
            }
        """)
        
        await page.wait_for_timeout(2000)
        
        # Check current results
        cards = await page.locator('[role="article"]').all()
        results_found = len(cards)
        
        # Check if we reached the end
        current_height = await page.evaluate("""
            const feed = document.querySelector('[role="feed"]');
            return feed ? feed.scrollHeight : 0;
        """)
        
        if current_height == last_height:
            no_change_count += 1
        else:
            no_change_count = 0
            last_height = current_height
        
        # Progress
        if results_found % 20 == 0:
            print(f"   Found {results_found} results...")
    
    print(f"✅ Total cards found: {results_found}")
    
    # Extract all business data
    results = []
    cards = await page.locator('[role="article"]').all()
    
    for idx, card in enumerate(cards[:max_results], 1):
        try:
            # Click card to show details
            await card.click()
            await page.wait_for_timeout(1200)
            
            # Extract ALL data
            business = {}
            
            # Title
            title_elem = page.locator('h1').first
            business['title'] = await title_elem.inner_text() if await title_elem.count() > 0 else ""
            
            # Get the whole page content for extraction
            content = await page.content()
            
            # Phone - try button first
            phone = ""
            try:
                phone_button = page.locator('button[data-item-id*="phone"]').first
                if await phone_button.count() > 0:
                    aria = await phone_button.get_attribute('aria-label')
                    if aria:
                        phone = extract_phone(aria)
            except:
                pass
            
            if not phone:
                phone = extract_phone(content)
            
            business['phone'] = phone
            
            # Website
            website = ""
            try:
                website_link = page.locator('a[data-item-id="authority"]').first
                if await website_link.count() > 0:
                    website = await website_link.get_attribute('href')
            except:
                pass
            business['website'] = website or ""
            
            # Address
            address = ""
            try:
                address_button = page.locator('button[data-item-id="address"]').first
                if await address_button.count() > 0:
                    address = await address_button.inner_text()
            except:
                pass
            business['address'] = address or ""
            
            # Rating
            rating = ""
            try:
                rating_elem = page.locator('[role="img"][aria-label*="stars"]').first
                if await rating_elem.count() > 0:
                    aria = await rating_elem.get_attribute('aria-label')
                    if aria:
                        match = re.search(r'([\d\.]+) stars', aria)
                        if match:
                            rating = match.group(1)
            except:
                pass
            business['rating'] = rating or ""
            
            # Reviews
            reviews = ""
            try:
                reviews_elem = page.locator('[role="img"][aria-label*="reviews"]').first
                if await reviews_elem.count() > 0:
                    aria = await reviews_elem.get_attribute('aria-label')
                    if aria:
                        match = re.search(r'([\d,]+) reviews', aria)
                        if match:
                            reviews = match.group(1)
            except:
                pass
            business['reviews'] = reviews or ""
            
            # Category
            category = ""
            try:
                category_button = page.locator('button[jsaction*="category"]').first
                if await category_button.count() > 0:
                    category = await category_button.inner_text()
            except:
                pass
            business['category'] = category or ""
            
            # Initialize social/email fields
            business['email'] = ''
            business['instagram'] = ''
            business['facebook'] = ''
            business['twitter'] = ''
            business['tiktok'] = ''
            business['linkedin'] = ''
            business['youtube'] = ''
            business['query'] = query
            
            results.append(business)
            
            if idx % 10 == 0:
                print(f"   Extracted {idx}/{min(len(cards), max_results)}")
            
        except Exception as e:
            print(f"   ⚠️  Error on card {idx}: {str(e)}")
            continue
    
    print(f"✅ Extracted {len(results)} businesses")
    return results

# ============================================================================
# WEBSITE SCRAPER (EMAILS + SOCIALS)
# ============================================================================

async def scrape_website_for_contacts(page, business):
    """Extract emails and social media from business website"""
    
    website = business.get('website', '')
    
    if not website:
        return business
    
    # Check if website IS social media
    if 'instagram.com' in website:
        business['instagram'] = website
        return business
    elif 'facebook.com' in website:
        business['facebook'] = website
        return business
    elif 'tiktok.com' in website:
        business['tiktok'] = website
        return business
    elif 'twitter.com' in website or 'x.com' in website:
        business['twitter'] = website
        return business
    elif 'linkedin.com' in website:
        business['linkedin'] = website
        return business
    
    # It's a real website - extract contacts
    try:
        await page.goto(website, timeout=8000, wait_until='domcontentloaded')
        await page.wait_for_timeout(1500)
        
        # Get content
        html = await page.content()
        
        # Extract emails
        emails = extract_emails(html)
        if emails:
            business['email'] = emails[0]
        
        # Extract socials
        socials = extract_socials(html)
        business['instagram'] = socials.get('instagram', '')
        business['facebook'] = socials.get('facebook', '')
        business['twitter'] = socials.get('twitter', '')
        business['tiktok'] = socials.get('tiktok', '')
        business['linkedin'] = socials.get('linkedin', '')
        business['youtube'] = socials.get('youtube', '')
        
        # Try contact page if no email
        if not business['email']:
            for path in ['/contact', '/contact-us', '/about', '/about-us']:
                try:
                    await page.goto(f"{website.rstrip('/')}{path}", timeout=5000)
                    await page.wait_for_timeout(1000)
                    html = await page.content()
                    emails = extract_emails(html)
                    if emails:
                        business['email'] = emails[0]
                        break
                except:
                    continue
        
    except Exception as e:
        pass
    
    return business

# ============================================================================
# MAIN FUNCTION
# ============================================================================

async def scrape_all(queries, max_results_per_query=1000, extract_contacts=True):
    """
    Main scraping function
    NO LIMITS - scrape as much as you need!
    """
    
    all_results = []
    
    async with async_playwright() as p:
        # Launch browser
        browser = await p.chromium.launch(
            headless=True,
            args=['--no-sandbox', '--disable-dev-shm-usage']
        )
        
        context = await browser.new_context(
            viewport={'width': 1920, 'height': 1080},
            user_agent='Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
        )
        
        # Phase 1: Scrape Google Maps
        print("\n" + "="*60)
        print("📍 PHASE 1: GOOGLE MAPS SCRAPING")
        print("="*60)
        
        maps_page = await context.new_page()
        
        for idx, query in enumerate(queries, 1):
            print(f"\n[{idx}/{len(queries)}]")
            results = await scrape_google_maps_search(maps_page, query, max_results_per_query)
            all_results.extend(results)
        
        await maps_page.close()
        
        print(f"\n{'='*60}")
        print(f"✅ PHASE 1 COMPLETE: {len(all_results)} businesses")
        print(f"{'='*60}")
        
        # Phase 2: Extract contacts
        if extract_contacts:
            print("\n" + "="*60)
            print("📧 PHASE 2: EMAIL & SOCIAL MEDIA EXTRACTION")
            print("="*60)
            
            # Filter businesses with websites
            with_websites = [b for b in all_results if b.get('website')]
            print(f"\n🌐 {len(with_websites)} businesses have websites")
            
            # Create pages for parallel processing
            num_workers = 3
            pages = []
            for _ in range(num_workers):
                pages.append(await context.new_page())
            
            # Process in batches
            for i in range(0, len(with_websites), num_workers):
                batch = with_websites[i:i+num_workers]
                
                # Process batch in parallel
                tasks = []
                for idx, business in enumerate(batch):
                    page_idx = idx % len(pages)
                    tasks.append(scrape_website_for_contacts(pages[page_idx], business))
                
                await asyncio.gather(*tasks)
                
                progress = min(i + num_workers, len(with_websites))
                if progress % 30 == 0 or progress == len(with_websites):
                    print(f"   📊 Progress: {progress}/{len(with_websites)} ({progress*100//len(with_websites)}%)")
            
            for page in pages:
                await page.close()
            
            print(f"\n✅ PHASE 2 COMPLETE!")
        
        await browser.close()
    
    return all_results

# ============================================================================
# SAVE FUNCTION
# ============================================================================

def save_to_csv(results, filename):
    """Save results to CSV"""
    
    if not results:
        print("❌ No results to save!")
        return
    
    fieldnames = ['title', 'address', 'phone', 'website', 'email', 
                  'instagram', 'facebook', 'twitter', 'tiktok', 'linkedin', 'youtube',
                  'rating', 'reviews', 'category', 'query']
    
    with open(filename, 'w', encoding='utf-8', newline='') as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(results)
    
    print(f"\n💾 Saved to: {filename}")
    
    # Print stats
    total = len(results)
    with_phone = sum(1 for r in results if r.get('phone'))
    with_email = sum(1 for r in results if r.get('email'))
    with_website = sum(1 for r in results if r.get('website'))
    with_instagram = sum(1 for r in results if r.get('instagram'))
    with_facebook = sum(1 for r in results if r.get('facebook'))
    with_tiktok = sum(1 for r in results if r.get('tiktok'))
    
    print("\n" + "="*60)
    print("📊 FINAL STATISTICS")
    print("="*60)
    print(f"Total businesses: {total}")
    print(f"With phone:     {with_phone:4d} ({with_phone*100//total if total else 0:2d}%)")
    print(f"With website:   {with_website:4d} ({with_website*100//total if total else 0:2d}%)")
    print(f"With email:     {with_email:4d} ({with_email*100//total if total else 0:2d}%)")
    print(f"With Instagram: {with_instagram:4d} ({with_instagram*100//total if total else 0:2d}%)")
    print(f"With Facebook:  {with_facebook:4d} ({with_facebook*100//total if total else 0:2d}%)")
    print(f"With TikTok:    {with_tiktok:4d} ({with_tiktok*100//total if total else 0:2d}%)")
    print("="*60)

# ============================================================================
# CLI INTERFACE
# ============================================================================

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description='Google Maps Scraper - NO LIMITS!')
    parser.add_argument('--queries', required=True, help='Path to queries file')
    parser.add_argument('--output', default='results.csv', help='Output CSV file')
    parser.add_argument('--max', type=int, default=1000, help='Max results per query (NO LIMIT!)')
    parser.add_argument('--no-contacts', action='store_true', help='Skip email/social extraction')
    
    args = parser.parse_args()
    
    # Read queries
    with open(args.queries, 'r', encoding='utf-8') as f:
        queries = [line.strip() for line in f if line.strip() and not line.startswith('#')]
    
    print("="*60)
    print("🚀 GOOGLE MAPS SCRAPER - UNLIMITED VERSION")
    print("="*60)
    print(f"📋 Queries: {len(queries)}")
    print(f"📊 Max per query: {args.max}")
    print(f"📧 Extract contacts: {not args.no_contacts}")
    print("="*60)
    
    # Run scraper
    start_time = time.time()
    results = asyncio.run(scrape_all(queries, args.max, not args.no_contacts))
    
    # Save
    save_to_csv(results, args.output)
    
    # Time
    elapsed = time.time() - start_time
    print(f"\n⏱️  Total time: {elapsed//60:.0f}m {elapsed%60:.0f}s")
