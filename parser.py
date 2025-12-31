import requests
import re
import os
import urllib.parse
from concurrent.futures import ThreadPoolExecutor, as_completed
from threading import Lock, Event, Thread
import time
import urllib3
import random
import json
from queue import Queue
import colorama
import zipfile

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
colorama.init(autoreset=True)

COLOR_RESET = '\033[0m'
COLOR_GREEN = '\033[92m'
COLOR_BLUE = '\033[94m'
COLOR_CYAN = '\033[96m'
COLOR_YELLOW = '\033[93m'

rate_limit_event = Event()
rate_limit_event.set()
global_lock = Lock()

backup_session_queue = Queue(maxsize=3)
dork_counter = {'count': 0}
dork_counter_lock = Lock()

persistent_rate_limit = {'consecutive_fails': 0, 'last_success_time': time.time()}
persistent_lock = Lock()

saved_urls_set = set()
saved_urls_lock = Lock()

def extract_dorks_if_needed():
    """Extract cc_dorks.txt from zip if needed"""
    dorks_file = "cc_dorks.txt"
    zip_file = "cc_dorks.zip"
    
    if os.path.exists(dorks_file):
        return True
    
    if os.path.exists(zip_file):
        print(f"Extracting {zip_file}...")
        try:
            with zipfile.ZipFile(zip_file, 'r') as zip_ref:
                zip_ref.extractall('.')
            print(f"✓ Extracted {dorks_file}")
            return True
        except Exception as e:
            print(f"ERROR extracting zip: {e}")
            return False
    
    return True  # If neither exists, continue (will error later)

# Extract dorks if compressed
extract_dorks_if_needed()

# Configuration from environment variables
choice = os.getenv('PROXY_CHOICE', '1').strip()
engine_choice = os.getenv('SEARCH_ENGINE', '1').strip()
mode_choice = os.getenv('MODE', '1').strip()
dorks_file = os.getenv('DORKS_FILE', 'cc_dorks.txt').strip()

print("=" * 50)
print("CONFIGURATION")
print("=" * 50)

proxies = None
if choice == "2":
    proxy_string = os.getenv('PROXY_STRING', "43.159.29.246:9999:td-customer-K17667574031427-country-us:K17667574031427")
    parts = proxy_string.split(":")
    proxy_host = parts[0]
    proxy_port = parts[1]
    proxy_user = parts[2]
    proxy_pass = parts[3]
    
    proxy_url = f"http://{proxy_user}:{proxy_pass}@{proxy_host}:{proxy_port}"
    proxies = {
        'http': proxy_url,
        'https': proxy_url
    }
    print(f"Proxy: {proxy_host}:{proxy_port}")
else:
    print("Proxy: None")

engine_names = {"1": "Google only", "2": "Bing only", "3": "Mix (Google + Bing)"}
print(f"Search Engine: {engine_names.get(engine_choice, 'Google only')}")

single_threaded = mode_choice != "2"
mode_name = "Single-threaded" if single_threaded else "Multi-threaded"
print(f"Mode: {mode_name}")

progress_file = "progress.json"
start_index = 0

if os.path.exists(progress_file):
    try:
        with open(progress_file, 'r') as f:
            progress_data = json.load(f)
            start_index = progress_data.get('last_completed', 0)
            print(f"Resuming from dork #{start_index + 1}")
    except:
        print("Starting from beginning")
        start_index = 0

if not os.path.exists(dorks_file):
    print(f"Error: File '{dorks_file}' not found!")
    exit(1)

print(f"Dorks file: {dorks_file}")
with open(dorks_file, 'r', encoding='utf-8') as f:
    dorks = [line.strip() for line in f if line.strip()]

print(f"Loaded {len(dorks)} dork(s)")

# Try to find user_agents.txt in current directory or use default
user_agents_file = "user_agents.txt"
if not os.path.exists(user_agents_file):
    print(f"Warning: User agents file not found, using default")
    user_agents = ['Mozilla/5.0 (iPhone; CPU iPhone OS 18_7_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) GSA/396.0.833910942 Mobile/22H217 Safari/604.1']
