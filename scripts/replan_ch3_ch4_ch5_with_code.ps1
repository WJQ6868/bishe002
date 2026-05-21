$ErrorActionPreference = 'Stop'

$root = 'D:\bishe\one'
$srcDocx = 'C:\Users\wangj\Desktop\2405273202-王佳齐-AI赋能的高校教务系统(ai) -.docx'
$zipPath = Join-Path $root 'tmp_replan345_apply.zip'
$unzipDir = Join-Path $root 'tmp_replan345_apply_unzip'
$updatedZip = Join-Path $root 'tmp_replan345_apply_updated.zip'
$updatedDocx = Join-Path $root 'tmp_replan345_apply_updated.docx'

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
$body = $doc.SelectSingleNode('//w:body', $ns)

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

function Find-P {
    param([string]$Text)
    foreach ($node in $body.ChildNodes) {
        if ($node.LocalName -eq 'p' -and (Get-Text $node) -eq $Text) {
            return $node
        }
    }
    return $null
}

function New-P-Like {
    param([System.Xml.XmlNode]$Template, [string]$Text)
    $p = $Template.CloneNode($true)
    Set-Text $p $Text
    return $p
}

function Insert-Paragraphs-After {
    param([System.Xml.XmlNode]$Anchor, [string[]]$Texts)
    $template = $Anchor
    $last = $Anchor
    foreach ($text in $Texts) {
        $p = New-P-Like $template $text
        [void]$body.InsertAfter($p, $last)
        $last = $p
    }
}

function Set-Table-Data {
    param([System.Xml.XmlNode]$Table, [object[]]$Data)
    $rows = @($Table.SelectNodes('./w:tr', $ns))
    while ($rows.Count -lt $Data.Count) {
        $newRow = $rows[-1].CloneNode($true)
        [void]$Table.AppendChild($newRow)
        $rows = @($Table.SelectNodes('./w:tr', $ns))
    }
    for ($r = 0; $r -lt $Data.Count; $r++) {
        $cells = @($rows[$r].SelectNodes('./w:tc', $ns))
        for ($c = 0; $c -lt [Math]::Min($cells.Count, $Data[$r].Count); $c++) {
            Set-Text $cells[$c] $Data[$r][$c]
        }
    }
}

$changed = 0

