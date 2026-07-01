
from flask import Flask, render_template, request, send_file
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse, urldefrag
from collections import Counter, deque
import requests, time, re, csv, io

app = Flask(__name__)
APP_NAME = "SEO Intelligence Pro"
UA = "SEOIntelligenceProBot/1.0"
LAST_REPORT = None

GUIDES = {
    "HTTP Error": ["Critical","Crawlability","Broken or unavailable URLs block users and search engines.","The page may be deleted, moved, blocked, or returning a server error.","Restore the page, redirect it to a relevant live URL, or remove links pointing to it.","Add a 301 redirect or fix the server-side error.","AI engines are less likely to cite unstable or inaccessible pages.","Important URLs should return 200 status codes.","https://developers.google.com/search/docs/crawling-indexing/http-network-errors"],
    "Missing Title": ["Critical","On-Page SEO","Titles help search engines and users understand the page topic.","The CMS template or SEO field is not outputting a title tag.","Add a unique, intent-focused title tag to every indexable page.","<title>Primary Keyword | Brand</title>","Use entity-rich and intent-focused wording for LLM understanding.","Keep titles unique, descriptive, and usually under 60 characters.","https://developers.google.com/search/docs/appearance/title-link"],
    "Duplicate Title": ["High","On-Page SEO","Duplicate titles reduce page differentiation.","Multiple pages use the same CMS title or template fallback.","Rewrite titles so each page targets a unique topic, service, product, or location.","Use dynamic title fields by page type.","Distinct titles improve AI and search interpretation.","Each indexable URL should have a unique title.","https://developers.google.com/search/docs/appearance/title-link"],
    "Missing Meta Description": ["High","On-Page SEO","Descriptions influence SERP messaging and CTR.","The description field is empty or not rendered.","Write a unique 140–155 character description with value proposition and intent.","<meta name=\"description\" content=\"Clear page summary with benefit and CTA.\">","Summarize the page clearly for AI snippets and answer engines.","Descriptions should match visible page content.","https://developers.google.com/search/docs/appearance/snippet"],
    "Missing H1": ["High","On-Page SEO","The H1 defines the main page topic and hierarchy.","The template may use styled text instead of semantic headings.","Add one clear H1 that describes the primary topic.","<h1>Primary Page Topic</h1>","Use question-led or entity-rich H1s where relevant.","One main H1 with supporting H2/H3 sections.","https://developers.google.com/search/docs/fundamentals/seo-starter-guide"],
    "Multiple H1": ["Medium","On-Page SEO","Multiple H1s can weaken content hierarchy.","Reusable sections may output H1 tags repeatedly.","Keep one main H1 and convert others to H2/H3.","Update section templates so only the hero uses H1.","Clear heading structure helps LLMs parse answers.","Use one main H1 per page.","https://developers.google.com/search/docs/fundamentals/seo-starter-guide"],
    "Missing Canonical": ["Medium","Indexability","Canonical tags help clarify the preferred URL version.","Canonical logic is missing from the page template.","Add a self-referencing canonical unless another URL is preferred.","<link rel=\"canonical\" href=\"https://example.com/preferred-url\">","Canonical clarity reduces duplicate entity confusion.","Every indexable page should have a correct canonical.","https://developers.google.com/search/docs/crawling-indexing/consolidate-duplicate-urls"],
    "Noindex Found": ["Critical","Indexability","Noindex prevents the page from appearing in search results.","A CMS, plugin, staging setting, or template is adding noindex.","Remove noindex if the page should rank.","Remove <meta name=\"robots\" content=\"noindex\"> or update to index,follow.","Noindexed pages are unlikely to be used by answer engines.","Only noindex pages that should be excluded.","https://developers.google.com/search/docs/crawling-indexing/block-indexing"],
    "Low Word Count": ["Medium","Content","Thin pages often fail to satisfy search intent.","The page has limited explanatory copy or weak content depth.","Expand the page with FAQs, benefits, proof, examples, and internal links.","Add editable content blocks for FAQs, use cases, and supporting copy.","Add concise answers, entities, examples, and evidence.","Prioritize usefulness and completeness over arbitrary word count.","https://developers.google.com/search/docs/fundamentals/creating-helpful-content"],
    "Images Missing ALT": ["Low","Accessibility & Image SEO","ALT text improves accessibility and image SEO.","Image components or CMS uploads are missing ALT fields.","Add descriptive ALT text to meaningful images.","<img src=\"service.jpg\" alt=\"AI website development team planning architecture\">","Descriptive image context can support multimodal AI understanding.","Describe images naturally without keyword stuffing.","https://developers.google.com/search/docs/appearance/google-images"],
    "Missing Schema": ["Medium","Schema & AI Search","Structured data helps search engines and AI systems understand entities.","JSON-LD schema is not implemented.","Add relevant schema such as Organization, Service, FAQPage, Article, BreadcrumbList, Product, or LocalBusiness.","<script type=\"application/ld+json\">{}</script>","Schema improves entity clarity for AI Overviews, ChatGPT Search, Gemini, Perplexity, and Copilot.","Use valid JSON-LD matching visible content.","https://schema.org/"],
    "Missing AEO Signals": ["High","AEO","Answer engines prefer clear question-and-answer content.","The page lacks FAQ sections, question headings, or concise answers.","Add FAQs covering what, why, how, cost, comparison, alternatives, and implementation questions.","Create FAQ blocks and add FAQPage schema where appropriate.","Use direct answers under question-based H2/H3 headings.","Answers should be concise, factual, and useful.","https://developers.google.com/search/docs/appearance/structured-data/faqpage"],
    "Missing GEO Signals": ["High","GEO","Generative engines need clear entities, evidence, and structured content.","The page lacks entity consistency, proof, author/company trust, or AI-friendly structure.","Add entity-rich sections, citations, proof points, schema, and clear summaries.","Add Organization schema, Breadcrumb schema, author/company blocks, and sameAs links.","Make the page citation-ready with clear claims and supporting proof.","Combine schema, topical depth, E-E-A-T, and answer-first content.","https://developers.google.com/search/docs/fundamentals/creating-helpful-content"],
    "Missing E-E-A-T Signals": ["High","E-E-A-T","Trust signals help users, search engines, and AI systems evaluate credibility.","The page lacks visible expertise, company, author, testimonial, review, or policy signals.","Add About, Contact, author, case study, testimonial, review, and policy signals.","Add author/company components and link them across key templates.","AI systems are more likely to cite trustworthy, attributed sources.","Make expertise and ownership clear.","https://developers.google.com/search/docs/fundamentals/creating-helpful-content"],
    "Slow Response": ["High","Performance","Slow pages weaken UX, crawl efficiency, and conversions.","Possible causes include slow hosting, uncached pages, heavy plugins, or database delays.","Improve hosting, caching, CDN, backend queries, and reduce heavy scripts.","Measure TTFB, enable page cache, compression, CDN, and optimize server response.","Fast pages are easier for crawlers and users to access consistently.","Monitor server response and Core Web Vitals.","https://web.dev/learn/performance/"]
}