else:
    with open(user_agents_file, 'r', encoding='utf-8') as f:
        user_agents = [line.strip() for line in f if line.strip()]
    print(f"Loaded {len(user_agents)} user agent(s)")

output_file = "jphq.txt"
file_lock = Lock()

if os.path.exists(output_file):
    print(f"Loading existing URLs for duplicate filtering...")
    try:
        with open(output_file, 'r', encoding='utf-8') as f:
            for line in f:
                url = line.strip()
                if url:
                    saved_urls_set.add(url)
        print(f"Loaded {len(saved_urls_set)} existing URL(s)")
    except Exception as e:
        print(f"Warning: Could not load existing URLs: {e}")

print("=" * 50 + "\n")

base_headers = {
    'Host': 'www.google.com',
    'X-Client-Pctx': 'CgUSA8ABAA==',
    'X-Client-Data': 'CgSou7IIUvgFQ0FJU3RRUUl3Y3F5Q0FqVy1iTUlDS0NJdEFnSXBvaTBDQWp0aXJRSUNQT0t0QWdJdUtHMENBaS1vYlFJQ0lqTHRBZ0lqc3UwQ0FqNzNMUUlDSUhkdEFnSTBlYTBDQWpYNXJRSUNQcnF0QWdJX091MENBaUM3TFFJQ056OXRBZ0lxNGExQ0FpS2pMVUlDSkNNdFFnSTRxTzFDQWpsbzdVSUNNeXN0UWdJejZ5MUNBalhzclVJQ0lHOHRRZ0lycnkxQ0FpVHpMVUlDSmJNdFFnSXNOMjFDQWpEMzdVSUNQRGh0UWdJOC1HMUNBaXI1YlVJQ0s3bHRRZ0lxZXkxQ0FpczdMVUlDTTdzdFFnSTBleTFDQWpZN3JVSUNLcnd0UWdJcVBHMUNBaVA4N1VJQ1A3MHRRZ0lnZlcxQ0FpMDk3VUlDTGYzdFFnSWpQaTFDQWlQLUxVSUNPUDV0UWdJNXZtMUNBaVctclVJQ0puNnRRZ0kxUHUxQ0FqWC03VUlDSl85dFFnSW92MjFDQWl3X2JVSUNLai10UWdJcV82MUNBajJfclVJQ1BuLXRRZ0lqdi0xQ0FpUl83VUlDUDNfdFFnSTdZQzJDQWp3Z0xZSUNJdUJ0Z2dJNElHMkNBampnYllJQ1BxQnRnZ0luSUsyQ0FpMGdyWUlDSktFdGdnSWxZUzJDQWlwaExZSUNPeUV0Z2dJbllXMkNBajBoYllJQ1BlRnRnZ0ktNFcyQ0FpS2g3WUlDSTJIdGdnSWs0ZTJDQWlXaDdZSUNLZUh0Z2dJellxMkNBamtpcllJQ0p5TXRnZ0lxSXkyQ0FpN2piWUlDTVdOdGdnSXlJMjJDQWpLamJZSUNLMlB0Z2dndDg3c0lpQ2J6NjhDSUxqQmpRSWdtdERySWlDcHV2QWlJSjdnOFNJZy11M2xJaUR0bGVzdUlMbTU3eUlnMDg3aklpRGJ0NlF2SUltNjR5SWd5YjNhSWlDVmlLOENJSnFVNlM0Z19zanBMaUN6M2VFblIIQ0FNU0FBPT1SCENBTVNBQT09UiRDQU1TRmcwTTJvaXhEOWpvX3ltcjJnRVZBSnYtOXlYQjF3WT16EQoPGKjvtAgYoYS2CBjd2rII',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'X-Silk-Capabilities': 'CAESBhABEAAYIBIKEAIQARADEAAYPhIGEAAQARhtEgQQABhZEgoQABABEAUQBhgrEgYQABABGCQSBBAAGDwSBhAAEAEYThIEEAAYKRIEEAAYLBIEEAAYOhIEEAAYWxIEEAAYLxIEEAAYORIEEAAYQxIEEAAYGxIIEAIQARAAGBMSBBAAGAsSBBAAGBASDBACEAMQBBAGEAAYQhIEEAAYRxIEEAAYaxIEEAAYahIEEAAYVxIEEAAYWhIEEAAYYhIEEAAYJhIEEAAYChIEEAAYHxIEEAAYJRIWEAMQCxAHEAQQBRACEAYQCRANEAAYYRIEEAAYARIEEAAYCRIMEAAQARADEAQQBhgwEgQQABhNEgYQABABGGcSBBAAGA4SBhAAEAEYTxIMEAAQARACEAMQBBgVEggQARADEAAYKBIEEAAYShIEEAAYHhIEEAAYVA==',
    'X-Speech-Cookie': 'D7FFC2EE-D51C-4640-9398-917B038913FD',
    'X-First-App-Launch-Ms': '-1',
    'Sec-Fetch-Site': 'none',
    'X-Client-Opt-In-Context': 'H4sIAAAAAAAAE-NiEmCUAmInJgEGAAxDUsUMAAAA',
    'Accept-Language': 'en-IN,en;q=0.9',
    'Accept-Encoding': 'gzip, deflate, br',
    'Sec-Fetch-Mode': 'navigate',
    'X-Gsa-Lat': '1',
    'Sec-Fetch-Dest': 'document'
}

