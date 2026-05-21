$ErrorActionPreference = 'Stop'

$root = 'D:\bishe\one'
$unzipDir = Join-Path $root 'tmp_ai_thesis_unzip'
$documentXmlPath = Join-Path $unzipDir 'word\document.xml'
$imagePath = Join-Path $unzipDir 'word\media\image3.png'
$assetDir = Join-Path $root 'generated\thesis_assets'
$assetPath = Join-Path $assetDir 'fig_2_2_ai_existing_system_arch.png'
$updatedZip = Join-Path $root 'tmp_ai_thesis_updated.zip'
$updatedDocx = Join-Path $root 'tmp_ai_thesis_updated.docx'

if (-not (Test-Path -LiteralPath $unzipDir)) {
    throw "Unzip directory not found: $unzipDir"
}
if (-not (Test-Path -LiteralPath $documentXmlPath)) {
    throw "document.xml not found: $documentXmlPath"
}

New-Item -ItemType Directory -Path $assetDir -Force | Out-Null

Add-Type -AssemblyName System.Drawing

function New-FontFamily {
    param([string[]]$Names)
    foreach ($name in $Names) {
        try {
            return New-Object System.Drawing.FontFamily($name)
        } catch {
            continue
        }
    }
    return [System.Drawing.FontFamily]::GenericSansSerif
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
    $head = 26.0
    $a1 = $angle - [Math]::PI / 7
    $a2 = $angle + [Math]::PI / 7
    $p1 = [System.Drawing.PointF]::new(
        [float]($X2 - $head * [Math]::Cos($a1)),
        [float]($Y2 - $head * [Math]::Sin($a1))
    )
    $p2 = [System.Drawing.PointF]::new(
        [float]($X2 - $head * [Math]::Cos($a2)),
        [float]($Y2 - $head * [Math]::Sin($a2))
    )
    $Graphics.DrawLine($Pen, $X2, $Y2, $p1.X, $p1.Y)
    $Graphics.DrawLine($Pen, $X2, $Y2, $p2.X, $p2.Y)
}

function Draw-CenteredBox {
    param(
        [System.Drawing.Graphics]$Graphics,
        [System.Drawing.RectangleF]$Rect,
        [string]$Title,
        [string[]]$Lines,
        [System.Drawing.FontFamily]$Family,
        [float]$TitleSize,
        [float]$BodySize,
        [System.Drawing.Pen]$BorderPen,
        [System.Drawing.Brush]$TextBrush
    )

    $Graphics.FillRectangle([System.Drawing.Brushes]::White, $Rect)
    $Graphics.DrawRectangle($BorderPen, $Rect.X, $Rect.Y, $Rect.Width, $Rect.Height)

    $titleFont = [System.Drawing.Font]::new($Family, $TitleSize, [System.Drawing.FontStyle]::Bold, [System.Drawing.GraphicsUnit]::Pixel)
    $bodyFont = [System.Drawing.Font]::new($Family, $BodySize, [System.Drawing.FontStyle]::Regular, [System.Drawing.GraphicsUnit]::Pixel)
    try {
        $format = New-Object System.Drawing.StringFormat
        $format.Alignment = [System.Drawing.StringAlignment]::Center
        $format.LineAlignment = [System.Drawing.StringAlignment]::Center
        $format.Trimming = [System.Drawing.StringTrimming]::None
        $format.FormatFlags = 0

        $lineHeightTitle = $titleFont.GetHeight($Graphics) + 8
        $lineHeightBody = $bodyFont.GetHeight($Graphics) + 6
        $totalHeight = $lineHeightTitle + ($Lines.Count * $lineHeightBody)
        $currentY = $Rect.Y + [Math]::Max(8, ($Rect.Height - $totalHeight) / 2)
        $textWidth = $Rect.Width - 18

        $titleRect = [System.Drawing.RectangleF]::new($Rect.X + 9, $currentY, $textWidth, $lineHeightTitle)
        $Graphics.DrawString($Title, $titleFont, $TextBrush, $titleRect, $format)
        $currentY += $lineHeightTitle

        foreach ($line in $Lines) {
            $lineRect = [System.Drawing.RectangleF]::new($Rect.X + 9, $currentY, $textWidth, $lineHeightBody)
            $Graphics.DrawString($line, $bodyFont, $TextBrush, $lineRect, $format)
            $currentY += $lineHeightBody
        }
    } finally {
        $titleFont.Dispose()
        $bodyFont.Dispose()
    }
}

