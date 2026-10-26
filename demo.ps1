<#
.SYNOPSIS
  Starts the SentrAI demo lab on Windows (the PowerShell twin of demo.sh; Windows PowerShell 5.1 works).

.DESCRIPTION
  panel   SentrAI's own core + dashboard, from a SentrAI checkout     http://127.0.0.1:8000 / :8501
  agent   SentrAI's machine agent, joined to the panel as "aegis-web": ships the portal's logs
          and keeps the panel's blocks for this machine
  portal  the fake Aegis Academy student portal                     http://127.0.0.1:5000
          with the test-attack buttons on                           http://127.0.0.1:5000/lab

  Everything the demo makes stays in .demo\ (its own SentrAI settings, logs, keys), so it never
  touches a real SentrAI install on the same computer. Stop it all with .\stop.ps1.

.EXAMPLE
  .\demo.ps1                          # everything on this computer (panel, agent, portal)
  .\demo.ps1 -Tripwires               # also the decoy admin page, bait rows and tarpit
  .\demo.ps1 -SentrAI C:\src\SentrAI  # use this SentrAI checkout instead of cloning one into .demo\
  .\demo.ps1 -Panel https://panel.example.com:8000 -Code ABCD-EFGH-JKLM
                                      # lab machine only: join a panel running elsewhere (-AllowHttp
                                      # on a private test network without HTTPS)
  .\demo.ps1 -PanelOnly -AttackerIp 192.168.1.60
                                      # three-machine demo, machine 1: only the SentrAI panel. The attacker's
                                      # address is the one allowed to be blocked (private networks are
                                      # otherwise never auto-blocked)
  .\demo.ps1 -Panel http://PANEL:8000 -AllowHttp -Code CODE -Listen
                                      # machine 2: the website (portal) + agent, open to the network so the
                                      # AI attacker machine can reach it on port 5000
                                      # machine 3: python attacker.py --portal http://PORTAL-IP:5000
  .\demo.ps1 -Name web-02             # the lab machine's name on the panel (default aegis-web)
  .\demo.ps1 -Speed 60                # faster panel timers (1 real minute = 1 hour); default real time
  .\demo.ps1 -Fresh                   # start over: new panel data, new join, empty portal logs (keeps
                                      # the SentrAI copy and the Python packages)
#>
param(
    [string]$SentrAI = $env:SENTRAI_DIR,
    [string]$Panel = "",
    [string]$Code = "",
    [switch]$AllowHttp,
    [string]$Name = "aegis-web",
    [Alias("Spines")] [switch]$Tripwires,
    [double]$Speed = $(if ($env:DEMO_SPEED) { [double]$env:DEMO_SPEED } else { 1 }),
    [switch]$NoDashboard,
    [switch]$Fresh,
    [switch]$PanelOnly,
    [switch]$Listen,
    [string]$AttackerIp = "",
    [switch]$NoBrowser
)

$ErrorActionPreference = "Stop"
$Kit = Split-Path -Parent $MyInvocation.MyCommand.Path
$State = Join-Path $Kit ".demo"
$Repo = if ($env:SENTRAI_REPO) { $env:SENTRAI_REPO } else { "https://github.com/RexGuard/SentrAI" }
$Branch = if ($env:SENTRAI_BRANCH) { $env:SENTRAI_BRANCH } else { "main" }
$PidFile = Join-Path $State "pids"
$AgentFile = Join-Path $State "agent.json"

if ($Panel -and -not $Code -and -not (Test-Path $AgentFile)) {
    Write-Host "-Panel needs -Code: make a join code on the panel's Machines page." -ForegroundColor Red; exit 2
}
if (Test-Path $PidFile) {
    Write-Host "The demo seems to be running already (found .demo\pids). Run .\stop.ps1 first." -ForegroundColor Yellow; exit 1
}
try {
    $c = New-Object System.Net.Sockets.TcpClient; $c.Connect("127.0.0.1", 5000); $c.Close()
    Write-Host "Port 5000 (the portal's) is already in use: stop whatever runs there first." -ForegroundColor Red; exit 1
} catch { }
if ($Fresh) {
    Write-Host "Starting over: removing the demo's panel data, agent key and portal logs ..."
    foreach ($x in @("panel", "agent", "logs", "agent.json", "portal.sqlite3")) {
        Remove-Item -Recurse -Force -ErrorAction SilentlyContinue (Join-Path $State $x)
    }
}
foreach ($d in @("logs", "agent", "panel", "panel\data")) { New-Item -ItemType Directory -Force -Path (Join-Path $State $d) | Out-Null }
Remove-Item -Force -ErrorAction SilentlyContinue (Join-Path $State "panel\started")

