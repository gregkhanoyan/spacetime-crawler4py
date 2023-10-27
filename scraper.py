import re
# comment out requests when running in openlab
import requests
from urllib.parse import urlparse, urljoin, urldefrag, unquote
from bs4 import BeautifulSoup
from collections import Counter
from difflib import SequenceMatcher
from robotexclusionrulesparser import RobotExclusionRulesParser

seed = "https://ics.uci.edu/" 
# seed = "https://sami.ics.uci.edu/research.html"

# linkSet will transform list of links into a set to remove duplicates
linkSet = set()

# set that stores all the domains for robots.txt
domainSet = set()

# pagewordCounts dictionary will hold url and word count
pageWordCounts = {}

# subdomainCounts dictionary will hold subdomains and their frequency
subdomainCounts = {}

# wordCounter will hold number of times a certain word is read
wordCounter = Counter()

user_agent = "IR UF23 11539047,55544104"

# list of stopwords
# why are there 2 equals lmao
stopWords = stopwords = set([
    "a", "about", "above", "after", "again", "against", "all", "am", "an", "and", "any", 
    "are", "aren't", "as", "at", "be", "because", "been", "before", "being", "below", 
    "between", "both", "but", "by", "can't", "cannot", "could", "couldn't", "did", "didn't", 
    "do", "does", "doesn't", "doing", "don't", "down", "during", "each", "few", "for", 
    "from", "further", "had", "hadn't", "has", "hasn't", "have", "haven't", "having", "he", 
    "he'd", "he'll", "he's", "her", "here", "here's", "hers", "herself", "him", "himself", 
    "his", "how", "how's", "i", "i'd", "i'll", "i'm", "i've", "if", "in", "into", "is", 
    "isn't", "it", "it's", "its", "itself", "let's", "me", "more", "most", "mustn't", "my", 
    "myself", "no", "nor", "not", "of", "off", "on", "once", "only", "or", "other", "ought", 
    "our", "ours", "ourselves", "out", "over", "own", "same", "shan't", "she", "she'd", 
    "she'll", "she's", "should", "shouldn't", "so", "some", "such", "than", "that", "that's", 
    "the", "their", "theirs", "them", "themselves", "then", "there", "there's", "these", "they", 
    "they'd", "they'll", "they're", "they've", "this", "those", "through", "to", "too", "under", 
    "until", "up", "very", "was", "wasn't", "we", "we'd", "we'll", "we're", "we've", "were", 
    "weren't", "what", "what's", "when", "when's", "where", "where's", "which", "while", "who", 
    "who's", "whom", "why", "why's", "with", "won't", "would", "wouldn't", "you", "you'd", 
    "you'll", "you're", "you've", "your", "yours", "yourself", "yourselves"
])

valid_domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]

def scraper(url, resp):
    if is_valid(url):
        if resp.status_code == 408:
            print("timeout")
            return
        # print("Testing URL: " , url)
        # try:
        #     resp = requests.get(url)
        # except:
        #     print("Timeout")

        # Fixes URL's having / at the end being different from not

        url = url.rstrip("/")

        # Function call to extract_next_links in order to retrieve hyperlinks/pages
        links = extract_next_links(url, resp)
        # print(links)

        if links is not None:
            for link in links:
                if link not in linkSet:
                    linkSet.add(link)
        else:
            print("No more links here! Moving on...")
            # return

        # print("LINK LENGTH: ", len(links))

        # why do we do this?
        if links is not None and url in links:
            links.remove(url)

        # print("Extracted Links:")

        if(links is not None):
            linkSet.update(links)
            # Find number of unique pages
            uniquePages = len(linkSet)
            print("Number of Unique Pages: ", uniquePages)
        
        # Store word count for the current URL
        if resp.text and resp.text is not None:
            content = resp.text
            pageWordCounts[url] = count_words(content)

            # Update wordCounter for each tokenized word, not including stop words
            tokens = tokenize(content)
            for word in tokens:
                if word not in stopWords:
                    wordCounter[word] += 1

        # parsed_url = urlparse(url)
        # if parsed_url.netloc.endswith('ics.uci.edu'):
            
        #     # Extract the subdomain part
        #     subdomain = parsed_url.netloc.rsplit('.', 2)[0]

        #     if subdomain == 'ics':
        #         subdomain = parsed_url.netloc.rsplit('.', 3)[1]
            
        #     # Increment count for the subdomain or initialize it if it doesn't exists
        #     subdomainCounts[subdomain] = subdomainCounts.get(subdomain, 0) + 1

        # if links is not None:
            # for link in links:
        # if linkSet is not None:
        #     for link in linkSet:
        #         print(link)
    else:
        print(url, " is not a valid URL for crawling.")



    # Find the url of the longest page in terms of words count
    if pageWordCounts:
        # how does this work?
        longest_page_url = max(pageWordCounts, key=pageWordCounts.get)
        print("Longest Page URL: ", longest_page_url, " - with ", pageWordCounts[longest_page_url], " words!")

    # Get the 50 most common words
    most_common_words = wordCounter.most_common(50)
    print("50 Most Common Words:", most_common_words)

    # Print out the counts for each subdomain
    sorted_subdomains = sorted(subdomainCounts.items(), key=lambda x: x[0])  # Sort by subdomain name
    for subdomain, count in sorted_subdomains:
        print(f"http://{subdomain}.ics.uci.edu, {count}")

    links_return = []

    for link in linkSet:
        if is_valid(link):
            links_return.append(link)

    # returns a list of links
    return links_return
    # return [link for link in links if is_valid(link)]
    
