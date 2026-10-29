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

## Geçmiş sekmesi ve veritabanı (güncel durum)

- Sol menüde **Arama** ve **Geçmiş** sekmeleri var. Her arama ve her işletme okunurken PostgreSQL'e yazılır (`db.py`: `searches` ve `places` tabloları); iptal/hata olsa da o ana kadar okunan veri kaybolmaz. Geçmişten Excel/CSV yeniden indirilebilir (`/api/history/{id}/excel`).
- Bağlantı `DATABASE_URL` ortam değişkeniyle verilir; sunucuda `C:\inetpub\mapkesif\.env` içinde durur (repoya girmez). `DATABASE_URL` yoksa uygulama çalışır, Geçmiş sekmesi "veritabanına ulaşılamıyor" der (yerel geliştirmede de böyle).
- **Kurulu (29 Ekim 2026):** PostgreSQL 18'de ayrı `mapkesif` veritabanı ve `mapkesif` rolü (yalnızca kendi veritabanına yetkili; `tasktakip_app` bu veritabanına bağlanamaz). Bağlantı `C:\inetpub\mapkesif\.env` içinde (yalnızca Administrators/SYSTEM okuyabilir). Tablolar uygulama ilk bağlandığında kendiliğinden oluşur. `deploy.ps1` `.env` dosyasına dokunmaz.
- **Yedek:** `MapkesifBackup` zamanlanmış görevi her gün 03:30'da `C:\backups\mapkesif-yedekle.ps1` çalıştırır (`pg_dump`, `C:\backups\mapkesif-<tarih>.dump`, son 7 gün tutulur; sonuç `C:\backups\son-yedek-mapkesif.txt`). tasktakip'in yedeğinden bağımsızdır.
- **Güvenlik notu:** PostgreSQL yönetici şifreleri sunucuda düz metin dosyalarında duruyor (`C:\pginstall\dbadmin.txt`, `C:\pginstall\super.txt`, ayrıca `C:\pginstall\pw.tmp`). Kurulum tamamlandığı için silinmeleri önerilir (proje sahibi karar verir); bu yüzden şifre bu repoya veya sohbete yazılmaz.
- **Geri yükleme:** `pg_restore -h 127.0.0.1 -U mapkesif -d mapkesif --clean --if-exists C:\backups\mapkesif-<tarih>.dump`

## Başka bilgisayardaki Claude için prompt

Aşağıdaki metni yeni oturumun başına yapıştırın:

```
Locatify (mapkesif.tr) projesini devralıyorsun. Önce repoyu çek: git pull origin main
Sonra DEPLOY.md dosyasını oku; ardından aşağıdaki özeti esas al.

SUNUCU VE DEPLOY
- Sunucu: Windows Server 2025, 31.57.77.179, kullanıcı Administrator (WinRM/RDP).
  tasktakip.tr de aynı sunucuda çalışıyor, ONU BOZMA.
  Şifreyi repoya/dosyaya YAZMA, benden iste. Deploy için oturumda ortam değişkeni olarak ver:
    $env:TT_DEPLOY_PASS = '<şifre>'
- Mimari: Caddy (80/443, otomatik Let's Encrypt) alan adına göre yönlendirir:
    tasktakip.tr -> https://127.0.0.1:8443 (tasktakip, pm2)
    mapkesif.tr  -> http://127.0.0.1:8000  (Locatify, pm2 uygulaması "mapkesif")
- Locatify sunucuda C:\inetpub\mapkesif (main.py, db.py, templates/, exports/, venv/),
  Python 3.12 venv, Playwright Chromium C:\playwright-browsers, pm2 (PM2_HOME=C:\pm2).
- PostgreSQL 18 (C:\PostgreSQL\18) aynı sunucuda; tasktakip kendi veritabanını kullanır.
  Locatify geçmişi için AYRI veritabanı/kullanıcı kullanılır (DATABASE_URL, sunucuda
  C:\inetpub\mapkesif\.env). DATABASE_URL yoksa uygulama çalışır ama Geçmiş sekmesi 503 verir.

DEPLOY NASIL YAPILIR (repo kökünden, Windows PowerShell 5.1):
  $env:TT_DEPLOY_PASS = '<şifre>'
  powershell -File deploy\deploy.ps1
Betik şunları yapar:
  1. main.py, db.py, requirements.txt, templates\* dosyalarını PowerShell remoting
     (New-PSSession -Authentication Negotiate) ile sunucuya C:\deploytmp\mk-<tarih> altına kopyalar
     (zip yok, Expand-Archive sunucuda çalışmıyor).
  2. Sunucuda eski sürümü C:\deploytmp\mk-bak-<tarih> altına yedekler, yenileri C:\inetpub\mapkesif'e
     koyar (exports/, venv/ ve .env silinmez). requirements.txt değiştiyse pip install çalıştırır.
  3. index.html içindeki __DEPLOY_VERSION__ yer tutucusunu sürüm damgasıyla değiştirir.
  4. pm2 restart mapkesif yapar; http://127.0.0.1:8000/ 200 dönene kadar bekler.
     Dönmezse yedeği geri yükler ve hata verir.
  5. Dışarıdan https://mapkesif.tr 200 mü diye doğrular.
Deploy sonrası tasktakip'in bozulmadığını kontrol et:
  curl.exe -s --resolve tasktakip.tr:443:31.57.77.179 https://tasktakip.tr/api/health  -> {"ok":true}

KURALLAR
- tasktakip'e, Caddy yapılandırmasına (C:\caddy\Caddyfile) ve PostgreSQL güvenlik ayarlarına
  (pg_hba.conf) dokunma. Caddy'de değişiklik gerekirse önce caddy validate, sonra reload.
- pm2 komutlarını sunucuda Start-Process cmd /c "pm2 ... > log 2>&1" -Wait ile, çıktıyı dosyaya alarak çalıştır.
- PowerShell dosyalarını UTF-8 BOM'lu kaydet (Türkçe karakter için).
- Değişiklikten sonra commit + push yap (main). İki kişi çalışıyoruz: push öncesi git pull --rebase.
```

