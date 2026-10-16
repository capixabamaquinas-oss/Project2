$ErrorActionPreference = 'Stop'
$project = 'C:\OllamaLimit\Sei l' + [char]0x00E1 + '\Projeto TTC\Babel Pura TTC'
$base = Join-Path $project 'experiments\X1-X6_20261015'
$dossier = 'C:\Users\User PC\Downloads\Dossi' + [char]0x00EA + ' Operacional ' + [char]0x2014 + ' Babel Pura App v3 (revisado).docx'
$python = 'C:\Users\User PC\.cache\codex-runtimes\codex-primary-runtime\dependencies\python\python.exe'
Write-Output '=== SHA-256: source files before experiment run (sorted; excludes this run directory) ==='
$files = @(Get-ChildItem -LiteralPath $project -Force -Recurse -File | Where-Object { -not $_.FullName.StartsWith($base, [StringComparison]::OrdinalIgnoreCase) } | Sort-Object FullName)
foreach ($file in $files) { $h = Get-FileHash -Algorithm SHA256 -LiteralPath $file.FullName; '{0} *{1}' -f $h.Hash, $h.Path }
$h = Get-FileHash -Algorithm SHA256 -LiteralPath $dossier
'{0} *{1}' -f $h.Hash, $h.Path
Write-Output '=== Python version ==='
& $python --version
& $python -I -c "import sys,platform; print('sys.version=' + sys.version.replace('\n',' ')); print('platform=' + platform.platform()); print('implementation=' + platform.python_implementation())"
Write-Output '=== Windows version ==='
[System.Environment]::OSVersion.VersionString

