param(
    [string]$RepoPath = "external/gaussian-splatting",
    [string]$Model = "outputs/composed_bicycle_chair"
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$RepoFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $RepoPath))
$ModelFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $Model))

if (-not (Test-Path $RepoFullPath)) {
    throw "3DGS repo not found at $RepoFullPath. Run scripts/setup_3dgs.ps1 first."
}
if (-not (Test-Path $ModelFullPath)) {
    throw "Composed model not found at $ModelFullPath. Run scripts/compose_bicycle_chair.ps1 first."
}

Push-Location $RepoFullPath
python render.py -m $ModelFullPath
Pop-Location

