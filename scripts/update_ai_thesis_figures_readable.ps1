$ErrorActionPreference = 'Stop'

$root = 'D:\bishe\one'
$srcDocx = 'C:\Users\wangj\Desktop\2405273202-王佳齐-AI赋能的高校教务系统(ai) -.docx'
$workDocx = Join-Path $root 'tmp_ai_thesis_figs.docx'
$workZip = Join-Path $root 'tmp_ai_thesis_figs.zip'
$unzipDir = Join-Path $root 'tmp_ai_thesis_figs_unzip'
$assetDir = Join-Path $root 'generated\thesis_assets'
$updatedZip = Join-Path $root 'tmp_ai_thesis_figs_updated.zip'
$updatedDocx = Join-Path $root 'tmp_ai_thesis_figs_updated.docx'

Copy-Item -LiteralPath $srcDocx -Destination $workDocx -Force
Copy-Item -LiteralPath $srcDocx -Destination $workZip -Force
if (Test-Path -LiteralPath $unzipDir) {
    Remove-Item -LiteralPath $unzipDir -Recurse -Force
}
Expand-Archive -LiteralPath $workZip -DestinationPath $unzipDir -Force
New-Item -ItemType Directory -Path $assetDir -Force | Out-Null

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

function New-Canvas {
    param([int]$Width, [int]$Height)
    $bmp = [System.Drawing.Bitmap]::new($Width, $Height)
    $bmp.SetResolution(300, 300)
    $g = [System.Drawing.Graphics]::FromImage($bmp)
    $g.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $g.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $g.Clear([System.Drawing.Color]::White)
    return @($bmp, $g)
}

function Draw-TextCenter {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.RectangleF]$Rect,
        [string]$Text,
        [System.Drawing.Font]$Font,
        [System.Drawing.Brush]$Brush
    )
    $sf = [System.Drawing.StringFormat]::new()
    $sf.Alignment = [System.Drawing.StringAlignment]::Center
    $sf.LineAlignment = [System.Drawing.StringAlignment]::Center
    $sf.Trimming = [System.Drawing.StringTrimming]::None
    try {
        $Graphics.DrawString($Text, $Font, $Brush, $Rect, $sf)
    } finally {
        $sf.Dispose()
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
    $head = 30.0
    $a1 = $angle - [Math]::PI / 7
    $a2 = $angle + [Math]::PI / 7
    $p1 = [System.Drawing.PointF]::new([float]($X2 - $head * [Math]::Cos($a1)), [float]($Y2 - $head * [Math]::Sin($a1)))
    $p2 = [System.Drawing.PointF]::new([float]($X2 - $head * [Math]::Cos($a2)), [float]($Y2 - $head * [Math]::Sin($a2)))
    $Graphics.DrawLine($Pen, $X2, $Y2, $p1.X, $p1.Y)
    $Graphics.DrawLine($Pen, $X2, $Y2, $p2.X, $p2.Y)
}