# Settings below are for this demo only: put them back afterwards so this PowerShell window is unchanged.
$kitEnv = @("CONFIG", "RISK_SCOPE", "SCOUT_SOURCES", "AGENT_FILE", "COLLECTOR_STATE", "LAB_LOGS", "FIREWALL", "SPINES", "DB", "QUARANTINE")
$envNames = @("DEMO_SPEED", "PYTHONUNBUFFERED", "PYTHONUTF8", "PROTECTED_NETS", "PROTECTED_IPS", "PORTAL_HOST")
foreach ($k in $kitEnv) { $envNames += "SENTRAI_$k"; $envNames += "CACTAI_$k" }
$savedEnv = @{}
foreach ($n in $envNames) { $savedEnv[$n] = [Environment]::GetEnvironmentVariable($n, "Process") }

# SentrAI renamed its CACTAI_* settings to SENTRAI_* (PR #88; the old names still work there, with a
# warning, and older checkouts only know the old ones). Each setting is made under the name the
# checkout in use understands, so the kit works with either and never triggers the warning.
$script:KitPrefix = "CACTAI_"
function Set-KitEnv([string]$Name, [string]$Value) {
    [Environment]::SetEnvironmentVariable("$($script:KitPrefix)$Name", $Value, "Process")
    # clear the other spelling so a stale value can't linger
    $other = if ($script:KitPrefix -eq "SENTRAI_") { "CACTAI_" } else { "SENTRAI_" }
    [Environment]::SetEnvironmentVariable("$other$Name", $null, "Process")
}
function Get-KitEnv([string]$Name, [string]$Default) {
    foreach ($p in @("SENTRAI_", "CACTAI_")) {
        $v = [Environment]::GetEnvironmentVariable("$p$Name", "Process")
        if ($v) { return $v }
    }
    return $Default
}
function Get-ConfigScript([string]$Mvp) {
    $n = Join-Path $Mvp "sentrai_config.py"
    if (Test-Path $n) { return $n } else { return (Join-Path $Mvp "cactai_config.py") }
}

function Find-Python {
    foreach ($cand in @("py", "python")) {
        if (Get-Command $cand -ErrorAction SilentlyContinue) { return $cand }
    }
    throw "Python 3 not found (install it from python.org and tick 'Add to PATH')."
}

function Wait-Http([string]$Url, [int]$Seconds = 40) {
    $deadline = (Get-Date).AddSeconds($Seconds)
    while ((Get-Date) -lt $deadline) {
        try { Invoke-WebRequest -UseBasicParsing -TimeoutSec 2 $Url | Out-Null; return $true } catch { Start-Sleep -Milliseconds 500 }
    }
    return $false
}

