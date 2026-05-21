$ErrorActionPreference = 'Stop'

$root = 'D:\bishe\one'
$srcDocx = 'C:\Users\wangj\Desktop\2405273202-王佳齐-AI赋能的高校教务系统(ai) -.docx'
$zipPath = Join-Path $root 'tmp_fig_2_3_cycle.zip'
$unzipDir = Join-Path $root 'tmp_fig_2_3_cycle_unzip'
$assetDir = Join-Path $root 'generated\thesis_assets'
$assetPath = Join-Path $assetDir 'fig_2_3_ai_cycle_corrected.png'
$updatedZip = Join-Path $root 'tmp_fig_2_3_cycle_updated.zip'
$updatedDocx = Join-Path $root 'tmp_fig_2_3_cycle_updated.docx'

New-Item -ItemType Directory -Path $assetDir -Force | Out-Null
if (Test-Path -LiteralPath $zipPath) {
    Remove-Item -LiteralPath $zipPath -Force
}
if (Test-Path -LiteralPath $unzipDir) {
    Remove-Item -LiteralPath $unzipDir -Recurse -Force
}
Copy-Item -LiteralPath $srcDocx -Destination $zipPath -Force
Expand-Archive -LiteralPath $zipPath -DestinationPath $unzipDir -Force

Add-Type -AssemblyName System.Drawing

function Get-CnFontFamily {
    foreach ($name in @('Microsoft YaHei', 'Microsoft YaHei UI', 'SimHei', 'SimSun')) {
        try {
            return [System.Drawing.FontFamily]::new($name)
        } catch {
            continue
        }
    }
    return [System.Drawing.FontFamily]::GenericSansSerif
}

function Draw-CenteredText {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.RectangleF]$Rect,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [System.Drawing.Brush]$Brush
    )
    $format = [System.Drawing.StringFormat]::new()
    $format.Alignment = [System.Drawing.StringAlignment]::Center
    $format.LineAlignment = [System.Drawing.StringAlignment]::Center
    try {
        $Graphics.DrawString($Text, $Font, $Brush, $Rect, $format)
    } finally {
        $format.Dispose()
    }
}

function Draw-Arrow {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.Pen]$Pen,
        [float]$X1,
        [float]$Y1,
        [float]$X2,
        [float]$Y2
    )
    $Graphics.DrawLine($Pen, $X1, $Y1, $X2, $Y2)
    $angle = [Math]::Atan2($Y2 - $Y1, $X2 - $X1)
    $head = 38.0
    $a1 = $angle - [Math]::PI / 7
    $a2 = $angle + [Math]::PI / 7
    $p1 = [System.Drawing.PointF]::new([float]($X2 - $head * [Math]::Cos($a1)), [float]($Y2 - $head * [Math]::Sin($a1)))
    $p2 = [System.Drawing.PointF]::new([float]($X2 - $head * [Math]::Cos($a2)), [float]($Y2 - $head * [Math]::Sin($a2)))
    $Graphics.DrawLine($Pen, $X2, $Y2, $p1.X, $p1.Y)
    $Graphics.DrawLine($Pen, $X2, $Y2, $p2.X, $p2.Y)
}

