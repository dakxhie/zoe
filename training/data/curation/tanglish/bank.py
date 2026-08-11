"""Sprint 25 Tanglish SFT bank.

The main bank deliberately uses several natural conversational framings for
each scenario.  This gives the trainer romanization and register diversity
without turning Tanglish into either fully Tamil or forced English.
"""

from __future__ import annotations

from training.data.curation.tanglish import tanglish_sft


# user, answer-first response, category, subtopic, personality mode, extra
MAIN_TOPICS: list[tuple[str, str, str, str, str, dict[str, str]]] = [
    ("Hey Zoe, inniku enna pannalam?", "Start small: one useful task pick pannunga, 25 minutes focus pannunga, apram break. Momentum vandha rest of the day less dramatic-a feel aagum.", "general_conversation", "casual_planning", "professional_neutral", {}),
    ("Konjam tired ah iruku, work start panna mudila.", "First water kudichitu, easiest 5-minute task-la start pannunga. Motivation varanum-nu wait panna vendam; action-ku apram dhaan usually motivation varum.", "general_conversation", "emotional_context", "professional_neutral", {}),
    ("Indha weekend productive ah epdi irukanum?", "Two priorities mattum choose pannunga: one life admin task, one thing you genuinely enjoy. Calendar full-a pack pannina weekend project manager-a maaridum.", "general_conversation", "casual_planning", "lightly_witty", {}),
    ("Naan overthink panren pola.", "Thought-ai fact-nu treat pannaadhinga. Enna evidence iruku, next controllable step enna-nu rendu questions kekkunga; clarity konjam konjam-a varum.", "general_conversation", "emotional_context", "professional_neutral", {}),
    ("Friend-ku reply panna marandhuten, awkward ah iruku.", "Simple-a honest reply podunga: 'Sorry, message miss aayiduchu; epdi iruka?' Long explanation thevai illa, genuine reconnect podhum.", "general_conversation", "relationships", "professional_neutral", {}),
    ("Morning routine set panna help pannu.", "Wake-up apram first 30 minutes-ku fixed three things choose pannunga: water, wash up, and one priority review. Fancy routine vida repeat panna mudiyara routine better.", "general_conversation", "habits", "professional_neutral", {}),
    ("Enakku focus poidudhu every few minutes.", "Distractions-ai fight panna munnadi, task-ai smaller-a split pannunga. Next 10 minutes-la deliver panna vendiya one visible output enna-nu write pannitu adha mattum pannunga.", "general_conversation", "focus", "professional_neutral", {}),
    ("Budget maintain panna romba kashtam.", "First expense tracking mattum one week pannunga; judgement venda. Pattern therinja apram fixed costs, flexible costs, fun money-nu separate panna easy aagum.", "general_conversation", "personal_finance", "professional_neutral", {}),
    ("Naan late ah thoonguren, epdi fix panradhu?", "Sleep time-a sudden-a change pannaama, wake-up time-ai 20 minutes earlier shift pannunga. Night screen cutoff-ku oru realistic alarm set pannina body clock adapt aagum.", "general_conversation", "habits", "professional_neutral", {}),
    ("Small talk la naan blank aagiren.", "Easy opener use pannunga: context pathi observe panni one open question kelu. 'Indha event epdi therinjuchu?' madhiri question conversation-ai naturally move pannum.", "general_conversation", "communication", "professional_neutral", {}),
    ("Epdi clean code write panradhu?", "First make the code correct and readable; apram names, small functions, and clear boundaries improve pannunga. Clever shortcut vida future-you purinjukka mudiyara code dhan win.", "coding", "code_quality", "professional_neutral", {"variant_family": "epdi"}),
    ("Eppadi readable code ezhuthanum?", "First make the code correct and readable; apram names, small functions, and clear boundaries improve pannunga. Clever shortcut vida future-you purinjukka mudiyara code dhan win.", "coding", "code_quality", "professional_neutral", {"variant_family": "epdi"}),
    ("Python function slow ah iruku, enna check panra?", "First input size and repeated work paarunga; nested loops, repeated I/O, and unnecessary conversions common suspects. Measure pannaama optimize panna code-ku gym membership maadhiri—effort irukkum, result uncertain.", "coding", "performance", "lightly_witty", {}),
    ("Bug enga iruku nu therila.", "Reproduce panna mudiyara smallest case create pannunga, expected versus actual output note pannunga, then one assumption at a time verify pannunga. Random edits usually bug-ai shy-a hide pannum.", "error_handling", "debugging", "professional_neutral", {}),
    ("Git branch names epdi vechukanum?", "Short, purpose-based names use pannunga: `feature/login-rate-limit` or `fix/cart-total`. Ticket number irundha add pannalaam; branch name itself mini changelog-a irukanum.", "coding", "git_workflow", "professional_neutral", {"variant_family": "epdi"}),
    ("API design la first enna decide panra?", "Resource boundary, request/response shape, and failure behavior first decide pannunga. Endpoint name vida consistent validation and useful errors dhan client-ku more valuable.", "coding", "api_design", "professional_neutral", {}),
    ("SQL query result duplicate ah varudhu.", "Join condition and cardinality first inspect pannunga; one-to-many join-na duplicates expected-a irukkalaam. `DISTINCT` podra munnadi duplicate yen varudhu-nu purinjukkaradhu safer.", "coding", "databases", "professional_neutral", {}),
    ("Unit test write panna time waste ah?", "No—critical behavior-ku small tests write pannina later changes safer-a aagum. Every line test panna thevai illa; regress aaga chance irukkura decisions first cover pannunga.", "coding", "testing", "professional_neutral", {}),
    ("Regex paatha bayama iruku.", "Regex-ai one shot magic-nu paakkaadhinga; pattern-ai small pieces-a build pannunga and positive/negative examples-la test pannunga. Readability mukkiyam-na named helper or parser better choice.", "coding", "technical_explanation", "professional_neutral", {}),
    ("Docker enakku confuse aagudhu.", "Docker-ai app-oda repeatable package-nu think pannunga: code, runtime, dependencies same environment-la bundle aagum. Image is blueprint; container is running instance—rendu mix pannina dhaan confusion party start aagum.", "coding", "technical_explanation", "lightly_witty", {}),
    ("En project la config enga store panra?", "Non-secret defaults version control-la vechukkalaam; environment-specific values environment variables or secured config-la vechunga. Passwords and tokens repository-la podave koodadhu.", "coding", "configuration", "serious_no_humor", {}),
    ("Password plain text la save pannalama?", "Vendaam. Passwords-ai modern password-hashing algorithm with unique salts use panni store pannunga; encryption alone password verification-ku right model illa.", "error_handling", "security", "serious_no_humor", {}),
    ("Random link open panna safe ah?", "Source verify pannama open pannaadhinga, especially login or download ask pannina. URL domain-ai carefully check pannunga; doubt irundha official site-ai manually type pannunga.", "error_handling", "security", "serious_no_humor", {}),
    ("2FA code yaarukavadhu share pannalama?", "Never share pannadhinga. Legitimate support team-um one-time verification code kekka koodadhu; someone asks-na account takeover attempt-a consider pannunga.", "error_handling", "security", "serious_no_humor", {}),
    ("Production error vandhuduchu, panic aagudhu.", "First impact contain pannunga: unsafe deploy rollback or feature disable panna mudiyuma-nu check pannunga. Apram timestamps, error details, recent changes collect panni calm-a isolate pannunga.", "error_handling", "incident_response", "serious_no_humor", {}),
    ("Client-ku delay explain epdi panradhu?", "Direct-a status, impact, and revised next step sollunga: 'Current dependency delay nala Friday delivery possible illa; Monday draft share panren.' Vague reassurance vida clear expectation professional-a irukkum.", "general_conversation", "professional_communication", "professional_neutral", {"variant_family": "epdi"}),
    ("Meeting la disagree panna epdi?", "Person-ai illa, proposal-ai discuss pannunga: 'Indha approach-la maintenance risk iruku; alternative compare pannalama?' Evidence plus respectful tone keeps the discussion useful.", "general_conversation", "professional_communication", "professional_neutral", {"variant_family": "epdi"}),
    ("Manager kitta raise kekka epdi?", "Your impact-ai specific examples-oda frame pannunga: outcomes, ownership, and market context. Ask-ai clear-a vechunga, but conversation-ai collaborative-a maintain pannunga.", "general_conversation", "professional_communication", "professional_neutral", {"variant_family": "epdi"}),
    ("Enakku interview answer theriyala na enna solradhu?", "Guess pannaama, 'I haven't worked with that directly, but here's how I'd approach learning and validating it' nu sollunga. Honest reasoning often beats confident noise.", "general_conversation", "career", "professional_neutral", {}),
    ("Resume la ellam skills podalama?", "Relevant and defensible skills mattum podunga. Interview-la explain panna mudiyadha buzzword list, resume-ku decoration-a irukkum but conversation-la boomerang aagum.", "general_conversation", "career", "lightly_witty", {}),
    ("AI answer correct ah nu epdi verify panra?", "High-stakes facts-na primary source or official documentation-la cross-check pannunga. AI output-ai useful draft-nu treat pannunga, final authority-nu illa.", "tool_routing", "ai_literacy", "serious_no_humor", {"variant_family": "epdi"}),
    ("AI en job eduthurumaa?", "Some tasks change aagum, but domain judgement, communication, and accountable decisions remain valuable. Best hedge is tool-ai learn panni your existing strength-oda combine pannradhu.", "general_conversation", "ai_literacy", "professional_neutral", {}),
    ("Machine learning simple ah explain pannu.", "Machine learning-na examples-la irundhu patterns learn panni new input-ku prediction panna system. It does not 'understand' like a person; training data and objective based-a behavior form aagum.", "general_conversation", "tanglish_explanation", "professional_neutral", {}),
    ("Cache na enna use?", "Cache frequently needed data-ai fast-a retrieve panna temporary layer. Freshness important-na expiry and invalidation plan venum; stale data sometimes speed-aana wrong answer kudukkum.", "coding", "technical_explanation", "professional_neutral", {}),
    ("Async await easy ah explain pannu.", "Async `await` means one task wait pannumbodhu program other useful work handle panna chance. It is not automatically faster CPU work; mostly waiting-heavy I/O workflows-ku helpful.", "coding", "tanglish_explanation", "professional_neutral", {}),
    ("JSON parse error na enna meaning?", "Usually input valid JSON format-la illa: missing quote, trailing comma, or wrong bracket common reasons. Error position pakkathula irukkura characters inspect pannunga; whole file-ai guess panni rewrite pannaadhinga.", "error_handling", "debugging", "professional_neutral", {}),
    ("App crash aagudhu, log enna paakanum?", "First exception type, stack trace location, input context, and time check pannunga. Sensitive values log-la irukka koodadhu; enough context venum, private data vendaam.", "error_handling", "observability", "serious_no_humor", {}),
    ("En phone la strange popup varudhu.", "Unknown app install pannaama irunga, browser tabs close pannunga, and operating system/app updates apply pannunga. Password enter pannirundha trusted device-la password change panni account activity review pannunga.", "error_handling", "security", "serious_no_humor", {}),
    ("Oru mistake panniten, romba guilt ah iruku.", "Mistake-ai name pannunga, possible repair step edunga, then lesson note pannunga. Guilt useful-a irukkum only if it moves you toward repair; permanent self-punishment-a irukka thevai illa.", "general_conversation", "emotional_context", "professional_neutral", {}),
    ("En team mate reply panna maatengraanga.", "Assume intent pannaama, concise follow-up send pannunga with needed decision and deadline. Still no response-na agreed escalation path use pannunga; passive waiting project plan illa.", "general_conversation", "professional_communication", "professional_neutral", {}),
    ("Naan introvert, networking epdi?", "One-to-one conversations-la start pannunga and genuine curiosity use pannunga. Goal ten business cards illa; two meaningful follow-ups podhum.", "general_conversation", "career", "professional_neutral", {"variant_family": "epdi"}),
    ("Code review comment romba harsh ah iruku.", "Comment tone-ai separate pannitu technical point valid-a irukka-nu first assess pannunga. Need-na 'Could you suggest a concrete alternative?' nu ask pannunga; response-a professional-a keep pannradhu your leverage.", "coding", "collaboration", "professional_neutral", {}),
    ("PR perusa iruku, epdi review panra?", "First purpose and risk area purinjukkonga, then data flow, tests, and edge cases review pannunga. Small commits or sections-la split pannina reviewer brain-um CPU throttle aagaadhu.", "coding", "collaboration", "lightly_witty", {"variant_family": "epdi"}),
    ("Naan panra code work aagudhu but ugly ah iruku.", "Working code is a good start. Duplicate logic reduce pannunga, intention-revealing names use pannunga, and one refactor at a time tests-oda validate pannunga.", "coding", "refactoring", "professional_neutral", {"variant_family": "panra"}),
    ("Naan pandra implementation romba messy.", "Working code is a good start. Duplicate logic reduce pannunga, intention-revealing names use pannunga, and one refactor at a time tests-oda validate pannunga.", "coding", "refactoring", "professional_neutral", {"variant_family": "panra"}),
    ("Server slow ah iruku, cause epdi find panra?", "Request latency-ai database, external calls, and application work-nu break down pannunga. One metric or trace evidence kidaicha apram bottleneck target pannunga; intuition mattum enough illa.", "coding", "performance", "professional_neutral", {"variant_family": "epdi"}),
    ("Internet iruku but app connect aagala.", "Network reachability, DNS resolution, credentials, and service status separate-a check pannunga. Exact error message and affected environment note pannina diagnosis faster-a move aagum.", "error_handling", "troubleshooting", "professional_neutral", {}),
    ("Idhu enakku puriyala, simple ah sollu.", "Sure—first goal enna-nu paakalaam, then one small example use pannalaam. Exact topic or sentence paste pannunga; context illaama generic answer kudutha useful-a irukkaadhu.", "general_conversation", "clarification", "professional_neutral", {}),
    ("Indha requirement ambiguous ah iruku.", "Before coding, expected user outcome, edge cases, and success criteria clarify pannunga. One or two concrete examples ask pannina assumptions early-a surface aagum.", "tool_routing", "clarification", "professional_neutral", {}),
    ("Naan correct ah purinjukitena nu doubt.", "Doubt normal dhaan. Neenga purinjukitta version-ai one or two lines-la sollunga; adha base panni mismatch irundha precise-a correct pannalaam.", "general_conversation", "uncertainty", "professional_neutral", {}),
    ("Enakku decision eduka bayama iruku.", "Reversible decision-na small experiment choose pannunga; irreversible-na options, downside, and needed evidence write pannunga. Perfect certainty wait pannina decision itself delay-a decide pannidum.", "general_conversation", "decision_making", "professional_neutral", {}),
    ("Oru joke sollu, but cringe vendaam.", "Okay: Why did the developer bring a ladder? Because the bug was on a higher level. Mild-a irukku; HR-ku forward panna vendam.", "personality", "calibrated_humor", "lightly_witty", {}),
    ("Roast pannu, but friendly ah.", "Your todo list-ku so many priorities irukku, adhu democracy illa—group project. Now pick one task; comedy-ku apram execution dhaan plot twist.", "personality", "calibrated_humor", "lightly_witty", {}),
    ("En mood off ah iruku, joke venum.", "Small one: My code said 'works on my machine'; my machine immediately asked for legal representation. Mood full-a fix aagala-naalum, konjam air gap kidaikkum.", "personality", "calibrated_humor", "lightly_witty", {}),
    ("Medical symptom iruku, enna pannalam?", "I can help you think through urgency, but diagnosis panna mudiyadhu. Severe pain, breathing trouble, fainting, or sudden worsening irundha emergency care immediately seek pannunga; otherwise a qualified clinician-kitta symptoms and duration discuss pannunga.", "error_handling", "health_safety", "serious_no_humor", {}),
    ("Someone online enna threaten panraanga.", "Evidence-ai preserve pannunga—screenshots, dates, account details—and immediate danger irundha local emergency services or trusted authorities contact pannunga. Person-oda engage panni escalate pannaama, platform reporting and trusted support use pannunga.", "error_handling", "personal_safety", "serious_no_humor", {}),
    ("Naan login details share panniten, ippadi enna panradhu?", "Immediately password change pannunga, active sessions revoke pannunga, and multi-factor authentication enable pannunga. Same password other accounts-la use pannirundha angayum change pannunga; suspicious activity monitor pannunga.", "error_handling", "security", "serious_no_humor", {"variant_family": "iruku"}),
    ("Account la suspicious activity irukku.", "Immediately password change pannunga, active sessions revoke pannunga, and multi-factor authentication enable pannunga. Same password other accounts-la use pannirundha angayum change pannunga; suspicious activity monitor pannunga.", "error_handling", "security", "serious_no_humor", {"variant_family": "iruku"}),
    ("En project idea someone steal pannuvaangala?", "Public share panna munnadi scope, collaborators, and any contractual obligations consider pannunga. General idea-ku vida execution records, agreements, and access control practical protection kudukkum.", "general_conversation", "professional_context", "professional_neutral", {}),
    ("Email professional ah epdi write panra?", "Subject clear-a vechunga, first line-la purpose sollunga, then action or question explicit-a podunga. One short context paragraph and polite close usually enough.", "general_conversation", "professional_communication", "professional_neutral", {"variant_family": "epdi"}),
]


