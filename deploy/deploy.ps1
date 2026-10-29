# Locatify -> mapkesif.tr deploy: dosyaları sunucuya gönder, gerekirse bağımlılıkları kur, pm2 restart, sağlık kontrolü (hata olursa geri al)
#
# Kullanım (repo kökünden):
#   $env:TT_DEPLOY_PASS = '<Administrator şifresi>'     # verilmezse sorulur
#   powershell -File deploy\deploy.ps1
#
# Sunucudaki exports/ ve venv/ klasörlerine dokunulmaz. tasktakip'e ve Caddy'ye dokunulmaz.
param(
  [string]$Server = '31.57.77.179',
  [string]$User = 'Administrator'
)
$ErrorActionPreference = 'Stop'
$repo = Split-Path $PSScriptRoot -Parent
$stamp = Get-Date -Format 'yyyyMMdd-HHmmss'

foreach ($f in 'main.py', 'db.py', 'requirements.txt', 'templates\index.html') {
  if (-not (Test-Path "$repo\$f")) { throw "$f bulunamadı, repo kökünden çalıştırın." }
}

$secure = if ($env:TT_DEPLOY_PASS) { ConvertTo-SecureString $env:TT_DEPLOY_PASS -AsPlainText -Force } else { Read-Host 'Sunucu şifresi' -AsSecureString }
$cred = New-Object PSCredential($User, $secure)
$version = 'v' + (Get-Date -Format 'yyyy.MM.dd HH:mm')
$session = New-PSSession $Server -Credential $cred -Authentication Negotiate
try {
  $stage = "C:\deploytmp\mk-$stamp"
  Invoke-Command $session -ArgumentList $stage { param($stage) New-Item -ItemType Directory -Force "$stage\templates" | Out-Null }
  Copy-Item "$repo\main.py", "$repo\db.py", "$repo\requirements.txt" -Destination $stage -ToSession $session
  Copy-Item "$repo\templates\*" -Destination "$stage\templates" -ToSession $session
  Write-Host "Dosyalar sunucuya gönderildi ($version), yerleştiriliyor" -ForegroundColor Cyan

  $result = Invoke-Command $session -ArgumentList $stage, $stamp, $version -ScriptBlock {
    param($stage, $stamp, $version)
    $ErrorActionPreference = 'Stop'
    $app = 'C:\inetpub\mapkesif'
    $bak = "C:\deploytmp\mk-bak-$stamp"
    $env:PM2_HOME = 'C:\pm2'
    $env:Path = [Environment]::GetEnvironmentVariable('Path', 'Machine') + ';C:\Users\Administrator\AppData\Roaming\npm'

    function Restart {
      Start-Process cmd.exe -ArgumentList "/c pm2 restart mapkesif > C:\deploytmp\mk-restart-$stamp.log 2>&1" -WorkingDirectory $app -WindowStyle Hidden -Wait
    }
    function Healthy {
      for ($i = 0; $i -lt 30; $i++) {
        if ((curl.exe -s -m 4 -o NUL -w '%{http_code}' http://127.0.0.1:8000/) -eq '200') { return $true }
        Start-Sleep -Milliseconds 700
      }
      return $false
    }

    # Geri alma noktası (yalnızca kod)
    New-Item -ItemType Directory -Force "$bak\templates" | Out-Null
    Copy-Item "$app\main.py", "$app\requirements.txt" $bak -Force
    if (Test-Path "$app\db.py") { Copy-Item "$app\db.py" $bak -Force }
    Copy-Item "$app\templates\*" "$bak\templates" -Force

    $index = Join-Path $stage 'templates\index.html'
    $html = [IO.File]::ReadAllText($index)
    if ($html -notlike '*__DEPLOY_VERSION__*') { throw 'index.html içinde __DEPLOY_VERSION__ yok.' }
    [IO.File]::WriteAllText($index, $html.Replace('__DEPLOY_VERSION__', $version))

    $old = (Get-FileHash "$app\requirements.txt").Hash
    Copy-Item "$stage\main.py", "$stage\db.py", "$stage\requirements.txt" $app -Force
    Copy-Item "$stage\templates\*" "$app\templates" -Force

    $installed = $false
    if ($old -ne (Get-FileHash "$app\requirements.txt").Hash) {
      cmd /c "$app\venv\Scripts\python.exe -m pip install -q -r $app\requirements.txt > C:\deploytmp\mk-pip-$stamp.log 2>&1"
      $installed = $true
    }

    Restart
    $ok = Healthy
    if (-not $ok) {
      Copy-Item "$bak\main.py", "$bak\requirements.txt" $app -Force
      if (Test-Path "$bak\db.py") { Copy-Item "$bak\db.py" $app -Force }
      Copy-Item "$bak\templates\*" "$app\templates" -Force
      Restart
    }
    # Eski hazırlık/yedek klasörlerinden son 3'ü kalsın
    foreach ($p in 'mk-2*', 'mk-bak-*') {
      foreach ($d in Get-ChildItem C:\deploytmp -Directory -Filter $p | Sort-Object Name -Descending | Select-Object -Skip 3) { [IO.Directory]::Delete($d.FullName, $true) }
    }
    [pscustomobject]@{ Ok = $ok; Installed = $installed }
  }

  if (-not $result.Ok) { throw 'Sağlık kontrolü başarısız, önceki sürüm geri yüklendi.' }
  Write-Host ('Sunucu yenilendi' + $(if ($result.Installed) { ' (bağımlılıklar kuruldu)' } else { '' })) -ForegroundColor Cyan
}
finally {
  Remove-PSSession $session -ErrorAction SilentlyContinue
}

# Dışarıdan doğrulama (DNS gecikmesinden etkilenmesin diye --resolve)
$code = curl.exe -s -m 15 -o NUL -w '%{http_code}' --resolve "mapkesif.tr:443:$Server" https://mapkesif.tr/
if ($code -ne '200') { throw "https://mapkesif.tr beklenen yanıtı vermedi (HTTP $code)." }
Write-Host 'Canlı: https://mapkesif.tr (200)' -ForegroundColor Green