bing_headers = {
    'Host': 'www.bing.com',
    'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
    'Sec-Fetch-Site': 'none',
    'Sapphire-Devicetype': 'iPhoneXR',
    'Sapphire-Configuration': 'Production',
    'Accept-Language': 'en-IN,en;q=0.9',
    'Sapphire-Apiversion': '126',
    'Sec-Fetch-Mode': 'navigate',
    'Sapphire-Market': 'en-in',
    'User-Agent': 'Mozilla/5.0 (iPhone; CPU iPhone OS 18_7_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/18.7.3 Mobile/15E148 Safari/605.1.15 BingSapphire/32.6.431215001',
    'Sapphire-Osversion': '18.7.3',
    'Sec-Fetch-Dest': 'document',
}

bing_cookies_container = {'cookies': {}}

def extract_urls_from_html(html_content):
    urls = set()
    patterns = [
        r'<a[^>]+href="(https?://(?!accounts\.google|support\.google|policies\.google|google\.com)[^"]+)"',
        r'href="/url\?q=(https?://[^&"]+)',
        r'data-ved="[^"]*"[^>]*href="(https?://(?!google\.com)[^"]+)"',
    ]
    
    for pattern in patterns:
        matches = re.findall(pattern, html_content, re.IGNORECASE)
        for match in matches:
            url = match
            url = urllib.parse.unquote(url)
            
            if '/url?q=' in url:
                url = url.split('/url?q=')[-1].split('&')[0]
                url = urllib.parse.unquote(url)
            
            excluded_domains = ['google.com', 'google.', 'gstatic.com', 'googleusercontent.com', 
                              'youtube.com', 'schema.org', 'w3.org']
            
            if url.startswith('http') and not any(domain in url.lower() for domain in excluded_domains):
                url = url.split('#')[0]
                urls.add(url)
    
    return urls

