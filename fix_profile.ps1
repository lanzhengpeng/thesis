$user = 'lanzhengpeng'
$profilePath = "C:\Users\$user"
$defaultHive = 'C:\Users\Default\NTUSER.DAT'
$userHive = "$profilePath\NTUSER.DAT"
$backupHive = "$profilePath\NTUSER.DAT.backup.$(Get-Date -Format yyyyMMddHHmmss)"

if (Test-Path $userHive) {
    Rename-Item $userHive $backupHive -Force
    Write-Host "Backed up existing NTUSER.DAT to $backupHive"
}

Copy-Item $defaultHive $userHive -Force
Write-Host "Copied Default NTUSER.DAT to $userHive"

takeown /F $userHive /A | Out-Null
icacls $userHive /grant "$user`:(F)" /grant 'Administrators:(F)' /inheritance:r | Out-Null
Write-Host "Permissions set for $user"

# Fix ProfileList registry
$regPath = 'HKLM:\SOFTWARE\Microsoft\Windows NT\CurrentVersion\ProfileList'
$sid = 'S-1-5-21-1428882062-3347508204-3945601965-1000'
$badKey = "$regPath\$sid"
$bakKey = "$regPath\$sid.bak"

if (Test-Path $badKey) {
    Remove-Item $badKey -Recurse -Force
    Write-Host "Removed bad ProfileList key"
}
if (Test-Path $bakKey) {
    Rename-Item $bakKey $sid -Force
    Write-Host "Renamed .bak key"
}

Set-ItemProperty -Path $badKey -Name 'State' -Value 0 -Type DWord -ErrorAction SilentlyContinue
Set-ItemProperty -Path $badKey -Name 'RefCount' -Value 0 -Type DWord -ErrorAction SilentlyContinue
Write-Host "Registry fixed"
