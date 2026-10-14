#!/usr/bin/env python3
"""Read-only SEO/AEO facts from the actual public homepage.

Shows markup presence, not rankings. Logs no private content.
"""
import json
import os
from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By

def main():
    opts=Options()
    opts.add_argument("--headless=new")
    opts.add_argument("--no-sandbox")
    opts.add_argument("--disable-dev-shm-usage")
    if os.environ.get("CHROME_BINARY"):opts.binary_location=os.environ["CHROME_BINARY"]
    svc=Service(executable_path=os.environ["CHROMEDRIVER_BINARY"]) if os.environ.get("CHROMEDRIVER_BINARY") else Service()
    d=webdriver.Chrome(options=opts,service=svc)
    try:
        for url in ("https://www.lauraelizabethhand.com/","https://www.lauraelizabethhand.com/about/"):
            d.get(url)
            info=d.execute_script("""
                const meta=(sel)=>[...document.querySelectorAll(sel)].map(x=>x.content||x.href).slice(0,3);
                const schemas=[...document.querySelectorAll('script[type="application/ld+json"]')]
                  .flatMap(x=>{try{const v=JSON.parse(x.textContent);return [v]}catch(e){return [{error:String(e)}]}});
                return {title:document.title,url:location.href,
                    description:meta('meta[name="description"]'),
                    canonical:meta('link[rel="canonical"]'),
                    robots:meta('meta[name="robots"]'),
                    ogTitle:meta('meta[property="og:title"]'),
                    schema:schemas};
            """)
            schemas=info["schema"]
            nodes=[node for block in schemas for node in block.get("@graph",[block])]
            website=[node for node in nodes if "WebSite" in [node.get("@type")] if isinstance(node,dict)]
            persons=[node for node in nodes if node.get("@type")=="Person"]
            assert website, "Yoast WebSite schema missing"
            assert info["canonical"] and info["canonical"][0].startswith("https://www.lauraelizabethhand.com/")
            assert not any("noindex" in r for r in info["robots"])
            assert "Laura Elizabeth Hand" in info["title"]
            assert "Laura Elizabeth" in " ".join(info["description"])
            if url.endswith(".com/"):
                assert any(n.get("alternateName")=="Laura Elizabeth" and n.get("name")=="Laura Elizabeth Hand"
                           for n in persons), "Person schema missing the shorter-name identity"
                assert any("github.com/hand-lauraelizabeth" in str(n.get("sameAs")) for n in persons), "Public profile source missing"
            else:
                profiles=[node for node in nodes if node.get("@type")=="ProfilePage"]
                assert len(profiles)==1, "About page needs one valid ProfilePage identity node"
                me=profiles[0].get("mainEntity",{})
                assert me.get("@id")=="https://www.lauraelizabethhand.com/#laura-elizabeth-hand"
                assert me.get("name")=="Laura Elizabeth Hand" and me.get("alternateName")=="Laura Elizabeth"
                visible=d.execute_script("return document.body.innerText")
                assert "also known as Laura Elizabeth" in visible, "About page doesn't show shortened name visibly"
                print("PASS profile identity",json.dumps({"type":"ProfilePage","id":me.get("@id"),
                      "name":me.get("name"),"alternateName":me.get("alternateName")}),flush=True)
            print("PASS SEO",json.dumps({"url":url,"title":info["title"],"description":info["description"],
                 "canonical":info["canonical"],"robots":info["robots"],"websiteCount":len(website),
                 "person":persons},ensure_ascii=False)[:4200],flush=True)
    finally:d.quit()
if __name__=="__main__":main()