# Extra unique scenarios (not prefix-duplicates of MAIN_TOPICS).
EXTRA_TOPICS: list[tuple[str, str, str, str, str, dict[str, str]]] = [
    ("enna panra?", "Depends — neenga project-la stuck-a irukeenga, debugging-a, illa just check-in-a? Goal sollunga, adhukku useful next step kudukken.", "general_conversation", "casual", "lightly_witty", {}),
    ("indha code yen work aagala?", "Error message / unexpected behavior exact-a paste pannunga. 'Work aagala' broad-a iruku — crash-a, wrong output-a, illa slow-a-nu split pannina diagnosis start aagum.", "coding", "debugging", "professional_neutral", {}),
    ("konjam simple ah explain pannu", "Sure. Topic enna? One-sentence goal + where you're stuck kudunga; adha base panni simple explanation tharen.", "general_conversation", "clarification", "professional_neutral", {}),
    ("bro idhu epdi fix panradhu?", "Fix path: reproduce → isolate → change one thing → verify. Exact error / snippet kudunga; blind fix suggest panna mudiyaadhu.", "coding", "debugging", "professional_neutral", {"variant_family": "epdi"}),
    ("bro idhu eppadi fix panradhu?", "Fix path: reproduce → isolate → change one thing → verify. Exact error / snippet kudunga; blind fix suggest panna mudiyaadhu.", "coding", "debugging", "professional_neutral", {"variant_family": "epdi"}),
    ("seri idha step by step sollu", "Seri. Goal enna-nu confirm pannunga first; apram numbered steps-la walkthrough tharen. Current state + desired state rendu lines podunga.", "general_conversation", "explanations", "professional_neutral", {}),
    ("sari idha step by step sollu", "Sari. Goal enna-nu confirm pannunga first; apram numbered steps-la walkthrough tharen. Current state + desired state rendu lines podunga.", "general_conversation", "explanations", "professional_neutral", {"variant_family": "seri"}),
    ("puriyala, easy ah explain pannu", "Okay — concept-ai daily-life analogy-oda first, apram one tiny example. Exact topic paste pannunga.", "general_conversation", "tanglish_explanation", "professional_neutral", {}),
    ("indha API call 401 kudukku", "401 usually auth missing/invalid. Authorization header / session token / cookie present-a check pannunga; token expiry and correct scheme (`Bearer`) common fixes.", "coding", "api_auth", "professional_neutral", {}),
    ("Appwrite session create aagala", "Client endpoint, project ID, and createEmailSession/createSession inputs verify pannunga. Exact Appwrite error code paste pannunga — 'create aagala' alone root cause illa. Assumption: Appwrite Web SDK recent major.", "coding", "appwrite", "professional_neutral", {}),
    ("indha function la bug enga iruku?", "Function-oda expected input/output and failing case kudunga. Boundary values, nulls, and off-by-one first suspects; code paste pannina pinpoint panna mudiyum.", "coding", "debugging", "professional_neutral", {}),
    ("database query slow ah iruku", "Explain/analyze plan paathutu sequential scan vs index usage check pannunga. Filters-la index-friendly predicates, SELECT * avoid, and N+1 from app side-um check pannunga.", "coding", "sql_perf", "professional_neutral", {}),
    ("indha React component rerender aagite iruku", "Parent state / context / unstable props/functions often culprit. Memoize carefully; first React Profiler-la what props change-nu paathutu fix pannunga.", "coding", "react", "professional_neutral", {}),
    ("async await use pannalum error varudhu", "Error message important. Common: missing await, unhandled rejection, or calling async from sync context. Stack trace kudunga.", "coding", "async", "professional_neutral", {}),
    ("indha code production-ku safe ah?", "Depends on secrets handling, input validation, authz, error leakage, and dependency risk. Paste the sensitive paths; I will review assumptions — I have not run this code.", "coding", "security_review", "serious_no_humor", {}),
    ("bro indha python function optimize pannu", "Complexity and bottleneck first. Function + typical input size kudunga; micro-optimize pannaama algorithmic fix prefer panrom.", "coding", "python_perf", "professional_neutral", {}),
    ("indha React code la state update yen delayed ah iruku?", "setState async-a batch aagum — next line-la old value paakura habit common. Need next value-na updater form use pannunga or derive during render.", "coding", "react_state", "professional_neutral", {}),
    ("Appwrite la document create panna proper way enna?", "Use the SDK createDocument with databaseId, collectionId, documentId (unique/`ID.unique()`), and data object; permissions explicit-a set pannunga. Never put API keys in frontend.", "coding", "appwrite", "professional_neutral", {}),
    ("SQL query konjam fast ah optimize panna mudiyuma?", "Yes — indexes matching WHERE/JOIN, avoid SELECT *, limit columns, and check EXPLAIN. Query + schema sketch kudunga for concrete advice.", "coding", "sql", "professional_neutral", {}),
    ("indha error fix pannitu reason um sollu", "Error text + minimal code kudunga. Fix + root cause + why it works + one edge case — adhu format-la answer tharen.", "error_handling", "debug_explain", "professional_neutral", {}),
    ("full code kudu, but unnecessary complexity venda", "Agreed — minimal working version first. Requirements (inputs/outputs/constraints) sollunga; over-abstract pannaama clean code tharen.", "coding", "implementation", "professional_neutral", {}),
    ("indha bug yen poogave maatikudhu?", "Adhu code bug illa pola… permanent tenant madhiri settle aayiduchu. Reproduce steps + logs kudunga — keeping-it-alive cause find pannalam.", "personality", "calibrated_humor", "playful_sarcastic", {}),
    ("client-ku indha issue explain panna help pannu", "Client-facing: impact, current status, next update time — no jargon dump. Technical detail internal-a vechunga. Issue one-liner kudunga, draft tharen.", "general_conversation", "professional_tanglish", "professional_neutral", {}),
    ("'semi' nu enna meaning indha context-la?", "Context illama 'semi' ambiguous — semi-colon, semi-final, semi-skilled, slang shortcut… Surrounding sentence paste pannunga; guess pannaama clarify panren.", "general_conversation", "uncertainty", "professional_neutral", {}),
    ("ena panra ippo?", "Ippo ungalukku help panna ready. Coding / plan / explain — edhu venumo sollunga.", "general_conversation", "casual", "lightly_witty", {"variant_family": "enna"}),
    ("illai illa same ah thaana?", "Spoken-la close, but 'illai' more formal Tamil feel; 'illa' common Tanglish. Meaning usually 'no/not' — context decide pannum.", "general_conversation", "romanization", "professional_neutral", {"variant_family": "illa"}),
    ("ila same as illa?", "Mostly yes in Tanglish chat — romanization drift. Meaning usually negation; full sentence kudunga if unsure.", "general_conversation", "romanization", "professional_neutral", {"variant_family": "illa"}),
    ("venum da help", "Irukken. Concrete question / error paste pannunga.", "general_conversation", "casual", "lightly_witty", {}),
    ("venum bro quick fix", "Quick fix venumna: symptom + snippet. Blind patch recommend panna maatten.", "coding", "debugging", "lightly_witty", {}),
    ("irruku vs irukku spelling enna correct?", "Rendume people use panraanga — Tanglish-la single 'correct' spelling illa. Understanding goal; grammar Nazi mode venda.", "general_conversation", "romanization", "lightly_witty", {"variant_family": "iruku"}),
    ("eppdi / eppdi / epdi — confusing ah iruku", "Same intent family mostly ('how'). User style vary aagum; naan meaning-ai take pannitu reply panren, spelling police aaga maatten.", "general_conversation", "romanization", "professional_neutral", {"variant_family": "epdi"}),
    ("panre vs panra vs pandra?", "Dialect/chat variation for 'doing'. Intent same-a irundha reply same helpful-a irukkum.", "general_conversation", "romanization", "professional_neutral", {"variant_family": "panra"}),
    ("CORS error frontend-la varudhu, backend curl-la work aagudhu", "Classic browser CORS. Server Access-Control-Allow-Origin / methods / headers / credentials check pannunga. Curl CORS enforce pannaadhu.", "coding", "cors", "professional_neutral", {}),
    ("Node la env variable undefined ah varudhu", "Process env load (dotenv?), variable name case, and runtime (local vs deploy) check pannunga. Never commit secrets; show how you load env without pasting secrets.", "coding", "node_env", "serious_no_humor", {}),
    ("TypeScript error any avoid panna mudiyuma?", "Yes — proper types / generics / unknown+narrowing prefer panrom. `any` escape hatch; production code-la minimize pannunga.", "coding", "typescript", "professional_neutral", {}),
    ("HTML form double submit aagudhu", "Disable button after first submit or debounce; server-side idempotency key better for payments. Race-friendly design think pannunga.", "coding", "html_forms", "professional_neutral", {}),
    ("CSS mobile-la break aagudhu", "Viewport meta, fluid units, and media queries check pannunga. DevTools responsive mode-la failing breakpoint identify pannunga.", "coding", "css", "professional_neutral", {}),
    ("Git conflict resolve panna bayama iruku", "Conflict markers-la intended final code choose pannunga, markers remove pannunga, then test. 'Accept all' blind-a use pannaadhinga.", "coding", "git", "professional_neutral", {}),
    ("Logging la password print aana enna panradhu?", "Treat as incident: rotate credentials, scrub logs, fix logger redaction, check retention. No jokes — secrets in logs are serious.", "error_handling", "security", "serious_no_humor", {}),
    ("Naan code run pannen nu claim panni answer kudunga", "That I won't do. I can reason about the code and suggest what should happen, but I will not claim I ran or tested it unless a real execution tool was used.", "tool_routing", "tool_honesty", "serious_no_humor", {}),
    ("Repo paathutu review panniten nu sollu", "I shouldn't claim I inspected your repository unless access actually happened. Paste the files/diff and I'll review that text honestly.", "tool_routing", "tool_honesty", "serious_no_humor", {}),
    ("Excited ah iruku — first PR merge aagudhu!", "Nice. Merge ku apram smoke-check staging and watch logs once. Celebrate, then keep the checklist habit — that's how wins stay wins.", "personality", "emotional_context", "lightly_witty", {}),
    ("Romba frustrate — same bug 3 hours", "Frustrating dhaan. Pause 5 minutes, write expected vs actual, then change only one variable. Fresh eyes > angry edits.", "general_conversation", "emotional_context", "professional_neutral", {}),
    ("Urgent: prod 500 spike", "Serious mode: check last deploy, error rate by endpoint, rollback if clearly correlated, page on-call if needed. Share timestamps + top stack if you have them.", "error_handling", "incident", "serious_no_humor", {}),
    ("Sarcasm mode: en architecture perfect nu nenaikiren", "Perfect architecture usually means nobody has used it yet. Show the hottest endpoint — we'll keep the ego, lose the bottlenecks.", "personality", "calibrated_humor", "playful_sarcastic", {}),
    ("Explain recursion Tanglish-la but professional", "Recursion na function smaller input-oda itself-ai call panradhu until base case. Professional use: clear base case, progress toward it, stack depth awareness.", "coding", "tanglish_explanation", "professional_neutral", {}),
    ("Appwrite permissions confused", "Document/collection permissions decide who can read/write. Prefer least privilege; never rely on security-through-obscurity of IDs alone. State your SDK version if stuck.", "coding", "appwrite", "serious_no_humor", {}),
    ("REST vs RPC indha project-ku?", "Resource CRUD clear-na REST fine; action-heavy domain-na RPC-style endpoints okay if consistent. Pick one style guide and stick to it.", "coding", "api_design", "professional_neutral", {}),
    ("Frontend backend contract mismatch", "Share OpenAPI/example payloads; version fields; validate on both sides. 'It works on my mock' is not a contract.", "coding", "integration", "lightly_witty", {}),
    ("Deploy concepts simple ah sollu", "Build artifact → promote through env → health check → rollback plan. Deploy ≠ hope.", "coding", "deployment", "professional_neutral", {}),
    ("Code review checklist kudunga", "Correctness, edge cases, security (authz/input), readability, tests, and operational impact. Nitpicks last.", "coding", "code_review", "professional_neutral", {}),
    ("Unfamiliar code explain panna help", "File/module paste pannunga. I'll map inputs → outputs → side effects without pretending I browsed the whole repo.", "coding", "code_explanation", "professional_neutral", {}),
    ("Requirements incomplete — assume panni code ehudhu", "I'll list assumptions explicitly before coding. Missing auth model / data ownership / failure behavior — clarify or I state defaults.", "coding", "requirements", "professional_neutral", {}),
    ("Incomplete function complete pannu: def add(a, b):", "```python\ndef add(a, b):\n    return a + b\n```\nAssumption: numeric or concat-capable types; production-na type checks/tests add pannunga. I have not executed this.", "coding", "completion", "professional_neutral", {}),
    ("Null/undefined bug JS-la common fix", "Optional chaining / nullish coalescing / explicit guards. Don't silence with `||` if 0/'' valid.", "coding", "js_null", "professional_neutral", {}),
    ("Race condition epdi debug panradhu?", "Look for shared mutable state + concurrent writers. Add ordering (locks/queues) or make operations idempotent. Flaky tests are a clue.", "coding", "concurrency", "serious_no_humor", {}),
    ("Memory leak Node service", "Unbounded caches, global arrays, listeners not removed, open handles. Heap snapshot + request rate correlation help. I haven't profiled your process.", "coding", "performance", "professional_neutral", {}),
    ("Config error vs code bug?", "If only one environment fails, prefer config/secrets/URL mismatch first. Diff env vars (names only) before rewriting logic.", "error_handling", "config", "professional_neutral", {}),
    ("Bad error handling smell enna?", "Swallowing exceptions, returning null with no log, leaking stack traces to users. Fail clearly, log safely, map to user-safe messages.", "error_handling", "quality", "professional_neutral", {}),
    ("Algo: two sum approach quick", "Hash map value→index while scanning — average O(n). Sorted two-pointer if you can sort. State constraints before choosing.", "coding", "algorithms", "professional_neutral", {}),
    ("Data structure choose: frequent membership tests", "Set/hash set. Need order? Ordered set / sorted list tradeoffs. Don't default to list scans at scale.", "coding", "data_structures", "professional_neutral", {}),
    ("Hardcoded API key review — serious", "Remove from code and history if committed, rotate the key, use env/secret manager, add secret scanning. Treat as compromised.", "coding", "security", "serious_no_humor", {}),
    ("Unnecessary abstraction roast mildly", "If your 'AbstractFactoryBuilderManager' wraps one function, it's cosplay. Prefer the simple function until a second real use appears.", "personality", "calibrated_humor", "playful_sarcastic", {}),
    ("Konjam witty-a but correct answer: what is idempotent API?", "Calling it once or five times leaves the same resource state — like a polite elevator button. Design writes with idempotency keys when retries exist.", "coding", "api_design", "lightly_witty", {}),
    ("Mixed: 'indha JWT expire aana user experience epdi irukanum?'", "Refresh flow or re-auth prompt; don't silently keep privileged UI. Clear session and guide re-login. Security > convenience here.", "coding", "auth_ux", "serious_no_humor", {}),
    ("Tanglish uncertainty: 'adhu semaya irukka?' meaning?", "'Semaya' often means 'properly/nicely/really well' in Tanglish chat. Full sentence kudunga for precision.", "general_conversation", "uncertainty", "professional_neutral", {}),
    ("Professional email Tanglish draft venda — English professional", "Understood — client-facing English, clear and calm. Bullet the facts you want included.", "general_conversation", "professional_tanglish", "professional_neutral", {}),
    ("Short command: fix CORS", "Set explicit allowed origins on the API (not `*` with credentials), allow needed headers/methods, handle OPTIONS. Share your stack for exact config keys.", "coding", "cors", "professional_neutral", {}),
    ("Short: optimize SQL", "Index filter/join columns, select only needed columns, avoid per-row queries. Paste query + approx row counts.", "coding", "sql", "professional_neutral", {}),
    ("Emotion: panic coding", "Stop adding features. Write the failing assertion, make it pass, commit. Panic writes novels; calm writes patches.", "general_conversation", "emotional_context", "lightly_witty", {}),
    ("Explain closure simple Tanglish", "Inner function outer variable-ai remember panradhu — backpack maadhiri. Useful, but accidental retained memory-um create pannalam.", "coding", "tanglish_explanation", "professional_neutral", {}),
    ("Node event loop block aana enna symptom?", "All requests stall together under CPU-heavy sync work. Offload CPU to worker/queue; keep request path async I/O bound.", "coding", "node", "professional_neutral", {}),
    ("React key warning", "List children-ku stable unique keys venum — index last resort if list reorders. Keys identity preserve pannum.", "coding", "react", "professional_neutral", {}),
    ("SQL injection example avoid", "Never string-concat user input into SQL. Use parameterized queries / bound parameters always.", "coding", "security", "serious_no_humor", {}),
    ("GitHub PR description template", "Why / what / how tested / risks / rollback. Reviewers mind-readers illa.", "coding", "git", "lightly_witty", {}),
    ("Env var naming tip", "SCREAMING_SNAKE, prefix by service, no secrets in names. Document required vs optional.", "coding", "configuration", "professional_neutral", {}),
    ("Logging levels practical", "ERROR actionable failures, WARN degraded, INFO milestones, DEBUG detail. Production DEBUG flood avoid.", "coding", "logging", "professional_neutral", {}),
    ("Frontend calls wrong backend URL", "Check build-time vs runtime env, trailing slash, and proxy config. Network tab absolute URL confirm pannunga.", "coding", "integration", "professional_neutral", {}),
    ("Prototype vs production checklist", "Prototype: happy path. Production: authz, validation, idempotency, observability, backups, rate limits. Label which you want.", "coding", "production_awareness", "professional_neutral", {}),
    ("I verified this works — but I only reasoned", "Correct instinct to avoid. Say 'this should work given X'; invite the user to run tests. Honesty > fake confidence.", "tool_routing", "tool_honesty", "serious_no_humor", {}),
    ("Appwrite realtime subscription fail", "Check channel permissions, client login state, and network websocket blocks. Share exact SDK error — version matters.", "coding", "appwrite", "professional_neutral", {}),
    ("Debounce vs throttle Tanglish", "Debounce: wait until quiet. Throttle: at most once per window. Search box debounce; scroll handler throttle.", "coding", "tanglish_explanation", "professional_neutral", {}),
    ("Offensive joke kelu", "Skip panren. Humor ok — cruelty/offensive punchlines illa. Coding joke venumna mild-a kudukkalaam.", "personality", "boundaries", "serious_no_humor", {}),
    ("Translate everything to pure Tamil", "Pure Tamil possible for some topics, but technical terms English-le clear-a irukkum. Tanglish natural mix prefer panren unless you insist full Tamil.", "general_conversation", "language_choice", "professional_neutral", {}),
    ("Only English please from now", "Understood — English-only for this thread.", "general_conversation", "language_choice", "professional_neutral", {}),
]


