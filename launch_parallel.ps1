# Launch 3 parallel workers, one per model family, each with its own Groq key.
# Each opens a new PowerShell window so progress is visible independently.
#
# Key assignment:
#   GROQ_API_KEY  -> M1 (llama-3.1-8b-instant)      — original key
#   GROQ_KEY_1    -> M2 (llama-4-scout-17b)          — second key
#   GROQ_KEY_2    -> M3 (allam-2-7b)                 — third key

$py   = (Get-Command python).Source
$base = "E:\compactation-poisoning"

$key0 = [System.Environment]::GetEnvironmentVariable("GROQ_API_KEY", "User")
$key1 = [System.Environment]::GetEnvironmentVariable("GROQ_KEY_1",   "User")
$key2 = [System.Environment]::GetEnvironmentVariable("GROQ_KEY_2",   "User")

if (-not $key0) { Write-Error "GROQ_API_KEY not set"; exit 1 }
if (-not $key1) { Write-Error "GROQ_KEY_1 not set";   exit 1 }
if (-not $key2) { Write-Error "GROQ_KEY_2 not set";   exit 1 }

Write-Host "Keys found. Launching 3 workers..." -ForegroundColor Green

# Worker 1 — M1 (llama-3.1-8b-instant) using original key
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Write-Host 'M1 Worker: llama-3.1-8b-instant' -ForegroundColor Cyan; " +
    "& '$py' '$base\run_pair.py' --model llama-3.1-8b-instant --tag-prefix M1 --groq-key '$key0'"
) -WindowStyle Normal

Start-Sleep -Seconds 3

# Worker 2 — M2 (llama-4-scout-17b) using second key
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Write-Host 'M2 Worker: llama-4-scout-17b-16e-instruct' -ForegroundColor Yellow; " +
    "& '$py' '$base\run_pair.py' --model 'meta-llama/llama-4-scout-17b-16e-instruct' --tag-prefix M2 --groq-key '$key1'"
) -WindowStyle Normal

Start-Sleep -Seconds 3

# Worker 3 — M3 (allam-2-7b) using third key
Start-Process powershell -ArgumentList @(
    "-NoExit", "-Command",
    "Write-Host 'M3 Worker: allam-2-7b' -ForegroundColor Magenta; " +
    "& '$py' '$base\run_pair.py' --model allam-2-7b --tag-prefix M3 --groq-key '$key2'"
) -WindowStyle Normal

Write-Host ""
Write-Host "3 workers launched in separate windows." -ForegroundColor Green
Write-Host "Progress logs: E:\compactation-poisoning\logs\pair_M*.log"
Write-Host "Results:       E:\compactation-poisoning\results\M*.jsonl"
Write-Host ""
Write-Host "To check progress anytime:"
Write-Host "  python E:\compactation-poisoning\quick_analysis.py"
