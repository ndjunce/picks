# Update app.py and Push to GitHub
# This script takes code input and automatically updates your file and pushes to GitHub

param(
    [Parameter(Mandatory=$false)]
    [string]$FilePath = "C:\fantasy python\app.py",
    
    [Parameter(Mandatory=$false)]
    [string]$ProjectPath = "C:\fantasy python",
    
    [Parameter(Mandatory=$false)]
    [string]$CommitMessage = "Updated app.py from Claude",
    
    [Parameter(Mandatory=$false)]
    [string]$Branch = "main"
)

function Update-FileAndPush {
    Write-Host "=== Code Update and Git Push Tool ===" -ForegroundColor Cyan
    Write-Host "File: $FilePath" -ForegroundColor Yellow
    Write-Host "Repo: ndjunce/picks" -ForegroundColor Yellow
    Write-Host ""
    
    # Get code from clipboard or user input
    Write-Host "Choose input method:" -ForegroundColor Green
    Write-Host "1. Paste code directly (press Enter when done)" -ForegroundColor White
    Write-Host "2. Read from clipboard" -ForegroundColor White
    Write-Host "3. Enter code line by line (type 'END' on new line to finish)" -ForegroundColor White
    
    $choice = Read-Host "Enter choice (1, 2, or 3)"
    
    $newCode = ""
    
    switch ($choice) {
        "1" {
            Write-Host "`nPaste your code and press Enter twice when done:" -ForegroundColor Green
            $lines = @()
            do {
                $line = Read-Host
                if ($line -ne "") {
                    $lines += $line
                } else {
                    break
                }
            } while ($true)
            $newCode = $lines -join "`n"
        }
        "2" {
            try {
                $newCode = Get-Clipboard -Raw
                Write-Host "Code read from clipboard!" -ForegroundColor Green
            }
            catch {
                Write-Host "Error reading clipboard: $($_.Exception.Message)" -ForegroundColor Red
                return
            }
        }
        "3" {
            Write-Host "`nEnter your code (type 'END' on a new line to finish):" -ForegroundColor Green
            $lines = @()
            do {
                $line = Read-Host
                if ($line -eq "END") {
                    break
                }
                $lines += $line
            } while ($true)
            $newCode = $lines -join "`n"
        }
        default {
            Write-Host "Invalid choice. Exiting." -ForegroundColor Red
            return
        }
    }
    
    if ([string]::IsNullOrWhiteSpace($newCode)) {
        Write-Host "No code provided. Exiting." -ForegroundColor Red
        return
    }
    
    # Show preview of code
    Write-Host "`n=== Code Preview ===" -ForegroundColor Cyan
    Write-Host $newCode.Substring(0, [Math]::Min(200, $newCode.Length))
    if ($newCode.Length -gt 200) {
        Write-Host "... (truncated)" -ForegroundColor Gray
    }
    
    $confirm = Read-Host "`nWrite this code to $FilePath? (y/n)"
    
    if ($confirm -eq "y" -or $confirm -eq "Y") {
        try {
            # Create directory if it doesn't exist
            $directory = Split-Path $FilePath -Parent
            if (-not (Test-Path $directory)) {
                New-Item -ItemType Directory -Path $directory -Force
                Write-Host "Created directory: $directory" -ForegroundColor Green
            }
            
            # Write code to file
            $newCode | Out-File -FilePath $FilePath -Encoding UTF8 -Force
            Write-Host "✅ Code written to $FilePath" -ForegroundColor Green
            
            # Change to project directory
            Push-Location $ProjectPath
            
            try {
                Write-Host "`nCommitting and pushing to GitHub..." -ForegroundColor Yellow
                
                # Add the file
                git add $FilePath
                
                # Check if there are changes
                $status = git status --porcelain $FilePath
                if ([string]::IsNullOrEmpty($status)) {
                    Write-Host "No changes detected in the file." -ForegroundColor Yellow
                    return
                }
                
                # Commit with timestamp
                $timestampedMessage = "$CommitMessage - $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')"
                git commit -m $timestampedMessage
                
                # Push to remote
                git push origin $Branch
                
                Write-Host "✅ Successfully pushed to GitHub!" -ForegroundColor Green
                Write-Host "Repository: https://github.com/ndjunce/picks" -ForegroundColor Cyan
                
            }
            catch {
                Write-Host "❌ Git error: $($_.Exception.Message)" -ForegroundColor Red
                Write-Host "Make sure you're in a git repository and have configured your remote." -ForegroundColor Yellow
            }
            finally {
                Pop-Location
            }
            
        }
        catch {
            Write-Host "❌ Error writing file: $($_.Exception.Message)" -ForegroundColor Red
        }
    }
    else {
        Write-Host "Operation cancelled." -ForegroundColor Yellow
    }
}

# Run the function
Update-FileAndPush