IMPACT = {
    "Critical": {"Rankings":5,"Crawlability":5,"Indexing":5,"UX":4,"AI Search":5},
    "High": {"Rankings":4,"Crawlability":3,"Indexing":4,"UX":4,"AI Search":5},
    "Medium": {"Rankings":3,"Crawlability":2,"Indexing":3,"UX":3,"AI Search":3},
    "Low": {"Rankings":2,"Crawlability":1,"Indexing":2,"UX":2,"AI Search":2}
}

def stars(n):
    return "★"*n + "☆"*(5-n)

def norm(url):
    url = urldefrag(url.strip())[0]
    if not url.startswith(("http://","https://")):
        url = "https://" + url
    return url.rstrip("/")

def domain(url):
    return urlparse(norm(url)).netloc.lower().replace("www.","")

def same(url, root):
    h = urlparse(url).netloc.lower().replace("www.","")
    return h == root or h.endswith("." + root)

def get(url):
    start = time.time()
    try:
        r = requests.get(url, timeout=15, headers={"User-Agent": UA}, allow_redirects=True)
        return r, round(time.time()-start,2), None
    except Exception as e:
        return None, round(time.time()-start,2), str(e)

def add(issues, name, url, detail=""):
    g = GUIDES[name]
    sev = g[0]
    issues.append({
        "issue": name, "severity": sev, "category": g[1], "url": url, "detail": detail,
        "why": g[2], "root": g[3], "fix": g[4], "developer": g[5], "ai": g[6],
        "best": g[7], "reference": g[8],
        "impact": {k: stars(v) for k,v in IMPACT[sev].items()}
    })

def text_from(soup):
    for tag in soup(["script","style","noscript"]):
        tag.decompose()
    return " ".join(soup.get_text(" ").split())

def analyze(url, html, status, elapsed, depth, final_url):
    soup = BeautifulSoup(html, "html.parser")
    title = soup.title.get_text(strip=True) if soup.title else ""
    desc_tag = soup.find("meta", attrs={"name": re.compile("^description$", re.I)})
    desc = desc_tag.get("content","").strip() if desc_tag else ""
    h1s = soup.find_all("h1")
    canonical = soup.find("link", rel=lambda x: x and "canonical" in x)
    robots = soup.find("meta", attrs={"name": re.compile("^robots$", re.I)})
    robots_content = robots.get("content","").lower() if robots else ""
    text = text_from(soup)
    lower = text.lower()
    imgs = soup.find_all("img")
    links = []
    for a in soup.find_all("a", href=True):
        href = a.get("href","").strip()
        if not href or href.startswith(("mailto:","tel:","javascript:","#")):
            continue
        links.append(norm(urljoin(final_url, href)))
    return {
        "url": url, "status": status, "depth": depth, "response_time": elapsed,
        "title": title, "title_length": len(title), "description": desc, "description_length": len(desc),
        "h1_count": len(h1s),
        "canonical": canonical.get("href","").strip() if canonical else "",
        "noindex": "noindex" in robots_content,
        "word_count": len(re.findall(r"\b\w+\b", text)),
        "image_count": len(imgs),
        "missing_alt": len([i for i in imgs if not i.has_attr("alt")]),
        "schema_count": len(soup.find_all("script", attrs={"type":"application/ld+json"})),
        "aeo": bool(re.search(r"\b(faq|frequently asked|question|how|what|why|cost|best|compare|alternative)\b", lower)),
        "geo": bool(re.search(r"\b(author|organization|sameas|source|research|data|according to|case study|expert)\b", lower)),
        "eeat": bool(re.search(r"\b(about us|case stud|testimonial|review|certified|award|experience|expert|privacy policy|contact)\b", lower)),
        "links": links
    }

