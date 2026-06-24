param(
    [string]$RepoPath = "external/gaussian-splatting",
    [switch]$SkipConda
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$RepoFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $RepoPath))

if (-not (Test-Path $RepoFullPath)) {
    New-Item -ItemType Directory -Force -Path (Split-Path $RepoFullPath) | Out-Null
    git clone https://github.com/graphdeco-inria/gaussian-splatting --recursive $RepoFullPath
} else {
    Push-Location $RepoFullPath
    git submodule update --init --recursive
    Pop-Location
}

if ($SkipConda) {
    Write-Host "Skipped conda environment creation."
    exit 0
}

if (-not (Get-Command conda -ErrorAction SilentlyContinue)) {
    Write-Warning "Conda was not found. Install Miniconda/Anaconda, then run: conda env create --file external/gaussian-splatting/environment.yml"
    exit 0
}

Push-Location $RepoFullPath
conda env create --file environment.yml
Pop-Location

Write-Host "Created the gaussian_splatting conda environment. Activate it with: conda activate gaussian_splatting"