$paragraphReplacements = @{
    '本章集中说明AI模块的系统设计关系：不同角色由哪些页面承接，场景请求由哪些接口调度，后台资源如何持续支撑问答和生成。先明确模块关系，再展开知识组织、检索增强和表结构设计，可以使本章设计内容更加集中。' =
    '本章集中说明系统设计内容，重点回答AI能力由哪些页面承接、通过哪些接口调度、由哪些核心类和数据表支撑。第三章只讨论模块组织、工作流、知识资源、检索生成和数据结构之间的关系；具体页面交互、代码调用和运行结果放在第四章实现部分展开。';

    '从系统设计看，项目没有把AI处理为脱离教务业务的独立模块，而是将其嵌入原有业务场景中，详情见图 3-1 AI模块架构、代码组织与接口关系图。学生主要从客服或课程问答入口进入，教师使用课程助手和智能教案，管理员维护模型、知识库和工作流。三类入口面向的角色不同，但底层复用同一套AI资源底座，从而降低后续扩展新场景的成本。' =
    '从系统设计看，项目没有把AI处理为脱离教务业务的独立模块，而是将其嵌入原有业务场景中，详情见图 3-1 AI模块架构、代码组织与接口关系图。学生主要从AI客服或课程问答入口进入，教师使用课程助手和智能教案，管理员维护模型、知识库和工作流。三类入口面向的角色不同，但底层共同依赖统一问答接口、工作流配置和知识库数据。';

    '图3-1将AI模块从角色入口到数据表的关系划分为五层。左侧角色场景层说明学生、教师、管理员分别从咨询、课程资料和配置治理进入；前端页面组织层对应AdminAIConfig.vue、CourseAssistant.vue、LessonPlan.vue等页面，负责将不同角色的操作分配到清晰入口；后端接口收口层通过/admin/ai/*、/ai/course-assistant/*、/ai/teacher/*和/ai_qa/qa/stream等接口统一接入请求；AI能力编排层完成工作流选择、模型优先级判断、文档抽取分块、TF-IDF检索和SSE流式输出；数据与资源层保存模型API、知识库、文档分块、工作流、教案任务和使用日志。通过这种分层，后台治理、前台场景和统一问答链路能够保持清晰边界，后续新增AI入口时也可以沿用同一结构。' =
    '图3-1将AI模块从角色入口到数据表的关系划分为五层。角色场景层说明学生、教师、管理员分别从咨询、课程资料和配置治理进入；前端页面组织层对应StudentAIChat.vue、AdminAIConfig.vue、CourseAssistant.vue、StudentCourseAssistant.vue和LessonPlan.vue等组件；后端接口收口层通过/admin/ai/*、/ai/*和/ai_qa/qa/stream统一接入请求；AI能力编排层完成工作流选择、模型优先级判断、文档抽取分块、TF-IDF检索和SSE流式输出；数据与资源层保存模型API、知识库、文档分块、工作流、教案任务和使用日志。表3-1进一步列出前端组件、接口封装、后端路由与核心类之间的对应关系，第四章的实现说明即围绕这些关系展开。';

    '数据库设计这里，重点不是单纯把表建出来，而是把AI功能运行过程中会产生的不同类型数据分清楚。现有教务数据继续承载用户、课程、选课、请假和办事流程；AI扩展数据则专门负责模型配置、知识资源、文档分块、工作流、任务结果和使用日志。两类数据分层存放以后，结构会清楚很多，后期维护也不容易乱。' =
    '数据库设计的重点不是单纯列出数据表，而是明确AI功能运行过程中不同类型数据的职责。现有教务数据继续承载用户、课程、选课、请假和办事流程；AI扩展数据负责模型配置、知识资源、文档分块、工作流、任务结果和使用日志。两类数据分层存放后，系统结构更加清晰，也便于后续维护。';

    '再往细里看，模型表解决的是“调用谁”，知识库和文档表解决的是“依据什么回答”，工作流表解决的是“在哪个场景调用”，任务与日志表则负责把生成过程和使用结果留下来。这样安排不是为了把表做多，而是为了让AI能力真正具备可配置、可追踪、可复用的基础。后面的ER图 3-2 AI核心数据ER图和表 3-1 AI核心数据表设计说明结构说明，也正是围绕这条思路展开的。' =
    '进一步看，模型表解决“调用谁”的问题，知识库和文档表解决“依据什么回答”的问题，工作流表解决“在哪个场景调用”的问题，任务与日志表负责保存生成过程和使用结果。这样的安排不是为了增加表数量，而是为了让AI能力具备可配置、可追踪和可复用的基础。后面的图 3-2 AI核心数据ER图和表 3-2 AI核心数据表设计说明正是围绕这条思路展开。';

    '本章在第三章系统设计的基础上，围绕项目中已经落地的页面、接口和数据对象说明实现过程。为避免后续模块重复解释同一批组件，先说明实现层的基础关系：前端侧主要由StudentAIChat.vue、CourseAssistant.vue、StudentCourseAssistant.vue、LessonPlan.vue和AdminAIConfig.vue承接交互，接口封装集中在ai.ts、aiPortal.ts和adminAi.ts中。' =
    '本章不再重复第三章中的设计关系，而是按照项目中的实际页面和代码说明实现过程。每个模块均按“用户进入页面—执行交互动作—前端调用接口—后端处理数据—页面返回结果”的顺序展开，使界面描述和流程描述分开呈现。';

    '后端侧主要由ai_qa.py、ai_portal.py和admin_ai.py协同完成。ai_qa.py提供统一的/ai_qa/qa/stream流式问答入口，负责模型选择、知识库检索、Prompt组装和SSE返回；ai_portal.py负责学生端和教师端的场景接口，包括客服配置读取、课程助手、课程资料上传和教案任务管理；admin_ai.py负责管理员侧模型API、知识库、工作流和客服参数配置。' =
    '第四章中的代码片段只截取关键逻辑，样式代码、普通表单校验和提示信息不再展开。AI客服重点展示SSE流式问答调用，AI课程助手重点展示教师复制工作流和课程知识库接入，智能教案重点展示任务创建、流式生成和结果回写，管理端AI配置重点展示模型、知识库与工作流配置如何被前台业务读取。';

    '数据层围绕AiModelApi、AiKnowledgeBase、AiKbDocument、AiKbChunk、AiWorkflowApp、AiLessonPlanTask和AiUsageLog等对象展开。其中，模型表决定“调用谁”，知识库和分块表决定“依据什么回答”，工作流表决定“在哪个场景调用”，教案任务和日志表负责保存生成过程与使用结果。后续几个模块的实现，均在这套组件、接口和数据对象基础上展开。' =
    '为便于阅读，本章保留各模块的界面截图和实现流程图。流程图用于说明关键调用链路，截图用于说明最终页面效果，代码片段用于说明项目中真正承担核心功能的调用位置。';

    'AI客服的实际入口由StudentAIChat.vue组件承担，主要嵌入在学生端页面中。组件加载后并不是直接进入问答，而是先通过aiPortal.ts读取客服展示配置和启用工作流：/ai/customer-service/config用于取得欢迎语、推荐问题和输入提示语，目的是让页面展示内容可以由后台维护；/ai/customer-service/apps用于取得当前启用的客服工作流，目的是让前端知道本次咨询应绑定哪一个业务场景。完成这两步后，组件会创建默认会话，并把欢迎语写入第一条AI消息。用户的新建会��、删除会话和重命名会话在前端完成，历史会话保存在localStorage中，页面刷新后仍能恢复最近的咨询记录。' =
    'AI客服的界面入口由StudentAIChat.vue组件承担，主要嵌入在学生端页面右下角。用户打开页面后，组件首先加载客服欢迎语、推荐问题和当前启用的客服工作流，然后创建默认会话并显示第一条AI欢迎消息。用户可以直接输入问题，也可以点击推荐问题发起咨询；新建会话、删除会话、重命名会话等交互在前端完成，历史会话通过localStorage保存。';

    '用户提交问题时，前端先把用户消息追加到当前会话，再生成一条空AI消息作为流式占位，随后通过ai.ts中的streamQA方法向/ai_qa/qa/stream发送POST请求。这里使用统一问答接口，是因为AI客服、课程助手和智能教案都需要复用模型解析、知识检索、上下文组装和SSE返回能力，如果每个页面单独写一套调用逻辑，后续维护会很分散。请求体中的user_id、question、workflow等参数用于告诉后端“谁在问、问什么、按哪个场景处理”。后端收到请求后，根据workflow读取AiWorkflowApp，再按优先级解析模型配置，收集可用知识库，组装Prompt并调用上游模型，最后将结果以SSE片段持续返回，详情见图4-1 AI客服核心处理流程。' =
    '在交互实现上，用户提交问题后，前端先把用户消息追加到当前会话，再创建一条空AI消息作为流式占位，随后调用ai.ts中的streamQA方法访问/ai_qa/qa/stream。该接口采用SSE返回结果，前端每接收到一个分段内容就追加到当前AI消息中，因此页面能够呈现逐步输出的效果。代码4-1为前端流式读取的关键代码。';

    '从界面交互看，AI客服不仅提供输入框，还支持会话列表、推荐问题点击、Markdown内容展示和流式回答追加。推荐问题被点击后会直接进入提问流程，流式返回时前端边接收边拼接文本，用户能够看到回答逐步展开。该实现将页面展示、配置读取和统一问答接口分开处理，既便于管理员调整客服内容，也便于前端保持稳定的交互体验，详情见图4-2 AI客服界面截图。' =
    '后端实现集中在ai_qa.py中。/ai_qa/qa/stream接收问题后，根据workflow读取AiWorkflowApp，再解析模型配置、收集知识库编号、构造Prompt并返回StreamingResponse。这样一来，AI客服页面不需要直接处理模型密钥、知识库编号和上游接口细节，只需要提交问题和工作流编码即可。代码4-2为统一问答接口的核心实现，图4-1展示AI客服流式问答实现流程，图4-2展示AI客服界面截图。';

    'AI课程助手的实现分为教师配置和学生使用两条路径。教师端CourseAssistant.vue进入页面后，会通过aiPortal.ts加载本人课程、管理员提供的基础课程助手以及教师已经创建的自定义助手；学生端StudentCourseAssistant.vue则主要加载可用课程助手并提供提问入口。教师如果需要为某门课程建立专属助手，会调用/ai/teacher/course-assistant/apps，在基础工作流之上复制出新的课程助手实例，并写入课程、所有者和工作流编码等信息。这样做的原因是课程助手既要复用统一AI底座，又要保留教师和课程维度的差异。' =
    'AI课程助手由教师端CourseAssistant.vue和学生端StudentCourseAssistant.vue共同实现。教师进入页面后，可以查看本人课程、基础课程助手和已有自定义助手；当教师为某门课程创建专属助手时，前端调用/ai/teacher/course-assistant/apps，后端在基础course_assistant工作流之上复制出新的AiWorkflowApp，并写入教师、课程和模型知识库绑定关系。代码4-3展示教师复制课程助手工作流的关键逻辑。';

    '课程资料上传由/ai/teacher/kb/upload等接口处理。后端首先校验当前教师是否拥有该课程，随后准备课程知识库对象，再完成文件保存、文本抽取和分块重建。资料上传后不会只作为附件存在，而是会写入ai_kb_documents和ai_kb_chunks等表，转化为后续可检索的知识片段。师生发起课程问答时，请求会携带课程标识和所选助手编码，统一问答接口据此收集基础知识库和课程知识库，让回答尽量贴近对应课程资料，而不是停留在泛化解释。' =
    '资料上传是课程助手实现中的关键环节。教师上传课程文档时，/ai/teacher/kb/upload会先校验课程归属，再准备课程知识库对象，随后保存文件、抽取文本并重建分块。资料进入ai_kb_documents和ai_kb_chunks后，课程问答请求即可携带course_id和workflow进入统一问答接口，系统会同时收集基础知识库和课程知识库，从而使回答更贴近该门课程资料。';

    '从实际操作看，教师可以在页面中创建、重命名、删除课程助手，也可以持续上传或替换课程资料；学生只需要选择课程助手并输入问题即可。图4-3展示的是课程助手的实现流程：基础课程助手先由管理员准备，教师再复制并绑定到自己的课程，学生或教师提问时，系统合并工作流知识库与课程知识库进行检索，最后由统一问答接口返回结果。图4-4展示课程助手界面。通过这种实现，课程答疑从“通用聊天”转为“围绕课程资料的定向问答”[15]。' =
    '在学生端，页面只保留助手选择和提问入口，降低使用复杂度；在教师端，页面提供助手创建、资料上传、资料替换和资料删除等操作。图4-3展示AI课程助手资料与问答实现流程，图4-4展示课程助手界面。该模块的实现重点在于把教师维护资料、学生发起提问和后端知识检索连成同一条运行链路。';

    '智能教案模块由LessonPlan.vue承载，采用“任务先创建、内容再生成、结果再回写”的实现方式。教师在页面中先选择课程，填写教案标题和大纲，并选择或解析课程资料；点击生成后，前端先调用/ai/teacher/lesson-plan/tasks创建任务记录。这个接口的作用不是生成正文，而是把课程、标题、大纲、知识库和模型等上下文先保存到AiLessonPlanTask中，使后续生成过程有明确的任务编号和状态记录。这样即使页面刷新或网络短暂波动，系统也能依据任务记录继续追踪本次教案生成。' =
    '智能教案由LessonPlan.vue实现。教师在页面中先选择课程，填写教案标题和大纲，并选择或解析课程资料；点击生成后，前端并不直接等待模型返回，而是先调用/ai/teacher/lesson-plan/tasks创建AiLessonPlanTask任务。该任务保存课程、标题、大纲、知识库和模型等上下文，使本次生成具备明确的任务编号和状态记录。';

    '任务创建完成后，前端会根据标题、课程信息、教师填写的大纲和已解析资料组织生成提示词，再通过streamQA调用/ai_qa/qa/stream，并指定lesson_plan工作流。这里继续复用统一流式问答接口，是因为教案生成同样需要模型选择、知识检索、上下文组装和SSE返回，只是输出内容从短问答变成结构化教案。模型返回过程中，前端实时拼接生成内容；生成结束后，再调用/ai/teacher/lesson-plan/tasks/{id}/result把正文、状态和完成时间写回数据库。如果中途失败，任务状态也会保留，便于教师重新处理。' =
    '任务创建后，前端根据标题、课程信息、大纲和解析资料组织提示词，再通过streamQA调用/ai_qa/qa/stream，并指定lesson_plan工作流。模型返回过程中，前端实时拼接教案内容；生成结束后，再调用/ai/teacher/lesson-plan/tasks/{id}/result写回结果、状态和完成时间。代码4-4展示LessonPlan.vue中的核心实现。';

    '生成完成后，教师可以在任务列表中重新打开历史教案，对生成结果进行人工修改，并将最终内容导出为Markdown文件。也就是说，智能教案不是一次性把文本显示在页面上，而是把“任务创建、流式生成、结果回写、人工编辑、文件导出”串成了完整实现链路，详情见图4-5智能教案任务化生成流程和图4-6智能教案界面。这样的处理更接近教师真实备课习惯，AI负责形成初稿和整理材料，最终内容仍由教师审校和调整[17]。' =
    '生成完成后，教师可以在任务列表中重新打开历史教案，对生成结果进行人工修改，并将最终内容导出为Markdown文件。该模块并非只显示一次性文本，而是形成“任务创建、流式生成、结果回写、人工编辑、文件导出”的完整实现链路。图4-5展示智能教案任务化实现流程，图4-6展示智能教案界面。';

    '管理端AI配置由AdminAIConfig.vue实现，是整套AI能力能够运行起来的后台入口。管理员在页面中分别维护模型接口、知识库、工作流应用和客服展示参数。模型管理对应/admin/ai/model-apis等接口，用来保存provider、endpoint、model_name、api_key、启用状态和默认模型标记，并通过/admin/ai/model-apis/test进行连通性测试。知识库管理对应/admin/ai/workflows/knowledge-bases及其文档上传接口，上传或手工录入的资料会经过文本抽取和分块处理后进入可检索状态，详情见图4-7管理员AI配置界面。' =
    '管理端AI配置由AdminAIConfig.vue实现。管理员进入页面后，可以分别维护模型接口、知识库、工作流应用和客服展示参数。模型管理区域调用/admin/ai/model-apis保存provider、endpoint、model_name、api_key、启用状态和默认模型标记，并通过/admin/ai/model-apis/test进行连通性测试；知识库区域调用/admin/ai/workflows/knowledge-bases及其文档接口，使上传或手工录入的资料经过文本抽取和分块后进入可检索状态。';

    '工作流管理对应/admin/ai/workflows/apps接口，管理员可以把模型、知识库和业务类型绑定成customer_service、course_assistant、lesson_plan等可调用入口。前台页面之所以能够只传workflow编码，就是因为这些复杂配置已经在管理端完成。客服参数则通过/admin/ai/customer-service/settings维护欢迎语、推荐问题和输入提示，前端只负责读取和展示。表4-1整理了各AI模块在项目中的实现入口、关键接口和后端处理对象。' =
    '工作流管理对应/admin/ai/workflows/apps接口，管理员可以把模型、知识库和业务类型绑定成customer_service、course_assistant、lesson_plan等可调用入口。前台页面之所以只需要传workflow编码，是因为模型、知识库和场景关系已经在管理端完成绑定。客服参数通过/admin/ai/customer-service/settings维护欢迎语、推荐问题和输入提示，前端读取后直接渲染。';

    '从实现链路看，管理端完成配置后，学生端和教师端会在各自页面按场景读取配置并调用统一接口，中间不需要重复处理模型密钥、知识库编号和接口地址。这样处理后，模型具备可替换性，知识库具备可维护性，工作流也可以按场景启停。管理端将“配置、测试、业务调用”连接成一条实际可运行的链路，而不只是停留在配置页面展示。' =
    '从实现链路看，管理端完成配置后，学生端和教师端会在各自页面按场景读取配置并调用统一接口，中间不需要重复处理模型密钥、知识库编号和接口地址。这样处理后，模型具备可替换性，知识库具备可维护性，工作流也可以按场景启停。图4-7展示管理员AI配置界面。';

    '本文的测试目标是验证系统主要功能链路是否能够按照设计流程稳定运行，并使测试过程具备可复现性。测试范围包括管理端模型配置与连通性测试、知识库文档上传与分块入库、AI客服配置读取与流式问答、教师创建课程助手、学生使用课程助手提问、智能教案任务创建与结果回写等内容。测试方法以本地环境下的页面操作、浏览器网络请求观察、接口返回结果核对和数据库记录复查为主，重点说明“从哪个角色进入、点击哪些按钮、触发哪些接口、在哪里查看结果”。' =
    '本文的测试目标是验证第三章设计关系和第四章实现链路是否能够稳定运行，并使测试过程具备可复现性。第五章不再介绍组件、接口和核心类之间的设计关系，而是围绕实际操作结果进行验证。测试范围包括管理端模型配置与连通性测试、知识库文档上传与分块入库、AI客服配置读取与流式问答、教师创建课程助手、学生使用课程助手提问、智能教案任务创建与结果回写等内容。测试方法以页面操作、浏览器网络请求观察、接口返回结果核对和数据库记录复查为主。';

    '在测试数据方面，本地数据库已经包含5条模型API配置、4个知识库、3份知识库文档、86个知识分块、4个工作流应用、4条教案任务记录和4条AI使用日志。测试过程中重点关注三个层面的结果：第一，前端页面是否能够正确加载配置并提交用户操作；第二，后端接口是否能够完成工作流查找、知识库编号收集、Prompt组装和结果返回；第三，数据库是否能够保存模型配置、知识库文档、文本分块、工作流应用和教案任务等关键数据[19]。通过上述方法，可以较全面地观察系统功能是否形成有效闭环。' =
    '在测试数据方面，本地数据库已经包含5条模型API配置、4个知识库、3份知识库文档、86个知识分块、4个工作流应用、4条教案任务记录和4条AI使用日志。测试过程中重点关注三个层面的结果：第一，前端页面是否能够正确加载配置并提交用户操作；第二，后端接口是否能够完成工作流查找、知识库编号收集、Prompt组装和结果返回；第三，数据库是否能够保存模型配置、知识库文档、文本分块、工作流应用和教案任务等关键数据[19]。接口和数据表名称在本章只作为测试观察点使用，具体关系已在第三章和第四章说明。';

    '按照上述用例执行后，系统主要AI链路能够按照设计流程运行，详情见表5-2 AI核心功能测试结果。客服配置读取与统一问答接口联调通过，说明工作流配置和问答执行之间的连接有效；课程助手创建与资料上传通过，说明管理员提供的基础能力可以继续向教师课程场景分发；教案任务创建与结果回写通过，说明系统不仅可以生成文本，还能够对生成行为进行结构化管理。' =
    '按照上述用例执行后，系统主要AI链路能够按预期运行，详情见表5-2 AI核心功能测试结果。客服配置读取与统一问答接口联调通过，说明工作流配置和问答执行之间的连接有效；课程助手创建与资料上传通过，说明管理员提供的基础能力可以继续向教师课程场景分发；教案任务创建与结果回写通过，说明系统不仅可以生成文本，还能够对生成行为进行结构化管理。';
}

