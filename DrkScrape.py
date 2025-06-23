import argparse
import requests
import sys
import time
import threading
import json
import os
from urllib.parse import urljoin, urlparse
from bs4 import BeautifulSoup
from colorama import Fore, Style, init
from collections import deque
from datetime import datetime
import urllib3

init(autoreset=True)

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

visited_links = set()
lock = threading.Lock()

proxies = {
    'http': 'socks5h://127.0.0.1:9050',
    'https': 'socks5h://127.0.0.1:9050'
}

session = requests.Session()
adapter = requests.adapters.HTTPAdapter(max_retries=3)
session.mount('http://', adapter)
session.mount('https://', adapter)

accessible_count = 0
inaccessible_count = 0
added_links = 0
matched_links = []
data_store = []
retry_queue = deque()
permanent_failures = set()

matched_data = []

def show_logo():
    print(Fore.CYAN + Style.BRIGHT + r'''
     _____                _____                _      _____
     |  _ \      _   __  / ____|             _| |    /  _  |   
     | | | |____| | / / | (___   ___ ____ __| | |__ |  |_| |   
     | | | | __/| '/ /   \___ \ / __| __// _  |  _ \|   ___|   
     | |_| | |  | |\ \  _____) | (__| | | |_| | |_| |  |__     
     |____/|_|  |_| \_\ |____ / \___|_|  \____| ___/\_____|    
                                              |_|              
                             
                 By: https://tryhackme.com/p/DrkDeath
    ''')

def fetch_page(url, verbose=False):
    try:
        response = session.get(url, proxies=proxies, timeout=10, verify=False)
        return response
    except requests.exceptions.ConnectionError:
        return None if not verbose else "Connection error"
    except Exception as e:
        return None if not verbose else str(e)

def extract_links(html, base_url):
    soup = BeautifulSoup(html, 'html.parser')
    links = set()
    for tag in soup.find_all('a', href=True):
        href = tag['href']
        full_url = urljoin(base_url, href)
        if ".onion" in full_url.lower():
            links.add(full_url.split('#')[0])
    return links

def search_keywords(html, url, keywords, quiet):
    matched = []
    for word in keywords:
        if word.lower() in html.lower():
            matched.append(word)
            if not quiet:
                print(Fore.LIGHTGREEN_EX + f"[*] Match in {url} for keyword: '{word}'\n")
    if matched:
        matched_links.append(url)
        matched_data.append((url, matched, datetime.now().isoformat()))
    return matched

def load_onion_links(file_path):
    with open(file_path, 'r') as f:
        return set(line.strip() for line in f if line.strip())

def save_onion_link(file_path, url):
    with lock:
        with open(file_path, 'a') as f:
            f.write(url + '\n')

def save_json_output(filename, data):
    with lock:
        if os.path.exists(filename):
            with open(filename, 'r') as f:
                existing_data = json.load(f)
        else:
            existing_data = []

        existing_map = {item['url']: item for item in existing_data}
        for entry in data:
            url = entry['url']
            if url in existing_map:
                existing_keywords = set(existing_map[url].get('keywords', []))
                entry_keywords = set(entry.get('keywords', []))
                combined_keywords = list(existing_keywords.union(entry_keywords))
                existing_map[url]['keywords'] = combined_keywords
                existing_map[url]['login'] = entry.get('login', existing_map[url].get('login'))
                if 'timestamp' not in existing_map[url]:
                    existing_map[url]['timestamp'] = entry.get('timestamp', datetime.now().isoformat())
            else:
                existing_map[url] = entry

        with open(filename, 'w') as f:
            json.dump(list(existing_map.values()), f, indent=2)

def graceful_exit():
    print(Fore.YELLOW + "[.] Exiting gracefully. Finishing current operation...\n")
    save_json_output("output.json", data_store)
    if permanent_failures:
        with open("failed_links.txt", 'w') as f:
            for url in permanent_failures:
                f.write(url + '\n')
    sys.exit(0)

def try_login(url, username, password):
    try:
        session = requests.Session()
        session.proxies = proxies
        response = session.get(url, timeout=10)
        soup = BeautifulSoup(response.text, 'html.parser')
        form = soup.find('form')
        if not form:
            return None
        action = urljoin(url, form.get('action'))
        inputs = form.find_all('input')
        data = {}
        for i in inputs:
            name = i.get('name')
            if name:
                if 'user' in name.lower():
                    data[name] = username
                elif 'pass' in name.lower():
                    data[name] = password
                else:
                    data[name] = i.get('value', '')
        login_response = session.post(action, data=data, timeout=10)
        if "incorrect" in login_response.text.lower() or "invalid" in login_response.text.lower():
            return False
        return True
    except:
        return None

