<#
.SYNOPSIS
    One end-to-end Windows/PowerShell entrypoint for PR #90's corrected Round 6 rebind frozen
    protocol's independent reproduction submission (Issue #89,
    ADOPT_P90_R6_REBIND_PRE_RESULT_FREEZE_AND_FRESH_RUN, comment 5715652626).

.DESCRIPTION
    Runs entirely on SHUKOU's own machine, the one holding the real encrypted PKCS8 PEM private
    key. This wrapper does nothing cryptographic itself -- it only locates a Python interpreter
    with the `cryptography` package installed and invokes this repository's own
    scripts\generate_and_sign_frozen_protocol_r6_independent_reproduction_submission.py, which
    does the actual reproduction, signing, and local verification.

    This script never reads, prints, logs, or persists the PEM file's contents or the
    passphrase. The passphrase is entered at a hidden prompt by the wrapped Python script
    itself (getpass.getpass); this wrapper never sees it. -PemPath is only ever passed through
    as a file path argument, never opened by this script.

.PARAMETER PemPath
    Path to SHUKOU's own encrypted PKCS8 PEM Ed25519 private key file. Read only by the wrapped
    Python script, only in memory, only for the one signing call.

.PARAMETER OutputPath
    Path to write the completed, publicly-safe submission JSON to. Defaults to
    independent_reproduction_submission.json under
    examples\comparative_benchmark\frozen_protocol_r6 next to this script's own repository
    root. Never contains the private key or passphrase.

.NOTES
    Windows bootstrap (P90-R6-WINDOWS-F1, PR #90 comment 5723625948) -- run these exact
    commands, in order, in PowerShell, before invoking this script:

        # 1. Clone (or update an existing clone of) the repository.
        git clone https://github.com/manosube/manosube-agent-civilization-os.git
        cd manosube-agent-civilization-os

        # 2. Check out the exact reviewed head this fix was verified against. Replace this
        #    with the current PR #90 head if SHUKOU has been told to re-run against a newer
        #    commit; otherwise use this literal commit.
        git checkout e66475ce0290c7f715515d76c609414caecc8ae4

        # 3. Create and activate a dedicated virtual environment. Requires Python 3.12 or
        #    later on PATH (this repository's own pyproject.toml requires-python = ">=3.12";
        #    SHUKOU's own prior run used Python 3.12.10).
        py -3.12 -m venv .venv
        .\.venv\Scripts\Activate.ps1

        # 4. Install this repository (and its "cryptography" dependency) into that venv.
        #    This is the one command that makes "python", "cryptography", and this
        #    repository's own packages resolvable -- do not skip it.
        pip install -e .

        # 5. Confirm "cryptography" installed correctly before proceeding.
        python -c "import cryptography; print(cryptography.__version__)"

    Only after all five steps succeed, run this script itself (see .EXAMPLE below). The
    -PemPath value in that example is illustrative and must be replaced with the real,
    absolute path to SHUKOU's own encrypted PKCS8 PEM private key file on this machine (never
    committed to, read from, or inferred by this repository).

.EXAMPLE
    .\scripts\reproduce_and_sign_frozen_protocol_r6_submission.ps1 `
        -PemPath "C:\path\to\your\encrypted_private_key.pem"
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
$GenerateScript = Join-Path $RepoRoot "scripts\generate_and_sign_frozen_protocol_r6_independent_reproduction_submission.py"

if (-not (Test-Path $GenerateScript)) {
    throw "Could not find $GenerateScript -- run this script from a checkout of manosube-agent-civilization-os."
}

if (-not (Test-Path $PemPath)) {
    throw "PEM file not found at $PemPath"
}

if (-not $OutputPath) {
    $OutputPath = Join-Path $RepoRoot "examples\comparative_benchmark\frozen_protocol_r6\independent_reproduction_submission.json"
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
Write-Host "Reproducing and signing the corrected Round 6 rebind frozen-protocol submission..."
Write-Host "You will be prompted for the PEM passphrase (input hidden, never logged by this wrapper)."

& $Python $GenerateScript --pem-path $PemPath --output $OutputPath
$ExitCode = $LASTEXITCODE

if ($ExitCode -ne 0) {
    throw "generate_and_sign_frozen_protocol_r6_independent_reproduction_submission.py exited with code $ExitCode"
}

Write-Host "Submission written to: $OutputPath"
Write-Host "This file contains no private-key material and is safe to publish/hand off for admission."