def extract_urls_from_bing(html_content):
    urls = set()
    
    excluded_domains = [
        'bing.com', 'microsoft.com', 'msn.com', 'live.com', 'microsoftonline.com',
        'schema.org', 'w3.org', 'office.com', 'office365.com', 'outlook.com',
        'google.com', 'account.google.com', 'passwords.google.com', 'support.google.com',
        'wikipedia.org', 'stackoverflow.com', 'stackexchange.com',
        'facebook.com', 'twitter.com', 'linkedin.com', 'instagram.com', 'youtube.com',
        'github.com', 'gitlab.com', 
        'forum.', 'forums.', 'community.'
    ]
    
    result_blocks = re.findall(r'<li class="b_algo"[^>]*>(.*?)</li>', html_content, re.DOTALL | re.IGNORECASE)
    
    for block in result_blocks:
        link_match = re.search(r'<h2[^>]*>.*?<a[^>]+href="([^"]+)"', block, re.DOTALL | re.IGNORECASE)
        if link_match:
            url = link_match.group(1)
            url = urllib.parse.unquote(url)
            
            if url.startswith('http') and not any(domain in url.lower() for domain in excluded_domains):
                url = url.split('#')[0]
                urls.add(url)
    
    return urls

def get_bing_cookies(proxies, user_agents):
    try:
        headers_first = {
            "User-Agent": random.choice(user_agents)
        }
        response = requests.get("https://www.bing.com", headers=headers_first, proxies=proxies, verify=False, timeout=10)
        cookies_dict = {}
        for cookie in response.cookies:
            cookies_dict[cookie.name] = cookie.value
        return cookies_dict
    except:
        return {}

def search_dork_bing(dork, proxies, user_agents, dork_num, total_dorks, mix_mode=False):
    max_retries = 5
    max_pages = 5
    all_urls = set()
    
    engine_prefix = f"{COLOR_CYAN}[BING]{COLOR_RESET}" if mix_mode else ""
    dork_display = dork[:60] + "..." if len(dork) > 60 else dork
    print(f"[{dork_num}/{total_dorks}] {engine_prefix} Searching: {dork_display}")
    
    for page in range(max_pages):
        first_result = page * 10
        
        for attempt in range(max_retries):
            rate_limit_event.wait()
            
            try:
                query = urllib.parse.quote(dork)
                search_url = f'https://www.bing.com/search?q={query}&first={first_result}&PC=OPALIOS&form=LWS001&ssp=1&cc=IN&setlang=en&pc=OPALIOS&safesearch=moderate&intermdt=1'
                
                if not bing_cookies_container['cookies']:
                    bing_cookies_container['cookies'] = get_bing_cookies(proxies, user_agents)
                
                current_headers = bing_headers.copy()
                current_headers['User-Agent'] = random.choice(user_agents)
                
                response = requests.get(search_url, cookies=bing_cookies_container['cookies'], headers=current_headers, proxies=proxies, verify=False, timeout=30)
                
                if response.status_code == 200:
                    urls = extract_urls_from_bing(response.text)
                    if urls:
                        all_urls.update(urls)
                    else:
                        break
                    break
                        
                elif response.status_code == 429 or response.status_code == 403:
                    error_type = "Rate limited (429)" if response.status_code == 429 else "Forbidden (403)"
                    print(f"[{dork_num}/{total_dorks}] [BING] ⚠ {error_type}. Getting fresh cookies...")
                    bing_cookies_container['cookies'] = get_bing_cookies(proxies, user_agents)
                    print(f"[{dork_num}/{total_dorks}] [BING] ⚠ Waiting 3s... (Attempt {attempt+1}/{max_retries})")
                    time.sleep(3)
                    continue
                else:
                    break
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    break
        
        time.sleep(0.5)
    
    save_progress(dork_num)
    
    if all_urls:
        saved_count = save_urls(all_urls, output_file)
        if saved_count > 0:
            print(f"[{dork_num}/{total_dorks}] {COLOR_GREEN}✓ Found {saved_count} URL(s) from {page+1} page(s){COLOR_RESET}")
            return saved_count
        else:
            print(f"[{dork_num}/{total_dorks}] ✗ All URLs were duplicates")
            return 0
    else:
        print(f"[{dork_num}/{total_dorks}] ✗ No URLs found")
        return 0

