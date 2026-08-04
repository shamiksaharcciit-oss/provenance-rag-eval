<#
.SYNOPSIS
  Create the Track C / M5 seed corpus as Confluence pages.

.DESCRIPTION
  Reads testdata/track_c_seed/*.md, converts each to Confluence storage format, and creates
  one page per file via the REST API. Pasting five markdown files by hand works too, but the
  editor's markdown conversion is inconsistent — this produces identical ADF every time.

  WRITES to Confluence. This is a standalone provisioning script using YOUR personal API
  token; the Forge app and the cross-check harness remain read-only and are unaffected.

  The body deliberately keeps the H1 heading even though Confluence stores the title
  separately: the formatter's subject heuristic reads the body's first block, and a bare
  system name there is what makes it return "The Kestrel indexer" instead of a fragment.

.PARAMETER SpaceKey
  Target space key, e.g. PH. Find it with: npm run crosscheck -- --list-spaces

.PARAMETER DryRun
  Print what would be created without calling the API.

.EXAMPLE
  .\scripts\publish_seed_corpus.ps1 -SpaceKey PH
#>
[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)][string]$SpaceKey,
    [switch]$DryRun
)

$ErrorActionPreference = 'Stop'
[Net.ServicePointManager]::SecurityProtocol = [Net.SecurityProtocolType]::Tls12

foreach ($v in 'CONFLUENCE_SITE', 'CONFLUENCE_EMAIL', 'CONFLUENCE_API_TOKEN') {
    if (-not (Get-Item "env:$v" -ErrorAction SilentlyContinue)) {
        throw "$v is not set. Set it in this window first (see forge-app/README.md)."
    }
}

$site = $env:CONFLUENCE_SITE
$pair = "$($env:CONFLUENCE_EMAIL):$($env:CONFLUENCE_API_TOKEN)"
$auth = [Convert]::ToBase64String([Text.Encoding]::UTF8.GetBytes($pair))
$headers = @{ Authorization = "Basic $auth"; Accept = 'application/json' }

$seedDir = Join-Path $PSScriptRoot '..\testdata\track_c_seed'
$files = Get-ChildItem -Path $seedDir -Filter '*.md' | Where-Object { $_.Name -ne 'README.md' }
if ($files.Count -eq 0) { throw "No seed markdown found in $seedDir" }

function ConvertTo-StorageFormat {
    param([string]$Markdown)
    $esc = { param($s) $s.Replace('&', '&amp;').Replace('<', '&lt;').Replace('>', '&gt;') }
    $out = New-Object System.Text.StringBuilder
    foreach ($block in ($Markdown -split "(\r?\n){2,}")) {
        $b = $block.Trim()
        if (-not $b) { continue }
        if ($b -match '^##\s+(.*)$')  { [void]$out.Append("<h2>$(& $esc $Matches[1])</h2>"); continue }
        if ($b -match '^#\s+(.*)$')   { [void]$out.Append("<h1>$(& $esc $Matches[1])</h1>"); continue }
        # collapse soft line breaks inside a paragraph, as markdown does
        $text = ($b -replace '\r?\n', ' ')
        [void]$out.Append("<p>$(& $esc $text)</p>")
    }
    return $out.ToString()
}

# Resolve the space key to its numeric id (the v2 create endpoint wants spaceId).
# Skipped under -DryRun so a dry run makes no network call at all.
$spaceId = $null
if (-not $DryRun) {
    $spaceUri = "https://$site/wiki/api/v2/spaces?keys=$([Uri]::EscapeDataString($SpaceKey))"
    $spaceResp = Invoke-RestMethod -Uri $spaceUri -Headers $headers -Method Get
    if (-not $spaceResp.results -or $spaceResp.results.Count -eq 0) {
        throw "No space with key '$SpaceKey' (keys are case-sensitive)."
    }
    $spaceId = $spaceResp.results[0].id
    Write-Host "Space $SpaceKey -> id $spaceId" -ForegroundColor Cyan
}

$created = @()
foreach ($file in $files) {
    $md = Get-Content -Path $file.FullName -Raw -Encoding UTF8
    $titleLine = ($md -split "`n" | Where-Object { $_ -match '^#\s+' } | Select-Object -First 1)
    if (-not $titleLine) { Write-Warning "$($file.Name): no H1, skipped"; continue }
    $title = ($titleLine -replace '^#\s+', '').Trim()
    $storage = ConvertTo-StorageFormat -Markdown $md

    if ($DryRun) {
        Write-Host "  [dry-run] would create '$title' ($($storage.Length) chars)"
        Write-Verbose ("           " + $storage.Substring(0, [Math]::Min(220, $storage.Length)))
        continue
    }

    $payload = @{
        spaceId = $spaceId
        status  = 'current'
        title   = $title
        body    = @{ representation = 'storage'; value = $storage }
    } | ConvertTo-Json -Depth 6 -Compress

    try {
        $resp = Invoke-RestMethod -Uri "https://$site/wiki/api/v2/pages" -Headers $headers `
            -Method Post -ContentType 'application/json' -Body ([Text.Encoding]::UTF8.GetBytes($payload))
        Write-Host ("  created {0,-10} {1}" -f $resp.id, $title) -ForegroundColor Green
        $created += $resp.id
    }
    catch {
        $msg = $_.Exception.Message
        if ($_.ErrorDetails.Message) { $msg = $_.ErrorDetails.Message }
        Write-Warning "  '$title' failed: $msg"
        Write-Warning "  (a page with this title may already exist in $SpaceKey)"
    }
}

if ($DryRun) { return }

Write-Host ""
if ($created.Count -eq 0) {
    Write-Warning "No pages created."
    return
}
Write-Host "$($created.Count) page(s) created." -ForegroundColor Cyan
Write-Host ""
Write-Host "Next:" -ForegroundColor Cyan
Write-Host "  cd forge-app"
Write-Host "  npm run crosscheck -- --inspect $($created -join ' ')"
Write-Host "  npm run crosscheck -- $($created -join ' ')"
