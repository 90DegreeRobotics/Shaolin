param(
    [switch]$Install,    # add the ear to Windows Startup (current user)
    [switch]$Uninstall,  # remove it from Startup
    [switch]$Stop        # stop a running ear
)

$ErrorActionPreference = "Stop"

$repo = "C:\Shaolin"
$python = Join-Path $repo ".venv\Scripts\python.exe"
$startupCmd = Join-Path ([Environment]::GetFolderPath("Startup")) "Chirox_Voice.cmd"

if (-not (Test-Path -LiteralPath $python)) {
    throw "Chirox virtual environment was not found at $python"
}

function Get-EarProcess {
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object { $_.CommandLine -like "*chirox.listener*" }
}

function Get-VoiceOrganProcess {
    # Narrator / trainer share the PID lock the ear watches — -Stop must kill them too.
    Get-CimInstance Win32_Process -Filter "Name = 'python.exe'" |
        Where-Object {
            $_.CommandLine -like "*chirox.narrator*" -or
            $_.CommandLine -like "*chirox.trainer*"
        }
}

if ($Stop) {
    $organs = @(Get-VoiceOrganProcess)
    if ($organs.Count -gt 0) {
        $organs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }
        Write-Host "Stopped narration/training ($($organs.Count))."
    }
    $lock = Join-Path $repo "Dojo\voice\_narration.pid"
    if (Test-Path -LiteralPath $lock) {
        Remove-Item -LiteralPath $lock -Force -ErrorAction SilentlyContinue
    }
    $procs = @(Get-EarProcess)
    if ($procs.Count -gt 0) {
        $procs | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
        Write-Host "Chirox ear stopped."
    } else {
        Write-Host "Chirox ear was not running."
    }
    return
}

if ($Uninstall) {
    if (Test-Path -LiteralPath $startupCmd) {
        Remove-Item -LiteralPath $startupCmd -Force
        Write-Host "Removed from Startup: $startupCmd"
    } else {
        Write-Host "Not installed in Startup."
    }
    return
}

if ($Install) {
    # A visible .cmd in the user's Startup folder - inspectable, trivially removable.
    $line = "start `"Chirox Voice`" /min `"$python`" -m chirox.listener"
    Set-Content -LiteralPath $startupCmd -Value $line -Encoding ascii
    Write-Host "Installed to Startup: $startupCmd"
    Write-Host "The ear will wake with Windows. Starting it now as well..."
}

# One ear only: replace a stale instance so what runs is what is on disk.
$existing = Get-EarProcess
if ($existing) {
    $existing | ForEach-Object { Stop-Process -Id $_.ProcessId -Force }
    Start-Sleep -Milliseconds 500
}

Start-Process -FilePath $python `
    -ArgumentList "-m", "chirox.listener" `
    -WorkingDirectory $repo `
    -WindowStyle Minimized

Write-Host "Chirox is listening. Say: 'Chirox, what day is it?'"
Write-Host "Silence him with: .\Launch_Chirox_Voice.ps1 -Stop   (or say: 'Chirox, go to sleep')"
