# Quick Java Installation Check Script
# Run this script to verify Java is installed correctly

Write-Host "============================================================"
Write-Host "Java Installation Check"
Write-Host "============================================================"
Write-Host ""

# Check if Java is in PATH
try {
    $javaVersion = & java -version 2>&1
    if ($LASTEXITCODE -eq 0) {
        Write-Host "✓ Java is installed!" -ForegroundColor Green
        Write-Host "Version:" -ForegroundColor Cyan
        Write-Host $javaVersion[0]
        Write-Host ""
        
        # Try to find JAVA_HOME
        if ($env:JAVA_HOME) {
            Write-Host "✓ JAVA_HOME is set:" -ForegroundColor Green
            Write-Host "  $env:JAVA_HOME" -ForegroundColor Cyan
        } else {
            Write-Host "⚠ JAVA_HOME is not set" -ForegroundColor Yellow
            Write-Host ""
            Write-Host "Common Java installation locations:" -ForegroundColor Yellow
            $commonPaths = @(
                "C:\Program Files\Eclipse Adoptium\jdk-11*",
                "C:\Program Files\Java\jdk-11*",
                "C:\Program Files (x86)\Java\jdk-11*"
            )
            
            $found = $false
            foreach ($path in $commonPaths) {
                $jdkPath = Get-ChildItem -Path $path -ErrorAction SilentlyContinue | Select-Object -First 1
                if ($jdkPath) {
                    Write-Host "  Found Java at: $($jdkPath.FullName)" -ForegroundColor Cyan
                    Write-Host ""
                    Write-Host "To set JAVA_HOME, run:" -ForegroundColor Yellow
                    Write-Host "  `$env:JAVA_HOME = `"$($jdkPath.FullName)`"" -ForegroundColor White
                    Write-Host "  `$env:PATH = `"`$env:JAVA_HOME\bin;`$env:PATH`"" -ForegroundColor White
                    $found = $true
                    break
                }
            }
            
            if (-not $found) {
                Write-Host "  Could not automatically find Java installation" -ForegroundColor Red
                Write-Host ""
                Write-Host "Please install Java 11 from:" -ForegroundColor Yellow
                Write-Host "  https://adoptium.net/temurin/releases/?version=11" -ForegroundColor Cyan
            }
        }
        
        Write-Host ""
        Write-Host "============================================================"
        Write-Host "✓ Java check passed! You should be able to run Spark ETL." -ForegroundColor Green
        Write-Host "============================================================"
        exit 0
    }
} catch {
    Write-Host "✗ Java is NOT installed or not in PATH" -ForegroundColor Red
    Write-Host ""
    Write-Host "Please install Java 11:" -ForegroundColor Yellow
    Write-Host "  1. Visit: https://adoptium.net/temurin/releases/?version=11" -ForegroundColor Cyan
    Write-Host "  2. Download: JDK 11 → x64 Windows → JDK → HotSpot → Latest Release" -ForegroundColor Cyan
    Write-Host "  3. Run the installer (.msi file)" -ForegroundColor Cyan
    Write-Host "  4. Make sure to check 'Add to PATH' during installation" -ForegroundColor Cyan
    Write-Host "  5. Restart your terminal after installation" -ForegroundColor Cyan
    Write-Host ""
    Write-Host "============================================================"
    Write-Host "✗ Java check failed. Please install Java before running Spark ETL." -ForegroundColor Red
    Write-Host "============================================================"
    exit 1
}