def crawl(start, max_pages):
    start = norm(start)
    root = domain(start)
    q = deque([(start,0)])
    seen = set()
    pages, issues, internal_links = [], [], []
    while q and len(seen) < max_pages:
        url, depth = q.popleft()
        if url in seen or not same(url, root):
            continue
        seen.add(url)
        r, elapsed, err = get(url)
        if err or not r:
            add(issues, "HTTP Error", url, err or "Request failed")
            continue
        if r.status_code >= 400:
            add(issues, "HTTP Error", url, f"Status code {r.status_code}")
            continue
        if "text/html" not in r.headers.get("content-type",""):
            continue
        p = analyze(url, r.text, r.status_code, elapsed, depth, norm(r.url))
        pages.append(p)

        if elapsed > 2.5: add(issues, "Slow Response", url, f"{elapsed}s")
        if not p["title"]: add(issues, "Missing Title", url)
        elif p["title_length"] < 25: add(issues, "Missing Title", url, f"Title too short: {p['title_length']} characters")
        if not p["description"]: add(issues, "Missing Meta Description", url)
        if p["h1_count"] == 0: add(issues, "Missing H1", url)
        if p["h1_count"] > 1: add(issues, "Multiple H1", url, f"{p['h1_count']} H1 tags")
        if not p["canonical"]: add(issues, "Missing Canonical", url)
        if p["noindex"]: add(issues, "Noindex Found", url)
        if p["word_count"] < 250: add(issues, "Low Word Count", url, f"{p['word_count']} words")
        if p["missing_alt"] > 0: add(issues, "Images Missing ALT", url, f"{p['missing_alt']} images")
        if p["schema_count"] == 0: add(issues, "Missing Schema", url)
        if not p["aeo"]: add(issues, "Missing AEO Signals", url)
        if not p["geo"]: add(issues, "Missing GEO Signals", url)
        if not p["eeat"]: add(issues, "Missing E-E-A-T Signals", url)

        for link in p["links"]:
            if same(link, root):
                internal_links.append({"source": url, "target": link})
                if link not in seen and len(seen)+len(q) < max_pages*3:
                    q.append((link, depth+1))

    titles = Counter([p["title"] for p in pages if p["title"]])
    for p in pages:
        if p["title"] and titles[p["title"]] > 1:
            add(issues, "Duplicate Title", p["url"], p["title"])

    sev = Counter([i["severity"] for i in issues])
    cat = Counter([i["category"] for i in issues])
    penalty = sev["Critical"]*7 + sev["High"]*4 + sev["Medium"]*2 + sev["Low"]
    scores = {
        "SEO Health": max(0,100-penalty),
        "Technical": max(0,100-(cat["Crawlability"]+cat["Indexability"]+cat["On-Page SEO"])*3),
        "AEO": max(0,100-cat["AEO"]*7),
        "GEO": max(0,100-cat["GEO"]*7),
        "AI Visibility": max(0,100-(cat["AEO"]+cat["GEO"]+cat["Schema & AI Search"]+cat["E-E-A-T"])*4),
        "Content": max(0,100-cat["Content"]*5),
        "Performance": max(0,100-cat["Performance"]*7)
    }
    return {"start": start, "pages": pages, "issues": issues, "severity": dict(sev), "category": dict(cat), "scores": scores, "summary": {"pages": len(pages), "issues": len(issues), "links": len(internal_links)}}

@app.route("/", methods=["GET","POST"])
def index():
    global LAST_REPORT
    report = None
    url = ""
    max_pages = 25
    if request.method == "POST":
        url = request.form.get("url","").strip()
        max_pages = int(request.form.get("max_pages","25"))
        report = crawl(url, max_pages)
        LAST_REPORT = report
    return render_template("index.html", app_name=APP_NAME, report=report, url=url, max_pages=max_pages)

@app.route("/export-csv")
def export_csv():
    if not LAST_REPORT:
        return "No report available", 400
    out = io.StringIO()
    fields = ["severity","category","issue","url","detail","why","root","fix","developer","ai","best","reference"]
    writer = csv.DictWriter(out, fieldnames=fields)
    writer.writeheader()
    for i in LAST_REPORT["issues"]:
        writer.writerow({f: i.get(f,"") for f in fields})
    mem = io.BytesIO(out.getvalue().encode("utf-8"))
    mem.seek(0)
    return send_file(mem, mimetype="text/csv", as_attachment=True, download_name="seo-intelligence-pro-audit.csv")

if __name__ == "__main__":
    app.run(debug=True)