## Sunucu güvenlik duvarı: IP izinleri (WinRM 5985)

Deploy (`deploy\deploy.ps1`) PowerShell remoting (WinRM, TCP 5985) kullanır. Sunucuda 5985 herkese değil, yalnızca izinli IP'lere açıktır:

| Kural | Port | İzinli IP | Not |
|---|---|---|---|
| `WinRM-gecici` | 5985 | `78.174.104.213` | proje sahibinin bilgisayarı |
| `PostgreSQL-uzak` | 5432 | `78.174.104.213` | aynı bilgisayar; veritabanı dışarıya yalnızca buraya açık |
| `WinRM-diger-pc` | 5985 | `188.57.104.65` | ikinci geliştirici bilgisayarı (29 Ekim 2026'da eklendi) |

RDP (3389) herkese açıktır. Veritabanı (5432) ve `pg_hba.conf` ikinci bilgisayara **açılmadı**; deploy için gerekmez.

**Ev IP'si değişirse** (yeni IP'yi `(Invoke-RestMethod https://api.ipify.org)` ile öğrenin):

```powershell
# Sunucuda (RDP ile girip yönetici PowerShell'de, ya da izinli bilgisayardan Invoke-Command ile)
Set-NetFirewallRule -DisplayName 'WinRM-diger-pc' -RemoteAddress 1.2.3.4          # değiştir
Set-NetFirewallRule -DisplayName 'WinRM-diger-pc' -RemoteAddress 1.2.3.4,5.6.7.8  # birden fazla IP
Get-NetFirewallRule -DisplayName 'WinRM-diger-pc' | Get-NetFirewallAddressFilter   # kontrol
Remove-NetFirewallRule -DisplayName 'WinRM-diger-pc'                                # kaldır
```

Client'ta bağlantı testi: `Test-NetConnection 31.57.77.179 -Port 5985` (`TcpTestSucceeded : True`). IP ile bağlanırken hata alırsanız, yönetici PowerShell'de bir kez: `Set-Item WSMan:\localhost\Client\TrustedHosts -Value 31.57.77.179 -Force`.

**Claude için kalıcı talimat:** proje sahibi yeni bir IP verip "izin ekle" derse, onay sormadan o IP'yi `WinRM-diger-pc` kuralının `RemoteAddress` listesine **ekle** (mevcut IP'leri koru), kuralı doğrula ve sonucu bildir. Bu yalnızca WinRM 5985 içindir; 5432, `pg_hba.conf` ve diğer güvenlik ayarları için ayrıca onay gerekir. Yönetici şifresi bu dosyaya yazılmaz.