foreach ($p in $doc.SelectNodes('//w:body/w:p', $ns)) {
    $text = Get-Text $p
    if ($paragraphReplacements.ContainsKey($text)) {
        Set-Text $p $paragraphReplacements[$text]
        $changed++
    }
}

# Update captions and figure/table list entries.
$captionMap = @{
    '图4-1 AI客服核心处理流程' = '图4-1 AI客服流式问答实现流程';
    '图4-3 AI课程助手核心处理流程' = '图4-3 AI课程助手资料与问答实现流程';
    '图 4-5智能教案任务化生成流程' = '图 4-5 智能教案任务化实现流程';
    '表 3-1 AI核心数据表设计说明' = '表 3-2 AI核心数据表设计说明';
    '表 3-1 AI核心数据表设计说明15' = '表 3-2 AI核心数据表设计说明15';
    '图4-1 AI客服核心处理流程17' = '图4-1 AI客服流式问答实现流程17';
    '图4-3 AI课程助手核心处理流程19' = '图4-3 AI课程助手资料与问答实现流程19';
    '图 4-5 智能教案任务化生成流程20' = '图 4-5 智能教案任务化实现流程20';
}
foreach ($p in $doc.SelectNodes('//w:body/w:p', $ns)) {
    $text = Get-Text $p
    if ($captionMap.ContainsKey($text)) {
        Set-Text $p $captionMap[$text]
        $changed++
    }
}

