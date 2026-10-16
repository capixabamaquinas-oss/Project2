$ErrorActionPreference='Stop'
$run='C:\OllamaLimit\Sei l'+[char]0x00E1+'\Projeto TTC\Babel Pura TTC\experiments\X1-X6_20261015'
$ref=Join-Path $run 'references'
$lines=[System.IO.File]::ReadAllLines((Join-Path $ref 'director_dossier_text_utf8.txt'),[System.Text.Encoding]::UTF8)
$start=[Array]::FindIndex($lines,[Predicate[string]]{param($s) $s -match '^7\.1 Experimentos do Codex$'})
if ($start -lt 0) { throw 'X experiment table heading not found' }
$end=$start+1
while ($end -lt $lines.Length -and $lines[$end] -notmatch '^8\. Fases, gates') { $end++ }
if ($end -ge $lines.Length) { throw 'Next section boundary not found' }
$section=$lines[$start..($end-1)]
[System.IO.File]::WriteAllLines((Join-Path $ref 'dossier_section_7_1_X1-X7.txt'),$section,[System.Text.UTF8Encoding]::new($false))
$section
Get-FileHash -Algorithm SHA256 -LiteralPath (Join-Path $ref 'director_dossier_text_utf8.txt'),(Join-Path $ref 'director_dossier_text_source.json'),(Join-Path $ref 'dossier_section_7_1_X1-X7.txt') | Select-Object Hash,Path | Format-Table -AutoSize
