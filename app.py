def scrape_stable_bids(url):
    """Stable Selenium configuration for Streamlit Cloud."""
    chrome_options = Options()
    chrome_options.add_argument("--headless")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    
    try:
        # We stop using Service(ChromeDriverManager().install()) 
        # Streamlit Cloud finds 'chromedriver' automatically if packages.txt is correct.
        driver = webdriver.Chrome(options=chrome_options)
        driver.set_page_load_timeout(20)
        driver.get(url)
        
        # Give BidNet time to load its JavaScript table
        time.sleep(8) 
        
        soup = BeautifulSoup(driver.page_source, 'html.parser')
        driver.quit()
        
        found_bids = []
        # Find all links - this captures the bid titles shown in your screenshots
        for link in soup.find_all('a', href=True):
            text = link.get_text(separator=' ', strip=True)
            if len(text) > 30 and not any(x in text.lower() for x in ["login", "register", "support", "cookies"]):
                clean_name = " ".join(text.split()).upper()
                bid_link = urljoin(url, link['href'])
                
                # De-duplicate entries
                if clean_name[:50] not in [b['name'][:50] for b in found_bids]:
                    found_bids.append({
                        "name": clean_name, 
                        "full_text": f"PROJECT: {clean_name}. Source: {url}", 
                        "link": bid_link
                    })
        return found_bids[:8]
    except Exception as e:
        st.error(f"Scraper Error: {e}")
        return []
