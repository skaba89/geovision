"""Browser regression checks, with no live SMTP traffic."""
import threading
from http.server import ThreadingHTTPServer
from playwright.sync_api import sync_playwright
import server


def main():
    http = ThreadingHTTPServer(('127.0.0.1', 0), server.Handler)
    threading.Thread(target=http.serve_forever, daemon=True).start()
    base = f'http://127.0.0.1:{http.server_port}'
    try:
        with sync_playwright() as p:
            browser = p.chromium.launch()
            for w, h in [(320, 568), (390, 844), (600, 960), (768, 1024), (1024, 768), (1280, 720), (1920, 1080), (2560, 1440)]:
                page = browser.new_page(viewport={'width': w, 'height': h})
                for path in ['/', '/detection.html', '/georeferencement.html', '/cartographie.html', '/informations.html']:
                    page.goto(base + path)
                    page.evaluate('document.fonts.ready')
                    assert page.evaluate('document.documentElement.scrollWidth') <= w + 1, (w, path)
                page.goto(base + '/#contact')
                form = page.locator('#quote')
                for name, value in {'nom': 'Test', 'entreprise': 'Test', 'email': 'test@example.test', 'lieu': 'Paris', 'projet': 'Demande de test'}.items():
                    form.locator(f'[name={name}]').fill(value)
                for name, value in {'service': 'SIG & cartographie', 'type': 'Collectivité', 'delai': 'Urgent'}.items():
                    form.locator(f'[name={name}]').select_option(label=value)
                page.route('**/api/contact', lambda route: route.fulfill(json={'reference': 'GV-TEST', 'acknowledgement_sent': True}))
                form.locator('[type=submit]').click()
                page.locator('#result h3').wait_for()
                assert not form.is_visible()
                page.get_by_role('button', name='Nouvelle demande').click()
                assert form.is_visible()
                assert form.locator('[name=nom]').input_value() == ''
                page.close()
                print(f'OK {w}x{h}')
            browser.close()
    finally:
        http.shutdown()
        http.server_close()


if __name__ == '__main__':
    main()