$width = 4199
$height = 2500
$bitmap = [System.Drawing.Bitmap]::new($width, $height)
$bitmap.SetResolution(300, 300)
$graphics = [System.Drawing.Graphics]::FromImage($bitmap)
try {
    $graphics.SmoothingMode = [System.Drawing.Drawing2D.SmoothingMode]::AntiAlias
    $graphics.TextRenderingHint = [System.Drawing.Text.TextRenderingHint]::AntiAliasGridFit
    $graphics.Clear([System.Drawing.Color]::White)

    $family = New-FontFamily @('Microsoft YaHei', 'Microsoft YaHei UI', 'SimHei', 'SimSun')
    $black = [System.Drawing.Color]::Black
    $borderPen = [System.Drawing.Pen]::new($black, 7)
    $arrowPen = [System.Drawing.Pen]::new($black, 7)
    $brush = [System.Drawing.Brushes]::Black

    $marginX = 110.0
    $gap = 60.0
    $contentW = $width - $marginX * 2
    $roleW = ($contentW - 2 * $gap) / 3
    $roleY = 80.0
    $roleH = 380.0

    $studentRect = [System.Drawing.RectangleF]::new($marginX, $roleY, $roleW, $roleH)
    $teacherRect = [System.Drawing.RectangleF]::new($marginX + $roleW + $gap, $roleY, $roleW, $roleH)
    $adminRect = [System.Drawing.RectangleF]::new($marginX + 2 * ($roleW + $gap), $roleY, $roleW, $roleH)

    Draw-CenteredBox $graphics $studentRect '学生端' @('选课冲突咨询', '成绩查询说明', '请假与报到流程', 'AI客服 / 课程助手') $family 66 50 $borderPen $brush
    Draw-CenteredBox $graphics $teacherRect '教师端' @('课程资料整理', '作业与成绩处理', '课程问答沉淀', '智能教案生成') $family 66 50 $borderPen $brush
    Draw-CenteredBox $graphics $adminRect '管理员端' @('用户与流程维护', '模型API配置', '知识库管理', '工作流编排') $family 66 50 $borderPen $brush

    $frontRect = [System.Drawing.RectangleF]::new($marginX, 560.0, $contentW, 280.0)
    $backendRect = [System.Drawing.RectangleF]::new($marginX, 950.0, $contentW, 280.0)
    $lowerGap = 80.0
    $lowerW = ($contentW - $lowerGap) / 2
    $businessRect = [System.Drawing.RectangleF]::new($marginX, 1340.0, $lowerW, 520.0)
    $aiRect = [System.Drawing.RectangleF]::new($marginX + $lowerW + $lowerGap, 1340.0, $lowerW, 520.0)
    $dataRect = [System.Drawing.RectangleF]::new($marginX, 2050.0, $contentW, 360.0)

    Draw-CenteredBox $graphics $frontRect '前端展示层' @('Vue3 + TypeScript + Element Plus', '角色页面 / 业务表单 / AI对话窗口 / SSE流式展示') $family 72 54 $borderPen $brush
    Draw-CenteredBox $graphics $backendRect '后端服务层' @('FastAPI + SQLAlchemy + Socket.IO', '统一接口 / 权限校验 / 业务编排 / AI任务回写') $family 72 54 $borderPen $brush
    Draw-CenteredBox $graphics $businessRect '现有教务业务底座' @('课程 / 选课 / 排课', '成绩 / 证书查询', '请假 / 审批流程', '办事大厅 / 报到', '用户 / 角色权限') $family 68 56 $borderPen $brush
    Draw-CenteredBox $graphics $aiRect 'AI增强能力层' @('AI客服 / 课程助手', '智能教案任务', '知识库文档分块', '模型API / 工作流', 'Prompt组装 / 流式输出') $family 68 56 $borderPen $brush
    Draw-CenteredBox $graphics $dataRect '数据与外部资源层' @('SQLite业务数据 / AI配置 / 使用日志 / 知识分块', 'DashScope、Ark 等大模型接口', '本地环境与阿里云 Ubuntu 公网部署 wangjiaqi.me') $family 70 52 $borderPen $brush

    $roleBottomY = $roleY + $roleH
    $frontTopY = $frontRect.Y
    foreach ($rect in @($studentRect, $teacherRect, $adminRect)) {
        $cx = $rect.X + $rect.Width / 2
        Draw-Arrow $graphics $arrowPen $cx ($roleBottomY + 12) $cx ($frontTopY - 24)
    }

    $centerX = $marginX + $contentW / 2
    Draw-Arrow $graphics $arrowPen $centerX ($frontRect.Y + $frontRect.Height + 12) $centerX ($backendRect.Y - 24)
    Draw-Arrow $graphics $arrowPen ($centerX - 430) ($backendRect.Y + $backendRect.Height + 12) ($businessRect.X + $businessRect.Width / 2) ($businessRect.Y - 24)
    Draw-Arrow $graphics $arrowPen ($centerX + 430) ($backendRect.Y + $backendRect.Height + 12) ($aiRect.X + $aiRect.Width / 2) ($aiRect.Y - 24)
    Draw-Arrow $graphics $arrowPen ($businessRect.X + $businessRect.Width / 2) ($businessRect.Y + $businessRect.Height + 12) ($dataRect.X + $dataRect.Width / 2 - 620) ($dataRect.Y - 24)
    Draw-Arrow $graphics $arrowPen ($aiRect.X + $aiRect.Width / 2) ($aiRect.Y + $aiRect.Height + 12) ($dataRect.X + $dataRect.Width / 2 + 620) ($dataRect.Y - 24)

    $bitmap.Save($assetPath, [System.Drawing.Imaging.ImageFormat]::Png)
    Copy-Item -LiteralPath $assetPath -Destination $imagePath -Force
} finally {
    $graphics.Dispose()
    $bitmap.Dispose()
}

