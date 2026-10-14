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
            print("SEO AUDIT",json.dumps(info,ensure_ascii=False)[:7500],flush=True)
    finally:d.quit()
if __name__=="__main__":main()
