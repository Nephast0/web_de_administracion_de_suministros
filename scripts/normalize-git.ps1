<#
.SYNOPSIS
    Normaliza el repositorio: trae los commits remotos pendientes y resuelve
    las "modificaciones" falsas causadas por terminadores de línea CRLF/LF.

.DESCRIPTION
    Tras la auditoría del 11-mayo-2026 se detectó que:
      - 47 archivos aparecían como modified, pero el diff era solo CRLF↔LF.
      - La rama local estaba 3 commits por detrás de origin/main.
      - El nuevo .gitattributes (commit local) define la política de EOL.

    Este script aplica la secuencia segura:
      1. Confirma que estás en la raíz del repo.
      2. Descarta el ruido CRLF (las "modificaciones" no son cambios reales).
      3. Hace pull --ff-only para integrar los commits remotos.
      4. Renormaliza el repo con la nueva política de .gitattributes.
      5. Si la renormalización produce cambios, los deja staged para
         que tú revises y commitees.

.USO
    PS> cd C:\Users\noev8\PycharmProjects\Project\pythonProject
    PS> ./scripts/normalize-git.ps1

.NOTAS
    - No empuja a remoto. Tú decides cuándo hacer push.
    - Si tienes cambios en curso reales (no CRLF), GUÁRDALOS ANTES con
      git stash o un commit; este script descarta lo no commiteado.
#>

$ErrorActionPreference = "Stop"

function Write-Step($msg) {
    Write-Host "==> $msg" -ForegroundColor Cyan
}

function Confirm-Step($msg) {
    Write-Host ""
    $resp = Read-Host "$msg [s/N]"
    if ($resp -notmatch '^(s|si|y|yes)$') {
        Write-Host "Cancelado por el usuario." -ForegroundColor Yellow
        exit 1
    }
}

# 1. Validar entorno
Write-Step "Validando que estamos en un repo git..."
git rev-parse --git-dir | Out-Null

$branch = git rev-parse --abbrev-ref HEAD
Write-Host "    Rama actual: $branch"

# 2. Mostrar estado y pedir confirmación
Write-Step "Estado actual del working tree:"
git status --short

Write-Host ""
Write-Step "Commits remotos pendientes:"
git fetch origin 2>&1 | Out-Null
$ahead = git rev-list --count "HEAD..origin/$branch" 2>$null
$behind_remote = git rev-list --count "origin/$branch..HEAD" 2>$null
Write-Host "    Por delante de origin/$branch: $behind_remote"
Write-Host "    Por detrás de origin/$branch:  $ahead"

if ($ahead -eq "0" -and (git status --porcelain) -eq $null) {
    Write-Host "El repo ya está limpio y al día. Nada que hacer." -ForegroundColor Green
    exit 0
}

Confirm-Step "Voy a DESCARTAR los cambios locales no commiteados (todos son CRLF↔LF según la auditoría) y hacer fast-forward de $ahead commits. ¿Continuar?"

# 3. Descartar el ruido CRLF
Write-Step "Descartando modificaciones de terminadores de línea..."
git checkout -- .

# 4. Fast-forward
Write-Step "Trayendo commits remotos (fast-forward)..."
git pull --ff-only origin $branch

# 5. Renormalizar bajo la política de .gitattributes
Write-Step "Renormalizando terminadores de línea según .gitattributes..."
git add --renormalize .

# 6. Si quedó algo staged, dejarlo listo para commit
$staged = git diff --cached --name-only
if ($staged) {
    Write-Host ""
    Write-Host "Archivos renormalizados (staged, pendientes de commit):" -ForegroundColor Yellow
    $staged | ForEach-Object { Write-Host "    $_" }
    Write-Host ""
    Write-Host "Revísalos y commitea cuando estés conforme:" -ForegroundColor Green
    Write-Host '    git commit -m "Normalizar terminadores de línea según .gitattributes"' -ForegroundColor Green
} else {
    Write-Host ""
    Write-Host "Repo limpio y normalizado. Nada más que hacer." -ForegroundColor Green
}
