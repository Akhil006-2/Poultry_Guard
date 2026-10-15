$ErrorActionPreference='Stop'
$base='http://127.0.0.1:8000'
Write-Host 'Health:'; Invoke-RestMethod "$base/health" | ConvertTo-Json
Write-Host 'Status:'; Invoke-RestMethod "$base/api/v1/status" | ConvertTo-Json
Write-Host 'Summary:'; Invoke-RestMethod "$base/api/v1/reports/summary" | ConvertTo-Json
$video=Get-ChildItem '.\sample_data\poultry_videos' -File -Include *.mp4,*.avi,*.mov,*.mkv -Recurse | Select-Object -First 1
if ($video) { Write-Host "Found sample video: $($video.FullName)"; Write-Host 'Upload through Swagger /docs or run scripts/analyze_video.py directly.' } else { Write-Warning 'No sample video folder found.' }