function Draw-Box {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.RectangleF]$Rect,
        [string]$Title,
        [string[]]$Lines,
        [System.Drawing.FontFamily]$Family,
        [System.Drawing.Pen]$Pen,
        [System.Drawing.Brush]$Brush
    )
    $Graphics.FillRectangle([System.Drawing.Brushes]::White, $Rect)
    $Graphics.DrawRectangle($Pen, $Rect.X, $Rect.Y, $Rect.Width, $Rect.Height)

    $headerH = 82.0
    $titleFont = [System.Drawing.Font]::new($Family, 54, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $lineFont = [System.Drawing.Font]::new($Family, 40, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
    try {
        $headerRect = [System.Drawing.RectangleF]::new($Rect.X + 10, $Rect.Y + 4, $Rect.Width - 20, $headerH - 8)
        Draw-CenteredText $Graphics $headerRect $Title $titleFont $Brush
        $Graphics.DrawLine($Pen, $Rect.X, $Rect.Y + $headerH, $Rect.X + $Rect.Width, $Rect.Y + $headerH)

        $rowH = ($Rect.Height - $headerH) / $Lines.Count
        for ($i = 0; $i -lt $Lines.Count; $i++) {
            $rowRect = [System.Drawing.RectangleF]::new($Rect.X + 12, $Rect.Y + $headerH + $i * $rowH + 2, $Rect.Width - 24, $rowH - 4)
            Draw-CenteredText $Graphics $rowRect $Lines[$i] $lineFont $Brush
        }
    } finally {
        $titleFont.Dispose()
        $lineFont.Dispose()
    }
}

$width = 2400
$height = 780
$bmp = [System.Drawing.Bitmap]::new($width, $height)
$bmp.SetResolution(300, 300)
$g = [System.Drawing.Graphics]::FromImage($bmp)
$family = Get-CnFontFamily
$boxPen = [System.Drawing.Pen]::new([System.Drawing.Color]::Black, 5)
$arrowPen = [System.Drawing.Pen]::new([System.Drawing.Color]::Black, 8)
$brush = [System.Drawing.Brushes]::Black

try {
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $g.Clear([System.Drawing.Color]::White)

    $leftTop = [System.Drawing.RectangleF]::new(180, 55, 760, 250)
    $rightTop = [System.Drawing.RectangleF]::new(1460, 55, 760, 250)
    $rightBottom = [System.Drawing.RectangleF]::new(1460, 475, 760, 250)
    $leftBottom = [System.Drawing.RectangleF]::new(180, 475, 760, 250)

    Draw-Box $g $leftTop '1 配置准备' @('模型接口配置', '知识库资料整理', '客服与场景参数') $family $boxPen $brush
    Draw-Box $g $rightTop '2 场景调用' @('学生咨询', '课程答疑', '教师教案生成') $family $boxPen $brush
    Draw-Box $g $rightBottom '3 结果沉淀' @('问答记录保存', '课程资料更新', '教案任务回写') $family $boxPen $brush
    Draw-Box $g $leftBottom '4 持续优化' @('补充知识内容', '调整模型配置', '优化工作流入口') $family $boxPen $brush

    Draw-Arrow $g $arrowPen ($leftTop.X + $leftTop.Width + 32) ($leftTop.Y + $leftTop.Height / 2) ($rightTop.X - 36) ($rightTop.Y + $rightTop.Height / 2)
    Draw-Arrow $g $arrowPen ($rightTop.X + $rightTop.Width / 2) ($rightTop.Y + $rightTop.Height + 28) ($rightBottom.X + $rightBottom.Width / 2) ($rightBottom.Y - 34)
    Draw-Arrow $g $arrowPen ($rightBottom.X - 32) ($rightBottom.Y + $rightBottom.Height / 2) ($leftBottom.X + $leftBottom.Width + 36) ($leftBottom.Y + $leftBottom.Height / 2)
    Draw-Arrow $g $arrowPen ($leftBottom.X + $leftBottom.Width / 2) ($leftBottom.Y - 28) ($leftTop.X + $leftTop.Width / 2) ($leftTop.Y + $leftTop.Height + 34)

    $centerFont = [System.Drawing.Font]::new($family, 50, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $centerRect = [System.Drawing.RectangleF]::new(880, 330, 640, 120)
    Draw-CenteredText $g $centerRect "运行反馈`n持续迭代" $centerFont $brush
    $centerFont.Dispose()

    $bmp.Save($assetPath, [System.Drawing.Imaging.ImageFormat]::Png)
    Copy-Item -LiteralPath $assetPath -Destination (Join-Path $unzipDir 'word\media\image4.png') -Force
} finally {
    $g.Dispose()
    $bmp.Dispose()
    $boxPen.Dispose()
    $arrowPen.Dispose()
}

if (Test-Path -LiteralPath $updatedZip) {
    Remove-Item -LiteralPath $updatedZip -Force
}
if (Test-Path -LiteralPath $updatedDocx) {
    Remove-Item -LiteralPath $updatedDocx -Force
}
Push-Location $unzipDir
try {
    Compress-Archive -Path * -DestinationPath $updatedZip -Force
} finally {
    Pop-Location
}
Move-Item -LiteralPath $updatedZip -Destination $updatedDocx -Force
Copy-Item -LiteralPath $updatedDocx -Destination $srcDocx -Force

Write-Output "Redrew Figure 2-3 as cycle diagram: $assetPath"
Write-Output "Saved to: $srcDocx"


