# Descarga FFmpeg (build GPL v3 de gyan.dev) y comprueba su SHA-256 antes de usarlo.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'
$ver = '9.0.2'
$sha = '60F467265B1E312373DBCD92200C2618A74850F98D3D078E94296BB3FA2047BA'
$zip = Join-Path $env:TEMP "ffmpeg-$ver-essentials.zip"
Invoke-WebRequest "https://github.com/GyanD/codexffmpeg/releases/download/$ver/ffmpeg-$ver-essentials_build.zip" -OutFile $zip
if ((Get-FileHash $zip -Algorithm SHA256).Hash -ne $sha) {
    Remove-Item $zip
    throw 'El SHA-256 de FFmpeg no coincide: descarga descartada.'
}
New-Item -ItemType Directory -Force "$PSScriptRoot\ffmpeg" | Out-Null
Add-Type -AssemblyName System.IO.Compression.FileSystem
$z = [IO.Compression.ZipFile]::OpenRead($zip)
foreach ($e in $z.Entries) {
    if ($e.FullName -match '/(bin/ffmpeg\.exe|LICENSE(\.txt)?)$') {
        [IO.Compression.ZipFileExtensions]::ExtractToFile($e, "$PSScriptRoot\ffmpeg\$($e.Name)", $true)
    }
}
$z.Dispose()
Remove-Item $zip
if (-not (Test-Path "$PSScriptRoot\ffmpeg\ffmpeg.exe")) { throw 'ffmpeg.exe no encontrado en el ZIP.' }
