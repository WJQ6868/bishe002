param(
  [string]$UnzipDir = 'D:\bishe\one\tmp_table_edit_567_unzip',
  [string]$OutputDocx = 'D:\bishe\one\tmp_table_edit_567_updated.docx'
)

$ErrorActionPreference = 'Stop'

$wNs = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
$xmlNs = 'http://www.w3.org/XML/1998/namespace'
$docPath = Join-Path $UnzipDir 'word\document.xml'

$settings = New-Object System.Xml.XmlReaderSettings
$settings.DtdProcessing = [System.Xml.DtdProcessing]::Ignore
$reader = [System.Xml.XmlReader]::Create($docPath, $settings)
$doc = New-Object System.Xml.XmlDocument
$doc.Load($reader)
$reader.Close()

$ns = New-Object System.Xml.XmlNamespaceManager($doc.NameTable)
$ns.AddNamespace('w', $wNs)

function New-WElement {
  param([string]$Name)
  return $doc.CreateElement('w', $Name, $wNs)
}

function Set-WAttr {
  param(
    [System.Xml.XmlElement]$Node,
    [string]$Name,
    [string]$Value
  )
  $attr = $Node.GetAttributeNode($Name, $wNs)
  if (-not $attr) {
    $attr = $doc.CreateAttribute('w', $Name, $wNs)
    [void]$Node.Attributes.Append($attr)
  }
  $attr.Value = $Value
}

function Set-XmlSpacePreserve {
  param([System.Xml.XmlElement]$Node)
  $attr = $Node.GetAttributeNode('space', $xmlNs)
  if (-not $attr) {
    $attr = $doc.CreateAttribute('xml', 'space', $xmlNs)
    [void]$Node.Attributes.Append($attr)
  }
  $attr.Value = 'preserve'
}

function Upsert-WChild {
  param(
    [System.Xml.XmlElement]$Parent,
    [string]$Name
  )
  $child = $Parent.SelectSingleNode("./w:$Name", $ns)
  if (-not $child) {
    $child = New-WElement $Name
    [void]$Parent.AppendChild($child)
  }
  return $child
}

function Remove-WChild {
  param(
    [System.Xml.XmlElement]$Parent,
    [string]$Name
  )
  $target = $Parent.SelectSingleNode("./w:$Name", $ns)
  if ($target) {
    [void]$Parent.RemoveChild($target)
  }
}

function Ensure-ParagraphFormatting {
  param(
    [System.Xml.XmlElement]$ParagraphPr,
    [string]$Align
  )
  Remove-WChild $ParagraphPr 'numPr'

  $ind = Upsert-WChild $ParagraphPr 'ind'
  Set-WAttr $ind 'firstLine' '0'
  Set-WAttr $ind 'left' '0'
  Set-WAttr $ind 'right' '0'

  $spacing = Upsert-WChild $ParagraphPr 'spacing'
  Set-WAttr $spacing 'before' '0'
  Set-WAttr $spacing 'after' '0'
  Set-WAttr $spacing 'line' '240'
  Set-WAttr $spacing 'lineRule' 'auto'

  $jc = Upsert-WChild $ParagraphPr 'jc'
  Set-WAttr $jc 'val' $Align
}

function Ensure-RunFormatting {
  param([System.Xml.XmlElement]$RunPr)
  $color = Upsert-WChild $RunPr 'color'
  Set-WAttr $color 'val' '000000'
}

function Set-CellText {
  param(
    [System.Xml.XmlElement]$Cell,
    [string]$Text,
    [string]$Align = 'left'
  )

  $tcPrTemplate = $null
  $pPrTemplate = $null
  $rPrTemplate = $null

  $tcPrNode = $Cell.SelectSingleNode('./w:tcPr', $ns)
  if ($tcPrNode) {
    $tcPrTemplate = $tcPrNode.CloneNode($true)
  }

  $pPrNode = $Cell.SelectSingleNode('./w:p/w:pPr', $ns)
  if ($pPrNode) {
    $pPrTemplate = $pPrNode.CloneNode($true)
  }

  $rPrNode = $Cell.SelectSingleNode('.//w:r/w:rPr', $ns)
  if ($rPrNode) {
    $rPrTemplate = $rPrNode.CloneNode($true)
  }

  while ($Cell.HasChildNodes) {
    [void]$Cell.RemoveChild($Cell.FirstChild)
  }

  if ($tcPrTemplate) {
    [void]$Cell.AppendChild($tcPrTemplate)
  }

  $p = New-WElement 'p'
  $pPr = if ($pPrTemplate) { [System.Xml.XmlElement]$pPrTemplate } else { New-WElement 'pPr' }
  Ensure-ParagraphFormatting -ParagraphPr $pPr -Align $Align
  [void]$p.AppendChild($pPr)

  $r = New-WElement 'r'
  $rPr = if ($rPrTemplate) { [System.Xml.XmlElement]$rPrTemplate } else { New-WElement 'rPr' }
  Ensure-RunFormatting -RunPr $rPr
  [void]$r.AppendChild($rPr)

  $t = New-WElement 't'
  Set-XmlSpacePreserve $t
  $t.InnerText = $Text
  [void]$r.AppendChild($t)

  [void]$p.AppendChild($r)
  [void]$Cell.AppendChild($p)
}

