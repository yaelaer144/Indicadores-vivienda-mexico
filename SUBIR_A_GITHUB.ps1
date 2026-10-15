$ErrorActionPreference = 'Stop'
if (-not (Get-Command git -ErrorAction SilentlyContinue)) { throw 'Instala Git para Windows antes de continuar: https://git-scm.com/downloads/win' }
Set-Location $PSScriptRoot
$url = Read-Host 'Pega la URL HTTPS de tu repositorio GitHub (https://github.com/usuario/repositorio.git)'
if ($url -notmatch '^https://github\.com/[^/]+/[^/]+(?:\.git)?/?$') { throw 'URL de GitHub no valida.' }
if (-not (Test-Path '.git')) { git init; if ($LASTEXITCODE -ne 0) { throw 'git init fallo' } }
git branch -M main
$remotes = @(git remote)
if ($remotes -contains 'origin') { git remote set-url origin $url } else { git remote add origin $url }
git add -A
if ($LASTEXITCODE -ne 0) { throw 'git add fallo' }
git diff --cached --quiet
if ($LASTEXITCODE -ne 0) {
  git -c user.name='Dashboard Vivienda' -c user.email='dashboard@users.noreply.github.com' commit -m 'Publicar dashboard y automatizaciones'
  if ($LASTEXITCODE -ne 0) { throw 'git commit fallo' }
}
git push -u origin main
if ($LASTEXITCODE -ne 0) { throw 'No se pudo subir. Comprueba permisos, autenticacion y si el repositorio remoto ya tiene commits.' }
Write-Host 'Proyecto completo subido a GitHub, incluidas carpetas ocultas y workflows.' -ForegroundColor Green
