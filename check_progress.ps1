# check_progress.ps1
# Run this anytime to see how many conditions have completed across all 10 batches.
# Usage: powershell -File E:\compactation-poisoning\check_progress.ps1 [-Pid <PID>]

param([int]$ProcId = 0)

$results = "E:\compactation-poisoning\results"
$logs    = "E:\compactation-poisoning\logs"
$total_conditions = 1040

Write-Host ""
Write-Host "====== ISMC EXPERIMENT PROGRESS ======" -ForegroundColor Cyan
Write-Host "  Checked at: $(Get-Date -Format 'yyyy-MM-dd HH:mm:ss')" -ForegroundColor DarkGray
Write-Host ""

# Process alive check
if ($ProcId -gt 0) {
    $proc = Get-Process -Id $ProcId -ErrorAction SilentlyContinue
    if ($proc) {
        Write-Host "  Orchestrator PID $ProcId : RUNNING (CPU=$($proc.CPU)s)" -ForegroundColor Green
    } else {
        Write-Host "  Orchestrator PID $ProcId : NOT FOUND (may have finished or crashed)" -ForegroundColor Red
    }
    Write-Host ""
}

# Per-batch progress
Write-Host "  Batch                  Rows    /1040    Pct    Status" -ForegroundColor White
Write-Host "  -------------------------------------------------------" -ForegroundColor DarkGray

$batches = @(
    "M1_anthropic","M1_mem0",
    "M2_anthropic","M2_mem0",
    "M3_anthropic","M3_mem0",
    "M4_anthropic","M4_mem0",
    "M5_anthropic","M5_mem0"
)

$grand_total = 0
foreach ($batch in $batches) {
    $file = "$results\$batch.jsonl"
    if (Test-Path $file) {
        $lines = (Get-Content $file -ErrorAction SilentlyContinue | Measure-Object -Line).Lines
    } else {
        $lines = 0
    }
    $grand_total += $lines
    $pct = if ($total_conditions -gt 0) { [math]::Round(($lines / $total_conditions) * 100, 1) } else { 0 }

    if ($lines -ge $total_conditions) {
        $status = "DONE  "; $color = "Green"
    } elseif ($lines -gt 0) {
        $status = "ACTIVE"; $color = "Yellow"
    } else {
        $status = "PENDING"; $color = "DarkGray"
    }

    Write-Host ("  {0,-22} {1,5}    {2,5}  {3,5}%   " -f $batch, $lines, $total_conditions, $pct) -NoNewline
    Write-Host $status -ForegroundColor $color
}

$grand_pct = [math]::Round(($grand_total / (10 * $total_conditions)) * 100, 1)
Write-Host ""
Write-Host "  Total: $grand_total / 10400   ($grand_pct% complete)" -ForegroundColor Cyan

# ETA estimate
if ($grand_total -gt 0 -and $grand_total -lt 10400) {
    $log_file = "$logs\run_log.txt"
    if (Test-Path $log_file) {
        $start_lines = Get-Content $log_file | Where-Object { $_ -match "EXPERIMENT RUN STARTED" }
        $last_start = $start_lines | Select-Object -Last 1
        if ($last_start -match "\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]") {
            try {
                $start_time = [datetime]::ParseExact($Matches[1], "yyyy-MM-dd HH:mm:ss", $null)
                $elapsed_min = (Get-Date - $start_time).TotalMinutes
                if ($elapsed_min -gt 0 -and $grand_total -gt 0) {
                    $rate = $grand_total / $elapsed_min
                    $remaining = (8 * $total_conditions) - $grand_total  # 8 Groq batches only
                    $eta_min = [math]::Round($remaining / $rate, 0)
                    $eta_time = (Get-Date).AddMinutes($eta_min)
                    $rate_r = [math]::Round($rate, 2)
                    Write-Host "  Rate: $rate_r rows/min  |  ETA: ~$eta_min min from now  (~$($eta_time.ToString('HH:mm ddd MMM d')))" -ForegroundColor Magenta
                }
            } catch {}
        }
    }
}

Write-Host ""
Write-Host "-- Run log (last 8 lines) --" -ForegroundColor DarkGray
Get-Content "$logs\run_log.txt" -Tail 8 -ErrorAction SilentlyContinue | ForEach-Object {
    Write-Host "  $_" -ForegroundColor DarkGray
}

# Error scan — show any recent error lines from stderr logs
Write-Host ""
Write-Host "-- Recent errors (if any) --" -ForegroundColor DarkGray
$error_lines = @()
foreach ($batch in $batches) {
    $err_file = "$logs\$batch.err"
    if (Test-Path $err_file) {
        $lines = Get-Content $err_file -Tail 5 -ErrorAction SilentlyContinue |
                 Where-Object { $_ -match "Error|Exception|Traceback|rate.limit|429" }
        foreach ($l in $lines) { $error_lines += "[$batch] $l" }
    }
}
if ($error_lines.Count -gt 0) {
    $error_lines | Select-Object -Last 10 | ForEach-Object { Write-Host "  $_" -ForegroundColor Red }
} else {
    Write-Host "  (none detected)" -ForegroundColor Green
}
Write-Host ""
