<h1>DrkScrape</h1>
A multithreaded web scraper to crawl .onion (Dark Web) websites via the Tor network, search for specified keywords, and optionally attempt login on discovered pages. Includes retry handling, graceful exit, JSON logging, and final scanning summary.

<h1> Features: </h1>
<ul>
<li>Crawl Tor hidden services using SOCKS5 proxy</li>
<li>Search for custom keywords in HTML content</li>
<li>Extract and queue new .onion links recursively</li>
<li>Multithreaded for improved performance</li>
<li>Graceful exit with automatic data saving</li>
<li>Retry failed links once before marking as permanently failed</li>
<li>Option to attempt login using supplied credentials</li>
<li>JSON output logging and optional summary output</li>
</ul>


<h1> Installation: </h1>
<code>pip install -r requirements.txt </code>
<br>
<h3>Tor Setup (Required)</h3>

<b>Step 1:</b> Install Tor
On Debian/Ubuntu:
<code>sudo apt update && sudo apt install tor</code>

<b>Step 2:</b> Start the Tor service

<code>sudo service tor start</code>

<p>NOTE: Ensure Tor is running and listening on localhost:9050, which is the default. </p>

<h1>Usage</h1>

<p> python scraper.py [keyword1] [keyword2] ... [options] </p>

<h3>Options:</h3>

<b>-s, --silent</b> : Suppress all output except keyword matches

<b>-v, --verbose</b> : Show verbose error info for inaccessible links

</b>-l, --login</b> : Prompt for username and password to attempt login

<b>-t, --threads <N></b> : Use N threads (default: 5)

<b>-j, --json</b> : Show previous matched keywords from output.json

<b>-h, --help</b> : Show help menu

<h3>Example:</h3>

<code>python scraper.py login bitcoin -s -v -t 10</code>


<h1>Output</h1>

All visited URLs saved to onion_links.txt

Matched results saved in output.json

Failed URLs after retry saved to failed_links.txt

Final summary shows count of accessible, inaccessible, added, and matched links



<h1>Technical Stack</h1>

<b>Language:</b> Python 3

<b>Libraries:</b> requests, bs4, colorama, urllib3, argparse, json

<b>Techniques:</b> multithreading, proxy configuration, Tor integration

<br>
<h4>By: <a href="https://tryhackme.com/p/DrkDeath">DrkDeath</a></h4>
