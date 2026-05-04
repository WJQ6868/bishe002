$ErrorActionPreference = 'Stop'

$docPath = 'D:\bishe\one\AI赋能的高校教务系统-毕业论文原创改写版.docx'
$titleText = 'AI赋能的高校教务系统'
$schoolHeader = '南京工业职业技术大学毕业设计（论文）'
$titleHeader = "$titleText(毕业设计（论文）题目)"
$figTableHeading = '图表清单'

function Get-ParagraphIndexByExactText {
  param($doc, [string]$text)
  for ($i = 1; $i -le $doc.Paragraphs.Count; $i++) {
    if ($doc.Paragraphs.Item($i).Range.Text.Trim() -eq $text) {
      return $i
    }
  }
  throw "Paragraph not found: $text"
}

function Normalize-Text {
  param([string]$text)
  if ($null -eq $text) { return '' }
  return (($text -replace "`r", '') -replace "`n", '' -replace [regex]::Escape([string][char]7), '').Trim()
}

function Clear-HeaderFooter {
  param($section)
  foreach ($kind in 1, 2, 3) {
    $section.Headers.Item($kind).LinkToPrevious = $false
    $section.Footers.Item($kind).LinkToPrevious = $false
    $section.Headers.Item($kind).Range.Text = ''
    $section.Footers.Item($kind).Range.Text = ''
  }
}

function Set-HeaderText {
  param($range, [string]$text, [int]$align = 1)
  $range.Text = ''
  $range.ParagraphFormat.Alignment = $align
  $range.Font.NameFarEast = '宋体'
  $range.Font.Name = 'Times New Roman'
  $range.Font.Size = 10.5
  $range.Font.Bold = 0
  $range.Text = $text
}

function Set-PageField {
  param($range, [int]$align, [string]$fieldCode)
  $range.Text = ''
  $range.ParagraphFormat.Alignment = $align
  $range.Font.NameFarEast = 'Times New Roman'
  $range.Font.Name = 'Times New Roman'
  $range.Font.Size = 10.5
  $range.Font.Bold = 0
  [void]$range.Fields.Add($range, -1, $fieldCode, $true)
}

function Set-ParagraphFormat {
  param(
    $para,
    [int]$align = 0,
    [double]$size = 12,
    [string]$farEast = '宋体',
    [string]$ascii = 'Times New Roman',
    [bool]$bold = $false
  )
  $rng = $para.Range
  $rng.ParagraphFormat.Alignment = $align
  $rng.ParagraphFormat.LineSpacingRule = 1
  $rng.ParagraphFormat.LineSpacing = $rng.Application.LinesToPoints(1.5)
  $rng.Font.NameFarEast = $farEast
  $rng.Font.Name = $ascii
  $rng.Font.Size = $size
  $rng.Font.Bold = [int]$bold
}

function Add-RightTabLeader {
  param($para, [double]$positionPoints)
  $para.TabStops.ClearAll()
  [void]$para.TabStops.Add($positionPoints, 2, 1)
}

function Invoke-ComRetry {
  param(
    [scriptblock]$Action,
    [int]$MaxAttempts = 20,
    [int]$DelayMs = 400
  )
  for ($attempt = 1; $attempt -le $MaxAttempts; $attempt++) {
    try {
      return & $Action
    }
    catch [System.Runtime.InteropServices.COMException] {
      if ($_.Exception.HResult -eq -2147418111 -and $attempt -lt $MaxAttempts) {
        Start-Sleep -Milliseconds $DelayMs
        continue
      }
      throw
    }
  }
}

function Get-CaptionItems {
  param($doc)
  $items = New-Object System.Collections.ArrayList
  for ($i = 1; $i -le $doc.Paragraphs.Count; $i++) {
    $txt = Normalize-Text $doc.Paragraphs.Item($i).Range.Text
    if (-not $txt) { continue }
    if ($txt -match '^(图|表)\s*\d+[-—－]\d+\s+.+') {
      $pageNo = $doc.Paragraphs.Item($i).Range.Information(3)
      [void]$items.Add([PSCustomObject]@{
        Text = $txt
        Page = [string]$pageNo
      })
    }
  }
  return ,$items
}