# Move current table 4-1 into Chapter 3 as table 3-1.
$oldTableCaption = Find-P '表4-1 AI模块实现入口与接口对应关系'
if ($oldTableCaption -ne $null) {
    $oldTable = $oldTableCaption.NextSibling
    while ($oldTable -ne $null -and $oldTable.LocalName -ne 'tbl') { $oldTable = $oldTable.NextSibling }
    $target = Find-P '图3-1将AI模块从角色入口到数据表的关系划分为五层。角色场景层说明学生、教师、管理员分别从咨询、课程资料和配置治理进入；前端页面组织层对应StudentAIChat.vue、AdminAIConfig.vue、CourseAssistant.vue、StudentCourseAssistant.vue和LessonPlan.vue等组件；后端接口收口层通过/admin/ai/*、/ai/*和/ai_qa/qa/stream统一接入请求；AI能力编排层完成工作流选择、模型优先级判断、文档抽取分块、TF-IDF检索和SSE流式输出；数据与资源层保存模型API、知识库、文档分块、工作流、教案任务和使用日志。表3-1进一步列出前端组件、接口封装、后端路由与核心类之间的对应关系，第四章的实现说明即围绕这些关系展开。'
    if ($target -ne $null -and $oldTable -ne $null) {
        Set-Text $oldTableCaption '表 3-1 AI功能组件、接口与核心类关系'
        $intro = New-P-Like $target '表3-1在图3-1的基础上进一步对应前端组件、接口封装、后端路由和核心数据对象。这样安排后，第三章集中说明设计关系，第四章只围绕这些关系说明具体实现，避免界面描述和设计说明混在一起。'
        [void]$body.InsertAfter($intro, $target)
        [void]$body.InsertAfter($oldTableCaption, $intro)
        [void]$body.InsertAfter($oldTable, $oldTableCaption)
        Set-Table-Data $oldTable @(
            @('模块', '前端组件/接口封装', '关键接口', '后端路由与核心类', '设计关系'),
            @('AI客服', 'StudentAIChat.vue；aiPortal.ts；ai.ts', '/ai/customer-service/config；/ai/customer-service/apps；/ai_qa/qa/stream', 'ai_portal.py；ai_qa.py；AiWorkflowApp；AiModelApi；AiKnowledgeBase；AiKbChunk', '读取客服配置，并通过统一问答链路流式返回咨询答案'),
            @('AI课程助手', 'CourseAssistant.vue；StudentCourseAssistant.vue；aiPortal.ts', '/ai/teacher/course-assistant/apps；/ai/teacher/kb/upload；/ai_qa/qa/stream', 'ai_portal.py；ai_qa.py；AiWorkflowApp；AiKnowledgeBase；AiKbDocument；AiKbChunk', '教师维护课程助手和资料，学生按课程发起定向问答'),
            @('智能教案', 'LessonPlan.vue；aiPortal.ts；ai.ts', '/ai/teacher/lesson-plan/tasks；/ai_qa/qa/stream；/ai/teacher/lesson-plan/tasks/{id}/result', 'ai_portal.py；ai_qa.py；AiLessonPlanTask；AiWorkflowApp；AiModelApi', '任务先落库，生成后回写结果并支持编辑导出'),
            @('管理端配置', 'AdminAIConfig.vue；adminAi.ts', '/admin/ai/model-apis；/admin/ai/workflows/apps；/admin/ai/customer-service/settings', 'admin_ai.py；AiModelApi；AiKnowledgeBase；AiWorkflowApp', '统一维护模型、知识库、工作流和客服展示参数')
        )
        $changed++
    }
}

