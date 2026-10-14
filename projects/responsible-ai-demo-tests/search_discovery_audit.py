#!/usr/bin/env python3
"""Inspect public crawler discovery without asserting actual Google indexing.

A server can block Python/GitHub automation while allowing browsers and
verified search crawlers; compare both transports before flagging a problem.
"""
from __future__ import annotations

from urllib.request import Request, urlopen
from urllib.error import HTTPError, URLError
from xml.etree import ElementTree as ET
from urllib.parse import urljoin, urlparse
import os
import re
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service

ROOT="https://www.lauraelizabethhand.com/"
CHECK=["robots.txt","sitemap_index.xml","wp-sitemap.xml","page-sitemap.xml"]

def direct(url):
    req=Request(url,headers={"User-Agent":"Mozilla/5.0 (compatible; PortfolioSearchAudit/1.0)",
                            "Accept":"text/xml,text/plain,application/xml,*/*"})
    try:
        with urlopen(req,timeout=15) as resp:
            return resp.status,resp.read(2_000_000).decode("utf-8","replace")
    except HTTPError as exc:
        return exc.code,""
    except URLError as exc:
        return 0,str(exc)

def locs(body):
    try:root=ET.fromstring(body)
    except ET.ParseError:return []
    if root.tag.rsplit("}",1)[-1] not in ("sitemapindex","urlset"):return []
    return [n.text for n in root.iter()
            if n.tag.rsplit("}",1)[-1]=="loc" and n.text]

def make_browser():
    opts=webdriver.ChromeOptions()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    if os.environ.get("CHROME_BINARY"):opts.binary_location=os.environ["CHROME_BINARY"]
    svc=Service(executable_path=os.environ["CHROMEDRIVER_BINARY"]) if os.environ.get("CHROMEDRIVER_BINARY") else Service()
    d=webdriver.Chrome(options=opts,service=svc)
    d.set_script_timeout(30)
    d.get(ROOT)
    assert "Laura Elizabeth Hand" in d.title,"Homepage not accessible to audit browser"
    return d

def browser_fetch(driver,url):
    # Same-origin browser request after a successful homepage load.
    if urlparse(url).netloc != urlparse(ROOT).netloc:
        return 0,"external host outside audited site"
    try:
        result=driver.execute_async_script("""
           const url=arguments[0],done=arguments[arguments.length-1];
           fetch(url,{credentials:'same-origin',cache:'no-store'})
             .then(async r=>done([r.status,(await r.text()).slice(0,2000000)]))
             .catch(e=>done([0,String(e)]));
        """,url)
        return result[0],result[1]
    except Exception as exc:
        return 0,str(exc)

def main():
    driver=make_browser()
    data={}
    try:
        for path in CHECK:
            url=urljoin(ROOT,path)
            code,body=direct(url)
            bcode,bbody=browser_fetch(driver,url)
            effective=bbody if bcode==200 else body
            data[path]=(code,bcode,effective,locs(effective))
            print("DISCOVERY",path,"direct HTTP",code,"browser HTTP",bcode,
                  "XML locations",len(data[path][3]),flush=True)
            if data[path][3]:print("SITEMAP SAMPLE",path,data[path][3][:6],flush=True)
            if path=="robots.txt" and bcode==200:print("ROBOTS",bbody[:1200],flush=True)

        robots=data["robots.txt"]
        # We do not infer a blanket crawl block from isolated Disallow lines:
        # relevant user-agent groups and verified Googlebot need separate checks.
        if robots[1] in (401,403):
            print("WARNING: Browser also denied robots.txt; inspect hosting/security logs and Googlebot verification.",flush=True)
        candidates=[p for p in ("sitemap_index.xml","wp-sitemap.xml") if data[p][1]==200 and data[p][3]]
        if candidates:
            candidate=candidates[0]
            print("PASS browser-accessible XML sitemap:",candidate,flush=True)
            for link in data[candidate][3][:25]:
                if "page" not in link or not link.endswith(".xml"):continue
                status,pages=browser_fetch(driver,link)
                pageurls=locs(pages)
                print("PAGES IN SITEMAP",link,"HTTP",status,
                      "count",len(pageurls),"about present",ROOT+"about/" in pageurls,flush=True)
                if status==200 and candidate=="sitemap_index.xml":
                    assert ROOT+"about/" in pageurls, "About missing from published page sitemap"
        else:
            print("UNRESOLVED: Browser could not fetch a standard XML sitemap. "
                  "It may be blocked to this runner; Google Search Console/hosting logs are required.",flush=True)
            raise AssertionError("No fetchable XML sitemap even with browser session.")
    finally:driver.quit()

if __name__=="__main__":main()