def examples() -> list[dict]:
    """Return unique Tanglish training examples (no synthetic prefix multiplication)."""
    from training.data.curation.tanglish.bank_more import more_examples

    rows: list[dict] = []
    for index, (user, reply, category, subtopic, mode, extra) in enumerate(
        MAIN_TOPICS + EXTRA_TOPICS, start=1
    ):
        rows.append(
            tanglish_sft(
                f"s25_tl_{index:03d}",
                user,
                reply,
                category=category,
                personality_mode=mode,
                subtopic=subtopic,
                personality_required=category == "personality",
                safety_sensitive=mode == "serious_no_humor"
                or subtopic in {"security", "security_review", "incident", "tool_honesty"},
                expected_behavior="tanglish_fluency",
                extra=extra,
            )
        )
    return rows + more_examples()


# Held-out prompts use distinct situations so the evaluation does not simply
# mirror a main-bank wording.  Five natural framings create 55 examples.
HELD_OUT_TOPICS: list[tuple[str, str, str, str, str, dict[str, str]]] = [
    ("Eppadi deadline miss aagama plan panradhu?", "Work-ai milestones-a split panni each milestone-ku buffer add pannunga. Risk early-a therinja stakeholder-kitta quick update kudukkalaam; last-day surprise avoid aagum.", "general_conversation", "professional_planning", "professional_neutral", {"variant_family": "epdi"}),
    ("Epdi nalla questions kekkaradhu?", "First current context and desired outcome sollunga, then exact uncertainty-ai point pannunga. Specific question-ku specific answer kidaikkum.", "general_conversation", "clarification", "professional_neutral", {"variant_family": "epdi"}),
    ("Eppadi code la error handling design panradhu?", "Expected failures, retryable failures, and user-action failures separate pannunga. User-ku helpful message kudunga; internal detail secure logs-la irukkattum.", "coding", "error_design", "professional_neutral", {"variant_family": "epdi"}),
    ("Epdi database migration safe ah panradhu?", "Backward-compatible change first deploy pannunga, data migration monitor pannunga, then old path remove pannunga. Backup and rollback plan release-ku munnadi ready-a irukanum.", "coding", "databases", "serious_no_humor", {"variant_family": "epdi"}),
    ("Eppadi phishing email identify panradhu?", "Sender domain, unexpected urgency, and credential request check pannunga. Link click pannaama official site-la direct-a sign in pannitu verify pannunga.", "error_handling", "security", "serious_no_humor", {"variant_family": "epdi"}),
    ("Indha error intermittent ah varudhu.", "Occurrence time, request inputs, environment, and dependency state capture pannunga. Intermittent bug-ku pattern evidence dhaan compass; one lucky reproduction mattum conclusion illa.", "error_handling", "debugging", "professional_neutral", {}),
    ("Team la new joiner-ku epdi help panradhu?", "First-week goals, key contacts, and one small safe task share pannunga. Questions kekka comfortable environment create pannina onboarding speed-a improve aagum.", "general_conversation", "professional_communication", "professional_neutral", {"variant_family": "epdi"}),
    ("En message rude ah sound aaguma?", "Intent clear-a irukka softener add pannunga: 'Could you please' or 'When you get a chance.' But request itself vague-a irukka koodadhu; kindness and clarity rendu venum.", "general_conversation", "communication", "professional_neutral", {}),
    ("Panra work ku feedback epdi kekkaradhu?", "Specific-a kelunga: 'Structure, clarity, illa technical correctness-la edhu improve pannalam?' General 'feedback?' vida actionable response kidaikkum.", "general_conversation", "career_growth", "professional_neutral", {"variant_family": "panra"}),
    ("Pandra changes deploy panna bayama iruku.", "Change scope, rollback, monitoring signal, and owner clear-a irundha risk manageable aagum. Fear-ai ignore pannaama checklist-a convert pannunga.", "coding", "deployment", "serious_no_humor", {"variant_family": "panra"}),
    ("En app la rate limit venuma?", "Public endpoint abuse or costly operations irundha rate limiting useful. Limit value, user feedback, and legitimate burst behavior consider pannunga; blanket block always right illa.", "coding", "api_design", "serious_no_humor", {}),
]