# Update table list: add new table 3-1, remove old table 4-1 list entry.
$tableListAnchor = Find-P '表 3-2 AI核心数据表设计说明15'
if ($tableListAnchor -ne $null) {
    $prev = $tableListAnchor.PreviousSibling
    $already = $false
    foreach ($p in $doc.SelectNodes('//w:body/w:p', $ns)) {
        if ((Get-Text $p) -eq '表 3-1 AI功能组件、接口与核心类关系14') { $already = $true }
    }
    if (-not $already) {
        $newEntry = New-P-Like $tableListAnchor '表 3-1 AI功能组件、接口与核心类关系14'
        [void]$body.InsertBefore($newEntry, $tableListAnchor)
        $changed++
    }
}
foreach ($p in @($doc.SelectNodes('//w:body/w:p', $ns))) {
    if ((Get-Text $p) -eq '表4-1 AI模块实现入口与接口对应关系21' -or (Get-Text $p) -eq '表4-1 三个AI模块的功能对比21') {
        [void]$body.RemoveChild($p)
        $changed++
    }
}

# Insert code snippets after corresponding implementation paragraphs.
$anchor = Find-P '在交互实现上，用户提交问题后，前端先把用户消息追加到当前会话，再创建一条空AI消息作为流式占位，随后调用ai.ts中的streamQA方法访问/ai_qa/qa/stream。该接口采用SSE返回结果，前端每接收到一个分段内容就追加到当前AI消息中，因此页面能够呈现逐步输出的效果。代码4-1为前端流式读取的关键代码。'
if ($anchor -ne $null -and (Get-Text $anchor.NextSibling) -ne '代码4-1 前端SSE流式读取关键代码') {
    Insert-Paragraphs-After $anchor @(
        '代码4-1 前端SSE流式读取关键代码',
        'const res = await fetch(`${API_BASE}/ai_qa/qa/stream`, { method: ''POST'', headers: buildHeaders(), body: JSON.stringify(payload) })',
        'const reader = res.body?.getReader(); const decoder = new TextDecoder(''utf-8''); let buffer = '''';',
        'while (true) { const { value, done } = await reader.read(); if (done) break; buffer += decoder.decode(value, { stream: true }); parseSseChunk(buffer, onChunk); }'
    )
    $changed++
}

$anchor = Find-P '后端实现集中在ai_qa.py中。/ai_qa/qa/stream接收问题后，根据workflow读取AiWorkflowApp，再解析模型配置、收集知识库编号、构造Prompt并返回StreamingResponse。这样一来，AI客服页面不需要直接处理模型密钥、知识库编号和上游接口细节，只需要提交问题和工作流编码即可。代码4-2为统一问答接口的核心实现，图4-1展示AI客服流式问答实现流程，图4-2展示AI客服界面截图。'
if ($anchor -ne $null -and (Get-Text $anchor.NextSibling) -ne '代码4-2 后端统一问答接口关键代码') {
    Insert-Paragraphs-After $anchor @(
        '代码4-2 后端统一问答接口关键代码',
        '@router.post("/qa/stream")',
        'async def stream_qa(request: QARequest, db: AsyncSession = Depends(get_db)):',
        '    app = await _load_workflow_app(db, request.workflow); model = await _resolve_model(db, request.model, app)',
        '    kb_ids = await _collect_kb_ids(db, app, request.course_id); prompt = await _build_prompt(db, question, kb_ids)',
        '    return StreamingResponse(gen(), media_type="text/event-stream")'
    )
    $changed++
}

$anchor = Find-P 'AI课程助手由教师端CourseAssistant.vue和学生端StudentCourseAssistant.vue共同实现。教师进入页面后，可以查看本人课程、基础课程助手和已有自定义助手；当教师为某门课程创建专属助手时，前端调用/ai/teacher/course-assistant/apps，后端在基础course_assistant工作流之上复制出新的AiWorkflowApp，并写入教师、课程和模型知识库绑定关系。代码4-3展示教师复制课程助手工作流的关键逻辑。'
if ($anchor -ne $null -and (Get-Text $anchor.NextSibling) -ne '代码4-3 教师课程助手工作流复制关键代码') {
    Insert-Paragraphs-After $anchor @(
        '代码4-3 教师课程助手工作流复制关键代码',
        'base_app = await db.execute(select(AiWorkflowApp).where(AiWorkflowApp.code == base_code, AiWorkflowApp.type == "course_assistant"))',
        'new_app = AiWorkflowApp(code=f"tca-{current_user.id}-{int(time.time())}", type="course_assistant", name=name.strip(), owner_user_id=current_user.id, course_id=course_id)',
        'new_app.knowledge_base_id = base_app.knowledge_base_id; new_app.model_api_id = base_app.model_api_id; db.add(new_app); await db.commit()'
    )
    $changed++
}

$anchor = Find-P '任务创建后，前端根据标题、课程信息、大纲和解析资料组织提示词，再通过streamQA调用/ai_qa/qa/stream，并指定lesson_plan工作流。模型返回过程中，前端实时拼接教案内容；生成结束后，再调用/ai/teacher/lesson-plan/tasks/{id}/result写回结果、状态和完成时间。代码4-4展示LessonPlan.vue中的核心实现。'
if ($anchor -ne $null -and (Get-Text $anchor.NextSibling) -ne '代码4-4 智能教案任务创建与结果回写关键代码') {
    Insert-Paragraphs-After $anchor @(
        '代码4-4 智能教案任务创建与结果回写关键代码',
        'const task = await aiPortalApi.createLessonPlanTask({ title: planTitle.value.trim(), outline: syllabus.value, course_id: selectedCourseId.value })',
        'await streamQA(userId, assemblePrompt(), false, chunk => { planContent.value += chunk }, selectedModel.value, selectedCourseId.value, ''lesson_plan'')',
        'await aiPortalApi.updateLessonPlanTaskResult(task.id, { status: ''completed'', result: planContent.value })'
    )
    $changed++
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

Write-Output "Replanned chapters 3-5. Changed items: $changed"
Write-Output "Saved to: $srcDocx"

