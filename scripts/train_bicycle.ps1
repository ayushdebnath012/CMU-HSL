param(
    [string]$RepoPath = "external/gaussian-splatting",
    [string]$Dataset = "data/360_v2/bicycle",
    [string]$Output = "outputs/bicycle",
    [string]$Images = "images_4",
    [int]$Iterations = 30000
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$RepoFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $RepoPath))
$DatasetFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $Dataset))
$OutputFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $Output))

if (-not (Test-Path $RepoFullPath)) {
    throw "3DGS repo not found at $RepoFullPath. Run scripts/setup_3dgs.ps1 first."
}
if (-not (Test-Path $DatasetFullPath)) {
    throw "Bicycle dataset not found at $DatasetFullPath. Run scripts/download_mipnerf360.ps1 or place the dataset there."
}

New-Item -ItemType Directory -Force -Path $OutputFullPath | Out-Null
Push-Location $RepoFullPath
python train.py -s $DatasetFullPath -m $OutputFullPath --eval -i $Images --iterations $Iterations --save_iterations $Iterations
Pop-Location

