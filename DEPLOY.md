# Locatify (mapkesif.tr) yayın notları

Son güncelleme: 29 Ekim 2026. Parola/şifreler bu repoya yazılmaz.

## Durum

- Adres: https://mapkesif.tr (uygulama sunucuda çalışıyor, ancak alan adının DNS delegasyonu henüz yayılmadıysa açılmaz).
- Sunucu: Windows Server 2025, `31.57.77.179`, kullanıcı `Administrator` (WinRM / RDP). tasktakip ile aynı sunucudur.
- DNS: alan adı Güzel Hosting nameserver'larında (`tr/eu/us/sg.guzelhosting.com`). `@` A kaydı `31.57.77.179`, `www` CNAME `mapkesif.tr`. Alan adı yeni alındığı için `.tr` delegasyonu birkaç saat gecikebilir. Kontrol: `nslookup mapkesif.tr 8.8.8.8`.
- `www.mapkesif.tr` için Caddyfile'da blok yok; istenirse eklenir.

## Mimari

```
İnternet -> Caddy (80/443, otomatik Let's Encrypt)
              |- tasktakip.tr, www.tasktakip.tr -> https://127.0.0.1:8443 (tasktakip, pm2 cluster)
              `- mapkesif.tr                    -> http://127.0.0.1:8000  (Locatify, pm2 "mapkesif")
```

- Caddy: `C:\caddy` (`caddy.exe`, `Caddyfile`, `Caddyfile.bak`), pm2 uygulaması `caddy`. Sertifikaları kendisi alır ve yeniler; ek görev gerekmez.
- Locatify: `C:\inetpub\mapkesif` (`main.py`, `templates/`, `exports/`, `venv/`, `ecosystem.config.cjs`). pm2 uygulaması `mapkesif`, uvicorn `127.0.0.1:8000`.
- Playwright Chromium: `C:\playwright-browsers` (`PLAYWRIGHT_BROWSERS_PATH`, pm2 ortamında tanımlı).
- pm2: `PM2_HOME=C:\pm2`; `pm2 save` yapıldı, sunucu açılışında `pm2-resurrect` görevi üç uygulamayı (tasktakip, mapkesif, caddy) geri getirir.
- Python 3.12 (`C:\Users\Administrator\AppData\Local\Programs\Python\Python312`).

## Güncelleme (Locatify)

Yerelde değişiklik sonrası, sunucuya (PowerShell remoting, `Negotiate`) şu dosyaları kopyala ve yeniden başlat:

1. `main.py`, `requirements.txt`, `templates\*` -> `C:\inetpub\mapkesif\` (`exports/` ve `venv/` silinmez).
2. Bağımlılık değiştiyse: `C:\inetpub\mapkesif\venv\Scripts\python.exe -m pip install -r requirements.txt`.
3. `pm2 restart mapkesif` (pm2 komutlarını `Start-Process cmd /c "pm2 ... > log 2>&1" -Wait` ile ve çıktıyı dosyaya alarak çalıştırın; doğrudan çağrı uzaktan oturumda takılabilir. PATH'e `C:\Users\Administrator\AppData\Roaming\npm` ekleyin).
4. Doğrulama: sunucuda `curl http://127.0.0.1:8000/` ve `https://mapkesif.tr`.

## Yeni alan adı ekleme

1. Alan adının `@` A kaydı `31.57.77.179` olmalı.
2. `C:\caddy\Caddyfile`'a blok ekle (örn. `ornek.com { reverse_proxy 127.0.0.1:<port> }`).
3. `C:\caddy\caddy.exe validate --config C:\caddy\Caddyfile`, ardından `C:\caddy\caddy.exe reload --config C:\caddy\Caddyfile`.
4. Yeni uygulama ise ayrı bir iç port ve pm2 uygulaması kullan (kullanımda: 80/443 Caddy, 8000 mapkesif, 8080 ve 8443 tasktakip).

## Yapılanlar (özet)

- Locatify sunucuya kuruldu: venv, bağımlılıklar, Playwright Chromium; sunucuda gerçek arama (`konya restoran`) denendi, Excel üretildi.
- tasktakip'in 80/443 portlarını tutması nedeniyle Caddy öne alındı. tasktakip artık `8443` (HTTPS) / `8080` (HTTP) dinler; bunun için tasktakip reposunda `deploy/server/index.js` (`HTTPS_PORT`, `HTTP_PORT` ortam değişkenleri; verilmezse eski 443/80), `deploy/ecosystem.config.cjs` ve `deploy/deploy.ps1` (sağlık kontrolü 8443) değişti. Ayrıntı: tasktakip `DEVIR_NOTU.md`.
- tasktakip.tr sertifikası win-acme'den Caddy'nin otomatik sertifikasına geçirildi. win-acme yenileme görevi ve `caddy-reload-certs` görevi **devre dışı** (silinmedi). Geri dönüş için `C:\caddy\Caddyfile.bak`.
- Geçiş sonrası doğrulandı: `https://tasktakip.tr` ve `www` 200, geçerli sertifika, HTTP -> HTTPS yönlendirmesi çalışıyor.

## Durum (güncel)

- mapkesif.tr DNS yayıldı, Caddy sertifikayı aldı; https://mapkesif.tr canlı (200, geçerli sertifika, HTTP -> HTTPS yönlendirmesi çalışıyor).
- Sorun olursa `C:\pm2\logs\caddy-error.log` içinde `mapkesif` satırlarına bakın.