def save_urls(urls, filename):
    if urls:
        new_urls = []
        with saved_urls_lock:
            for url in urls:
                parsed = urllib.parse.urlparse(url)
                if parsed.path in ('', '/'):
                    continue
                
                if url not in saved_urls_set:
                    saved_urls_set.add(url)
                    new_urls.append(url)
        
        if new_urls:
            with file_lock:
                with open(filename, 'a', encoding='utf-8') as f:
                    for url in new_urls:
                        f.write(url + '\n')
        return len(new_urls)
    return 0

def create_fresh_session(base_headers, proxies, user_agents):
    try:
        new_session = requests.Session()
        adapter = requests.adapters.HTTPAdapter(pool_connections=1, pool_maxsize=1, max_retries=0)
        new_session.mount('http://', adapter)
        new_session.mount('https://', adapter)
        
        headers = base_headers.copy()
        headers['User-Agent'] = random.choice(user_agents)
        response = new_session.get('https://www.google.com', headers=headers, proxies=proxies, verify=False, timeout=10)
        if response.status_code == 200:
            return new_session
        return None
    except:
        return None

def background_session_refresher(base_headers, proxies, user_agents, stop_event):
    while not stop_event.is_set():
        try:
            if not backup_session_queue.full():
                new_session = create_fresh_session(base_headers, proxies, user_agents)
                if new_session:
                    try:
                        backup_session_queue.put_nowait(new_session)
                    except:
                        pass
            time.sleep(5)
        except:
            pass

def get_fresh_cookies(session_container, base_headers, proxies, user_agents):
    try:
        old_session = session_container.get('session')
        if old_session:
            try:
                old_session.close()
            except:
                pass
        
        try:
            new_session = backup_session_queue.get_nowait()
            if new_session:
                session_container['session'] = new_session
                return True
        except:
            pass
        
        new_session = create_fresh_session(base_headers, proxies, user_agents)
        if new_session:
            session_container['session'] = new_session
            return True
        return False
    except:
        return False

def refresh_session_periodically(session_container, base_headers, proxies, user_agents):
    with dork_counter_lock:
        dork_counter['count'] += 1
        if dork_counter['count'] >= 20:
            dork_counter['count'] = 0
            try:
                new_session = backup_session_queue.get_nowait()
                if new_session:
                    old_session = session_container.get('session')
                    session_container['session'] = new_session
                    if old_session:
                        try:
                            old_session.close()
                        except:
                            pass
                    return True
            except:
                pass
    return False

def save_progress(index):
    with global_lock:
        with open(progress_file, 'w') as f:
            json.dump({'last_completed': index, 'timestamp': time.time()}, f)

def global_rate_limit_cooldown(session_container, base_headers, proxies, user_agents, wait_time):
    global rate_limit_event
    with global_lock:
        if rate_limit_event.is_set():
            rate_limit_event.clear()
            print(f"\n{'='*50}")
            print(f"⚠ GLOBAL RATE LIMIT - All requests paused for {wait_time}s")
            print(f"{'='*50}\n")
            
            time.sleep(wait_time)
            
            print("Creating fresh session after cooldown...")
            if get_fresh_cookies(session_container, base_headers, proxies, user_agents):
                print("✓ Fresh session ready")
            else:
                print("⚠ Could not create fresh session")
            
            rate_limit_event.set()
            print(f"\n{'='*50}")
            print("✓ Resuming requests...")
            print(f"{'='*50}\n")

