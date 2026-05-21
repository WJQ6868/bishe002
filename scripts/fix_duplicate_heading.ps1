$ErrorActionPreference = 'Stop'

$root = 'D:\bishe\one'
$srcDocx = 'C:\Users\wangj\Desktop\2405273202-王佳齐-AI赋能的高校教务系统(ai) -.docx'
$zipPath = Join-Path $root 'tmp_fix_duplicate_heading.zip'
$unzipDir = Join-Path $root 'tmp_fix_duplicate_heading_unzip'
$updatedZip = Join-Path $root 'tmp_fix_duplicate_heading_updated.zip'
$updatedDocx = Join-Path $root 'tmp_fix_duplicate_heading_updated.docx'

if (Test-Path -LiteralPath $zipPath) { Remove-Item -LiteralPath $zipPath -Force }
if (Test-Path -LiteralPath $unzipDir) { Remove-Item -LiteralPath $unzipDir -Recurse -Force }
Copy-Item -LiteralPath $srcDocx -Destination $zipPath -Force
Expand-Archive -LiteralPath $zipPath -DestinationPath $unzipDir -Force

$documentXmlPath = Join-Path $unzipDir 'word\document.xml'
$settings = [System.Xml.XmlReaderSettings]::new()
$settings.DtdProcessing = [System.Xml.DtdProcessing]::Ignore
$reader = [System.Xml.XmlReader]::Create($documentXmlPath, $settings)
$doc = [System.Xml.XmlDocument]::new()
$doc.PreserveWhitespace = $true
$doc.Load($reader)
$reader.Close()

$ns = [System.Xml.XmlNamespaceManager]::new($doc.NameTable)
$ns.AddNamespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')

function Get-Text {
    param([System.Xml.XmlNode]$Node)
    return (($Node.SelectNodes('.//w:t', $ns) | ForEach-Object { $_.InnerText }) -join '')
}

function Set-Text {
    param([System.Xml.XmlNode]$Node, [string]$Text)
    $texts = $Node.SelectNodes('.//w:t', $ns)
    if ($texts.Count -eq 0) { return }
    $texts[0].InnerText = $Text
    for ($i = 1; $i -lt $texts.Count; $i++) {
        $texts[$i].InnerText = ''
    }
}

$body = $doc.SelectSingleNode('//w:body', $ns)
$changed = 0
$lastText = $null
foreach ($node in @($body.ChildNodes)) {
    if ($node.LocalName -eq 'p') {
        $text = Get-Text $node
        if ($text -eq 'AI能力接入边界分析' -and $lastText -eq 'AI能力接入边界分析') {
            [void]$body.RemoveChild($node)
            $changed++
            continue
        }
        if ($text -eq '最后是部署与维护需求。设计的展示并不只发生在本地开发环境中，还要考虑教师评审、远程访问和后续演示的实际需要。因此，系统应同时支持本地联调与公网访问场景。当前项目除支持本地启动外，还通过部署在阿里云云服务器 Ubuntu系统上的站点对外提供服务，并可通过公网域名直接访问。这类需求虽然不直接体现为页面功能，却决定了系统能否稳定演示、持续维护和方便扩展。') {
            Set-Text $node '最后是部署与维护需求。系统展示并不只发生在本地开发环境中，还要考虑教师评审、远程访问和后续演示的实际需要。因此，系统应同时支持本地联调与公网访问场景。当前项目除支持本地启动外，还通过部署在阿里云云服务器 Ubuntu系统上的站点对外提供服务，并可通过公网域名直接访问。这类需求虽然不直接体现为页面功能，却决定了系统能否稳定演示、持续维护和方便扩展。'
            $changed++
        }
        $lastText = Get-Text $node
    }
}

$doc.Save($documentXmlPath)

if (Test-Path -LiteralPath $updatedZip) { Remove-Item -LiteralPath $updatedZip -Force }
if (Test-Path -LiteralPath $updatedDocx) { Remove-Item -LiteralPath $updatedDocx -Force }
Push-Location $unzipDir
try {
    Compress-Archive -Path * -DestinationPath $updatedZip -Force
} finally {
    Pop-Location
}
Move-Item -LiteralPath $updatedZip -Destination $updatedDocx -Force
Copy-Item -LiteralPath $updatedDocx -Destination $srcDocx -Force

Write-Output "Fixed duplicate heading and wording. Changed items: $changed"

