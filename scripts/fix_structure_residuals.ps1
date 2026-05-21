$ErrorActionPreference = 'Stop'

$root = 'D:\bishe\one'
$srcDocx = 'C:\Users\wangj\Desktop\2405273202-王佳齐-AI赋能的高校教务系统(ai) -.docx'
$zipPath = Join-Path $root 'tmp_fix_structure_residuals.zip'
$unzipDir = Join-Path $root 'tmp_fix_structure_residuals_unzip'
$updatedZip = Join-Path $root 'tmp_fix_structure_residuals_updated.zip'
$updatedDocx = Join-Path $root 'tmp_fix_structure_residuals_updated.docx'

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

$map = @{
    '总体设计与结构设计' = 'AI能力接入边界分析';
    '从组织方式上看，这些数据并不是彼此孤立保存，而是围绕用户、课程、知识资料和AI场景逐层关联。基础教务数据负责提供角色身份和课程边界，AI配置数据负责确定调用关系，知识数据负责提供内容依据，任务与日志数据负责保留运行结果。这样的规划能够较清楚地回答三个问题：AI能力由谁配置、依赖哪些资料、最终结果保存在哪里，也使系统在后续扩展课程答疑、教学生成或使用统计时具备较好的结构基础。' =
    '从需求关系看，这些数据并不是彼此孤立存在，而是围绕用户、课程、知识资料和AI场景逐层关联。基础教务数据提供角色身份和课程边界，AI配置数据确定调用关系，知识数据提供内容依据，任务与日志数据保留运行结果。通过这种分类，可以较清楚地回答三个问题：AI能力由谁配置、依赖哪些资料、最终结果保存在哪里。';
    '在系统架构层面，项目采用前后端分离方式组织多角色业务。前端主要负责学生、教师和管理员页面中的表单交互、状态反馈与结果展示，后端负责权限校验、业务编排、统一接口输出以及模型调用衔接。这样的划分使角色页面与AI服务链路能够相对独立演进，后续即使继续扩展课程助手或新增新的智能功能，也不必反复改动整套页面逻辑。' =
    '在前后端协同方面，项目需要通过前后端分离方式组织多角色业务。前端主要负责学生、教师和管理员页面中的表单交互、状态反馈与结果展示，后端负责权限校验、业务编排、统一接口输出以及模型调用衔接。这样的划分使角色页面与AI服务链路能够相对独立演进，后续即使继续扩展课程助手或新增新的智能功能，也不必反复改动整套页面逻辑。';
    '对这个项目来说，AI部分更需要先把结构讲清楚：哪些页面承接不同角色，哪些接口负责场景调度，哪些资源在后台持续支撑问答和生成。换句话说，先把骨架立住，后面的知识组织、检索增强和表结构设计才不会显得散。' =
    '本章集中说明AI模块的系统设计关系：不同角色由哪些页面承接，场景请求由哪些接口调度，后台资源如何持续支撑问答和生成。先明确模块关系，再展开知识组织、检索增强和表结构设计，可以使本章设计内容更加集中。';
    '图3-1把AI模块从角色入口到数据表的关系拆成五层。左侧角色场景层说明学生、教师、管理员分别从咨询、课程资料和配置治理进入；前端页面组织层对应AdminAIConfig.vue、CourseAssistant.vue、LessonPlan.vue等页面，负责把不同角色的操作拆分到清晰入口；后端接口收口层通过/admin/ai/*、/ai/course-assistant/*、/ai/teacher/*和/ai_qa/qa/stream等接口把请求统一接入；AI能力编排层再完成工作流选择、模型优先级判断、文档抽取分块、TF-IDF检索和SSE流式输出；最右侧数据与资源层保存模型API、知识库、文档分块、工作流、教案任务和使用日志。这样处理后，后台治理、前台场景和统一问答链路不会混在一起，后续新增AI入口时也可以沿着同一条关系继续扩展。' =
    '图3-1将AI模块从角色入口到数据表的关系划分为五层。左侧角色场景层说明学生、教师、管理员分别从咨询、课程资料和配置治理进入；前端页面组织层对应AdminAIConfig.vue、CourseAssistant.vue、LessonPlan.vue等页面，负责将不同角色的操作分配到清晰入口；后端接口收口层通过/admin/ai/*、/ai/course-assistant/*、/ai/teacher/*和/ai_qa/qa/stream等接口统一接入请求；AI能力编排层完成工作流选择、模型优先级判断、文档抽取分块、TF-IDF检索和SSE流式输出；数据与资源层保存模型API、知识库、文档分块、工作流、教案任务和使用日志。通过这种分层，后台治理、前台场景和统一问答链路能够保持清晰边界，后续新增AI入口时也可以沿用同一结构。'
}

$changed = 0
foreach ($p in $doc.SelectNodes('//w:body/w:p', $ns)) {
    $text = Get-Text $p
    if ($map.ContainsKey($text)) {
        Set-Text $p $map[$text]
        $changed++
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

Write-Output "Fixed residual structure wording. Changed items: $changed"