def extract_next_links(url, resp):
    link_list = []

    # checking if we actually got the page
    # do we have to check utf-8 encoding?
    # print(resp.status_code)
    # print(resp.headers)
    # print(resp.status_code)
    if resp.status_code == 200:
        try:
            # use BeautifulSoup library to parse the HTML content of the page
            # print("Raw Content: ", raw)

            soup = BeautifulSoup(resp.text, 'html.parser')

            
            # we want to eliminate the possibility of a 404 page which doesnt return 
            # an error 404 code, such as http://cs.uci.edu/page
            # title_tag = soup.find("title")
            # invalid_title = "Page not found"

            # # checks if Page not found is title, if so break of function
            # if title_tag and invalid_title:
            #     return

            # in the HTML, we want to find all '<a>' tags and extract the link, the 'href'
            for curr in soup.find_all('a'):
                link = curr.get('href')
                if link:
                    
                    # we then use 'urllib.parse: urljoin' in order to combine the relative URL's with our base URL in order to get our final URL
                    url_joined = urljoin(url, link)

                    url_joined = url_joined.rstrip("/")

                    # Use 'urllibe.parse: urldefrag' to remove the fragment, as in this assignment we ignore the fragment 
                    if "#" in url_joined:
                        url_joined = urldefrag(url_joined).url

                    # print("QUOTED: ", url_joined)
                    final_url  = unquote(url_joined)
                    # print(final_url)
                    # print("UNQUOTED: ", url_joined)

                    # checks validity of our final_url - if it is valid, then we can add it to our list of links
                    if is_valid(final_url) and not_similar(final_url):
                        parsed_url = urlparse(final_url)
                        domain = parsed_url.netloc
                        path = parsed_url.path
                        robots_url = f"http://{domain}/robots.txt"
                        robots_subdomain_url = f"http://{domain}{path}/robots.txt"
                        print(robots_subdomain_url)

                        if robots_url not in domainSet:
                            domainSet.add(robots_url)
                            

                        parser = RobotExclusionRulesParser()
                        parser.fetch(robots_url)
                    
                        if parser.is_allowed(user_agent, final_url): # tab next line
                            link_list.append(final_url)

        except Exception as e:
            print("ERROR: Error parsing " + url + " " +str(e))       
    # if the response code was something other than 200, means there was an error - print it so we can see
    else:
        print("Error: " + str(resp.status_code))
        return

    return link_list

# FUNCTION: is_valid(url) - checks the validity of a URL:str passed in - returns a boolean True or False
def is_valid(url):
    try:
        parsed = urlparse(url)
        if parsed.scheme not in set(["http", "https"]):
            return False
        
        url = unquote(url)

        # List of disallowed file extensions
        invalid = [
            "css", "js", "bmp", "gif", "jpg", "jpeg", "ico",
            "png", "tif", "tiff", "mid", "mp2", "mp3", "mp4",
            "wav", "avi", "mov", "mpeg", "ram", "m4v", "mkv", "ogg", "ogv", "pdf",
            "ps", "eps", "tex", "ppt", "pptx", "doc", "docx", "xls", "xlsx", "names",
            "data", "dat", "exe", "bz2", "tar", "msi", "bin", "7z", "psd", "dmg", "iso",
            "epub", "dll", "cnf", "tgz", "sha1", "thmx", "mso", "arff", "rtf", "jar", "csv",
            "rm", "smil", "wmv", "swf", "wma", "zip", "rar", "gz" , "img", "mpg"
        ]

        # List of valid domains we can crawl in
        domains = ["ics.uci.edu", "cs.uci.edu", "informatics.uci.edu", "stat.uci.edu"]

        # Check if the parsed domain matches any of the allowed domains
        domain_check = any(parsed.netloc.endswith("." + domain) or parsed.netloc == domain for domain in domains)

        # Check if the path doesn't have invalid extensions
        extension_check = not any(parsed.path.lower().endswith("." + filetype) for filetype in invalid)

        # return the boolean expression determined by the logical AND of domain_match and extension_match
        # if the url exists in our valid domains and does not fall under any of the invalid extensions, return True, else return False
        return domain_check and extension_check

    except TypeError:
        print("TypeError for ", parsed)
        raise