def search_dork(dork, session_container, base_headers, proxies, user_agents, dork_num, total_dorks, mix_mode=False):
    max_retries = 5
    base_delay = 3
    max_pages = 5
    all_urls = set()
    
    engine_prefix = f"{COLOR_BLUE}[GOOGLE]{COLOR_RESET}" if mix_mode else ""
    dork_display = dork[:60] + "..." if len(dork) > 60 else dork
    print(f"[{dork_num}/{total_dorks}] {engine_prefix} Searching: {dork_display}")
    
    for page in range(max_pages):
        start_param = page * 10
        
        for attempt in range(max_retries):
            rate_limit_event.wait()
            
            try:
                query = urllib.parse.quote(dork)
                search_url = f'https://www.google.com/search?q={query}&start={start_param}&client=mobilesearchapp&hl=en_GB&source=ios.gsa.default&v=396.0.833910942'
                
                headers = base_headers.copy()
                headers['User-Agent'] = random.choice(user_agents)
                
                session_obj = session_container['session']
                response = session_obj.get(search_url, headers=headers, proxies=proxies, verify=False, timeout=30)
                
                if response.status_code == 200:
                    urls = extract_urls_from_html(response.text)
                    
                    if page == 0:
                        save_progress(dork_num)
                        with persistent_lock:
                            persistent_rate_limit['consecutive_fails'] = 0
                            persistent_rate_limit['last_success_time'] = time.time()
                        
                        if refresh_session_periodically(session_container, base_headers, proxies, user_agents):
                            print(f"[{dork_num}/{total_dorks}] 🔄 Auto-refreshed session")
                    
                    if urls:
                        all_urls.update(urls)
                    else:
                        break
                    break
                        
                elif response.status_code == 429 or response.status_code == 403:
                    error_type = "Rate limited (429)" if response.status_code == 429 else "Forbidden (403)"
                    
                    if mix_mode and attempt >= 1:
                        print(f"[{dork_num}/{total_dorks}] ⚠ {error_type}. Switching to Bing...")
                        save_progress(dork_num)
                        return -1
                    
                    print(f"[{dork_num}/{total_dorks}] ⚠ {error_type}. Swapping to fresh session...")
                    if get_fresh_cookies(session_container, base_headers, proxies, user_agents):
                        print(f"[{dork_num}/{total_dorks}] ✓ Swapped to fresh session")
                    else:
                        print(f"[{dork_num}/{total_dorks}] ⚠ No fresh session available, creating new...")
                    
                    if attempt >= 2:
                        global_rate_limit_cooldown(session_container, base_headers, proxies, user_agents, 3)
                    else:
                        print(f"[{dork_num}/{total_dorks}] ⚠ Waiting 3s... (Attempt {attempt+1}/{max_retries})")
                        time.sleep(3)
                    continue
                else:
                    break
                    
            except Exception as e:
                if attempt < max_retries - 1:
                    time.sleep(3)
                else:
                    break
        
        time.sleep(0.5)
    
    save_progress(dork_num)
    
    if all_urls:
        saved_count = save_urls(all_urls, output_file)
        if saved_count > 0:
            print(f"[{dork_num}/{total_dorks}] {COLOR_GREEN}✓ Found {saved_count} URL(s) from {page+1} page(s){COLOR_RESET}")
            return saved_count
        else:
            print(f"[{dork_num}/{total_dorks}] ✗ All URLs were duplicates")
            return 0
    else:
        print(f"[{dork_num}/{total_dorks}] ✗ No URLs found")
        return -1 if mix_mode else 0

print("\n" + "=" * 50)
print("Starting dork searches...")
print("=" * 50 + "\n")

if os.path.exists(output_file):
    print(f"Appending to existing {output_file}\n")
else:
    print(f"Creating new {output_file}\n")

total_urls_found = 0
start_time = time.time()

dorks_to_process = dorks[start_index:]
print(f"\nDorks to process: {len(dorks_to_process)}")

session_container = {'session': None}
stop_refresher = Event()