function New-BorderNode {
  param(
    [string]$Name,
    [string]$Val,
    [string]$Size = '8',
    [string]$Color = '000000'
  )
  $node = New-WElement $Name
  Set-WAttr $node 'val' $Val
  Set-WAttr $node 'sz' $Size
  Set-WAttr $node 'space' '0'
  Set-WAttr $node 'color' $Color
  return $node
}

function Set-ThreeLineTable {
  param([System.Xml.XmlElement]$Table)

  $tblPr = $Table.SelectSingleNode('./w:tblPr', $ns)
  if (-not $tblPr) {
    $tblPr = New-WElement 'tblPr'
    if ($Table.HasChildNodes) {
      [void]$Table.InsertBefore($tblPr, $Table.FirstChild)
    } else {
      [void]$Table.AppendChild($tblPr)
    }
  }

  Remove-WChild $tblPr 'tblBorders'
  $tblBorders = New-WElement 'tblBorders'
  [void]$tblBorders.AppendChild((New-BorderNode -Name 'top' -Val 'single' -Size '8'))
  [void]$tblBorders.AppendChild((New-BorderNode -Name 'left' -Val 'none' -Size '0'))
  [void]$tblBorders.AppendChild((New-BorderNode -Name 'bottom' -Val 'single' -Size '8'))
  [void]$tblBorders.AppendChild((New-BorderNode -Name 'right' -Val 'none' -Size '0'))
  [void]$tblBorders.AppendChild((New-BorderNode -Name 'insideH' -Val 'none' -Size '0'))
  [void]$tblBorders.AppendChild((New-BorderNode -Name 'insideV' -Val 'none' -Size '0'))
  [void]$tblPr.AppendChild($tblBorders)

  $rows = $Table.SelectNodes('./w:tr', $ns)
  for ($r = 0; $r -lt $rows.Count; $r++) {
    $cells = $rows[$r].SelectNodes('./w:tc', $ns)
    foreach ($cell in $cells) {
      $tcPr = $cell.SelectSingleNode('./w:tcPr', $ns)
      if (-not $tcPr) {
        $tcPr = New-WElement 'tcPr'
        if ($cell.HasChildNodes) {
          [void]$cell.InsertBefore($tcPr, $cell.FirstChild)
        } else {
          [void]$cell.AppendChild($tcPr)
        }
      }
      Remove-WChild $tcPr 'tcBorders'
      if ($r -eq 0) {
        $tcBorders = New-WElement 'tcBorders'
        [void]$tcBorders.AppendChild((New-BorderNode -Name 'bottom' -Val 'single' -Size '4'))
        [void]$tcPr.AppendChild($tcBorders)
      }
    }
  }
}

$tables = $doc.SelectNodes('//w:body/w:tbl', $ns)
if ($tables.Count -lt 11) {
  throw "Unexpected table count: $($tables.Count)"
}