$pids = @()
function Start-Bg([string]$Title, [string]$Exe, [string[]]$ArgList) {
    $out = Join-Path $State "$Title.log"
    $err = Join-Path $State "$Title.err.log"
    $p = Start-Process -FilePath $Exe -ArgumentList $ArgList -WorkingDirectory $Kit -WindowStyle Hidden `
        -RedirectStandardOutput $out -RedirectStandardError $err -PassThru
    $script:pids += $p.Id
    $script:pids | Set-Content -Encoding ascii $PidFile
    Write-Host ("  started {0,-7} (pid {1}, log .demo\{0}.log)" -f $Title, $p.Id)
}

try {
    # 1. SentrAI itself: the product is never copied into this repo, only checked out next to it.
    if (-not $SentrAI) {
        $SentrAI = Join-Path $State "SentrAI"
        if (Test-Path (Join-Path $SentrAI ".git")) {
            Write-Host "Updating SentrAI ($Branch) in .demo\SentrAI ..."
            git -C $SentrAI pull -q --ff-only origin $Branch
            if ($LASTEXITCODE -ne 0) { Write-Host "  (could not update; using the copy there)" -ForegroundColor Yellow }
        } else {
            Write-Host "Getting SentrAI ($Branch) into .demo\SentrAI ..."
            git clone -q --depth 1 --branch $Branch $Repo $SentrAI
            if ($LASTEXITCODE -ne 0) { throw "git clone of $Repo failed." }
        }
    }
    $SentrAI = (Resolve-Path $SentrAI).Path
    $Mvp = Join-Path $SentrAI "mvp"
    if (-not (Test-Path (Join-Path $Mvp "lab\agent\agent.py"))) { throw "$SentrAI has no machine agent (mvp\lab\agent): use a newer SentrAI." }
    $SentrAI | Set-Content -Encoding utf8 (Join-Path $State "sentrai-dir")
    if (Test-Path (Join-Path $Mvp "sentrai_config.py")) { $script:KitPrefix = "SENTRAI_" }

    # 2. The portal's own Python packages.
    $pyKit = Join-Path $State "venv\Scripts\python.exe"
    if (-not (Test-Path $pyKit)) {
        Write-Host "Creating the portal's venv ..."
        $py = Find-Python
        & $py -m venv (Join-Path $State "venv")
    }
    & $pyKit -m pip install -q -r (Join-Path $Kit "requirements.txt")

    # 3. The panel, unless this machine joins one elsewhere. Host scope: each machine has its own
    #    risk score and its own blocks. Its settings are kept in .demo\panel.
    $AllowHttpJoin = [bool]$AllowHttp
    if (-not $Panel) {
        Set-KitEnv "CONFIG" (Join-Path $State "panel\config.json")
        Set-KitEnv "RISK_SCOPE" "host"
        $env:DEMO_SPEED = "$Speed"
        Set-KitEnv "SCOUT_SOURCES" (Join-Path $State "panel\sources.json")
        # The panel's database, machine keys, backups and quarantine also stay in .demo\panel, never
        # in the SentrAI checkout (which may be a real install when -SentrAI points at one).
        Set-KitEnv "DB" (Join-Path $State "panel\data\sentrai.db")
        Set-KitEnv "QUARANTINE" (Join-Path $State "panel\data\quarantine")
        $signIn = Join-Path $State "panel\sign-in.txt"
        if (-not (Test-Path $signIn)) {
            # Makes the panel's settings file (so SentrAI's first-run questions are skipped) and the
            # dashboard's first sign-in (a one-time Owner setup code, or a password on older SentrAI),
            # kept here because it is shown only once.
            & $pyKit (Get-ConfigScript $Mvp) admin --email judge@sentrai-demo.local | Set-Content -Encoding utf8 $signIn
        }
        $runArgs = @("-NoProfile", "-ExecutionPolicy", "Bypass", "-File", (Join-Path $Mvp "run.ps1"), "-Speed", "$Speed")
        if ($PanelOnly) {
            $runArgs += @("-CoreBind", "0.0.0.0")  # the website machine's agent reaches the panel over the network
            # SentrAI never auto-blocks private-network addresses (the "attacker" could be a colleague or a
            # gateway). In this lab the AI attacker is on the LAN, so allow blocking that one address.
            if ($AttackerIp) { $env:PROTECTED_NETS = "off"; $env:PROTECTED_IPS = "127.0.0.1,::1,localhost" }
            else { Write-Host "Note: no -AttackerIp given, so SentrAI will only ask a person to approve blocks from LAN addresses." -ForegroundColor Yellow }
        }
        Write-Host "Starting the SentrAI panel (it opens one window per part) ..."
        if ($NoDashboard) { $runArgs += "-NoDashboard" }
        if ($NoBrowser) { $runArgs += "-NoBrowser" }
        & powershell @runArgs
        if ($LASTEXITCODE -ne 0) { throw "The panel did not start (see above)." }
        "local" | Set-Content -Encoding ascii (Join-Path $State "panel\started")
        $port = Get-KitEnv "CORE_PORT" "8000"
        $Panel = "http://127.0.0.1:$port"
        $AllowHttpJoin = $true
        $env:PROTECTED_NETS = $savedEnv["PROTECTED_NETS"]; $env:PROTECTED_IPS = $savedEnv["PROTECTED_IPS"]
        if (-not (Wait-Http "$Panel/health")) { throw "The panel is not answering on $Panel (see its core window)." }
        $token = (& $pyKit (Get-ConfigScript $Mvp) token | Select-Object -Last 1).Trim()
        $joined = (Test-Path $AgentFile) -and ((Get-Content -Raw $AgentFile) -match [regex]::Escape("`"$Panel`""))
        if ($PanelOnly -or -not $joined) {
            $body = @{ operator = "demo"; name = $Name } | ConvertTo-Json
            $Code = (Invoke-RestMethod -Method Post -Uri "$Panel/fleet/join-codes" -Body $body -ContentType "application/json" `
                -Headers @{ Authorization = "Bearer $token" }).code
        }
    }

    foreach ($k in @("CONFIG", "SCOUT_SOURCES", "DB", "QUARANTINE", "RISK_SCOPE")) { Set-KitEnv $k $null }

    if ($PanelOnly) {
        $lan = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notmatch '^(127|169\.254)\.' } | Select-Object -First 1).IPAddress
        if (-not $lan) { $lan = "THIS-PANEL-IP" }
        Write-Host ""
        Write-Host "SentrAI panel is running for the three-machine demo." -ForegroundColor Green
        Get-Content (Join-Path $State "panel\sign-in.txt") | ForEach-Object { Write-Host ("  " + $_.Trim()) }
        Write-Host "  On the WEBSITE machine run:"
        Write-Host "    .\demo.ps1 -Panel http://${lan}:8000 -AllowHttp -Code $Code -Listen"
        Write-Host "  On the AI ATTACKER machine run:"
        Write-Host "    python attacker.py --portal http://WEBSITE-MACHINE-IP:5000"
        if (-not $AttackerIp) { Write-Host "  (restart this with -AttackerIp THE-ATTACKER-MACHINE-IP so SentrAI may block it)" }
        Write-Host "  The join code works once and lasts 24 hours. Stop with .\stop.ps1"
        return
    }

    # 4. The agent: its own settings, key file and collector place, reading only the portal's logs.
    $collectorState = Join-Path $State "agent\collector-state.json"
    Set-KitEnv "CONFIG" (Join-Path $State "agent\config.json")
    Set-KitEnv "AGENT_FILE" $AgentFile
    Set-KitEnv "COLLECTOR_STATE" $collectorState
    Set-KitEnv "SCOUT_SOURCES" (Join-Path $State "agent\sources.json")
    Set-KitEnv "LAB_LOGS" (Join-Path $State "logs")
    Set-KitEnv "FIREWALL" (Get-KitEnv "FIREWALL" "off")  # blocks show on the portal; no firewall rules
    $env:PYTHONUNBUFFERED = "1"; $env:PYTHONUTF8 = "1"
    $pyAgent = Join-Path $Mvp "lab\.venv\Scripts\python.exe"
    if (-not (Test-Path $pyAgent)) {
        Write-Host "Creating the agent's venv ..."
        $py = Find-Python
        & $py -m venv (Join-Path $Mvp "lab\.venv")
        & $pyAgent -m pip install -q -r (Join-Path $Mvp "lab\requirements.txt")
    }
    $agentRun = Join-Path $Kit "agent_run.py"
    if ($Code) {
        Remove-Item -Force -ErrorAction SilentlyContinue $AgentFile, $collectorState
        $join = @($agentRun, $SentrAI, "join", "--panel", $Panel, "--code", $Code, "--name", $Name)
        if ($AllowHttpJoin) { $join += "--allow-http" }
        & $pyAgent @join
        if ($LASTEXITCODE -ne 0) { throw "The agent could not join $Panel." }
    }
    Write-Host "Starting the agent and the portal ..."
    Start-Bg "agent" $pyAgent @("`"$agentRun`"", "`"$SentrAI`"", "run")

    # 5. The portal.
    if ($Tripwires) { Set-KitEnv "SPINES" "1" }
    if ($Listen) { $env:PORTAL_HOST = "0.0.0.0" }
    Start-Bg "portal" $pyKit @("-m", "portal")
    if (-not (Wait-Http "http://127.0.0.1:5000/healthz" 20)) { Write-Host "The portal is not answering yet (see .demo\portal.err.log)." -ForegroundColor Yellow }

    Write-Host ""
    Write-Host "SentrAI demo lab is running." -ForegroundColor Green
    if ((Test-Path (Join-Path $State "panel\started")) -and -not $NoDashboard) {
        $dport = Get-KitEnv "DASHBOARD_PORT" "8501"
        Write-Host "  Panel dashboard: http://127.0.0.1:$dport"
        Get-Content (Join-Path $State "panel\sign-in.txt") | ForEach-Object { Write-Host ("  " + $_.Trim()) }
        Write-Host "  (shown on every start; once the Owner account exists, sign in with it. If the code ran out:"
        Write-Host "   `$env:SENTRAI_CONFIG='.demo\panel\config.json'; .\.demo\venv\Scripts\python.exe .demo\SentrAI\mvp\sentrai_config.py admin)"
    } elseif (-not (Test-Path (Join-Path $State "panel\started"))) {
        Write-Host "  Panel:           $Panel  (dashboard of the panel's machine)"
    }
    Write-Host "  Portal:          http://127.0.0.1:5000        (this machine is `"$Name`" on the panel)"
    if ($Listen) {
        $lan = (Get-NetIPAddress -AddressFamily IPv4 -ErrorAction SilentlyContinue | Where-Object { $_.IPAddress -notmatch '^(127|169\.254)\.' } | Select-Object -First 1).IPAddress
        Write-Host "  Open to the network: http://${lan}:5000  <- point the AI attacker here"
    }
    Write-Host "  Test attacks:    http://127.0.0.1:5000/lab    or: .\.demo\venv\Scripts\python.exe scenario.py"
    Write-Host "  Stop everything: .\stop.ps1"
    if (-not $NoBrowser) { Start-Process "http://127.0.0.1:5000/lab" }
} finally {
    foreach ($n in $envNames) { [Environment]::SetEnvironmentVariable($n, $savedEnv[$n], "Process") }
}
