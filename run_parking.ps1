# Set working directory
Set-Location -Path "C:\AAA"

function Show-Header {
    Write-Host ""
    Write-Host "================================"
    Write-Host "    SISTEM PARKIR RSI BNA"
    Write-Host "================================"
    Write-Host ""
}

while ($true) {
    Show-Header
    $timestamp = Get-Date -Format "ddd MM/dd/yyyy HH:mm:ss.ff"
    Write-Host "[$timestamp] Starting parking system..."
    
    try {
        # Activate virtual environment and run the program
        & "$PWD\myenv\Scripts\python.exe" parking_camera_windows.py
    }
    catch {
        Write-Host ""
        Write-Host "[$timestamp] Program terminated with error. Restarting in 5 seconds..."
        Start-Sleep -Seconds 5
        continue
    }
    
    Write-Host ""
    Write-Host "[$timestamp] Program ended. Restarting in 5 seconds..."
    Start-Sleep -Seconds 5
} 