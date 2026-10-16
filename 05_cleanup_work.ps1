$ErrorActionPreference='Stop'
$run='C:\OllamaLimit\Sei l'+[char]0x00E1+'\Projeto TTC\Babel Pura TTC\experiments\X1-X6_20261015'
$target=Join-Path $run 'work'
$runFull=(Resolve-Path -LiteralPath $run).Path.TrimEnd('\')
$targetFull=(Resolve-Path -LiteralPath $target).Path.TrimEnd('\')
$prefix=$runFull+'\'
if ($targetFull -ne (Join-Path $runFull 'work')) { throw 'Unexpected cleanup target' }
if (-not $targetFull.StartsWith($prefix,[StringComparison]::OrdinalIgnoreCase)) { throw 'Cleanup target escaped run directory' }
$files=@(Get-ChildItem -LiteralPath $targetFull -Force -Recurse -File)
$bytes=($files | Measure-Object -Property Length -Sum).Sum
"verified_run=$runFull"
"verified_cleanup_target=$targetFull"
"files_to_remove=$($files.Count)"
"bytes_to_remove=$bytes"
Remove-Item -LiteralPath $targetFull -Recurse -Force
"work_exists_after=$(Test-Path -LiteralPath $targetFull)"