$table9Rows = @(
  @('用例编号', '测试目标与入口', '前置条件', '操作步骤', '观察点', '预期结果'),
  @(
    'TC-01',
    '验证学生端 AI 客服配置读取与问答入口',
    '1. 管理员账号可进入“AI设置”。2. customer_service 工作流已启用。3. 该工作流已绑定有效知识库与默认模型。4. 学生账号可正常登录前台。',
    '1. 管理员进入“AI设置-AI工作流”，确认 customer_service 处于启用状态。2. 学生登录前台首页并打开右下角 AI 客服组件。3. 检查欢迎语、输入提示语、推荐问题和工作流列表是否正常显示。4. 输入“如何请假？”并提交。5. 打开浏览器开发者工具 Network 面板查看请求和响应。',
    '1. 在浏览器开发者工具 Network 面板观察 GET /api/ai/customer-service/config。2. 观察 GET /api/ai/customer-service/apps。3. 观察 POST /api/ai_qa/qa/stream。4. 检查响应头是否为 text/event-stream，返回内容是否按分段持续追加。',
    '页面能够显示管理员配置的欢迎语、输入提示语和推荐问题；提交“如何请假？”后，回答区域逐段输出与请假流程相关的文本；Network 面板中上述三个请求均成功返回，说明客服配置读取与问答链路可用。'
  ),
  @(
    'TC-02',
    '验证学生端 AI 课程助手问答',
    '1. 学生账号可正常登录。2. 系统中至少存在一个已启用课程助手。3. 所选课程助手已绑定有效模型与知识库。',
    '1. 学生进入“AI课程助手”页面。2. 从下拉框选择一个已启用课程助手。3. 在输入框填写课程相关问题。4. 点击“提问”并等待返回结果。',
    '1. 观察课程助手列表是否正常加载。2. 观察 POST /api/ai_qa/qa/stream 的请求体中是否包含 workflow 字段。3. 观察响应头是否为 text/event-stream。',
    '系统能够根据所选工作流返回课程相关问答内容；前端能够持续接收并解析流式数据，学生可以在回答区域直接看到最终结果。'
  ),
  @(
    'TC-03',
    '验证教师创建课程助手与资料入库',
    '1. 教师账号可正常登录且拥有授课课程。2. 管理员已提供基础 course_assistant 工作流。3. 上传文件格式属于系统支持范围。',
    '1. 教师进入“AI课程助手”页面。2. 选择授课课程和基础工作流，填写自定义助手名称并点击“创建”。3. 在课程知识库区域选择文件并上传。4. 刷新页面并查看课程助手与资料列表。',
    '1. 观察 POST /api/ai/teacher/course-assistant/apps 是否创建成功。2. 观察 POST /api/ai/teacher/kb/upload 是否返回上传成功信息。3. 观察页面列表是否出现新助手和新资料。',
    '系统生成教师自定义课程助手，页面列表出现新工作流；上传资料后课程知识库成功新增文档及分块记录，课程助手具备结合课程资料进行问答的条件。'
  )
)

$table10Rows = @(
  @('用例编号', '测试目标与入口', '前置条件', '操作步骤', '观察点', '预期结果'),
  @(
    'TC-04',
    '验证智能教案生成、保存与查看',
    '1. 教师账号可正常登录且拥有授课课程。2. lesson_plan 工作流处于启用状态。3. 课程已存在可解析资料，或教师可先上传资料。',
    '1. 教师进入“智能教案”页面并选择授课课程。2. 上传或选择已解析的课程文档并点击“解析”。3. 在标题框填写“《Python程序设计》第3章 条件语句”，在大纲框填写“教学目标：掌握 if/elif/else 结构；教学重点：条件表达式；教学难点：多分支判断；课堂练习：成绩等级判断”。4. 点击“生成教案”。5. 生成完成后查看、保存并导出教案。',
    '1. 观察 POST /api/ai/teacher/lesson-plan/tasks 是否先创建任务。2. 观察 POST /api/ai_qa/qa/stream 是否持续返回生成内容。3. 观察 PUT /api/ai/teacher/lesson-plan/tasks/{id}/result 是否回写结果。4. 观察任务状态是否由 pending 变为 completed。',
    '系统生成的教案内容应至少包含教学目标、教学重点、教学难点、教学过程、课堂练习、课后作业和评价方式等结构项；任务列表状态更新为已完成；教师能够再次打开结果、保存修改并导出 Markdown 文件。'
  ),
  @(
    'TC-05',
    '验证管理员模型、知识库与工作流治理',
    '1. 管理员账号可正常登录并可访问“AI设置”。2. 外部模型接口参数已准备完成。3. 系统允许上传知识库文档。',
    '1. 管理员进入“AI设置-模型管理”，新增或编辑模型 API。2. 填写 provider、endpoint、model_name、api_key 等参数后点击“测试”，确认返回连通结果。3. 进入“知识库管理”新建“教务服务知识库”并上传制度文档。4. 进入“AI工作流”将 customer_service 工作流绑定该模型和知识库并保存。5. 使用学生账号重新打开 AI 客服页面，检查新配置是否生效。',
    '1. 观察模型测试弹窗是否返回成功信息或明确错误提示。2. 观察知识库保存、文档上传和工作流绑定后列表是否即时刷新。3. 观察学生端 AI 客服页面读取到的工作流与管理员端配置是否一致。',
    '模型测试能够给出明确结果；知识库、文档和工作流保存后可在管理端列表中查看到对应记录；学生端重新进入 AI 客服后能够读取最新工作流配置，说明管理端治理链路完整可用。'
  )
)