def tokenize(content):
    # Strip HTML markup
    soup = BeautifulSoup(content, 'html.parser')
    newContent = soup.get_text()

    # Splits words and creates list, non word characters act as the break
    # cleanTokens will set all tokens lower case and will discard any tokens with length less than 2 letters
    tokens = re.split(r'\W+', newContent)
    cleanTokens = []
    for token in tokens:
        if len(token) > 2:
            token.lower()
            cleanTokens.append(token)

    return cleanTokens

def count_words(content):
    # Strip HTML markup
    soup = BeautifulSoup(content, 'html.parser')
    newContent = soup.get_text()

    # Use regex to count the number of words in the content
    words = re.findall(r'\w+', newContent)
    return len(words)

def not_similar(url):
    flag = True
    # print("URL OG: ", url)
    parsed = urlparse(url)
    # print("Parsed URL OG", parsed)

    for other_url in linkSet:
        # print("other_url: ", other_url)
        other_parsed = urlparse(other_url)
        # print("Other Parsed: ", other_parsed)

        domain_similarity = SequenceMatcher(None, parsed.netloc, other_parsed.netloc).ratio()
        # print(domain_similarity)
        path_similarity = SequenceMatcher(None, parsed.path, other_parsed.path).ratio()
        # print(path_similarity)
        query_similarity = SequenceMatcher(None, parsed.query, other_parsed.query).ratio()
        # print(query_similarity)

        if (domain_similarity == 1 and path_similarity > 0.6):
            flag = False
            return flag
            # print("Similar")
        else:
            flag = True
            # print("Not Similar")
    return flag

# LOCAL DRIVER

resp = requests.get(seed)
urlsss = scraper(seed, resp)

print("URL's Scraped From Seed")
for i in urlsss:
    print(i)

# url1 = "https://wics.ics.uci.edu/events/2022-01-28/"
# url2 = "https://wics.ics.uci.edu/events/2022-02-19"
# url1 = "https://ics.uci.edu/happening/news/?filter%5Baffiliation_posts%5D=1990"
# url2 = "https://ics.uci.edu/happening/news/?filter%5Bresearch_areas_ics%5D=1994"
# url1 = "https://grape.ics.uci.edu/wiki/public/timeline?from=2019-03-13T22%3A33%3A25-07%3A00&precision=second"
# url2 = "https://grape.ics.uci.edu/wiki/public/timeline?from=2019-01-09T23%3A07%3A19-08%3A00&precision=second"

# url1_parsed = urlparse(url1)
# url2_parsed = urlparse(url2)

# domain = SequenceMatcher(None, url1_parsed.netloc, url2_parsed.netloc).ratio()
# path = SequenceMatcher(None, url1_parsed.path, url2_parsed.path).ratio()
# query = SequenceMatcher(None, url1_parsed.query, url2_parsed.query).ratio()

# print("DOMAIN SIMILARITY: " , domain)
# print("PATH SIMILARITY: " , path)
# print("QUERY SIMILARITY: " , query)

# url3 = unquote(url1)
# url4 = unquote(url2)

# url3_parsed = urlparse(url3)
# url4_parsed = urlparse(url3)
# print(url3_parsed)
# print(url4_parsed)

# domain = SequenceMatcher(None, url3_parsed.netloc, url4_parsed.netloc).ratio()
# path = SequenceMatcher(None, url3_parsed.path, url4_parsed.path).ratio()
# query = SequenceMatcher(None, url3_parsed.query, url4_parsed.query).ratio()

# print("DOMAIN SIMILARITY: " , domain)
# print("PATH SIMILARITY: " , path)
# print("QUERY SIMILARITY: " , query)

# linkSet.add(url4)
# print(linkSet)

# if not_similar(url3):
#     print("The URL's are not similar!")
# else:
#     print("The URL's are too similar! Disregarding!")

