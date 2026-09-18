<#
.SYNOPSIS
    One end-to-end Windows/PowerShell entrypoint for the Phase 21 independent reproduction
    submission (Issue #89, PR #90 Round 5,
    ADOPT_P90_R5_REAL_AGENT_FINAL_PROTOCOL_AND_EXECUTABLE_REPRODUCTION, P90-R5-F3).

.DESCRIPTION
    Runs entirely on SHUKOU's own machine, the one holding the real encrypted PKCS8 PEM private
    key. This wrapper does nothing cryptographic itself -- it only locates a Python interpreter
    with the `cryptography` package installed and invokes this repository's own
    scripts/generate_and_sign_comparative_benchmark_independent_reproduction_submission.py,
    which does the actual reproduction, signing, and local verification.

    This script never reads, prints, logs, or persists the PEM file's contents or the passphrase.
    The passphrase is entered at a hidden prompt by the wrapped Python script itself
    (getpass.getpass); this wrapper never sees it. -PemPath is only ever passed through as a
    file path argument, never opened by this script.

.PARAMETER PemPath
    Path to SHUKOU's own encrypted PKCS8 PEM Ed25519 private key file. Read only by the wrapped
    Python script, only in memory, only for the one signing call.

.PARAMETER OutputPath
    Path to write the completed, publicly-safe submission JSON to. Defaults to
    independent_reproduction_submission.json under examples\comparative_benchmark next to this
    script's own repository root. Never contains the private key or passphrase.

.EXAMPLE
    .\scripts\reproduce_and_sign_comparative_benchmark_submission.ps1 `
        -PemPath "C:\Users\Apache\Documents\MANOSUBE_Phase21_Reproducer_Key\phase21_reproducer_private_key.pem"
#>

[CmdletBinding()]
param(
    [Parameter(Mandatory = $true)]
    [string]$PemPath,

    [Parameter(Mandatory = $false)]
    [string]$OutputPath
)

$ErrorActionPreference = "Stop"

$RepoRoot = Split-Path -Parent $PSScriptRoot
$GenerateScript = Join-Path $RepoRoot "scripts\generate_and_sign_comparative_benchmark_independent_reproduction_submission.py"

if (-not (Test-Path $GenerateScript)) {
    throw "Could not find $GenerateScript -- run this script from a checkout of manosube-agent-civilization-os."
}

if (-not (Test-Path $PemPath)) {
    throw "PEM file not found at $PemPath"
}

if (-not $OutputPath) {
    $OutputPath = Join-Path $RepoRoot "examples\comparative_benchmark\independent_reproduction_submission.json"
}

$PythonCandidates = @("python", "python3", "py")
$Python = $null
foreach ($candidate in $PythonCandidates) {
    $found = Get-Command $candidate -ErrorAction SilentlyContinue
    if ($found) {
        $Python = $found.Source
        break
    }
}

if (-not $Python) {
    throw "No Python interpreter found on PATH (tried: $($PythonCandidates -join ', ')). Install " +
        "Python 3.11+ with the 'cryptography' package (pip install cryptography) before running " +
        "this script."
}

Write-Host "Using Python interpreter: $Python"
Write-Host "Reproducing and signing the Phase 21 independent reproduction submission..."
Write-Host "You will be prompted for the PEM passphrase (input hidden, never logged by this wrapper)."

& $Python $GenerateScript --pem-path $PemPath --output $OutputPath
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    throw "generate_and_sign_comparative_benchmark_independent_reproduction_submission.py exited with code $ExitCode"
}

Write-Host "Submission written to: $OutputPath"
Write-Host "This file contains no private-key material and is safe to publish/hand off for admission."
