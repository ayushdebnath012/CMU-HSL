param(
    [string]$Config = "configs/bicycle_chair.json",
    [string]$SceneModel = "outputs/bicycle",
    [string]$AssetModel = "outputs/chair",
    [string]$OutputModel = "outputs/composed_bicycle_chair",
    [int]$Iteration = 30000
)

$ErrorActionPreference = "Stop"
$Root = Resolve-Path (Join-Path $PSScriptRoot "..")
$ConfigFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $Config))
$SceneModelFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $SceneModel))
$AssetModelFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $AssetModel))
$OutputModelFullPath = [System.IO.Path]::GetFullPath((Join-Path $Root $OutputModel))

if (-not (Test-Path $ConfigFullPath)) {
    throw "Config not found: $ConfigFullPath"
}
if (-not (Test-Path $SceneModelFullPath)) {
    throw "Scene model not found: $SceneModelFullPath"
}
if (-not (Test-Path $AssetModelFullPath)) {
    throw "Asset model not found: $AssetModelFullPath"
}

if (-not (Test-Path $OutputModelFullPath)) {
    Copy-Item -Recurse -LiteralPath $SceneModelFullPath -Destination $OutputModelFullPath
}

$ScenePly = Join-Path $SceneModelFullPath "point_cloud\iteration_$Iteration\point_cloud.ply"
$AssetPly = Join-Path $AssetModelFullPath "point_cloud\iteration_$Iteration\point_cloud.ply"
$OutputPly = Join-Path $OutputModelFullPath "point_cloud\iteration_$Iteration\point_cloud.ply"

if (-not (Test-Path $ScenePly)) {
    throw "Scene PLY not found: $ScenePly"
}
if (-not (Test-Path $AssetPly)) {
    throw "Asset PLY not found: $AssetPly"
}

$ConfigObject = Get-Content -Raw -LiteralPath $ConfigFullPath | ConvertFrom-Json
$ConfigObject.scene_ply = $ScenePly
$ConfigObject.asset_ply = $AssetPly
$ConfigObject.output_ply = $OutputPly

$TmpConfig = Join-Path $env:TEMP ("hsl_placement_" + [System.Guid]::NewGuid().ToString() + ".json")
$ConfigObject | ConvertTo-Json -Depth 20 | Set-Content -Encoding UTF8 -LiteralPath $TmpConfig

python (Join-Path $Root "tools\compose_splats.py") --config $TmpConfig
Remove-Item -LiteralPath $TmpConfig

Write-Host "Composed model directory: $OutputModelFullPath"

