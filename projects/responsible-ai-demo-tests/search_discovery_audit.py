#!/usr/bin/env python3
"""Public indexing discovery audit: robots directives, XML sitemap, canonical roots.

A read-only diagnostic; this does not access Google Search Console or
claim that any URL is indexed, ranked, or accepted by a search provider.
"""
from __future__ import annotations

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree as ET
from urllib.parse import urljoin
import re

ROOT="https://www.lauraelizabethhand.com/"
UA="Mozilla/5.0 (compatible; PortfolioSearchAudit/1.0)"
urls=[
 "robots.txt","sitemap_index.xml","wp-sitemap.xml","page-sitemap.xml"
]

def fetch(url):
    req=Request(url,headers={"User-Agent":UA,"Accept":"text/xml,text/plain,application/xml,*/*"})
    try:
        with urlopen(req,timeout=20) as resp:
            data=resp.read(2_000_000)
            return resp.status,resp.url,data.decode("utf-8","replace"),resp.headers.get("Content-Type","")
    except HTTPError as exc:
        return exc.code,url,"",str(exc)
    except URLError as exc:
        return 0,url,str(exc),""

def sitemap_locs(body):
    try: xml=ET.fromstring(body)
    except ET.ParseError:return []
    if xml.tag.rsplit("}",1)[-1] not in ("sitemapindex","urlset"):return []
    return [n.text for n in xml.iter() if n.tag.rsplit("}",1)[-1]=="loc" and n.text]

def main():
    results={}
    for path in urls:
        url=urljoin(ROOT,path)
        status,final,body,content_type=fetch(url)
        locs=sitemap_locs(body)
        results[path]=(status,final,locs,body)
        print("DISCOVERY",path,"HTTP",status,"redirect-to",final,
              "locations",len(locs),"content-type",content_type,flush=True)
        if locs: print("SITEMAP SAMPLE",path,locs[:8],flush=True)
    status,final,_,body=results["robots.txt"]
    if status==200:
        print("ROBOTS BODY",body[:1800],flush=True)
        disallow=[x for x in body.splitlines()
                  if re.match(r"^\s*Disallow\s*:\s*/\s*(?:#.*)?$",x,re.I)]
        # This pattern is conservative. A disallow appearing only for another
        # user-agent may not block Google; inspect output if flagged.
        assert not disallow,"Possible blanket crawl prohibition: "+str(disallow)

    candidates=[p for p in ("sitemap_index.xml","wp-sitemap.xml") if results[p][0]==200
                and results[p][2]]
    assert candidates, "No indexable XML sitemap found at standard Yoast or WP location."
    idx=candidates[0]
    locs=results[idx][2]
    discovered_page=False
    for link in locs[:35]:
        if "page" in link and link.endswith(".xml"):
            code,final,body,_=fetch(link)
            pages=sitemap_locs(body)
            print("SITEMAP PAGES",link,"HTTP",code,"total",len(pages),
                  "homepagePresent",ROOT in pages,
                  "aboutPresent",urljoin(ROOT,"about/") in pages,flush=True)
            if "https://www.lauraelizabethhand.com/about/" in pages:discovered_page=True
    if idx=="sitemap_index.xml":
        assert discovered_page, "Page sitemap does not list About URL, investigate Yoast indexability"
    print("PASS robots/sitemap basic discovery audit; Search Console indexing status not available.",flush=True)

if __name__=="__main__":
    main()