$settings = New-Object System.Xml.XmlReaderSettings
$settings.DtdProcessing = [System.Xml.DtdProcessing]::Ignore
$reader = [System.Xml.XmlReader]::Create($documentXmlPath, $settings)
$xmlDoc = New-Object System.Xml.XmlDocument
$xmlDoc.PreserveWhitespace = $true
$xmlDoc.Load($reader)
$reader.Close()

$ns = New-Object System.Xml.XmlNamespaceManager($xmlDoc.NameTable)
$ns.AddNamespace('w', 'http://schemas.openxmlformats.org/wordprocessingml/2006/main')
$paragraphs = $xmlDoc.SelectNodes('//w:body/w:p', $ns)

function Get-ParagraphText {
    param([System.Xml.XmlNode]$Paragraph)
    $texts = $Paragraph.SelectNodes('.//w:t', $ns)
    return (($texts | ForEach-Object { $_.InnerText }) -join '')
}

function Set-ParagraphText {
    param(
        [System.Xml.XmlNode]$Paragraph,
        [string]$Text
    )
    $texts = $Paragraph.SelectNodes('.//w:t', $ns)
    if ($texts.Count -eq 0) {
        return
    }
    $texts[0].InnerText = $Text
    for ($i = 1; $i -lt $texts.Count; $i++) {
        $texts[$i].InnerText = ''
    }
}