$table11Rows = @(
  @('用例编号', '对应测试目标', '关键触发链路', '实际结果说明', '结论'),
  @(
    'TC-01',
    '学生端 AI 客服配置读取与问答入口',
    'GET /api/ai/customer-service/config；GET /api/ai/customer-service/apps；POST /api/ai_qa/qa/stream',
    '管理员完成 customer_service 工作流绑定后，学生端打开 AI 客服页面即可加载欢迎语、推荐问题和工作流列表；在浏览器开发者工具 Network 面板中可看到 GET /api/ai/customer-service/config、GET /api/ai/customer-service/apps 和 POST /api/ai_qa/qa/stream 三条请求；提交“如何请假？”后，/api/ai_qa/qa/stream 以 text/event-stream 返回分段内容，回答区域逐段显示结果。',
    '通过'
  ),
  @(
    'TC-02',
    '学生端 AI 课程助手问答',
    'POST /api/ai_qa/qa/stream',
    '学生进入 AI 课程助手页面后，可正常读取已启用助手列表；选择课程助手并提交课程相关问题后，请求体中包含 workflow 字段，前端能够持续接收并解析 text/event-stream 数据，最终在回答区域显示课程问答结果。',
    '通过'
  ),
  @(
    'TC-03',
    '教师创建课程助手与资料入库',
    'POST /api/ai/teacher/course-assistant/apps；POST /api/ai/teacher/kb/upload',
    '教师选择课程并基于基础工作流创建自定义课程助手后，页面表格能够显示新助手；上传课程资料后，课程知识库对应新增文档及分块记录，说明课程助手已具备结合教师资料开展问答的条件。',
    '通过'
  ),
  @(
    'TC-04',
    '智能教案生成、保存与查看',
    'POST /api/ai/teacher/lesson-plan/tasks；POST /api/ai_qa/qa/stream；PUT /api/ai/teacher/lesson-plan/tasks/{id}/result',
    '教师选择课程资料并完成解析后，按“《Python程序设计》第3章 条件语句”的标题与给定大纲创建任务，系统先写入教案任务记录，再返回流式生成内容，并在结束后完成结果回写；任务状态由 pending 更新为 completed，生成结果中可见教学目标、教学重点、教学难点、教学过程、课堂练习、课后作业和评价方式等结构项，随后可执行保存修改与导出 Markdown 操作。',
    '通过'
  ),
  @(
    'TC-05',
    '管理员模型、知识库与工作流治理',
    '管理员端模型测试、知识库保存、工作流绑定与前台读取链路',
    '管理员在模型管理页面填写接口参数并点击“测试”后，弹窗能够返回明确的连通结果；新建知识库并上传文档后，列表新增对应记录；将模型和知识库绑定到 customer_service 工作流并保存后，学生端重新打开 AI 客服页面即可读取更新后的工作流配置，说明模型配置、知识组织和业务入口之间的治理链路已经打通。',
    '通过'
  )
)

function Apply-TableData {
  param(
    [System.Xml.XmlElement]$Table,
    [object[]]$Rows,
    [int[]]$CenterBodyColumns = @()
  )

  $rowNodes = $Table.SelectNodes('./w:tr', $ns)
  if ($rowNodes.Count -ne $Rows.Count) {
    throw "Row count mismatch. Expected $($Rows.Count), actual $($rowNodes.Count)"
  }

  for ($r = 0; $r -lt $rowNodes.Count; $r++) {
    $cellNodes = $rowNodes[$r].SelectNodes('./w:tc', $ns)
    if ($cellNodes.Count -ne $Rows[$r].Count) {
      throw "Cell count mismatch at row $r. Expected $($Rows[$r].Count), actual $($cellNodes.Count)"
    }

    for ($c = 0; $c -lt $cellNodes.Count; $c++) {
      $align = if ($r -eq 0) { 'center' } elseif ($CenterBodyColumns -contains $c) { 'center' } else { 'left' }
      Set-CellText -Cell $cellNodes[$c] -Text $Rows[$r][$c] -Align $align
    }
  }

  Set-ThreeLineTable -Table $Table
}

Apply-TableData -Table $tables[8] -Rows $table9Rows -CenterBodyColumns @(0)
Apply-TableData -Table $tables[9] -Rows $table10Rows -CenterBodyColumns @(0)
Apply-TableData -Table $tables[10] -Rows $table11Rows -CenterBodyColumns @(0, 4)

$doc.Save($docPath)

$zipPath = [System.IO.Path]::ChangeExtension($OutputDocx, '.zip')
if (Test-Path $zipPath) {
  Remove-Item -LiteralPath $zipPath -Force
}
if (Test-Path $OutputDocx) {
  Remove-Item -LiteralPath $OutputDocx -Force
}

Compress-Archive -Path (Join-Path $UnzipDir '*') -DestinationPath $zipPath -Force
Move-Item -LiteralPath $zipPath -Destination $OutputDocx -Force

Write-Output "Updated document.xml: $docPath"
Write-Output "Created docx: $OutputDocx"