function Remove-ExistingFigTableSection {
  param($doc, $word, [string]$headingText, [string]$chapterHeading)

  $headingIdx = $null
  $chapterIdx = $null
  for ($i = 1; $i -le $doc.Paragraphs.Count; $i++) {
    $txt = Normalize-Text $doc.Paragraphs.Item($i).Range.Text
    if (-not $headingIdx -and $txt -eq $headingText) { $headingIdx = $i }
    if (-not $chapterIdx -and $txt -eq $chapterHeading) { $chapterIdx = $i }
  }

  if ($headingIdx -and $chapterIdx -and $headingIdx -lt $chapterIdx) {
    $start = $doc.Paragraphs.Item($headingIdx).Range.Start
    $end = $doc.Paragraphs.Item($chapterIdx).Range.Start
    $rng = $doc.Range($start, $end)
    $rng.Delete()
  }
}

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.ScreenUpdating = $false
$word.DisplayAlerts = 0
$wdSectionBreakOddPage = 5

try {
  $doc = $word.Documents.Open($docPath)
  Write-Host '[1/8] document opened'

  # 1. 目录级别：正文章/节/小节使用 1-3 级轮廓。
  for ($i = 1; $i -le $doc.Paragraphs.Count; $i++) {
    $para = $doc.Paragraphs.Item($i)
    $txt = Normalize-Text $para.Range.Text
    if (-not $txt) { continue }

    if ($txt -match '^第[一二三四五六七八九十百]+章\s+') {
      $para.OutlineLevel = 1
    }
    elseif ($txt -match '^\d+\.\d+\.\d+\s+') {
      $para.OutlineLevel = 3
    }
    elseif ($txt -match '^\d+\.\d+\s+') {
      $para.OutlineLevel = 2
    }
    else {
      $para.OutlineLevel = 10
    }
  }

  # 2. 清理可能残留的旧“图表清单”块，避免重复插入。
  Remove-ExistingFigTableSection $doc $word $figTableHeading '第一章 绪论'
  Invoke-ComRetry { $doc.Repaginate() | Out-Null }
  Write-Host '[2/8] old figure-table block cleaned'

  # 3. 在“第一章 绪论”前重建“图表清单”页，并将正文从新分节开始。
  $chapterIdx = Get-ParagraphIndexByExactText $doc '第一章 绪论'
  $chapterRange = $doc.Paragraphs.Item($chapterIdx).Range
  $chapterStart = $chapterRange.Start

  $insertRange = $doc.Range($chapterStart, $chapterStart)
  $insertRange.InsertBefore("$figTableHeading`r`r")
  $doc.Range($chapterStart, $chapterStart).InsertBreak($wdSectionBreakOddPage)
  Invoke-ComRetry { $doc.Repaginate() | Out-Null }
  Write-Host '[3/8] figure-table page inserted'

  # 4. 页眉页脚与页码。
  for ($s = 1; $s -le $doc.Sections.Count; $s++) {
    $doc.Sections.Item($s).PageSetup.OddAndEvenPagesHeaderFooter = -1
    $doc.Sections.Item($s).PageSetup.DifferentFirstPageHeaderFooter = $false
  }

  if ($doc.Sections.Count -lt 4) {
    throw "Expected at least 4 sections after rebuilding figure/table page, got $($doc.Sections.Count)"
  }
  Write-Host "[4/8] sections rebuilt: $($doc.Sections.Count)"

  # 第 1 节：封面，无页眉页脚
  Clear-HeaderFooter $doc.Sections.Item(1)

  # 第 2 节：诚信承诺书，无页眉页脚
  Clear-HeaderFooter $doc.Sections.Item(2)

  # 第 3 节：摘要/英文摘要/目录/图表清单，罗马页码，无页眉
  $sec3 = $doc.Sections.Item(3)
  Clear-HeaderFooter $sec3
  $sec3.Footers.Item(1).PageNumbers.RestartNumberingAtSection = $true
  $sec3.Footers.Item(1).PageNumbers.StartingNumber = 1
  Set-PageField $sec3.Footers.Item(1).Range 2 'PAGE \* roman'
  Set-PageField $sec3.Footers.Item(3).Range 0 'PAGE \* roman'

  # 第 4 节及以后：正文，奇偶页眉、阿拉伯页码
  for ($s = 4; $s -le $doc.Sections.Count; $s++) {
    $sec = $doc.Sections.Item($s)
    Clear-HeaderFooter $sec
    Set-HeaderText $sec.Headers.Item(1).Range $schoolHeader
    Set-HeaderText $sec.Headers.Item(3).Range $titleHeader
    if ($s -eq 4) {
      $sec.Footers.Item(1).PageNumbers.RestartNumberingAtSection = $true
      $sec.Footers.Item(1).PageNumbers.StartingNumber = 1
    }
    Set-PageField $sec.Footers.Item(1).Range 2 'PAGE'
    Set-PageField $sec.Footers.Item(3).Range 0 'PAGE'
  }
  Write-Host '[5/8] headers and footers updated'

  # 5. 更新三级目录。
  if ($doc.TablesOfContents.Count -ge 1) {
    $tocField = $doc.TablesOfContents.Item(1).Range.Fields.Item(1)
    $tocField.Code.Text = ' TOC \o "1-3" \h \z \u '
    Invoke-ComRetry { $doc.TablesOfContents.Item(1).Update() | Out-Null }
  }
  Write-Host '[6/8] toc updated'

  # 6. 生成“图表清单”内容。
  Invoke-ComRetry { $doc.Repaginate() | Out-Null }
  $captionItems = Get-CaptionItems $doc

  $figHeadingIdx = Get-ParagraphIndexByExactText $doc $figTableHeading
  $chapterIdx = Get-ParagraphIndexByExactText $doc '第一章 绪论'
  $contentStart = $doc.Paragraphs.Item($figHeadingIdx + 1).Range.Start
  $contentEnd = $doc.Paragraphs.Item($chapterIdx).Range.Start
  $contentRange = $doc.Range($contentStart, $contentEnd)
  $contentRange.Text = ''

  $sel = $word.Selection
  $sel.SetRange($contentStart, $contentStart)

  foreach ($item in $captionItems) {
    $sel.TypeText($item.Text)
    $sel.TypeText("`t")
    $sel.TypeText($item.Page)
    $sel.TypeParagraph()
  }
  Write-Host "[7/8] figure-table entries written: $($captionItems.Count)"

  # 7. 统一“图表清单”格式。
  Invoke-ComRetry { $doc.Repaginate() | Out-Null }
  $figHeadingIdx = Get-ParagraphIndexByExactText $doc $figTableHeading
  $chapterIdx = Get-ParagraphIndexByExactText $doc '第一章 绪论'
  Set-ParagraphFormat $doc.Paragraphs.Item($figHeadingIdx) 1 15 '黑体' 'Times New Roman' $true

  $rightPos = $doc.PageSetup.PageWidth - $doc.PageSetup.LeftMargin - $doc.PageSetup.RightMargin - 10
  for ($i = $figHeadingIdx + 1; $i -lt $chapterIdx; $i++) {
    $txt = Normalize-Text $doc.Paragraphs.Item($i).Range.Text
    if (-not $txt) { continue }
    $para = $doc.Paragraphs.Item($i)
    Set-ParagraphFormat $para 0 12 '宋体' 'Times New Roman' $false
    Add-RightTabLeader $para $rightPos
  }

  # 8. 最终刷新。
  Invoke-ComRetry { $doc.Repaginate() | Out-Null }
  if ($doc.TablesOfContents.Count -ge 1) {
    Invoke-ComRetry { $doc.TablesOfContents.Item(1).Update() | Out-Null }
  }

  Invoke-ComRetry { $doc.Save() | Out-Null }
  Write-Host '[8/8] document saved'
  $doc.Close()
}
finally {
  $word.Quit()
}

Write-Output 'Word structure sync completed.'