$replacements = @{
    '本文以AI赋能的高校教务系统为研究对象，针对高校教务场景中咨询渠道分散、课程答疑效率偏低、教案编写重复性较强等问题，设计并实现了一个面向学生、教师和管理员的智能化教务平台。系统采用前后端分离架构，前端基于Vue3实现，后端基于FastAPI构建，并在传统教务功能基础上融合知识库检索、工作流编排与流式问答能力，形成AI客服、AI课程助手和智能教案三类核心应用。测试结果表明，系统主要接口与关键业务链路运行稳定，能够满足教务咨询、课程辅助和教学内容生成等实际需求，为高校教务系统的智能化建设提供了可落地的实现方案。' =
    '本文以现有高校教务系统的智能化增强为研究对象，针对高校教务场景中咨询渠道分散、课程答疑效率偏低、教案编写重复性较强等问题，设计并实现了面向学生、教师和管理员的AI服务能力。系统采用前后端分离架构，前端基于Vue3实现，后端基于FastAPI构建，在原有课程、请假、办事大厅、用户权限等教务业务基础上，引入知识库检索、工作流编排与流式问答机制，形成AI客服、AI课程助手和智能教案三类核心应用。测试结果表明，系统主要接口与关键AI业务链路运行稳定，能够满足教务咨询、课程辅助和教学内容生成等实际需求，为高校教务系统在既有业务基础上的智能化升级提供了可落地的实现方案。';

    '2.2.1 基础教务功能需求6' =
    '2.2.1 现有教务业务支撑需求6';

    '本课题的研究目标，是构建并分析一套面向学生、教师和管理员的AI赋能高校教务系统。系统在保留课程查询、请假申请、办事大厅、用户管理等基础教务功能的基础上，重点实现AI客服、AI课程助手、智能教案和管理端AI配置能力。通过该目标，系统既能够覆盖高校教务管理中的常规业务，又能够围绕咨询、答疑和教学材料生成等场景提供智能化支持。围绕这一目标，本文从三个层面展开研究：其一，梳理学生、教师和管理员在系统中的业务入口与使用边界；其二，分析模型、知识库、工作流与任务表之间的协同关系；其三，结合本地联调结果，对系统主要功能链路的可运行性进行验证。' =
    '本课题的研究目标，是在已有高校教务系统基础上，构建并分析一套面向学生、教师和管理员的AI增强服务能力。系统保留课程查询、请假申请、办事大厅、用户管理等既有业务入口，但论文重点不再展开这些基础教务功能的完整设计、实现和测试，而是分析AI客服、AI课程助手、智能教案和管理端AI配置如何嵌入原有业务流程。围绕这一目标，本文从三个层面展开研究：其一，梳理学生、教师和管理员在系统中的业务入口与AI使用边界；其二，分析模型、知识库、工作流与任务表之间的协同关系；其三，结合本地联调结果，对AI增强链路的可运行性进行验证。';

    '本文的需求分析先设计一个传统的教务系统，再此基础上再去为AI寻找落点，实现AI赋能的高校教务系统本身。学生、教师和管理员共用同一套平台，但他们面对的业务压力、操作习惯和信息诉求并不一致。也正因为如此，AI能力不能脱离课程、请假、办事、成绩等既有业务独立存在，而应嵌入这些高频环节，承担解释、辅助和减负的作用。' =
    '本文的需求分析并不是从零重新设计一套完整教务系统，而是以已有教务系统的课程、选课、成绩、请假、办事大厅和用户管理等基础功能为业务底座，重点分析AI能力如何嵌入这些高频场景。学生、教师和管理员共用同一平台，但面对的问题并不一样：学生更常遇到选课冲突、成绩查询、请假流程和报到材料等咨询；教师更关注课程资料整理、重复答疑和教案准备；管理员则需要维护模型、知识库和工作流配置。因此，本文后续设计与实现重点放在AI客服、AI课程助手、智能教案和管理端AI配置上，基础教务功能主要作为业务上下文和权限边界存在。';

    '因此，本系统的需求分析不能简单理解为给传统教务系统外接一个聊天窗口。传统教务系统负责规则执行、信息展示和流程办理，AI部分更像嵌入式能力层，负责解释制度、理解问题、组织资料和辅助生成。两部分分工清楚，系统才不会出现功能重复、角色边界模糊或结果难以落地的问题。' =
    '因此，本系统的需求分析不能简单理解为重新写一套传统教务系统，也不是给现有系统外接一个聊天窗口。现有教务系统负责规则执行、信息展示和流程办理，AI部分更像嵌入式能力层，负责解释制度、理解问题、组织资料和辅助生成。两部分分工清楚，系统才不会出现功能重复、角色边界模糊或结果难以落地的问题。';

    '基础教务功能需求' =
    '现有教务业务支撑需求';

    '因此，基础教务功能首先需要保持完整和稳定。学生要能够完成课程查询、请假申请、成绩与证书查看、办事事项办理；教师要能够完成课程管理、作业与成绩处理、审批等教学组织工作；管理员要能够维护用户、流程和系统配置。这部分功能决定了系统的业务边界，也为AI判断面向谁服务、在什么场景下服务提供了前提。' =
    '本课题不把基础教务功能作为重新设计和完整测试的重点，而是将其作为已经具备的业务底座和数据边界。学生侧的课程查询、请假申请、成绩与证书查看、办事事项办理，教师侧的课程管理、作业与成绩处理、审批，管理员侧的用户、流程和系统配置维护，共同构成AI能力接入的上下文。换句话说，这些功能在论文中主要承担“场景来源”和“权限边界”的作用，后续章节重点讨论AI如何围绕这些入口完成解释、答疑、生成和配置治理。';

    '第四类是后台治理需求。AI功能真正进入教务系统后，管理员必须能够配置模型接口、维护知识库、绑定工作流，并检查前台是否能正常调用。没有这一层，AI客服、课程助手和智能教案就容易变成固定写死的功能，后续难以维护。通过这样的划分可以看出，AI客服、AI课程助手和智能教案虽然入口不同，但都围绕高校教务中的咨询、学习、备课和管理治理展开，最终目标是让传统教务系统从“办理事务”进一步扩展为“理解规则、辅助学习、支持教学”的综合服务平台。' =
    '第四类是后台治理需求。AI功能真正进入教务系统后，管理员必须能够配置模型接口、维护知识库、绑定工作流，并检查前台是否能正常调用。没有这一层，AI客服、课程助手和智能教案就容易变成固定写死的功能，后续难以维护。通过这样的划分可以看出，AI客服、AI课程助手和智能教案虽然入口不同，但都围绕高校教务中的咨询、学习、备课和管理治理展开，最终目标是在现有教务系统基础上补足解释、答疑和教学辅助能力，让系统从“办理事务”进一步扩展为“理解规则、辅助学习、支持教学”的综合服务平台。';

    '为满足高校教务场景下多角色访问、业务协同、AI接入与数据治理等需求，系统总体采用“前端展示层—后端服务层—AI能力层—数据与外部资源层”的分层架构，如图 2-2系统总体架构图。前端展示层负责承载学生、教师和管理员的业务入口与交互反馈；后端服务层负责统一接口组织、权限校验与业务编排；AI能力层负责模型调用、知识检索和内容生成；数据与外部资源层负责保存教务数据、AI配置数据、知识文档及外部模型服务连接信息[6]。' =
    '为满足在现有教务系统中接入多角色AI服务、业务协同和数据治理等需求，系统总体采用“前端展示层—后端服务层—现有教务业务底座—AI增强能力层—数据与外部资源层”的分层架构，如图 2-2基于现有教务系统的AI增强总体架构图。前端展示层负责承载学生、教师和管理员的业务入口与交互反馈；后端服务层负责统一接口组织、权限校验与业务编排；现有教务业务底座提供课程、成绩、请假、办事大厅和用户权限等场景；AI增强能力层负责模型调用、知识检索和内容生成；数据与外部资源层负责保存教务数据、AI配置数据、知识文档及外部模型服务连接信息[6]。';

    '图 2-2系统总体架构图' =
    '图 2-2基于现有教务系统的AI增强总体架构图';

    '这种模块划分方式的意义在于，它明确了AI在系统中的职责边界。基础教务模块仍然承担规则执行与流程办理，AI模块主要承担解释、增强和辅助生成作用；管理员负责治理底层AI资源，教师负责组织课程资料并开展教学辅助，学生则主要面向问答与使用结果。模块边界清晰后，系统才能避免“AI替代全部业务”的误解，并形成更适合高校教务场景的工程落地结构，如表2-2 系统模块划分与职责边界。' =
    '这种模块划分方式的意义在于，它明确了AI在系统中的职责边界。现有教务业务模块仍然承担规则执行与流程办理，AI模块主要承担解释、增强和辅助生成作用；管理员负责治理底层AI资源，教师负责组织课程资料并开展教学辅助，学生则主要面向问答与使用结果。模块边界清晰后，系统才能避免“AI替代全部业务”的误解，并形成更适合高校教务场景的工程落地结构，如表2-2 系统模块划分与职责边界。';

    '前面的需求分析与总体设计明确了系统要解决什么问题，而关键技术选择则回答系统依靠什么把这些能力稳定落到项目中。考虑到本课题既包含课程管理、请假、办事大厅等传统教务业务，又要承载AI客服、AI课程助手和智能教案等新增能力，技术方案不能只追求复杂堆叠，而应服务于结构清晰、部署简洁、便于演示和后续扩展这几个现实目标。' =
    '前面的需求分析与总体设计明确了系统要解决什么问题，而关键技术选择则回答系统依靠什么把这些能力稳定落到项目中。考虑到本课题是在现有课程管理、请假、办事大厅等教务业务基础上增加AI客服、AI课程助手和智能教案等能力，技术方案不能只追求复杂堆叠，而应服务于结构清晰、部署简洁、便于演示和后续扩展这几个现实目标。';

    '数据库设计这里，重点不是单纯把表建出来，而是把AI功能运行过程中会产生的不同类型数据分清楚。基础教务数据继续承载用户、课程、选课、请假和办事流程；AI扩展数据则专门负责模型配置、知识资源、文档分块、工作流、任务结果和使用日志。两类数据分层存放以后，结构会清楚很多，后期维护也不容易乱。' =
    '数据库设计这里，重点不是单纯把表建出来，而是把AI功能运行过程中会产生的不同类型数据分清楚。现有教务数据继续承载用户、课程、选课、请假和办事流程；AI扩展数据则专门负责模型配置、知识资源、文档分块、工作流、任务结果和使用日志。两类数据分层存放以后，结构会清楚很多，后期维护也不容易乱。';

    '从功能完整性角度看，系统已经形成“管理员配置AI资源、教师组织课程资料、学生和教师调用AI服务、系统保存任务结果”的闭环。传统教务功能为AI应用提供课程、用户和办事场景支撑，AI模块则提升咨询、答疑和教案生成的效率。经过本章的测试说明，用户可以较清楚地理解每个功能如何进入、如何操作、如何触发接口以及如何确认结果，整体上能够体现AI技术在高校教务系统中的实际应用价值。' =
    '从功能完整性角度看，系统已经形成“管理员配置AI资源、教师组织课程资料、学生和教师调用AI服务、系统保存任务结果”的闭环。现有教务功能为AI应用提供课程、用户和办事场景支撑，AI模块则提升咨询、答疑和教案生成的效率。经过本章的测试说明，用户可以较清楚地理解每个AI功能如何进入、如何操作、如何触发接口以及如何确认结果，整体上能够体现AI技术在高校教务系统中的实际应用价值。';

    '本文围绕 AI 赋能的高校教务系统展开研究，重点开展了系统的需求分析、总体架构、模块划分、数据库规划、核心 AI 功能和运行验证工作。系统面向学生、教师和管理员三类角色，既包含课程查询、请假申请、办事大厅、用户管理等基础教务功能，也包含 AI 客服、AI 课程助手、智能教案等智能化功能。' =
    '本文围绕现有高校教务系统的 AI 增强展开研究，重点开展了需求分析、总体架构、模块划分、数据库规划、核心 AI 功能和运行验证工作。系统面向学生、教师和管理员三类角色，以课程查询、请假申请、办事大厅、用户管理等已有教务入口为业务基础，重点扩展 AI 客服、AI 课程助手、智能教案等智能化能力。';
}

$changed = 0
foreach ($p in $paragraphs) {
    $text = Get-ParagraphText $p
    if ($replacements.ContainsKey($text)) {
        Set-ParagraphText $p $replacements[$text]
        $changed++
    }
}

$allTexts = $xmlDoc.SelectNodes('//w:t', $ns)
foreach ($node in $allTexts) {
    if ($node.InnerText -eq '基础教务支撑模块') {
        $node.InnerText = '现有教务支撑模块'
        $changed++
    } elseif ($node.InnerText -eq '承载高校教务的原生业务流程') {
        $node.InnerText = '提供已有教务业务流程'
        $changed++
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

Write-Output "Updated paragraphs/table text count: $changed"
Write-Output "Generated diagram: $assetPath"
Write-Output "Updated docx: $updatedDocx"