function Draw-GridBox {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.RectangleF]$Rect,
        [string]$Header,
        [string[]]$Rows,
        [System.Drawing.FontFamily]$Family,
        [float]$HeaderSize,
        [float]$RowSize,
        [System.Drawing.Pen]$Pen,
        [System.Drawing.Brush]$Brush
    )
    $Graphics.FillRectangle([System.Drawing.Brushes]::White, $Rect)
    $Graphics.DrawRectangle($Pen, $Rect.X, $Rect.Y, $Rect.Width, $Rect.Height)

    $headerH = [Math]::Min(92.0, [Math]::Max(68.0, $Rect.Height * 0.16))
    $headerRect = [System.Drawing.RectangleF]::new($Rect.X + 6, $Rect.Y + 2, $Rect.Width - 12, $headerH - 4)
    $headerFont = [System.Drawing.Font]::new($Family, $HeaderSize, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $rowFont = [System.Drawing.Font]::new($Family, $RowSize, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
    try {
        Draw-TextCenter $Graphics $headerRect $Header $headerFont $Brush
        $Graphics.DrawLine($Pen, $Rect.X, $Rect.Y + $headerH, $Rect.X + $Rect.Width, $Rect.Y + $headerH)

        $rowH = ($Rect.Height - $headerH) / $Rows.Count
        for ($i = 0; $i -lt $Rows.Count; $i++) {
            $y = $Rect.Y + $headerH + $i * $rowH
            $rowRect = [System.Drawing.RectangleF]::new($Rect.X + 8, $y + 2, $Rect.Width - 16, $rowH - 4)
            Draw-TextCenter $Graphics $rowRect $Rows[$i] $rowFont $Brush
        }
    } finally {
        $headerFont.Dispose()
        $rowFont.Dispose()
    }
}

function Draw-LayerBox {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.RectangleF]$Rect,
        [string]$Title,
        [string]$Desc,
        [System.Drawing.FontFamily]$Family,
        [System.Drawing.Pen]$Pen,
        [System.Drawing.Brush]$Brush
    )
    $Graphics.FillRectangle([System.Drawing.Brushes]::White, $Rect)
    $Graphics.DrawRectangle($Pen, $Rect.X, $Rect.Y, $Rect.Width, $Rect.Height)
    $titleFont = [System.Drawing.Font]::new($Family, 52, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $descFont = [System.Drawing.Font]::new($Family, 38, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
    try {
        Draw-TextCenter $Graphics ([System.Drawing.RectangleF]::new($Rect.X + 20, $Rect.Y + 22, $Rect.Width - 40, 62)) $Title $titleFont $Brush
        Draw-TextCenter $Graphics ([System.Drawing.RectangleF]::new($Rect.X + 26, $Rect.Y + 92, $Rect.Width - 52, $Rect.Height - 110)) $Desc $descFont $Brush
    } finally {
        $titleFont.Dispose()
        $descFont.Dispose()
    }
}

$family = Get-CnFontFamily
$black = [System.Drawing.Color]::Black
$brush = [System.Drawing.Brushes]::Black
$boxPen = [System.Drawing.Pen]::new($black, 5)
$arrowPen = [System.Drawing.Pen]::new($black, 8)

try {
    # 图 2-3 AI业务闭环逻辑
    $canvas = New-Canvas 2400 780
    $bmp = $canvas[0]
    $g = $canvas[1]
    try {
        $titleFont = [System.Drawing.Font]::new($family, 48, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
        Draw-TextCenter $g ([System.Drawing.RectangleF]::new(0, 22, 2400, 58)) 'AI业务闭环逻辑' $titleFont $brush
        $titleFont.Dispose()

        $boxY = 120.0
        $boxW = 430.0
        $boxH = 340.0
        $gap = 80.0
        $startX = 150.0
        $boxes = @(
            [System.Drawing.RectangleF]::new($startX, $boxY, $boxW, $boxH),
            [System.Drawing.RectangleF]::new($startX + ($boxW + $gap), $boxY, $boxW, $boxH),
            [System.Drawing.RectangleF]::new($startX + 2 * ($boxW + $gap), $boxY, $boxW, $boxH),
            [System.Drawing.RectangleF]::new($startX + 3 * ($boxW + $gap), $boxY, $boxW, $boxH)
        )
        Draw-GridBox $g $boxes[0] '配置准备' @('模型接口配置', '知识库资料整理', '客服与场景参数') $family 43 35 $boxPen $brush
        Draw-GridBox $g $boxes[1] '场景调用' @('学生咨询', '课程答疑', '教师教案生成') $family 43 35 $boxPen $brush
        Draw-GridBox $g $boxes[2] '结果沉淀' @('问答记录保存', '课程资料更新', '教案任务回写') $family 43 35 $boxPen $brush
        Draw-GridBox $g $boxes[3] '持续优化' @('补充知识内容', '调整模型配置', '优化工作流入口') $family 43 35 $boxPen $brush
        for ($i = 0; $i -lt 3; $i++) {
            Draw-Arrow $g $arrowPen ($boxes[$i].X + $boxes[$i].Width + 12) ($boxY + $boxH / 2) ($boxes[$i + 1].X - 18) ($boxY + $boxH / 2)
        }
        Draw-Arrow $g $arrowPen ($boxes[3].X + $boxes[3].Width / 2) ($boxes[3].Y + $boxes[3].Height + 18) ($boxes[0].X + $boxes[0].Width / 2) ($boxes[0].Y + $boxes[0].Height + 18)
        $labelFont = [System.Drawing.Font]::new($family, 33, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
        Draw-TextCenter $g ([System.Drawing.RectangleF]::new(690, 600, 1020, 70)) '运行数据反向支持知识补充与配置调整' $labelFont $brush
        $labelFont.Dispose()
        $target = Join-Path $assetDir 'fig_2_3_ai_business_loop.png'
        $bmp.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
        Copy-Item -LiteralPath $target -Destination (Join-Path $unzipDir 'word\media\image4.png') -Force
    } finally {
        $g.Dispose()
        $bmp.Dispose()
    }

    # 图 2-4 AI分层设计逻辑
    $canvas = New-Canvas 2400 1120
    $bmp = $canvas[0]
    $g = $canvas[1]
    try {
        $titleFont = [System.Drawing.Font]::new($family, 50, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
        Draw-TextCenter $g ([System.Drawing.RectangleF]::new(0, 20, 2400, 60)) 'AI分层设计逻辑' $titleFont $brush
        $titleFont.Dispose()

        $x = 140.0
        $w = 2120.0
        $h = 185.0
        $ys = @(120.0, 360.0, 600.0, 840.0)
        $layers = @(
            @{T='第一层：AI配置编排层'; D='围绕模型接入、场景入口和客服参数统一配置，为不同AI场景准备可切换底座。'},
            @{T='第二层：知识组织层'; D='整理制度文档、课程资料和教学材料，完成文本抽取、分块和知识来源绑定。'},
            @{T='第三层：推理执行层'; D='根据问题选择工作流和模型，完成知识检索、Prompt组装与SSE流式输出。'},
            @{T='第四层：业务接入层'; D='把AI能力开放到AI客服、课程助手和智能教案页面，让学生、教师和管理员按角色使用。'}
        )
        for ($i = 0; $i -lt 4; $i++) {
            $rect = [System.Drawing.RectangleF]::new($x, $ys[$i], $w, $h)
            Draw-LayerBox $g $rect $layers[$i].T $layers[$i].D $family $boxPen $brush
            if ($i -lt 3) {
                Draw-Arrow $g $arrowPen ($x + $w / 2) ($ys[$i] + $h + 8) ($x + $w / 2) ($ys[$i + 1] - 18)
            }
        }
        $target = Join-Path $assetDir 'fig_2_4_ai_layer_design.png'
        $bmp.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
        Copy-Item -LiteralPath $target -Destination (Join-Path $unzipDir 'word\media\image5.png') -Force
    } finally {
        $g.Dispose()
        $bmp.Dispose()
    }

    # 图 3-1 AI模块架构、代码组织与接口关系图
    $canvas = New-Canvas 2400 810
    $bmp = $canvas[0]
    $g = $canvas[1]
    try {
        $titleFont = [System.Drawing.Font]::new($family, 47, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
        Draw-TextCenter $g ([System.Drawing.RectangleF]::new(0, 18, 2400, 56)) 'AI模块架构、代码组织与接口关系图' $titleFont $brush
        $titleFont.Dispose()

        $boxY = 102.0
        $boxH = 575.0
        $boxW = 405.0
        $gap = 52.0
        $startX = 78.0
        $rects = @()
        for ($i = 0; $i -lt 5; $i++) {
            $rects += [System.Drawing.RectangleF]::new($startX + $i * ($boxW + $gap), $boxY, $boxW, $boxH)
        }
        Draw-GridBox $g $rects[0] '角色场景层' @('学生：AI客服', '学生：课程问答', '教师：资料与教案', '管理员：配置治理') $family 38 30 $boxPen $brush
        Draw-GridBox $g $rects[1] '前端页面组织' @('AdminAIConfig.vue', 'CourseAssistant.vue', 'LessonPlan.vue', 'StudentCourseAssistant.vue', 'aiPortal.ts / ai.ts') $family 38 27 $boxPen $brush
        Draw-GridBox $g $rects[2] '后端接口收口' @('/admin/ai/*', '/ai/course-assistant/*', '/ai/teacher/*', '/ai_qa/qa/stream', '统一权限校验') $family 38 27 $boxPen $brush
        Draw-GridBox $g $rects[3] 'AI能力编排层' @('工作流选择', '模型优先级', '文档抽取分块', 'TF-IDF检索组装', 'SSE流式输出') $family 38 30 $boxPen $brush
        Draw-GridBox $g $rects[4] '数据与资源层' @('ai_model_apis', 'ai_knowledge_bases', 'ai_kb_chunks', 'ai_workflow_apps', 'ai_lesson_plan_tasks') $family 38 27 $boxPen $brush
        for ($i = 0; $i -lt 4; $i++) {
            Draw-Arrow $g $arrowPen ($rects[$i].X + $rects[$i].Width + 10) ($boxY + $boxH / 2) ($rects[$i + 1].X - 15) ($boxY + $boxH / 2)
        }
        $labelFont = [System.Drawing.Font]::new($family, 30, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
        $labels = @('使用入口', '页面组织', '接口收口', '能力编排', '数据支撑')
        for ($i = 0; $i -lt 5; $i++) {
            Draw-TextCenter $g ([System.Drawing.RectangleF]::new($rects[$i].X, 706, $rects[$i].Width, 48)) $labels[$i] $labelFont $brush
        }
        $labelFont.Dispose()
        $target = Join-Path $assetDir 'fig_3_1_ai_module_code_api.png'
        $bmp.Save($target, [System.Drawing.Imaging.ImageFormat]::Png)
        Copy-Item -LiteralPath $target -Destination (Join-Path $unzipDir 'word\media\image6.png') -Force
    } finally {
        $g.Dispose()
        $bmp.Dispose()
    }
} finally {
    $boxPen.Dispose()
    $arrowPen.Dispose()
}

$documentXmlPath = Join-Path $unzipDir 'word\document.xml'
$settings = [System.Xml.XmlReaderSettings]::new()
$settings.DtdProcessing = [System.Xml.DtdProcessing]::Ignore
$reader = [System.Xml.XmlReader]::Create($documentXmlPath, $settings)
$xmlDoc = [System.Xml.XmlDocument]::new()
$xmlDoc.PreserveWhitespace = $true
$xmlDoc.Load($reader)
$reader.Close()

$ns = [System.Xml.XmlNamespaceManager]::new($xmlDoc.NameTable)
$ns.AddNamespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')
$paragraphs = $xmlDoc.SelectNodes('//w:body/w:p', $ns)

function Get-ParagraphText {
    param([System.Xml.XmlNode]$Paragraph)
    return (($Paragraph.SelectNodes('.//w:t', $ns) | ForEach-Object { $_.InnerText }) -join '')
}

function Set-ParagraphText {
    param([System.Xml.XmlNode]$Paragraph, [string]$Text)
    $nodes = $Paragraph.SelectNodes('.//w:t', $ns)
    if ($nodes.Count -eq 0) {
        return
    }
    $nodes[0].InnerText = $Text
    for ($i = 1; $i -lt $nodes.Count; $i++) {
        $nodes[$i].InnerText = ''
    }
}

$oldText = '从图3-1来看，这一层关系会直观一些。前端页面与代码组织负责把角色和场景分开，后端接口层负责收口与编排，再往下才是工作流、模型选择、文档处理、知识检索这些真正决定AI输出质量的能力。这里故意把接口分成管理配置接口、场景门户接口和统一问答接口三组，目的很实际：不让后台治理逻辑和前台业务入口搅在一起。'
$newText = '图3-1把AI模块从角色入口到数据表的关系拆成五层。左侧角色场景层说明学生、教师、管理员分别从咨询、课程资料和配置治理进入；前端页面组织层对应AdminAIConfig.vue、CourseAssistant.vue、LessonPlan.vue等页面，负责把不同角色的操作拆分到清晰入口；后端接口收口层通过/admin/ai/*、/ai/course-assistant/*、/ai/teacher/*和/ai_qa/qa/stream等接口把请求统一接入；AI能力编排层再完成工作流选择、模型优先级判断、文档抽取分块、TF-IDF检索和SSE流式输出；最右侧数据与资源层保存模型API、知识库、文档分块、工作流、教案任务和使用日志。这样处理后，后台治理、前台场景和统一问答链路不会混在一起，后续新增AI入口时也可以沿着同一条关系继续扩展。'
$textChanged = 0
foreach ($p in $paragraphs) {
    if ((Get-ParagraphText $p) -eq $oldText) {
        Set-ParagraphText $p $newText
        $textChanged++
    }
}
$xmlDoc.Save($documentXmlPath)

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

Write-Output "Updated figures: image4.png, image5.png, image6.png"
Write-Output "Updated explanation paragraphs: $textChanged"
Write-Output "Saved to: $srcDocx"