# urls = [
#     "http://ics.uci.edu/robots.txt",
#     "http://ics.uci.edu/robots.txt",
#     "http://ics.uci.edu/admissions-information-and-computer-science/robots.txt",
#     "http://ics.uci.edu/facts-figures/ics-mission-history/robots.txt",
#     "http://ics.uci.edu/facts-figures/robots.txt",
#     "http://ics.uci.edu/admissions-information-and-computer-science/robots.txt",
#     "http://ics.uci.edu/admissions-information-and-computer-science/admissions-process/robots.txt",
#     "http://ics.uci.edu/admissions-information-and-computer-science/graduate-admissions/robots.txt",
#     "http://ics.uci.edu/financial-aid-and-scholarships/undergraduate-financial-awards/robots.txt",
#     "http://ics.uci.edu/academics/graduate-fellowships-funding/robots.txt",
#     "http://ics.uci.edu/student-experience/robots.txt",
#     "http://ics.uci.edu/academics/undergraduate-programs/robots.txt",
#     "http://ics.uci.edu/academics/undergraduate/robots.txt",
#     "http://ics.uci.edu/honors/robots.txt",
#     "http://ics.uci.edu/academics/undergraduate-academic-advising/robots.txt",
#     "http://ics.uci.edu/academics/graduate-programs/robots.txt",
#     "http://ics.uci.edu/academics/graduate-programs/robots.txt",
#     "http://ics.uci.edu/academics/graduate-programs/robots.txt",
#     "http://ics.uci.edu/academics/graduate-academic-advising/robots.txt",
#     "http://ics.uci.edu/student-experience/robots.txt",
#     "http://oai.ics.uci.edu/robots.txt",
#     "http://ics.uci.edu/academics/career-development/robots.txt",
#     "http://ics.uci.edu/student-experience/clubs-organizations/robots.txt",
#     "http://ics.uci.edu/student-experience/entrepreneurship-student-experience/robots.txt",
#     "http://ics.uci.edu/student-experience/undergraduate-research/robots.txt",
#     "http://ics.uci.edu/academics/campus-resources/robots.txt",
#     "http://ics.uci.edu/computing-research/robots.txt",
#     "http://ics.uci.edu/computing-research/robots.txt",
#     "http://ics.uci.edu/research-areas/robots.txt",
#     "http://ics.uci.edu/departments/robots.txt",
#     "http://www.cs.uci.edu/robots.txt",
#     "http://www.informatics.uci.edu/robots.txt",
#     "http://www.stat.uci.edu/robots.txt",
#     "http://ics.uci.edu/computing-research/institutes-centers/robots.txt",
#     "http://futurehealth.ics.uci.edu/robots.txt",
#     "http://hpi.ics.uci.edu/robots.txt",
#     "http://cml.ics.uci.edu/robots.txt",
#     "http://create.ics.uci.edu/robots.txt",
#     "http://ics.uci.edu/academics/impact/robots.txt",
#     "http://ics.uci.edu/academics/impact/faculty-awards-honors/robots.txt",
#     "http://ics.uci.edu/academics/impact/student-awards-honors/robots.txt",
#     "http://ics.uci.edu/academics/impact/academic-placements-of-alumni/robots.txt",
#     "http://ics.uci.edu/academics/impact/technology-transfer/robots.txt",
#     "http://ics.uci.edu/people/robots.txt",
#     "http://ics.uci.edu/happening/news/robots.txt",
#     "http://ics.uci.edu/happening/news/robots.txt",
#     "http://ics.uci.edu/happening/news//robots.txt",
#     "http://ics.uci.edu/happening/news//robots.txt",
#     "http://ics.uci.edu/happening/news//robots.txt",
#     "http://ics.uci.edu/happening/news//robots.txt",
#     "http://ics.uci.edu/upcoming-events/robots.txt",
#     "http://ics.uci.edu/events/robots.txt",
#     "http://ics.uci.edu/seminar-series-2/distinguished-lectures/robots.txt",
#     "http://www.cs.uci.edu/events/seminar-series/robots.txt",
#     "http://www.informatics.uci.edu/explore/department-seminars/robots.txt",
#     "http://www.stat.uci.edu/seminar-series/robots.txt",
#     "http://hpi.ics.uci.edu/hpiuci-2022-grand-opening-event/robots.txt",
#     "http://cml.ics.uci.edu/aiml/robots.txt",
#     "http://create.ics.uci.edu/events/robots.txt",
#     "http://ics.uci.edu/happening/annual-reports-brochures/robots.txt",
#     "http://ics.uci.edu/alumni/corporate-engagement/robots.txt",
#     "http://ics.uci.edu/alumni/robots.txt",
#     "http://www.ics.uci.edu/events/list//robots.txt",
#     "http://ics.uci.edu/alumni/hall-of-fame/robots.txt",
#     "http://ics.uci.edu/alumni/corporate-engagement/robots.txt",
#     "http://ics.uci.edu/alumni/corporate-engagement/capstone-projects-corporate-engagement/robots.txt",
#     "http://ics.uci.edu/alumni/corporate-engagement/research-partnerships-corporate-engagement/robots.txt",
#     "http://ics.uci.edu/alumni/corporate-engagement/student-recruitment-corporate-engagement/robots.txt",
#     "http://ics.uci.edu/alumni/corporate-engagement/corporate-partners/robots.txt",
#     "http://ics.uci.edu/alumni/industry-advisory-council/robots.txt",
#     "http://ics.uci.edu/alumni/ics-advisory-board/robots.txt",
#     "http://ics.uci.edu/make-a-gift/robots.txt",
#     "http://ics.uci.edu/contact-us/robots.txt",
#     "http://ics.uci.edu/follow-us/robots.txt",
#     "http://ics.uci.edu/make-a-gift/robots.txt",
#     "http://ics.uci.edu/robots.txt",
#     "http://ics.uci.edu/2023/10/05/ics-welcomes-largest-incoming-class/robots.txt",
#     "http://ics.uci.edu/academics/undergraduate-programs/robots.txt",
#     "http://ics.uci.edu/academics/graduate-programs/robots.txt",
#     "http://ics.uci.edu/academic-recruitment/robots.txt",
#     "http://ics.uci.edu/2023/10/25/the-surprisingly-subtle-ways-microsoft-word-has-changed-the-way-we-use-language-bbc/robots.txt",
#     "http://ics.uci.edu/category/article/robots.txt",
#     "http://ics.uci.edu/2023/10/18/ruslan-manoharan-cracking-the-code-of-community-at-uci/robots.txt",
#     "http://ics.uci.edu/category/academics/computer-science/robots.txt",
#     "http://ics.uci.edu/2023/10/16/in-the-news-are-attention-spans-getting-shorter-and-does-it-matter-cbs-news/robots.txt",
#     "http://ics.uci.edu/category/article/robots.txt",
#     "http://ics.uci.edu/2023/10/16/advancing-storyai-the-vital-prize-challenge/robots.txt",
#     "http://ics.uci.edu/category/academics/informatics/robots.txt",
#     "http://ics.uci.edu/2023/10/13/eunkyung-jo-awarded-2023-google-fellowship/robots.txt",
#     "http://ics.uci.edu/category/article/awards/robots.txt",
#     "http://ics.uci.edu/2023/10/12/in-the-news-spectrum1-next-gen-health-care-phit/robots.txt",
#     "http://ics.uci.edu/category/article/robots.txt",
#     "http://ics.uci.edu/happening/news/robots.txt",
#     "http://create.ics.uci.edu/robots.txt",
#     "http://hpi.ics.uci.edu/robots.txt",
#     "http://ics.uci.edu/event/cascade-a-platform-for-fast-edge-intelligence/robots.txt",
#     "http://cs.uci.edu/events/seminar-series/robots.txt",
#     "http://ics.uci.edu/event/access-is-capture-datafication-race-and-education/robots.txt",
#     "http://informatics.uci.edu/explore/department-seminars/robots.txt",
#     "http://ics.uci.edu/event/ai-ml-seminar-tba/robots.txt",
#     "http://ics.uci.edu/event/core-stability-in-markets-with-budget-constrained-bidders/robots.txt",
#     "http://ics.uci.edu/event/department-of-statistics-seminar-series-statistical-inference-in-reinforcement-learning/robots.txt",
#     "http://stat.uci.edu/seminar-series/robots.txt",
#     "http://ics.uci.edu/event/how-language-models-work-and-thats-why-they-dont/robots.txt",
#     "http://informatics.uci.edu/explore/department-seminars/robots.txt",
#     "http://ics.uci.edu/events/robots.txt",
#     "http://ics.uci.edu/robots.txt",
#     "http://ics.uci.edu/people/robots.txt",
#     "http://ics.uci.edu/faculty-staff-resources/robots.txt",
#     "http://ics.uci.edu/faculty-staff-positions/robots.txt",
#     "http://ics.uci.edu/accessibility-statement/robots.txt"
# ]


# for url in urls:
#     resp = requests.get(url)
#     if resp.status_code != 200:
#         print("CODE: ", resp.status_code, " - URL: ", url)
#     else:
#         print("CODE : 200", " - URL: ", url)

