# Locatify (mapkesif.tr) deploy ve devir notu

Son güncelleme: 29 Ekim 2026. Bu dosya, çalışmaya başka bir bilgisayardan devam eden kişi içindir. **Parola/şifreler repoya yazılmaz**; sunucu şifresini proje sahibinden isteyin.

## Hızlı deploy

Repo kökünden, Windows PowerShell:

```powershell
$env:TT_DEPLOY_PASS = '<Administrator şifresi>'   # verilmezse betik sorar
powershell -File deploy\deploy.ps1
```

[deploy/deploy.ps1](deploy/deploy.ps1) şunları yapar:

1. `main.py`, `requirements.txt` ve `templates/` dosyalarını sunucuya (`C:\inetpub\mapkesif`) gönderir. Sunucudaki `exports/` ve `venv/` silinmez.
2. Eski sürümü `C:\deploytmp\mk-bak-<tarih>` altına yedekler.
3. `requirements.txt` değiştiyse `pip install` çalıştırır.
4. `pm2 restart mapkesif` yapar ve `http://127.0.0.1:8000/` 200 dönene kadar bekler. Dönmezse yedeği geri yükler ve hata verir.
5. Dışarıdan `https://mapkesif.tr` adresini doğrular.

Gereksinim: yerel makinede Windows PowerShell 5.1 (`powershell`), sunucuya WinRM erişimi (5985). tasktakip'e ve Caddy'ye dokunmaz. Kod değişmese de güvenle tekrar çalıştırılabilir (yalnızca yeniden başlatır).

Değişiklik sonrası deploy etmeden önce yerelde deneyin: `python main.py`, sonra http://127.0.0.1:8000 (kurulum için [README.md](README.md)).

## Sunucu

- Windows Server 2025, `31.57.77.179`, kullanıcı `Administrator` (WinRM / RDP). **tasktakip ile aynı sunucudur**; onu bozmayın (aşağıya bakın).
- Adres: https://mapkesif.tr (DNS Güzel Hosting nameserver'larında; `@` A kaydı `31.57.77.179`, `www` CNAME `mapkesif.tr`). `www.mapkesif.tr` için Caddy'de blok yok, istenirse eklenir.

```
İnternet -> Caddy (80/443, otomatik Let's Encrypt)
              |- tasktakip.tr, www.tasktakip.tr -> https://127.0.0.1:8443 (tasktakip, pm2 cluster)
              `- mapkesif.tr                    -> http://127.0.0.1:8000  (Locatify, pm2 "mapkesif")
```

- **Caddy:** `C:\caddy` (`caddy.exe`, `Caddyfile`, `Caddyfile.bak`), pm2 uygulaması `caddy`. Tüm sertifikaları kendisi alır ve yeniler; ek görev gerekmez.
- **Locatify:** `C:\inetpub\mapkesif` (`main.py`, `templates/`, `exports/`, `venv/`, `ecosystem.config.cjs`), pm2 uygulaması `mapkesif`, uvicorn `127.0.0.1:8000`.
- **Playwright Chromium:** `C:\playwright-browsers` (`PLAYWRIGHT_BROWSERS_PATH`, pm2 ortamında tanımlı).
- **pm2:** `PM2_HOME=C:\pm2`; `pm2 save` yapıldı, sunucu açılışında `pm2-resurrect` görevi tasktakip, mapkesif ve caddy'yi geri getirir. Python 3.12 (`C:\Users\Administrator\AppData\Local\Programs\Python\Python312`).
- Kullanılan portlar: 80/443 Caddy, 8000 mapkesif, 8080 ve 8443 tasktakip.

### Sunucuda pm2 / Caddy komutları

Uzaktan pm2'yi doğrudan çağırmak oturumu takılı bırakabilir. Şöyle çalıştırın:

```powershell
$env:PM2_HOME='C:\pm2'; $env:Path += ';C:\Users\Administrator\AppData\Roaming\npm'
Start-Process cmd.exe -ArgumentList '/c pm2 list > C:\deploytmp\out.log 2>&1' -WindowStyle Hidden -Wait
Get-Content C:\deploytmp\out.log
```

Loglar: `C:\pm2\logs\mapkesif-*.log`, `C:\pm2\logs\caddy-error.log`. Sunucuda `Expand-Archive` çalışmaz (modül yüklenemiyor); zip açmak için `[IO.Compression.ZipFile]::ExtractToDirectory` kullanın.

## Yeni alan adı ekleme

1. Alan adının `@` A kaydı `31.57.77.179` olmalı (yeni `.tr` alan adlarında delegasyon birkaç saat gecikebilir; `nslookup <alan> 8.8.8.8` ile kontrol edin).
2. `C:\caddy\Caddyfile`'a blok ekleyin: `ornek.com { reverse_proxy 127.0.0.1:<port> }`.
3. `C:\caddy\caddy.exe validate --config C:\caddy\Caddyfile`, ardından `C:\caddy\caddy.exe reload --config C:\caddy\Caddyfile`.
4. Yeni uygulama ise ayrı iç port ve ayrı pm2 uygulaması kullanın. DNS yayılmadan sertifika alınamaz; yayıldıktan sonra Caddy'yi bir kez `reload` etmek denemeyi hızlandırır.

## tasktakip ile ilişki (dikkat)

- tasktakip ([ramazanhaber/tasktakip](https://github.com/ramazanhaber/tasktakip)) aynı sunucuda çalışır ve artık `8443`/`8080` portlarında dinler (`HTTPS_PORT`/`HTTP_PORT`). Caddy önde olduğu için bu ayarı **geri almayın**, yoksa 80/443'te çakışma olur. Ayrıntı için tasktakip reposundaki `DEVIR_NOTU.md`.
- Caddy yapılandırmasını bozarsanız ikisi de kapanır. `caddy validate` olmadan `reload` yapmayın. Önceki (win-acme sertifikalı) yapılandırma `C:\caddy\Caddyfile.bak`'tir.

## Yapılanlar (özet)

- Locatify sunucuya kuruldu: venv, bağımlılıklar, Playwright Chromium; sunucuda gerçek arama (`konya restoran`) denendi, Excel üretildi.
- tasktakip 80/443'ü tuttuğu için Caddy öne alındı; tasktakip reposunda `deploy/server/index.js`, `deploy/ecosystem.config.cjs` ve `deploy/deploy.ps1` buna göre değişti.
- tasktakip.tr sertifikası win-acme'den Caddy'nin otomatik sertifikasına geçirildi. win-acme yenileme görevi ve `caddy-reload-certs` görevi **devre dışı** (silinmedi).
- mapkesif.tr DNS'i yayıldı, Caddy sertifikayı aldı; https://mapkesif.tr canlı (200, geçerli sertifika, HTTP -> HTTPS yönlendirmesi çalışıyor).
- Deploy betiği ([deploy/deploy.ps1](deploy/deploy.ps1)) sunucuya karşı denendi: yeniden başlatma ve dış doğrulama başarılı.

## Bilinen noktalar

- Google Maps tarafında bot kontrolü / onay penceresi çıkabilir; sunucuda Chromium headless çalışır. Sorun olursa `C:\pm2\logs\mapkesif-*.log` bakın.
- Otomatik toplama Google'ın kullanım şartlarıyla çelişebilir; yalnızca toplamaya izinli olduğunuz veriler için kullanın.
