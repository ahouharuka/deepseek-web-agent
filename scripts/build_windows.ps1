$ErrorActionPreference = "Stop"
$ProjectRoot = Split-Path -Parent $PSScriptRoot
Set-Location $ProjectRoot
python -m pip install -r requirements-build.txt
python -m PyInstaller --noconfirm --clean DeepSeekWebAgent.spec
Copy-Item "README-Windows.txt" "dist\DeepSeekWebAgent\README-Windows.txt" -Force
Compress-Archive -Path "dist\DeepSeekWebAgent" -DestinationPath "dist\DeepSeekWebAgent-windows.zip" -Force
Write-Host "Built dist\DeepSeekWebAgent-windows.zip"
