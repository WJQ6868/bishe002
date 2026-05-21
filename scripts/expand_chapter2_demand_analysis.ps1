param(
  [string]$DocPath = "C:\Users\wangj\Desktop\2405273202-王佳齐-AI赋能的高校教务系统(56).docx"
)

$ErrorActionPreference = "Stop"

if (-not (Test-Path -LiteralPath $DocPath)) {
  throw "File not found: $DocPath"
}

$backupPath = [System.IO.Path]::Combine(
  [System.IO.Path]::GetDirectoryName($DocPath),
  ([System.IO.Path]::GetFileNameWithoutExtension($DocPath) + "-第二章扩写前备份.docx")
)
Copy-Item -LiteralPath $DocPath -Destination $backupPath -Force

$word = New-Object -ComObject Word.Application
$word.Visible = $false
$word.DisplayAlerts = 0
$doc = $null

function Find-ParagraphIndex {
  param(
    $Document,
    [string]$ExactText
  )
  for ($i = 1; $i -le $Document.Paragraphs.Count; $i++) {
    $t = $Document.Paragraphs.Item($i).Range.Text.Trim([char]13, [char]7)
    if ($t -eq $ExactText) {
      return $i
    }
  }
  throw "Paragraph not found: $ExactText"
}

function Insert-AfterParagraph {
  param(
    $Document,
    [int]$Index,
    [string[]]$Paragraphs
  )
  $range = $Document.Paragraphs.Item($Index).Range
  $text = (($Paragraphs -join "`r") + "`r")
  $range.InsertAfter($text)
  [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($range)
}

try {
  $doc = $word.Documents.Open($DocPath, $false, $false)

  $p1 = '管理员用户的需求主要集中于配置治理与运行控制。管理员并非系统中的高频提问者，但需要对模型可用性、知识库归属关系、工作流开放范围以及界面参数配置进行统一管理。因此，在本系统中，管理员承担AI资源编排与治理职能。正是由于学生、教师与管理员在使用目标和操作权限方面存在显著差异，系统在设计上必须同时引入角色分层与工作流分层机制。'
  $i1 = Find-ParagraphIndex -Document $doc -ExactText $p1
  Insert-AfterParagraph -Document $doc -Index $i1 -Paragraphs @(
    '结合项目当前功能可以进一步看出，学生侧的需求并不局限于“提问”本身，而是围绕完整教务流程展开。学生在系统中需要查看课程信息、访问办事大厅、提交请假申请、查询个人成绩、查看证书入口，并在遇到流程不清、材料不全、课程内容难以理解等问题时得到即时帮助。因此，学生需求分析的重点在于：一方面保留菜单式业务入口，保证规则类操作可被准确执行；另一方面通过AI客服和AI课程助手降低信息理解成本，使学生能够在原有业务页面基础上完成“查询—理解—继续办理”的连续操作。',
    '从教师侧看，当前项目已实现课程助手、智能教案、成绩管理、作业管理和请假审批等功能，说明教师需求具有明显的“教学组织 + 教学辅助”双重特征。教师既需要完成成绩录入、作业布置、审批处理等确定性业务，又希望借助AI减少课程资料整理、答疑组织和教案撰写中的重复劳动。因此，教师需求分析不能只停留于内容生成层面，还需要考虑课程绑定是否准确、资料是否可持续更新、生成结果是否支持再次编辑、任务过程是否可以追踪等实际使用条件。',
    '管理员侧需求则体现出平台治理属性。除用户管理、办事配置、服务审核等传统后台能力外，项目还引入了模型API管理、知识库管理、工作流编排和客服参数维护等AI治理功能。由此可见，管理员关注的不只是功能“是否存在”，还关注模型是否可连接、知识库是否有明确归属、不同工作流是否面向不同场景开放，以及配置变更后前台页面能否及时读取到最新结果。这类需求决定了第二章中的总体设计必须把“后台可治理”作为AI落地的重要前提。',
    '若从跨角色业务协同角度观察，系统中至少存在三条典型需求链路。第一条是学生咨询链路，即学生在课程学习、办事办理和信息查询过程中通过AI客服获得规则解释；第二条是教师课程支持链路，即教师上传课程资料、创建课程助手，学生再围绕该课程发起提问；第三条是教案生成链路，即教师基于课程资料和教学目标创建任务并生成可编辑教案。上述链路表明，第二章的需求分析不仅要回答“谁需要什么功能”，还要回答“不同角色之间如何围绕同一数据和同一业务目标形成闭环”。'
  )

  $p2 = '智能教案模块体现出更为明显的任务型特征。教师在使用过程中需要经历课程选择、资料选取、任务创建、内容生成、结果修改、保存和导出等多个步骤。因此，该模块的核心需求并非单纯追求生成速度，而是确保生成过程具备可记录性、生成结果具备可复用性、异常情况具备可定位性。基于这一需求，系统以ai_lesson_plan_tasks表对教案生成过程进行结构化管理，而非仅返回一次性文本结果。'
  $i2 = Find-ParagraphIndex -Document $doc -ExactText $p2
  Insert-AfterParagraph -Document $doc -Index $i2 -Paragraphs @(
    '在传统教务功能层面，项目实际已经覆盖课程、成绩、请假、作业、办事大厅、证书入口、消息与好友等模块。这些模块虽然并不直接属于AI应用，但它们为AI功能提供了真实的业务上下文。例如，请假、成绩和办事相关页面为AI客服提供高频咨询场景，课程、作业和教学资料为课程助手与智能教案提供明确的课程边界，消息与通知类功能则为后续扩展智能提醒、结果推送和使用反馈预留了业务接口。因此，功能需求分析需要把传统模块视为AI能力的场景底座，而不是与AI并列、互不关联的独立部分。',
    '在AI增强功能层面，系统的需求可进一步拆分为配置需求、执行需求和沉淀需求三个维度。配置需求要求管理员能够维护模型、知识库和工作流绑定关系；执行需求要求学生与教师能够通过页面入口发起问答或生成请求，并获得流式或任务化结果；沉淀需求要求系统把文档、分块、任务、日志和结果保存下来，保证后续可复用、可复查、可统计。这样拆分之后，AI客服、AI课程助手和智能教案虽然场景不同，但都可以纳入统一需求框架中分析。',
    '进一步结合项目接口实现，可以发现需求分析还必须覆盖异常与状态反馈。教师上传课程文档时，需要知道资料是否上传成功、是否完成解析、是否进入课程知识库；学生提问时，需要知道工作流是否可用、回答是否正在生成、知识不足时系统应如何提示；教师生成教案时，需要知道任务是待处理、生成中还是已完成，并在失败时获得可定位的错误信息。上述状态反馈需求直接决定了前端提示、后端状态字段以及任务结果回写机制的设计方式。'
  )

  $p3 = '对于AI模块而言，结果可解释性与故障可处理性同样构成重要的非功能要求。当前系统通过知识分块、任务状态记录、工作流绑定关系与错误提示信息保留关键链路数据，使管理员、教师和学生能够从不同角色入口使用AI功能，并在数据库中形成可追踪的配置与结果记录。'
  $i3 = Find-ParagraphIndex -Document $doc -ExactText $p3
  Insert-AfterParagraph -Document $doc -Index $i3 -Paragraphs @(
    '除此之外，第二章中的非功能需求还应包含对响应连续性和访问便利性的考虑。项目当前采用SSE流式输出机制返回问答内容，其目的不仅是改善交互体验，也是在用户等待大模型返回结果时保持页面可感知状态，避免出现“请求已发送但界面无反馈”的使用断层。对于答辩演示场景而言，这种连续反馈机制能够更直观地体现系统处于可用状态。',
    '部署与运维需求同样是项目实际情况的重要组成部分。系统既支持Windows本地联调与脚本启动，也已部署到阿里云云服务器的Ubuntu环境并通过公网域名对外提供访问入口。这意味着需求分析不能只考虑单机开发便利性，还要考虑在不同部署环境下的可启动性、访问稳定性、配置迁移便捷性以及日志留存能力。对于毕业设计项目而言，这类需求虽然不直接表现为页面功能，却直接影响系统能否被完整演示和持续验证。'
  )

  $doc.Save()
}
finally {
  if ($doc -ne $null) {
    $doc.Close([ref]0)
    [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($doc)
  }
  $word.Quit()
  [void][System.Runtime.InteropServices.Marshal]::ReleaseComObject($word)
  [gc]::Collect()
  [gc]::WaitForPendingFinalizers()
}

Write-Output "Backup: $backupPath"
Write-Output "Chapter 2 expanded."
