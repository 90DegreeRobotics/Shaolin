# Chirox launcher - keep this file pure ASCII. PowerShell 5.1 reads BOM-less
# scripts as ANSI; a UTF-8 em-dash becomes a smart quote and breaks parsing.
$ErrorActionPreference = "Stop"

$repo = "C:\Shaolin"
$python = Join-Path $repo ".venv\Scripts\python.exe"
# Unique URL every launch: no browser can serve a cached copy of the page.
# autostart=1 opens the current Training Mode mirror on the built-in webcam.
$stamp = [DateTime]::Now.Ticks
$url = "http://127.0.0.1:8765/?autostart=1&t=$stamp"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Chirox virtual environment was not found at $python"
}

function Get-MirrorListener {
    Get-NetTCPConnection -LocalAddress 127.0.0.1 -LocalPort 8765 -State Listen -ErrorAction SilentlyContinue
}

# A server already on the port may be running stale code - stop it so the
# launcher always serves what is on disk now.
$listener = Get-MirrorListener
if ($listener) {
    # Ask it to release the cameras FIRST: force-killing a server mid-stream
    # leaves the UVC driver mid-negotiation, and the next open struggles.
    try {
        Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8765/api/session/stop" -TimeoutSec 4 | Out-Null
        Start-Sleep -Milliseconds 400
    } catch {}
    $listener | Select-Object -ExpandProperty OwningProcess -Unique | ForEach-Object {
        try { Stop-Process -Id $_ -Force -ErrorAction Stop } catch {}
    }
    $deadline = (Get-Date).AddSeconds(8)
    do {
        Start-Sleep -Milliseconds 200
        $listener = Get-MirrorListener
    } while ($listener -and (Get-Date) -lt $deadline)
    if ($listener) {
        $held = ($listener.OwningProcess | Select-Object -Unique) -join ', '
        throw "Port 8765 is still held by process(es) $held - close them and relaunch."
    }
}

# Sweep stale camera holders: web servers that lost their port, or vision/record
# runs left behind. Never touch the ear (chirox.listener) or a narration.
Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
    Where-Object { $_.CommandLine -match 'chirox\.web\.app|chirox\.vision|chirox\.cli.+(vision|record)' } |
    ForEach-Object { try { Stop-Process -Id $_.ProcessId -Force -ErrorAction Stop } catch {} }

Start-Process -FilePath $python `
    -ArgumentList "-m", "chirox.web.app" `
    -WorkingDirectory $repo `
    -WindowStyle Hidden

$deadline = (Get-Date).AddSeconds(12)
do {
    Start-Sleep -Milliseconds 300
    $listener = Get-MirrorListener
} until ($listener -or (Get-Date) -gt $deadline)

if (-not $listener) {
    throw "Chirox mirror server did not start within 12 seconds."
}

# Chirox is its own app, not a browser tab: an Edge app window with a private
# profile that belongs to Chirox alone. A fresh profile has NO old cache, so
# what is on disk is always exactly what is on screen.
$edge = "C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"
if (-not (Test-Path -LiteralPath $edge)) {
    $edge = "C:\Program Files\Microsoft\Edge\Application\msedge.exe"
}
$appProfile = Join-Path $repo "Dojo\data\chirox_browser"
if (Test-Path -LiteralPath $edge) {
    # Chirox owns the whole screen: an app window (no address bar) that opens
    # fullscreen. --start-fullscreen is the borderless F11 state; --start-maximized
    # is a fallback for builds that ignore it. Press F11 to drop out of fullscreen.
    Start-Process -FilePath $edge -ArgumentList `
        "--app=$url", "--user-data-dir=$appProfile", "--no-first-run", `
        "--start-fullscreen", "--start-maximized"
} else {
    Start-Process $url
}
