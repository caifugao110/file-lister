$ErrorActionPreference = "Stop"

$project_name = "file-lister"
$main_script = "app.py"
$icon = "assets\app.ico"

$script_dir = Split-Path -Parent $MyInvocation.MyCommand.Definition
$project_dir = Split-Path -Parent $script_dir
$build_dir = Join-Path $project_dir "build"
$dist_dir = Join-Path $project_dir "dist"

Set-Location $project_dir

if (Test-Path $dist_dir) {
    Remove-Item -Path $dist_dir -Recurse -Force
}
if (Test-Path $build_dir) {
    Remove-Item -Path $build_dir -Recurse -Force
}

New-Item -ItemType Directory -Path $dist_dir -Force | Out-Null

Write-Host "Building $project_name..." -ForegroundColor Cyan

pyinstaller `
    --name $project_name `
    --onefile `
    --windowed `
    --add-data "assets;assets" `
    --add-data "pyproject.toml;." `
    --icon $icon `
    $main_script

if (Test-Path (Join-Path $dist_dir "$project_name.exe")) {
    Write-Host "Build completed successfully!" -ForegroundColor Green
    Write-Host "Executable: $(Join-Path $dist_dir "$project_name.exe")"

    if (Test-Path $build_dir) {
        Remove-Item -Path $build_dir -Recurse -Force
        Write-Host "Intermediate build files cleaned up." -ForegroundColor Cyan
    }

    $spec_file = Join-Path $project_dir "$project_name.spec"
    if (Test-Path $spec_file) {
        Remove-Item -Path $spec_file -Force
        Write-Host "Spec file cleaned up." -ForegroundColor Cyan
    }
} else {
    Write-Host "Build failed!" -ForegroundColor Red
    exit 1
}
