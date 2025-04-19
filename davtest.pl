<#
  dlpload.ps1  – download an entire YouTube playlist with yt‑dlp,
                 write a consolidated log, skip files already in archive.

  Requirements : PowerShell 5.1+  •  yt‑dlp.exe present at $YtDlpExe
#>

# ---------------- USER CONFIG ----------------
$PlaylistURL = "https://www.youtube.com/playlist?list=PLWeMR3MET_31wpSQkb3Dba5uRbCbjKqEj"
$DownloadDir = Join-Path $env:USERPROFILE "Downloads\YT_Playlist"

# Full literal path to yt‑dlp.exe
$YtDlpExe    = "C:\Users\Admin\Music\yt-dlp.exe"

# ------------- SAFETY CHECKS -----------------
if (-not (Test-Path $YtDlpExe)) {
    Write-Error "yt‑dlp executable not found at '$YtDlpExe'. Update the path and re‑run."
    return
}

if (-not (Test-Path $DownloadDir)) { New-Item -ItemType Directory -Path $DownloadDir | Out-Null }

# Paths that depend on the folder existing
$ArchiveFile = Join-Path $DownloadDir "downloaded_videos.txt"
$LogFile     = Join-Path $DownloadDir ("yt‑dlp_{0:yyyyMMdd_HHmmss}.log" -f (Get-Date))
$OutputTmpl  = "$DownloadDir\%(playlist_index)03d - %(title)s.%(ext)s"

# ------------- yt‑dlp ARGUMENT ARRAY ----------
$Args = @(
    "--ignore-errors"
    "--yes-playlist"
    "--download-archive", $ArchiveFile
    "-o", $OutputTmpl
    $PlaylistURL
)

# ---------- run yt‑dlp and log stdout+stderr -----------------------
Write-Host "Starting yt‑dlp …"
"[$(Get-Date -f 'yyyy-MM-dd HH:mm:ss')] Starting download" | Out-File $LogFile -Append

# Invoke yt‑dlp; send stderr → stdout (2>&1) ; tee to log + console
& $YtDlpExe @Args 2>&1 | Tee-Object -FilePath $LogFile -Append

$exitCode = $LASTEXITCODE

# ---------- exit‑code handling ------------------------------------
if ($exitCode -eq 0) {
    "[$(Get-Date -f 'yyyy-MM-dd HH:mm:ss')] Completed OK." | Out-File $LogFile -Append
    Write-Host "Download complete.  Log: $LogFile"
} else {
    "[$(Get-Date -f 'yyyy-MM-dd HH:mm:ss')] yt‑dlp error $exitCode" | Out-File $LogFile -Append
    Write-Error "yt‑dlp exited with code $exitCode.  See log: $LogFile"
}
