# Descarga FFmpeg (build GPL v3 de gyan.dev) y LibreOffice (MSI oficial), comprueba su SHA-256 y los prepara.
$ErrorActionPreference = 'Stop'
$ProgressPreference = 'SilentlyContinue'

function Get-Verified($url, $sha) {
    $file = Join-Path $env:TEMP (Split-Path $url -Leaf)
    Invoke-WebRequest $url -OutFile $file
    if ((Get-FileHash $file -Algorithm SHA256).Hash -ne $sha) {
        Remove-Item $file
        throw "SHA-256 incorrecto, descarga descartada: $url"
    }
    $file
}

if (-not (Test-Path "$PSScriptRoot\ffmpeg\ffmpeg.exe")) {
    $zip = Get-Verified 'https://github.com/GyanD/codexffmpeg/releases/download/9.0.2/ffmpeg-9.0.2-essentials_build.zip' `
        '60F467265B1E312373DBCD92200C2618A74850F98D3D078E94296BB3FA2047BA'
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
}

if (-not (Test-Path "$PSScriptRoot\libreoffice.zip")) {
    $msi = Get-Verified 'https://download.documentfoundation.org/libreoffice/stable/26.2.6/win/x86_64/LibreOffice_26.2.6_Win_x86-64.msi' `
        'F9877032FD908BEB9C0DDF06DF4AF5C2E85F419C42E14876C4CCE5AAE5FB2660'
    $dir = Join-Path $env:TEMP 'jt-libreoffice'
    Remove-Item $dir -Recurse -Force -ErrorAction SilentlyContinue
    # "/a" solo extrae los archivos del MSI (instalacion administrativa): no instala nada en Windows
    $p = Start-Process msiexec.exe -ArgumentList '/a', "`"$msi`"", '/qn', "TARGETDIR=`"$dir`"" -Wait -PassThru
    if ($p.ExitCode) { throw "msiexec devolvio $($p.ExitCode)" }
    $root = (Get-ChildItem $dir -Recurse -Filter soffice.com | Select-Object -First 1).Directory.Parent.FullName
    if (-not $root) { throw 'soffice.com no encontrado en el MSI.' }
    Get-ChildItem $dir -Recurse -Include 'msvcp140*.dll', 'vcruntime140*.dll' |  # runtime C++ de 64 bits, por si el PC no lo tiene
        Where-Object { $_.FullName -match '\\System64\\' -and -not (Test-Path "$root\program\$($_.Name)") } |
        Copy-Item -Destination "$root\program"
    # Peso: fuera diccionarios ortograficos y traducciones de la interfaz (sin interfaz no se usan)
    Remove-Item "$root\share\extensions\dict-*" -Recurse -Force -ErrorAction SilentlyContinue
    Get-ChildItem "$root\program\resource" -Directory -ErrorAction SilentlyContinue | Where-Object Name -notin 'es', 'en-US' | Remove-Item -Recurse -Force
    tar.exe -a -cf "$PSScriptRoot\libreoffice.zip" -C $root .
    if ($LASTEXITCODE) { throw 'No se pudo comprimir LibreOffice.' }
    Write-Host ('libreoffice.zip: {0:N0} MB' -f ((Get-Item "$PSScriptRoot\libreoffice.zip").Length / 1MB))
    Remove-Item $dir, $msi -Recurse -Force
}