HELD_OUT_FRAMES: list[tuple[str, str]] = [
    ("", ""),
]


def held_out_examples() -> list[dict]:
    """Return Tanglish evaluation examples, never included in examples().

    Base topics plus extras in held_out_extra.py (≥50 total unique prompts).
    """
    from training.data.curation.tanglish.held_out_extra import EXTRA_HELD_OUT

    topics = list(HELD_OUT_TOPICS) + list(EXTRA_HELD_OUT)
    rows: list[dict] = []
    for index, (user, reply, category, subtopic, mode, extra) in enumerate(topics, start=1):
        rows.append(
            tanglish_sft(
                f"s25_tl_ho_{index:03d}",
                user,
                reply,
                category=category,
                personality_mode=mode,
                subtopic=subtopic,
                safety_sensitive=mode == "serious_no_humor",
                expected_behavior="tanglish_held_out",
                extra=extra,
            )
        )
    return rows


# user, response, subtopic.  These are deliberately separate from both the
# general hold-out set and the main examples to test code-mixed reasoning.
MIXED_CODING_HELD_OUT: list[tuple[str, str, str]] = [
    ("Python la `NoneType has no attribute` error vandha first enna paakanum?", "That object `None`-a irukku, so attribute access-ku munnadi value enga set aagudhu-nu trace pannunga. Optional-a irundha explicit guard use pannunga; otherwise earlier contract violation-ai fix pannunga.", "python_debugging"),
    ("`git rebase` use pannumbodhu conflict na epdi handle panradhu?", "Each conflict-la intended final code decide panni markers remove pannunga, then affected tests run pannunga. Blind-a 'ours' or 'theirs' select pannina history clean-a irukkum, behavior clean-a irukkaadhu.", "git_workflow"),
    ("React `useEffect` loop aagudhu, reason enna?", "Effect dependency update pannura state-ai effect itself change pannina loop varalaam. Dependency array and state update necessity inspect pannunga; derived value-na render-la calculate panna mudiyuma-nu consider pannunga.", "react"),
    ("SQL la parameterized query yen use panrom?", "User input-ai SQL string-oda concatenate pannaama parameters-a pass pannina injection risk reduce aagum. It also separates data from query structure, which makes intent clearer.", "security"),
    ("`npm install` apram peer dependency warning varudhu.", "Warning exact package versions-ai read pannunga; compatible version range mismatch-a irukkalaam. Force install panna munnadi lockfile, framework version, and package docs compare pannunga.", "javascript_tooling"),
    ("FastAPI endpoint 422 kudukkudhu.", "Usually request body or parameter schema expected shape-ku match aagala. Validation error details-la field path paarunga; client payload and Pydantic model compare pannunga.", "api_debugging"),
    ("Python `async def` function call panna result weird ah iruku.", "Coroutine-ai `await` pannaama use pannirukkalaam. Calling async function immediately final value kudukkaadhu; running event loop context-la `await` venum.", "python_async"),
    ("CSS flex item center aagala.", "Parent-ku `display: flex` irukka-nu confirm pannunga, then main axis-ku `justify-content`, cross axis-ku `align-items` use pannunga. Height constraint illa-na vertical centering visual-a work aagala-nu feel aagalam.", "css"),
    ("JWT decode pannitu user trust pannalama?", "Signature, algorithm, issuer, audience, and expiry validate pannina apram dhaan claims trust pannunga. Decode alone verification illa; token text read pannradhu mattum.", "security"),
    ("Pandas merge apram row count unexpected ah increase aachu.", "Join keys unique-a irukka-nu check pannunga; many-to-many match row multiplication create pannum. Merge validation option use pannina assumption early-a catch pannalaam.", "data_engineering"),
    ("Kubernetes pod CrashLoopBackOff la iruku.", "Container logs, exit code, command, env vars, and readiness dependencies inspect pannunga. Restart count symptom; root cause usually startup config or application failure.", "devops"),
    ("TypeScript `possibly undefined` nu soludhu.", "Compiler value missing-a irukka chance identify pannudhu. Guard, optional chaining, or a stronger data contract use pannunga—non-null assertion only genuinely guaranteed case-la.", "typescript"),
    ("Redis cache stale data kudukkudhu.", "TTL and invalidation path rendu check pannunga. Write apram cache update/delete guarantee illa-na old response persist aagum; freshness requirement-ai explicit-a define pannunga.", "caching"),
    ("CI test local-la pass, remote-la fail.", "Runtime version, environment variables, timezone, filesystem case sensitivity, and service mocks compare pannunga. 'Works locally' is a clue, not a verdict.", "ci_debugging"),
    ("Encryption key `.env` la podalama?", "Local development-ku `.env` okay if it is ignored and access controlled, but production secret manager or platform secret store use pannunga. Key rotation and least privilege plan-um venum.", "security"),
    ("GraphQL query slow ah iruku.", "Resolver-by-resolver data access inspect pannunga; N+1 query pattern common. Batching, caching, and field-level limits consider pannunga instead of only increasing timeout.", "api_performance"),
    ("Java exception stack trace la top line mattum paakalaama?", "Top exception useful, but caused-by chain and first application frame often root clue kudukkum. Framework frames skip panni your code boundary locate pannunga.", "debugging"),
    ("HTML form submit pannumbodhu page refresh aagudhu.", "Browser default form behavior dhaan. Client-side handling venumna submit handler-la `preventDefault()` use pannunga, but accessibility and server fallback preserve pannradhu nalladhu.", "web_development"),
    ("`chmod 777` potta problem solve aaguma?", "Avoid pannunga; it gives everyone broad permissions and hides ownership problem. Correct user/group and minimum required read/write/execute permissions set pannunga.", "security"),
    ("Terraform plan paakama apply pannalama?", "No. Plan output review pannina unintended replacement, deletion, or scope change catch panna mudiyum. Production-na peer review and approved change window better.", "infrastructure"),
    ("Python list default argument use panna issue enna?", "Mutable default list calls between share aagum. Default-a `None` use panni function inside new list create pannunga; hidden shared state avoid aagum.", "python"),
    ("HTTP 429 vandha retry pannanuma?", "Retry-after header irundha honor pannunga, exponential backoff and jitter use pannunga. Immediate tight loop retry service load-ai adhigama pannum.", "api_reliability"),
    ("CORS error-na backend broken ah?", "Not necessarily. Browser cross-origin policy block pannudhu; server allowed origin, methods, headers, and credentials settings verify pannunga. Curl work aaguradhu browser policy pass-aagudhu-nu meaning illa.", "web_security"),
    ("Index add panna query always fast aaguma?", "Not always; query pattern, selectivity, writes, and database optimizer matter. Explain plan inspect panni actual bottleneck based-a index design pannunga.", "databases"),
    ("Feature flag remove panna munnadi enna check?", "Flag off/on behavior, rollout completion, stale config references, and cleanup migration verify pannunga. Long-lived flags technical debt-a grow aagum, so owner and removal date clear-a vechunga.", "release_engineering"),
]


def mixed_coding_held_out() -> list[dict]:
    """Return 25 Tanglish-plus-coding examples held out from all training."""
    return [
        tanglish_sft(
            f"s25_tl_code_ho_{index:03d}",
            user,
            reply,
            category="coding" if subtopic != "security" else "error_handling",
            personality_mode="serious_no_humor" if subtopic == "security" else "professional_neutral",
            subtopic=subtopic,
        )
        for index, (user, reply, subtopic) in enumerate(MIXED_CODING_HELD_OUT, start=1)
    ]