if engine_choice == "1" or engine_choice == "3":
    print("\nGetting initial cookies from Google...")
    session = requests.Session()
    session_container = {'session': session}
    try:
        initial_headers = base_headers.copy()
        initial_headers['User-Agent'] = random.choice(user_agents)
        initial_response = session.get('https://www.google.com', headers=initial_headers, proxies=proxies, verify=False, timeout=10)
        print(f"Google initial request status: {initial_response.status_code}")
    except Exception as e:
        print(f"Warning: Could not get Google cookies: {e}")

    print("\nStarting background session refresher...")
    refresher_thread = Thread(target=background_session_refresher, args=(base_headers, proxies, user_agents, stop_refresher), daemon=True)
    refresher_thread.start()
    print("✓ Background refresher active (pre-fetching fresh sessions every 5s)")
    print("✓ Auto-refresh every 20 dorks")

if engine_choice == "2" or engine_choice == "3":
    print("\nGetting initial cookies from Bing...")
    bing_cookies_container['cookies'] = get_bing_cookies(proxies, user_agents)
    if bing_cookies_container['cookies']:
        print("✓ Bing cookies obtained")
    else:
        print("⚠ Could not get Bing cookies")

if single_threaded:
    max_workers = 1
    delay_between_requests = 3.0
    print("Mode: Single-threaded (1 worker, 3s delay)")
else:
    max_workers = 2
    delay_between_requests = 2.0
    print("Mode: Multi-threaded (2 workers, 2s delay)")

print(f"\n")

try:
    if engine_choice == "1":
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(search_dork, dork, session_container, base_headers, proxies, user_agents, start_index + i + 1, len(dorks)): dork 
                for i, dork in enumerate(dorks_to_process)
            }
            for future in as_completed(futures):
                dork = futures[future]
                try:
                    urls_count = future.result()
                    total_urls_found += urls_count
                except Exception as e:
                    print(f"✗ Error processing dork: {e}")
                time.sleep(delay_between_requests)
                
    elif engine_choice == "2":
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {
                executor.submit(search_dork_bing, dork, proxies, user_agents, start_index + i + 1, len(dorks)): dork 
                for i, dork in enumerate(dorks_to_process)
            }
            for future in as_completed(futures):
                dork = futures[future]
                try:
                    urls_count = future.result()
                    total_urls_found += urls_count
                except Exception as e:
                    print(f"✗ Error processing dork: {e}")
                time.sleep(delay_between_requests)
                
    else:
        use_google = True
        bing_fallback_count = 0
        
        for i, dork in enumerate(dorks_to_process):
            dork_num = start_index + i + 1
            
            if use_google:
                urls_count = search_dork(dork, session_container, base_headers, proxies, user_agents, dork_num, len(dorks), mix_mode=True)
                if urls_count == -1:
                    print(f"[{dork_num}/{len(dorks)}] {COLOR_YELLOW}🔄 Google rate limited, switching to Bing for 3 dorks...{COLOR_RESET}")
                    use_google = False
                    bing_fallback_count = 0
                    urls_count = search_dork_bing(dork, proxies, user_agents, dork_num, len(dorks), mix_mode=True)
                    bing_fallback_count += 1
            else:
                urls_count = search_dork_bing(dork, proxies, user_agents, dork_num, len(dorks), mix_mode=True)
                bing_fallback_count += 1
                
                if bing_fallback_count >= 3:
                    print(f"[{dork_num}/{len(dorks)}] {COLOR_YELLOW}🔄 Processed 3 Bing dorks, switching back to Google...{COLOR_RESET}")
                    use_google = True
                    bing_fallback_count = 0
            
            if urls_count > 0:
                total_urls_found += urls_count
            time.sleep(delay_between_requests)
            
except KeyboardInterrupt:
    print("\n\n" + "=" * 50)
    print("⚠ Interrupted! Progress saved.")
    print(f"Resume by redeploying.")
    print("=" * 50)

stop_refresher.set()

elapsed_time = time.time() - start_time

print("\n" + "=" * 50)
print("SUMMARY")
print("=" * 50)
print(f"Total dorks processed: {len(dorks)}")
print(f"Total URLs found: {total_urls_found}")
print(f"Time taken: {elapsed_time:.2f} seconds")
print(f"URLs saved to: {output_file}")
print("=" * 50)
