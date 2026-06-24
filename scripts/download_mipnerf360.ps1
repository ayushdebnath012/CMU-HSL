param(
    [string]$OutDir = "data/360_v2",
    [string]$ZipPath = "data/360_v2.zip"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$OutFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $OutDir))
$ZipFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $ZipPath))
$Url = "http://storage.googleapis.com/gresearch/refraw360/360_v2.zip"

New-Item -ItemType Directory -Force -Path $OutFullPath | Out-Null
Write-Host "Downloading Mip-NeRF 360 dataset archive. This is about 12.5 GB."
Invoke-WebRequest -Uri $Url -OutFile $ZipFullPath
Write-Host "Extracting archive to $OutFullPath"
Expand-Archive -LiteralPath $ZipFullPath -DestinationPath $OutFullPath -Force

Write-Host "Expected Bicycle path after extraction: data/360_v2/bicycle"
