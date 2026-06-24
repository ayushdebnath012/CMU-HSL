param(
    [string]$RepoPath = "external/gaussian-splatting",
    [string]$Dataset = "data/nerf_synthetic/chair",
    [string]$Output = "outputs/chair",
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
    throw "NeRF-Synthetic asset dataset not found at $DatasetFullPath. Download it from the official NeRF data link and place it there."
}

New-Item -ItemType Directory -Force -Path $OutputFullPath | Out-Null
Push-Location $RepoFullPath
python train.py -s $DatasetFullPath -m $OutputFullPath --eval -w --iterations $Iterations --save_iterations $Iterations
Pop-Location

