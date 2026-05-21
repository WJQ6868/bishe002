$ErrorActionPreference = 'Stop'

Add-Type -AssemblyName System.Drawing

$output = 'D:\bishe\one\generated\thesis_assets\fig_3_1_ai_architecture_code_api_design_v3.png'

[float]$W = 3200
[float]$H = 1080

$bmp = New-Object System.Drawing.Bitmap -ArgumentList ([int]$W), ([int]$H)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
$g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::ClearTypeGridFit
$g.Clear([System.Drawing.Color]::White)

$black = [System.Drawing.Color]::FromArgb(20, 20, 20)
$lineColor = [System.Drawing.Color]::FromArgb(35, 35, 35)
$textBrush = New-Object System.Drawing.SolidBrush($black)
$pen = New-Object System.Drawing.Pen($lineColor, 4)

function New-Font([float]$size, [string]$name = 'Microsoft YaHei') {
  return New-Object System.Drawing.Font($name, $size, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
}

function U {
  param(
    [Parameter(ValueFromRemainingArguments = $true)]
    [object[]]$codes
  )
  $chars = foreach ($code in $codes) {
    if ($code -is [System.Array]) {
      foreach ($inner in $code) {
        [char][int]$inner
      }
    } else {
      [char][int]$code
    }
  }
  return -join $chars
}

function Get-RoundedPath([System.Drawing.RectangleF]$rect, [float]$radius) {
  $path = New-Object System.Drawing.Drawing2D.GraphicsPath
  $d = $radius * 2
  $path.AddArc($rect.X, $rect.Y, $d, $d, 180, 90)
  $path.AddArc($rect.Right - $d, $rect.Y, $d, $d, 270, 90)
  $path.AddArc($rect.Right - $d, $rect.Bottom - $d, $d, $d, 0, 90)
  $path.AddArc($rect.X, $rect.Bottom - $d, $d, $d, 90, 90)
  $path.CloseFigure()
  return $path
}

function Draw-CenteredText($graphics, $brush, $font, [System.Drawing.RectangleF]$rect, [string]$text) {
  $size = $graphics.MeasureString($text, $font)
  $x = $rect.X + (($rect.Width - $size.Width) / 2)
  $y = $rect.Y + (($rect.Height - $size.Height) / 2)
  $graphics.DrawString($text, $font, $brush, $x, $y)
}

function Draw-CenteredBlock(
  $graphics,
  $brush,
  $font,
  [System.Drawing.RectangleF]$rect,
  [string[]]$lines,
  [bool]$fillHeight = $true,
  [int]$gapMin = 10,
  [int]$gapMax = 42
) {
  $heights = @()
  $widths = @()
  foreach ($line in $lines) {
    if ([string]::IsNullOrEmpty($line)) {
      $widths += 0
      $heights += [int]($font.Size * 0.65)
    } else {
      $size = $graphics.MeasureString($line, $font)
      $widths += $size.Width
      $heights += $size.Height
    }
  }

  $gap = 10
  if ($fillHeight -and $lines.Count -gt 1) {
    $sumHeights = 0.0
    foreach ($h in $heights) { $sumHeights += $h }
    $free = $rect.Height - $sumHeights
    $gap = [int]($free / ($lines.Count - 1))
    if ($gap -lt $gapMin) { $gap = $gapMin }
    if ($gap -gt $gapMax) { $gap = $gapMax }
  }

  $total = 0.0
  for ($i = 0; $i -lt $heights.Count; $i++) { $total += $heights[$i] }
  $total += ($lines.Count - 1) * $gap
  $y = $rect.Y + [Math]::Max(0, ($rect.Height - $total) / 2)

  for ($i = 0; $i -lt $lines.Count; $i++) {
    $line = $lines[$i]
    $h = $heights[$i]
    if (-not [string]::IsNullOrEmpty($line)) {
      $w = $widths[$i]
      $x = $rect.X + (($rect.Width - $w) / 2)
      $graphics.DrawString($line, $font, $brush, $x, $y)
    }
    $y += $h + $gap
  }
}

$titleFont = New-Font 48
$headFont = New-Font 36
$smallFont = New-Font 20
$labelFont = New-Font 24

$titleRect = New-Object System.Drawing.RectangleF(0, 16, $W, 70)
Draw-CenteredText $g $textBrush $titleFont $titleRect ((U @(0x0041, 0x0049, 0x6A21, 0x5757, 0x67B6, 0x6784, 0x3001, 0x4EE3, 0x7801, 0x7EC4, 0x7EC7, 0x4E0E, 0x63A5, 0x53E3, 0x5173, 0x7CFB, 0x56FE)))

[float]$left = 86
[float]$top = 105
[float]$boxW = 560
[float]$gap = 42
[float]$headerH = 88
[float]$boxH = 700
[float]$radius = 20

$boxes = @(
  @{
    Title = (U @(0x89D2, 0x8272, 0x4E0E, 0x573A, 0x666F, 0x5C42))
    Font = New-Font 30
    Lines = @(
      (U @(0x5B66, 0x751F)),
      (U @(0x0041, 0x0049, 0x5BA2, 0x670D, 0x3001, 0x8BFE, 0x7A0B, 0x95EE, 0x7B54)),
      '',
      (U @(0x6559, 0x5E08)),
      (U @(0x8BFE, 0x7A0B, 0x52A9, 0x624B, 0x3001, 0x667A, 0x80FD, 0x6559, 0x6848)),
      '',
      (U @(0x7BA1, 0x7406, 0x5458)),
      (U @(0x6A21, 0x578B, 0x3001, 0x77E5, 0x8BC6, 0x5E93, 0x3001, 0x5DE5, 0x4F5C, 0x6D41, 0x914D, 0x7F6E)),
      '',
      (U @(0x6838, 0x5FC3, 0x95EE, 0x9898)),
      (U @(0x8C01, 0x6765, 0x7528, 0x3001, 0x4ECE, 0x54EA, 0x8FDB))
    )
  },
  @{
    Title = (U @(0x524D, 0x7AEF, 0x9875, 0x9762, 0x4E0E, 0x4EE3, 0x7801, 0x7EC4, 0x7EC7))
    Font = New-Font 28
    Lines = @(
      'AdminAIConfig.vue',
      'CourseAssistant.vue',
      'LessonPlan.vue',
      'StudentAIChat.vue',
      'StudentCourseAssistant.vue',
      'adminAi.ts',
      'aiPortal.ts',
      'ai.ts'
    )
  },
  @{
    Title = (U @(0x540E, 0x7AEF, 0x63A5, 0x53E3, 0x5C42))
    Font = New-Font 24
    Lines = @(
      'admin_ai.py / ai_portal.py',
      '/admin/ai/model-apis',
      '/admin/ai/workflows/apps',
      '/admin/ai/workflows/knowledge-bases',
      '/ai/customer-service/config',
      '/ai/course-assistant/apps',
      '/ai/teacher/kb/upload',
      '/ai/teacher/lesson-plan/tasks',
      'ai_qa.py / ai_qa/qa/stream'
    )
  },
  @{
    Title = (U @(0x0041, 0x0049, 0x80FD, 0x529B, 0x7F16, 0x6392, 0x5C42))
    Font = New-Font 30
    Lines = @(
      (U @(0x5DE5, 0x4F5C, 0x6D41, 0x786E, 0x5B9A, 0x573A, 0x666F, 0x5165, 0x53E3)),
      (U @(0x6A21, 0x578B, 0x4F18, 0x5148, 0x7EA7, 0x9009, 0x62E9)),
      (U @(0x6587, 0x6863, 0x62BD, 0x53D6, 0x4E0E, 0x89C4, 0x8303, 0x5316)),
      (U @(0x6587, 0x672C, 0x5206, 0x5757, 0x4E0E, 0x77E5, 0x8BC6, 0x6574, 0x7406)),
      ('TF-IDF' + (U @(0x68C0, 0x7D22, 0x4E0E, 0x4E0A, 0x4E0B, 0x6587, 0x7EC4, 0x88C5))),
      ('SSE' + (U @(0x6D41, 0x5F0F, 0x8F93, 0x51FA))),
      (U @(0x7ED3, 0x679C, 0x56DE, 0x5199, 0x4E0E, 0x72B6, 0x6001, 0x4FDD, 0x7559))
    )
  },
  @{
    Title = (U @(0x6570, 0x636E, 0x4E0E, 0x8D44, 0x6E90, 0x5C42))
    Font = New-Font 28
    Lines = @(
      'ai_model_apis',
      'ai_knowledge_bases',
      'ai_kb_documents',
      'ai_kb_chunks',
      'ai_workflow_apps',
      'ai_lesson_plan_tasks',
      'ai_usage_logs'
    )
  }
)

for ($i = 0; $i -lt $boxes.Count; $i++) {
  $x = $left + $i * ($boxW + $gap)
  $rect = New-Object System.Drawing.RectangleF -ArgumentList ([single]$x), ([single]$top), ([single]$boxW), ([single]$boxH)
  $path = Get-RoundedPath $rect $radius
  $g.DrawPath($pen, $path)
  $g.DrawLine($pen, $x, $top + $headerH, $x + $boxW, $top + $headerH)

  $headerRect = New-Object System.Drawing.RectangleF -ArgumentList ([single]$x), ([single]($top + 4)), ([single]$boxW), ([single]($headerH - 8))
  Draw-CenteredText $g $textBrush $headFont $headerRect ($boxes[$i].Title)

  $bodyRect = New-Object System.Drawing.RectangleF -ArgumentList ([single]($x + 22)), ([single]($top + $headerH + 16)), ([single]($boxW - 44)), ([single]($boxH - $headerH - 34))
  Draw-CenteredBlock $g $textBrush ($boxes[$i].Font) $bodyRect ($boxes[$i].Lines) $true 10 42
}

$connectorLabels = @(
  (U @(0x573A, 0x666F, 0x8FDB, 0x5165)),
  (U @(0x9875, 0x9762, 0x8C03, 0x7528)),
  (U @(0x63A5, 0x53E3, 0x8C03, 0x5EA6)),
  (U @(0x6570, 0x636E, 0x652F, 0x6491))
)
$baseY = $top + $boxH + 46

for ($i = 0; $i -lt $connectorLabels.Count; $i++) {
  $xA = $left + $boxW * ($i + 1) + $gap * $i
  $xB = $left + $boxW * ($i + 1) + $gap * ($i + 1)
  $mid = ($xA + $xB) / 2
  $g.DrawLine((New-Object System.Drawing.Pen($lineColor, 3)), $xA + 8, $baseY, $xB - 36, $baseY)
  $pts = [System.Drawing.PointF[]]@(
    (New-Object System.Drawing.PointF -ArgumentList ([single]($xB - 36)), ([single]($baseY - 10))),
    (New-Object System.Drawing.PointF -ArgumentList ([single]($xB - 36)), ([single]($baseY + 10))),
    (New-Object System.Drawing.PointF -ArgumentList ([single]($xB - 6)), ([single]$baseY))
  )
  $g.FillPolygon($textBrush, $pts)
  $labelRect = New-Object System.Drawing.RectangleF -ArgumentList ([single]($mid - 70)), ([single]($baseY - 40)), ([single]140), ([single]28)
  Draw-CenteredText $g $textBrush $labelFont $labelRect $connectorLabels[$i]
}

$noteRect = New-Object System.Drawing.RectangleF -ArgumentList ([single]120), ([single]($H - 86)), ([single]($W - 240)), ([single]60)
$noteLines = @(
  (U @(0x8BF4, 0x660E, 0xFF1A, 0x8BE5, 0x56FE, 0x5C06, 0x89D2, 0x8272, 0x5165, 0x53E3, 0x3001, 0x524D, 0x7AEF, 0x9875, 0x9762, 0x3001, 0x63A5, 0x53E3, 0x5206, 0x7EC4, 0x3001, 0x0041, 0x0049, 0x80FD, 0x529B, 0x4E0E, 0x5E95, 0x5C42, 0x6570, 0x636E, 0x653E, 0x5230, 0x540C, 0x4E00, 0x6761, 0x8BBE, 0x8BA1, 0x94FE, 0x4E0A, 0xFF0C)),
  (U @(0x7528, 0x4E8E, 0x8BF4, 0x660E, 0x7ED3, 0x6784, 0x5173, 0x7CFB, 0x3001, 0x4EE3, 0x7801, 0x7EC4, 0x7EC7, 0x4E0E, 0x63A5, 0x53E3, 0x534F, 0x540C, 0x65B9, 0x5F0F, 0x3002))
)
Draw-CenteredBlock $g $textBrush $smallFont $noteRect $noteLines $false 4 4

if (Test-Path -LiteralPath $output) {
  Remove-Item -LiteralPath $output -Force
}
$bmp.Save($output, [System.Drawing.Imaging.ImageFormat]::Png)

$pen.Dispose()
$textBrush.Dispose()
$titleFont.Dispose()
$headFont.Dispose()
$smallFont.Dispose()
$labelFont.Dispose()
foreach ($box in $boxes) {
  $box.Font.Dispose()
}
$g.Dispose()
$bmp.Dispose()
