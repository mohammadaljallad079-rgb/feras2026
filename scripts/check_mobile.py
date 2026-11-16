from playwright.sync_api import sync_playwright
B="http://localhost:12000"
ROUTES=["/dashboard","/companies","/leads","/reports","/hr","/users","/audit","/accounting","/service-requests"]
with sync_playwright() as p:
    br=p.chromium.launch(executable_path="/usr/bin/chromium",args=["--no-sandbox"])
    ctx=br.new_context(viewport={"width":400,"height":900})
    pg=ctx.new_page()
    pg.goto(f"{B}/login"); pg.fill("#email","owner@safir-platform.com"); pg.fill("#password","Safir!2026")
    pg.click("button[type=submit]"); pg.wait_for_url("**/dashboard",timeout=20000)
    bad=[]
    for r in ROUTES:
        pg.goto(f"{B}{r}"); pg.wait_for_timeout(900)
        m=pg.evaluate("() => ({sw: document.documentElement.scrollWidth, cw: document.documentElement.clientWidth, bw: document.body.scrollWidth})")
        flag = "OVERFLOW" if m["sw"]>m["cw"] else "ok"
        if m["sw"]>m["cw"]: bad.append(r)
        print(f"{r.ljust(20)} scrollWidth={m['sw']} clientWidth={m['cw']} {flag}")
    print("HORIZONTAL OVERFLOW AT 400px:", bad or "none")
    br.close()
