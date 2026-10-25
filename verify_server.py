import urllib.request

urls = [
    '/',
    '/find-blood',
    '/request-blood',
    '/track-request',
    '/about',
    '/faq',
    '/contact',
    '/login',
    '/register/donor',
    '/register/hospital',
    '/api/locations/districts?state=Maharashtra',
    '/api/locations/districts?state=Tamil%20Nadu',
    '/api/hospitals?state=Delhi%20(NCR)&district=New%20Delhi',
    '/api/hospitals?state=Tamil%20Nadu&district=Chennai',
    '/find-blood?state=Tamil%20Nadu&blood_group=O%2B'
]

print("--- Verifying Server Endpoints ---")
all_ok = True
for u in urls:
    full_url = "http://127.0.0.1:5000" + u
    try:
        req = urllib.request.Request(full_url, headers={'User-Agent': 'Mozilla/5.0'})
        with urllib.request.urlopen(req) as resp:
            status = resp.status
            print(f"[OK] {u} -> Status {status}")
    except Exception as e:
        print(f"[FAIL] {u} -> Error {e}")
        all_ok = False

if all_ok:
    print("\nALL HTTP ENDPOINTS VERIFIED SUCCESSFULLY!")