def process_url(queue, onion_links, keywords, quiet, verbose, login_creds):
    global accessible_count, inaccessible_count, added_links
    while queue:
        with lock:
            if not queue:
                return
            url = queue.popleft()
        if url in visited_links:
            continue
        visited_links.add(url)
        response = fetch_page(url, verbose)
        if isinstance(response, str) or response is None:
            if url in retry_queue:
                permanent_failures.add(url)
            else:
                retry_queue.append(url)
            inaccessible_count += 1
            if not quiet:
                msg = response if isinstance(response, str) else "Unspecified error"
                print(Fore.LIGHTMAGENTA_EX + f"[-] {url}" + (f" - {msg}" if verbose else '') + '\n')
            continue
        if url in retry_queue:
            retry_queue.remove(url)
        accessible_count += 1
        if not quiet:
            print(Fore.GREEN + Style.DIM + f"[+] Accessible: {url}\n")
        save_onion_link('onion_links.txt', url)
        page_data = {"url": url, "keywords": [], "login": None, "timestamp": datetime.now().isoformat()}
        if login_creds:
            login_result = try_login(url, login_creds[0], login_creds[1])
            if login_result is False:
                if not quiet:
                    print(Fore.LIGHTMAGENTA_EX + f"[-] {url} - Login failed\n")
                page_data["login"] = "failed"
            elif login_result is True:
                page_data["login"] = "success"
            else:
                page_data["login"] = "not attempted"
        new_links = extract_links(response.text, url)
        for new_url in new_links:
            new_url = new_url.strip()
            with lock:
                if new_url not in visited_links and new_url not in queue and new_url not in onion_links:
                    queue.append(new_url)
                    onion_links.add(new_url)
                    added_links += 1
                    save_onion_link('onion_links.txt', new_url)
                    if not quiet:
                        print(Fore.LIGHTYELLOW_EX + f"[+] Added: {new_url}\n")
        matches = search_keywords(response.text, url, keywords, quiet)
        page_data["keywords"] = matches
        data_store.append(page_data)
        save_json_output("output.json", [page_data])

def show_past_matches(keywords):
    if not os.path.exists("output.json"):
        print("No output.json found.")
        return
    with open("output.json", 'r') as f:
        data = json.load(f)
    for entry in data:
        if any(k in entry.get("keywords", []) for k in keywords):
            ts = entry.get("timestamp", "unknown time")
            url = entry['url']
            kws = ", ".join(entry.get("keywords", []))
            print(Fore.LIGHTGREEN_EX + f"\n[*] Match Found:\n    URL     : {url}\n    Keywords: {kws}\n    Time    : {ts}")

def main():
    show_logo()
    parser = argparse.ArgumentParser(
        description="Tor .onion Scraper",
        formatter_class=argparse.RawTextHelpFormatter,
        epilog="""
Usage example:
    python3 scraper.py login card -s -t 10

Switches:
    -s / --silent   : Silent mode (only keyword matches are shown)
    -v / --verbose  : Verbose mode (show reasons for inaccessible sites)
    -l / --login    : Ask for username and password and try login
    -t / --threads  : Number of threads to use (default is 5)
    -j / --json     : Show past keyword matches from output.json
    -h / --help     : Show this help message and exit
        """
    )
    parser.add_argument('keywords', nargs='+', help="Keywords to search")
    parser.add_argument('-s', '--silent', action='store_true', help="Silent mode: Only show keyword matches")
    parser.add_argument('-v', '--verbose', action='store_true', help="Verbose output: Show error reasons for inaccessible links")
    parser.add_argument('-l', '--login', action='store_true', help="Prompt for login credentials to test login forms")
    parser.add_argument('-t', '--threads', type=int, default=5, help="Number of threads to use (default: 5)")
    parser.add_argument('-j', '--json', action='store_true', help="Show past matches from output.json")
    args = parser.parse_args()

    keywords = args.keywords
    if args.json:
        show_past_matches(keywords)
        return

    quiet = args.silent
    verbose = args.verbose
    login_creds = None
    thread_count = args.threads

    if args.login:
        username = input("Username: ")
        password = input("Password: ")
        login_creds = (username, password)

    onion_file = 'onion_links.txt'
    onion_links = load_onion_links(onion_file)
    queue = deque(onion_links)
    threads = []
    for _ in range(thread_count):
        t = threading.Thread(target=process_url, args=(queue, onion_links, keywords, quiet, verbose, login_creds), daemon=True)
        threads.append(t)
        t.start()
    try:
        for t in threads:
            t.join()
    except KeyboardInterrupt:
        graceful_exit()

    if retry_queue:
        print(Fore.YELLOW + f"[.] Retrying {len(retry_queue)} failed links...\n")
        queue.extend(retry_queue)
        retry_queue.clear()
        retry_threads = []
        for _ in range(thread_count):
            t = threading.Thread(target=process_url, args=(queue, onion_links, keywords, quiet, verbose, login_creds), daemon=True)
            retry_threads.append(t)
            t.start()
        for t in retry_threads:
            t.join()

    print(Fore.CYAN + Style.BRIGHT + "\nSummary:")
    print(Fore.CYAN + f"Accessible: {accessible_count}")
    print(Fore.CYAN + f"Inaccessible: {inaccessible_count}")
    print(Fore.CYAN + f"New Links Added: {added_links}")
    print(Fore.CYAN + f"Matched Links: {len(matched_data)}")
    for link, words, ts in matched_data:
        print(Fore.LIGHTGREEN_EX + f"\n[*] Match Found:\n    URL     : {link}\n    Keywords: {', '.join(words)}\n    Time    : {ts}")

if __name__ == '__main__':
    main()
