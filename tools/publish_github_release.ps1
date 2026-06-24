param(
    [Parameter(Mandatory = $true)]
    [string]$RepoSlug,
    [switch]$CreateRepo
)

$ErrorActionPreference = "Stop"

$root = Split-Path -Parent $PSScriptRoot
Set-Location $root

function Ensure-GitHubAuth {
    gh auth status | Out-Null
    if ($LASTEXITCODE -ne 0) {
        throw "GitHub CLI has not logged in yet. Run 'gh auth login' first, then retry this script."
    }
}

function Ensure-GitRepository {
    if (-not (Test-Path .git)) {
        git init -b main | Out-Null
    }
}

function Has-GitCommit {
    try {
        git rev-parse --verify HEAD 1>$null 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Ensure-InitialCommit {
    if (Has-GitCommit) {
        return
    }
    git add .
    git commit -m "Initial commit: Network Quiz APK" | Out-Null
}

function Has-OriginRemote {
    try {
        git remote get-url origin 1>$null 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Ensure-ReleaseNotes([string]$path, [string]$versionName) {
    if (Test-Path $path) {
        return
    }
    @"
# v$versionName

- Fill in the release notes for this version here.
"@ | Set-Content -Path $path -Encoding UTF8
}

function Read-JsonFile([string]$path) {
    return Get-Content -Raw -Encoding UTF8 $path | ConvertFrom-Json
}

function Test-ReleaseExists([string]$repoSlug, [string]$tag) {
    try {
        gh release view $tag --repo $repoSlug 1>$null 2>$null
        return $LASTEXITCODE -eq 0
    } catch {
        return $false
    }
}

function Get-ReleaseApi([string]$repoSlug, [string]$tag) {
    $json = gh api "repos/$repoSlug/releases/tags/$tag"
    return $json | ConvertFrom-Json
}

function Find-ApkAssetUrl($release, [string]$preferredName) {
    $apkAsset = $null
    if ($preferredName) {
        $apkAsset = $release.assets | Where-Object { $_.name -eq $preferredName } | Select-Object -First 1
    }
    if (-not $apkAsset) {
        $apkAsset = $release.assets | Where-Object { $_.name -like "*.apk" } | Select-Object -First 1
    }
    if (-not $apkAsset) {
        throw "No APK asset was found in release $($release.tag_name)."
    }
    return $apkAsset.browser_download_url
}

Ensure-GitHubAuth
Ensure-GitRepository
Ensure-InitialCommit

$manifest = Get-Content .\app\src\main\AndroidManifest.xml -Raw -Encoding UTF8
$versionName = [regex]::Match($manifest, 'android:versionName="([^"]+)"').Groups[1].Value
if (-not $versionName) {
    throw "Unable to read versionName from AndroidManifest.xml"
}

$tag = "v$versionName"
$notes = Join-Path $root "release\RELEASE_NOTES.md"
$meta = Join-Path $root "release\network_quiz_update.json"

Ensure-ReleaseNotes -path $notes -versionName $versionName

python .\tools\build_network_quiz_apk.py
python .\tools\generate_release_metadata.py --release-notes-file $notes

$metaInfo = Read-JsonFile $meta
$apk = Join-Path $root ("build\out\" + $metaInfo.apkFileName)
if (-not (Test-Path $apk)) {
    throw "APK not found: $apk"
}

if ($CreateRepo -and -not (Has-OriginRemote)) {
    gh repo create $RepoSlug --public --source . --remote origin --push
}

if (Test-ReleaseExists -repoSlug $RepoSlug -tag $tag) {
    gh release edit $tag --repo $RepoSlug --title $tag --notes-file $notes
    gh release upload $tag $apk --repo $RepoSlug --clobber
} else {
    gh release create $tag $apk --repo $RepoSlug --title $tag --notes-file $notes
}

$release = Get-ReleaseApi -repoSlug $RepoSlug -tag $tag
$apkDownloadUrl = Find-ApkAssetUrl -release $release -preferredName $metaInfo.apkFileName

python .\tools\generate_release_metadata.py --release-notes-file $notes --apk-download-url $apkDownloadUrl
gh release upload $tag $meta --repo $RepoSlug --clobber

$releaseUrl = $release.html_url
Write-Host "Release published:" $tag
Write-Host "Repository:" $RepoSlug
Write-Host "Release URL:" $releaseUrl
